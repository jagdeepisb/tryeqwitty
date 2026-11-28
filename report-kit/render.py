"""Offline open-methodology report renderer. Distinct from the hosted Eqwitty platform renderer."""
import argparse
import csv
import html
from html.parser import HTMLParser
import json
import pathlib
import re
from decimal import Decimal, localcontext
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
HEADINGS = ["Executive assessment","Scope and input inventory","Business and product","Team","Market and competition","Independent thesis and reconciliation","Financial analysis and calculations","Material factors and evidence coverage","Risks and safeguards","Valuation and sensitivity","Management questions","Methodology and limitations"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
LABEL = "Independent assessment: Eqwitty open methodology (not an official Eqwitty platform report)"

def validate(report):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
    if isinstance(report, dict) and report.get("version") == "1.3":
        version_13_schema(report, schema)
    else:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(report)
    if [s["heading"] for s in report["sections"]] != HEADINGS:
        raise ValueError("Sections must appear once in the declared order")
    ids = {s["id"] for s in report["sources"]}
    if len(ids) != len(report["sources"]):
        raise ValueError("Duplicate source identifiers")
    for section in report["sections"]:
        if not set(section["source_ids"]) <= ids:
            raise ValueError("Unknown source identifier")
    if report["version"] == "1.3":
        validate_structured(report, ids)
    for s in report["sources"]:
        if s["url"] is not None:
            u = urlsplit(s["url"])
            if u.scheme not in ("https", "http") or not u.hostname or u.username or u.password or any(ord(c) < 32 for c in s["url"]):
                raise ValueError("Source URL must be HTTP(S) without embedded credentials")
    if not report["missing_information"]:
        # Empty is allowed only when explicitly explained in the limitations section.
        if not any("no material gaps" in p.lower() for p in report["sections"][-1]["paragraphs"]):
            raise ValueError("List missing information or explicitly justify no material gaps")
    return report

def esc(s):
    return html.escape(str(s), quote=True)


# Publication transforms only the presentation, never the frozen report JSON.
# Source URLs, identifiers, numeric attributes and original evidence are preserved.
class PublicationHTML(HTMLParser):
    """Normalise visible punctuation and link every inline source reference."""

    def __init__(self, report):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.sources = {row["id"]: row for row in report["sources"]}
        self.prefix = "source-" if report["version"] == "1.3" else ""
        self.gaps = {row["id"]: row for row in report.get("missing_information", []) if "id" in row}
        ids = sorted(self.sources.keys() | self.gaps.keys(), key=lambda item: (-len(item), item))
        self.pattern = re.compile(r"(?<![\w-])(?:" + "|".join(map(re.escape, ids)) +
                                  r")(?![\w-])") if ids else None
        self.anchor = False
        self.raw = False
        self.visible = []

    def handle_decl(self, decl):
        self.parts.append("<!" + decl + ">")

    def handle_starttag(self, tag, attrs):
        original = self.get_starttag_text()
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            prefix = "#" + self.prefix
            ref = href[len(prefix):] if href.startswith(prefix) else None
            if ref in self.sources and "title" not in dict(attrs):
                source = self.sources[ref]
                description = " | ".join(filter(None, (source.get("publisher"), source["title"], source["locator"]))).replace("\u2014", " - ")
                original = original[:-1] + f' title="{esc(description)}">'
            self.anchor = True
        self.parts.append(original)
        if tag in {"style", "script"}:
            self.raw = True

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append("</" + tag + ">")
        if tag == "a":
            self.anchor = False
        if tag in {"style", "script"}:
            self.raw = False

    def handle_comment(self, data):
        self.parts.append("<!--" + data + "-->")

    def handle_data(self, data):
        if self.raw:
            self.parts.append(data)
            return
        # Keep the original extracts in the analytical record. Normalise only
        # the display copy, including Unicode and HTML-encoded em dashes.
        data = re.sub(r"[ \t]*\u2014[ \t]*", " - ", data)
        self.visible.append(data)
        if self.anchor or not self.pattern:
            self.parts.append(esc(data))
            return
        start = 0
        for match in self.pattern.finditer(data):
            self.parts.append(esc(data[start:match.start()]))
            ref = match.group()
            if ref in self.sources:
                source = self.sources[ref]
                description = " | ".join(filter(None, (source.get("publisher"), source["title"], source["locator"])))
                target = self.prefix + ref
            else:
                description = self.gaps[ref]["item"]
                target = "gap-" + ref
            description = description.replace("\u2014", " - ")
            self.parts.append(f'<a href="#{esc(target)}" title="{esc(description)}">{esc(ref)}</a>')
            start = match.end()
        self.parts.append(esc(data[start:]))


def publication_html(markup, report):
    parser = PublicationHTML(report)
    parser.feed(markup)
    parser.close()
    visible = " ".join(parser.visible)
    forbidden = r"\b(?:fallback export|palette with Lato substitute|Lato substitut(?:e|ion)|pinned release commit|standard commit|renderer version|bundle SHA-256|tool call unsuccessful)\b"
    if "\u2014" in visible or re.search(forbidden, visible, re.IGNORECASE):
        raise ValueError("Reader-facing editorial check failed; rewrite implementation language or em dashes without hiding material limitations")
    return "".join(parser.parts)


def reader_paragraphs(section):
    # Legacy bridge emits this exact provenance paragraph. The original JSON
    # still contains it; do not remove other limitations or research findings.
    for paragraph in section["paragraphs"]:
        provenance = re.fullmatch(r"(Open standard v[^;]+); source commit [0-9a-f]{40}; bundle SHA-256 [0-9a-f]{64}", paragraph)
        yield provenance.group(1) if provenance else paragraph


CSS = """
@page { size: A4; margin: 18mm 17mm 20mm;
  @bottom-left { content: 'eqwitty. | Open methodology'; font: 8pt 'DM Sans'; color: #666666; }
  @bottom-right { content: counter(page) ' / ' counter(pages); font: 8pt 'Space Grotesk'; color: #666666; }
}
body { font: 10pt/1.5 'DM Sans'; color: #111111; background: #FFFFFF; overflow-wrap: anywhere; }
h1,h2,h3 { font-family: 'Space Grotesk'; break-after: avoid; }
h1 { font-size: 23pt; margin: 14pt 0 6pt; } h2 { font-size: 15pt; margin-top: 20pt; border-bottom: 0.5pt solid #E5E5E5; padding-bottom: 5pt; }
h3 { font-size: 11pt; margin-bottom: 4pt; }
header { border-bottom: 2pt solid #3B82F6; padding-bottom: 12pt; margin-bottom: 20pt; }
.brand { font: bold 20pt 'Space Grotesk'; } .dot, a { color: #3B82F6; }
.notice,.gap { background: #F5F5F5; padding: 9pt; margin: 8pt 0; }
.notice,.muted { color: #666666; } p { orphans: 3; widows: 3; }
a { text-decoration: underline; overflow-wrap: anywhere; }
.gap { break-inside: avoid; } .gap p { margin: 3pt 0; }
.source { break-inside: avoid; margin-bottom: 8pt; }
"""

def report_html(report, *, include_operands=True, brief=False):
    validate(report)
    if brief and report["version"] != "1.3":
        raise ValueError("Decision briefs require structured report v1.3")
    if report["version"] == "1.3":
        return publication_html(structured_html(report, include_operands, brief=brief), report)
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Independent company assessment</title><style>', CSS, '</style></head><body>',
        '<header><div class="brand">eqwitty<span class="dot">.</span></div><h1>', esc(report["company"]), '</h1><p>', esc(report["objective"]), '</p><p class="muted">As of ', esc(report["as_of"]), '</p><p class="notice">', esc(LABEL), '</p></header>']
    for section in report["sections"]:
        parts += ['<section><h2>', esc(section["heading"]), '</h2>']
        parts += ["<p>"+esc(p)+"</p>" for p in reader_paragraphs(section)]
        if section["source_ids"]:
            parts += ['<p class="muted">Sources: ', ", ".join('<a href="#'+esc(s)+'">'+esc(s)+'</a>' for s in section["source_ids"]), '</p>']
        parts += ["</section>"]
    parts += ["<h2>Missing information</h2>"]
    for item in sorted(report["missing_information"], key=lambda x: PRIORITIES.index(x["priority"])):
        parts += ['<div class="gap"><h3>',esc(item["priority"]),": ",esc(item["item"]),"</h3>"]
        for key,label in [("period","Period / granularity"),("why","Why needed"),("conclusion","Conclusion affected"),("action","Reassessment action"),("availability","Availability")]:
            parts += ["<p><strong>",label,":</strong> ",esc(item[key]),"</p>"]
        parts += ["</div>"]
    if not report["missing_information"]:
        parts += ["<p>No material gaps listed; see methodology and limitations for justification.</p>"]
    parts += ["<h2>Sources</h2>"]
    for s in report["sources"]:
        parts += ['<div class="source" id="',esc(s["id"]),'"><strong>',esc(s["id"]),": ",esc(s["title"]),"</strong><p>",esc(s["type"])," · ",esc(s["locator"]),"</p>"]
        if s["url"]:
            parts += ['<a href="',esc(s["url"]),'">',esc(s["url"]),'</a>']
        parts += ["</div>"]
    if not report["sources"]:
        parts += ["<p>No sources recorded. Interpret findings accordingly.</p>"]
    parts += ["<p class='muted'>Informational analysis, not investment advice.</p></body></html>"]
    return publication_html("".join(parts), report)

def version_13_schema(report, legacy_schema):
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
    schema = json.loads((ROOT / "schema-v1.3.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource("schema.json", Resource(legacy_schema, DRAFT202012))
    Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).validate(report)


def validate_structured(report, sources):
    inputs = {row["id"] for row in report["operands"]}
    gaps = {row["id"] for row in report["missing_information"]}
    if len(inputs) != len(report["operands"]) or len(gaps) != len(report["missing_information"]):
        raise ValueError("Duplicate operand or missing-information ID")
    for operand in report["operands"]:
        if not set(operand["evidence_ids"]) <= sources:
            raise ValueError("Unknown operand source identifier")
    tables = [exhibit for section in report["sections"] for exhibit in section["tables"]]
    for exhibit in tables + report["schedules"]:
        columns = len(exhibit["headers"])
        for row in exhibit["rows"]:
            if len(row) != columns:
                raise ValueError("Exhibit row does not match headers")
            for cell in row:
                for key, known in (("source_ids", sources), ("input_ids", inputs), ("gap_ids", gaps)):
                    if not set(cell.get(key, [])) <= known:
                        raise ValueError(f"Unknown exhibit {key} reference")
                if cell.get("format") == "integer":
                    amount = Decimal(cell["value"])
                    if amount != amount.to_integral_value():
                        raise ValueError("Non-integer value in integer exhibit cell")
        for chart in exhibit.get("charts", []):
            if any(i >= columns for i in chart["columns"]):
                raise ValueError("Chart column is outside its exhibit")
            if any("text" not in row[0] or any("value" not in row[i] for i in chart["columns"])
                   for row in exhibit["rows"]):
                raise ValueError("Chart needs category labels and sourced numeric table cells")


def number_display(value, style):
    if style == "exact":
        return value
    precision = {"amount": 2, "ratio": 4, "percent": 4, "percentage_points": 4, "integer": 0}[style]
    with localcontext() as context:
        context.prec = 660
        amount = Decimal(value)
        if style in ("percent", "percentage_points"):
            amount *= 100
        result = format(amount, f",.{precision}f")
        if precision:
            result = result.rstrip("0").rstrip(".")
        if result in ("0", "-0"):
            result = f"{amount:.3E}" if amount else "0"
    return result + {"percent": "%", "percentage_points": " pp"}.get(style, "")


def source_links(ids):
    return ", ".join(f'<a href="#source-{esc(ref)}" aria-label="Evidence {esc(ref)}">{esc(ref)}</a>' for ref in ids)


def item_links(ids, name):
    return ", ".join(f'<a href="#{name}-{esc(ref)}">{esc(ref)}</a>' for ref in ids)


def cell_html(cell, header=False, input_links=True):
    tag = "th" if header else "td"
    scope = ' scope="row"' if header else ""
    classes = []
    if "value" in cell:
        value = cell["value"]
        classes.append("number")
        content = f'<span data-value="{esc(value)}">{esc(number_display(value, cell["format"]))}</span>'
    else:
        content = f'<span class="cell-text">{esc(cell["text"])}</span>'
    if cell.get("highlight"):
        classes.append("emphasis")
    if cell.get("note"):
        content += f'<span class="note">{esc(cell["note"])}</span>'
    references = []
    if cell.get("source_ids"):
        references.append(source_links(cell["source_ids"]))
    if cell.get("input_ids"):
        ids = item_links(cell["input_ids"], "input") if input_links else esc(", ".join(cell["input_ids"]))
        references.append(f"Inputs {ids}")
    if cell.get("gap_ids"):
        references.append(f'Gap {item_links(cell["gap_ids"], "gap")}')
    if references:
        content += f'<span class="cell-links">{" · ".join(references)}</span>'
    return f'<{tag}{scope} class="{" ".join(classes)}">{content}</{tag}>'


def chart_html(chart, exhibit):
    columns = chart["columns"]
    heights = [(row[0]["text"], exhibit["headers"][i], row[i]) for row in exhibit["rows"] for i in columns]
    values = [Decimal(item[2]["value"]) for item in heights]
    with localcontext() as context:
        context.prec = 660
        low, high = min(Decimal(0), *values), max(Decimal(0), *values)
        span = high - low or Decimal(1)
        zero = -low * 100 / span
        parts = [f'<figure class="chart" aria-hidden="true"><figcaption>{esc(chart["caption"])} · '
                 f'{esc(chart["unit"])}</figcaption>']
        for n, ((name, series, cell), value) in enumerate(zip(heights, values, strict=True)):
            left = (min(Decimal(0), value) - low) * 100 / span
            right = left + abs(value) * 100 / span
            label = name if len(columns) == 1 else f"{name} · {series}"
            color = "#244d85" if n % len(columns) else "#3b82f6"
            axis = (max(0, zero - Decimal("0.17")), min(100, zero + Decimal("0.17")))
            # A gradient works across flex layout in browsers and WeasyPrint.
            # The exact values and labels come from the underlying table.
            bars = (f"linear-gradient(90deg, transparent 0%, transparent {left:.6f}%, "
                    f"{color} {left:.6f}%, {color} {right:.6f}%, transparent {right:.6f}%, transparent 100%)")
            zero_line = (f"linear-gradient(90deg, transparent 0%, transparent {axis[0]:.6f}%, "
                         f"#7a8391 {axis[0]:.6f}%, #7a8391 {axis[1]:.6f}%, "
                         f"transparent {axis[1]:.6f}%, transparent 100%)")
            parts.append(
                f'<div class="chart-row"><span class="chart-key">{esc(label)}</span>'
                f'<span class="chart-plot" style="background-image:{zero_line},{bars}"></span>'
                f'<span class="chart-value">{esc(number_display(cell["value"], cell["format"]))}</span></div>'
            )
    return "".join(parts) + "</figure>"


def exhibit_html(exhibit, input_links=True):
    headers = exhibit["headers"]
    caption = esc(exhibit["caption"])
    if exhibit.get("note"):
        caption += f'<span class="note">{esc(exhibit["note"])}</span>'
    headings = "".join(f'<th scope="col">{esc(name)}</th>' for name in headers)
    rows = []
    for row in exhibit["rows"]:
        cells = "".join(cell_html(item, position == 0, input_links) for position, item in enumerate(row))
        rows.append(f"<tr>{cells}</tr>")
    charts = "".join(chart_html(chart, exhibit) for chart in exhibit.get("charts", []))
    grouped = " keep-together" if len(rows) <= 4 else ""
    evidence = " evidence-table" if headers[:2] in (["Claim", "Assessment"], ["Factor", "Assessment"]) else ""
    contents = "\n".join(rows)
    # Use a heading in print. The tagged PDF layout needs to keep it with the
    # first rows when a long table crosses a page boundary.
    return (f'<div class="table-wrap{grouped}"><h3 class="print-caption">{caption}</h3>'
            f'<table class="cols-{len(headers)}{evidence}"><caption>{caption}</caption>'
            f'<thead><tr>{headings}</tr></thead><tbody>{contents}</tbody></table></div>{charts}')


def gap_record(row):
    details = "".join(f'<p><strong>{heading}</strong> {esc(row[key])}</p>'
                      for key, heading in (("period", "Period"), ("why", "Why needed"), ("conclusion", "Conclusion affected"),
                                           ("action", "Reassessment action"), ("availability", "Availability")))
    return (f'<article class="record" id="gap-{esc(row["id"])}"><h3>{esc(row["id"])} · {esc(row["priority"])} · '
            f'{esc(row["item"])}</h3>{details}</article>')


def source_record(row):
    external = f'<p><a href="{esc(row["url"])}">Open source {esc(row["id"])} · {esc(row["title"])}</a></p>' if row["url"] else ""
    kind = row["type"].replace("_", " ")
    return (f'<article class="record" id="source-{esc(row["id"])}"><h3>{esc(row["id"])} · {esc(row["title"])}</h3>'
            f'<p class="detail">{esc(row["publisher"])} · {esc(kind)} · Grade {esc(row["grade"])} · '
            f'Accessed {esc(row["accessed"])}</p><p class="detail">{esc(row["locator"])}</p>'
            f'<p>{esc(row["extract"])}</p>{external}</article>')


def operands_html(operands):
    if not operands:
        return ""
    parts = ['<section><h2>Calculation operands</h2><div class="table-wrap"><table class="cols-4">'
             '<caption>Reported and assumed input record</caption><thead><tr><th scope="col">Input</th>'
             '<th scope="col">Value and unit</th><th scope="col">Period and basis</th>'
             '<th scope="col">Rationale and sources</th></tr></thead><tbody>']
    for row in operands:
        context = " · ".join(x for x in (row["entity"], row.get("accounting_basis"), row.get("quantity")) if x)
        value = f'{row["value"]} {row["currency"] or ""} {row["unit"].replace("_", " ")}'
        rationale = row["rationale"]
        if row.get("claim_ids"):
            rationale += "\nClaims " + ", ".join(row["claim_ids"])
        parts.append(f'<tr id="input-{esc(row["id"])}">'
                     f'{cell_html({"text": row["id"] + " · " + row["label"], "note": context}, header=True)}'
                     f'{cell_html({"text": value})}{cell_html({"text": row["period"], "note": row["basis"].capitalize()})}'
                     f'{cell_html({"text": rationale, "source_ids": row["evidence_ids"]})}</tr>')
    return "".join(parts) + "</tbody></table></div></section>"


def reader_exhibit(exhibit):
    """Use reader-friendly labels without altering figures or the report JSON."""
    caption = exhibit["caption"]
    view = {**exhibit}
    view["caption"] = re.sub(r"^RND([1-9][0-9]*) ", r"Financing round \1: ", caption)
    if caption in {"Financial and operating metrics", "Other valuation methods"}:
        rows = []
        for original in exhibit["rows"]:
            row = [dict(cell) for cell in original]
            row[0]["text"] = re.sub(r"^[MV][0-9]+ · ", "", row[0]["text"])
            if re.fullmatch(r"[a-z][a-z0-9_]*", row[0].get("note", "")):
                row[0].pop("note", None)
            row[2]["text"] = re.sub(r" · formula v[0-9.]+$", "", row[2]["text"])
            if row[2]["text"] == "Observed":
                row[2]["text"] = "Calculated from historical inputs"
            elif row[2]["text"] == "Assumed":
                row[2]["text"] = "Calculated from assumed inputs"
            rows.append(row)
        view["rows"] = rows
    return view


def reader_paragraph(paragraph, heading):
    if heading == "Executive assessment":
        paragraph = re.sub(r"^Qualified · ", "Decision subject to further evidence: ", paragraph)
    if paragraph == "Structured competitor comparison unavailable within this assessment.":
        return "The available records did not support a like-for-like competitor comparison."
    return paragraph


def structured_html(report, include_operands, *, brief=False):
    meta = report["methodology"]
    title = esc(report["company"])
    method = esc(meta["version"])
    css = (ROOT / "report-v1.3.css").read_text(encoding="utf-8")
    footer = f'@page {{ @bottom-left {{ content: "eqwitty. | Open methodology v{method}"; ' \
             'font: 8pt "DM Sans"; color: #555d69; } }'
    parts = [
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
        f'content="width=device-width, initial-scale=1"><title>{title} | Eqwitty assessment</title>'
        f'<style>{css}{footer}</style></head><body><a class="skip-link" href="#assessment">Skip to assessment</a>'
        f'<header class="hero"><div class="brand">eqwitty<span class="dot">.</span></div>'
        f'<h1>{title}</h1><p class="objective">{esc(report["objective"])}</p>'
        f'<div class="meta"><span>As of <time>{esc(report["as_of"])}</time></span>'
        f'<span>Methodology v{method}</span></div>'
        f'<p class="notice">{esc(LABEL)}</p></header><main id="assessment">'
    ]
    if brief:
        parts.append('<p class="notice">Decision brief. Read with the full assessment, which retains the detailed factor and research registers and cash schedules.</p>')
    seen = set()
    for section in report["sections"]:
        parts.append(f'<section><h2>{esc(section["heading"])}</h2>')
        section_seen = set()
        for paragraph in section["paragraphs"]:
            # Cross-section suppression in the brief is safe only when the
            # evidence context is identical. Never merge merely similar claims.
            identity = (paragraph, tuple(sorted(section["source_ids"])))
            if paragraph not in section_seen and (not brief or identity not in seen):
                display = reader_paragraph(paragraph, section["heading"])
                section_seen.add(paragraph)
                parts.append(f"<p>{esc(display)}</p>")
                seen.add(identity)
        if section["source_ids"]:
            parts.append(f'<p class="detail">Evidence {source_links(section["source_ids"])}</p>')
        for exhibit in section["tables"]:
            if brief and exhibit["caption"] == "Planned questions and recorded outcomes":
                continue
            if brief and exhibit["caption"] == "Material factors and evidence matrix":
                rows = [row for row in exhibit["rows"] if not (
                    row[1]["text"] == "Unknown" and row[0].get("note", "").lower() in {"medium priority", "low priority"})]
                omitted = len(exhibit["rows"]) - len(rows)
                if omitted:
                    parts.append(f"<p>{omitted} lower-priority unknown factors are detailed in the full assessment. Coverage counts include them.</p>")
                if not rows:
                    continue
                exhibit = {**exhibit, "rows": rows}
            exhibit = reader_exhibit(exhibit)
            parts.append(exhibit_html(exhibit, include_operands and not brief))
        if not (section["paragraphs"] or section["tables"]):
            parts.append("<p class=\"subtle\">Unavailable within assessed scope.</p>")
        parts.append("</section>")
    parts.append("<section><h2>Missing information</h2>")
    if report["missing_information"]:
        parts.extend(gap_record(row) for row in sorted(report["missing_information"], key=lambda g: PRIORITIES.index(g["priority"])))
    else:
        parts.append("<p>No material gaps listed within the assessed scope.</p>")
    parts.append("</section><section><h2>Sources</h2>")
    if report["sources"]:
        if any("\u2014" in row.get("extract", "") for row in report["sources"]):
            parts.append('<p class="detail">Source extracts are shown with normalised punctuation. Original wording is retained in the analytical record.</p>')
        parts.extend(source_record(row) for row in report["sources"])
    else:
        parts.append("<p>Source records unavailable.</p>")
    parts.append("</section>")
    if report["schedules"] and not brief:
        parts.append('<section class="appendix"><h2>Monthly cash schedules</h2>')
        parts.extend(exhibit_html(reader_exhibit(exhibit), include_operands) for exhibit in report["schedules"])
        parts.append("</section>")
    if include_operands and not brief:
        parts.append(operands_html(report["operands"]))
    elif report["operands"]:
        parts.append('<p class="detail">The complete calculation record is available separately.</p>')
    parts.append("</main></body></html>")
    return "\n".join(parts)


def pdf_bytes(report, *, brief=False):
    from weasyprint import CSS, HTML
    from weasyprint.text.fonts import FontConfiguration
    from weasyprint.urls import URLFetcherResponse

    font_paths = {
        "Space Grotesk": ("SpaceGrotesk-Regular.ttf", "SpaceGrotesk-Bold.ttf"),
        "DM Sans": ("DMSans-Regular.ttf", "DMSans-Bold.ttf"),
    }
    resources = {}
    rules = []
    for family, filenames in font_paths.items():
        for filename, weight in zip(filenames, (400, 700), strict=True):
            path = ROOT / "fonts" / filename
            url = path.as_uri()
            resources[url] = path.read_bytes()
            rules.append(f'@font-face {{ font-family: "{family}"; font-weight: {weight}; src: url("{url}"); }}')

    def fetch_font(url):
        if url not in resources:
            return deny_fetch(url)
        return URLFetcherResponse(url=url, body=resources[url], headers={"Content-Type": "font/ttf"})

    fonts = FontConfiguration()
    font_css = CSS(string="".join(rules), font_config=fonts, url_fetcher=fetch_font)
    options = {"pdf_variant": "pdf/ua-1"} if report["version"] == "1.3" else {}
    document = HTML(string=report_html(report, include_operands=False, brief=brief), url_fetcher=deny_fetch)
    rendered = document.render(stylesheets=[font_css], font_config=fonts)
    anchors = {anchor for page in rendered.pages for anchor in page.anchors}
    for page in rendered.pages:
        for kind, target, *_ in page.links:
            if kind == "internal" and target not in anchors:
                raise ValueError(f"Unresolved PDF link target: {target}")
    pdf = rendered.write_pdf(**options)
    if not pdf.startswith(b"%PDF-") or not pdf.rstrip().endswith(b"%%EOF"):
        raise RuntimeError("Invalid PDF output")
    return pdf


def deny_fetch(url, *args, **kwargs):
    raise ValueError("External and local document resource fetching disabled")

def safe_csv(s):
    return "'" + s if re.match(r"^[=+@\-\t\r\n]", s) else s

def write_missing(report, path):
    keys=["priority","item","period","why","conclusion","action","availability"]
    if report["version"] == "1.3":
        keys.insert(0, "id")
    with path.open("w",encoding="utf-8",newline="") as f:
        line_ending = "\n" if report["version"] == "1.3" else "\r\n"
        out=csv.DictWriter(f,fieldnames=keys,lineterminator=line_ending)
        out.writeheader()
        for item in sorted(report["missing_information"], key=lambda x: PRIORITIES.index(x["priority"])):
            out.writerow({k:safe_csv(item[k]) for k in keys})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=pathlib.Path)
    p.add_argument("--out",type=pathlib.Path,required=True)
    p.add_argument("--bundle", type=pathlib.Path, help="Check the report against this analytical bundle before rendering")
    p.add_argument("--html-only",action="store_true",help="Create HTML and CSV only; not a PDF")
    p.add_argument("--brief", action="store_true", help="Also create a concise decision brief for a structured report")
    a=p.parse_args()
    size = a.input.stat().st_size
    if size > 10_000_000:
        raise ValueError("Input exceeds 10 MB")
    report = validate(json.loads(a.input.read_text(encoding="utf-8")))
    if report["version"] == "1.0" and size > 2_000_000:
        raise ValueError("Legacy report input exceeds 2 MB")
    if a.bundle is not None:
        import sys
        kit = ROOT.parent / "analysis-kit"
        if not (kit / "to_report.py").is_file():
            raise ValueError("Bundle checking requires the analysis-kit from the reviewed repository")
        sys.path.insert(0, str(kit))
        from to_report import verify_bundle
        verify_bundle(report, a.bundle)
    output = report_html(report)
    pdf = pdf_bytes(report) if not a.html_only else None
    brief_html = report_html(report, brief=True) if a.brief else None
    brief_pdf = pdf_bytes(report, brief=True) if a.brief and not a.html_only else None
    a.out.mkdir(parents=True,exist_ok=True)
    names = ("assessment.pdf", "assessment.html", "missing-information.csv")
    if a.brief:
        names += ("decision-brief.html", "decision-brief.pdf")
    for name in names:
        if (a.out / name).exists() or (a.out / name).is_symlink():
            raise ValueError("Output artifacts already exist; use a fresh output directory")
    if pdf is not None:
        (a.out/"assessment.pdf").write_bytes(pdf)
    (a.out/"assessment.html").write_text(output,encoding="utf-8")
    write_missing(report,a.out/"missing-information.csv")
    if brief_html is not None:
        (a.out/"decision-brief.html").write_text(brief_html, encoding="utf-8")
    if brief_pdf is not None:
        (a.out/"decision-brief.pdf").write_bytes(brief_pdf)
    print("HTML and missing-information CSV written" if a.html_only else "PDF, HTML and missing-information CSV written")
if __name__=="__main__":
    main()

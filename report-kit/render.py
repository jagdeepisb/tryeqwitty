"""Offline open-methodology report renderer. Distinct from the hosted Eqwitty platform renderer."""
import argparse
import csv
import html
import json
import pathlib
import re
import subprocess
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
HEADINGS = ["Executive assessment","Scope and input inventory","Business and product","Team","Market and competition","Independent thesis and reconciliation","Financial analysis and calculations","Material factors and evidence coverage","Risks and safeguards","Valuation and sensitivity","Management questions","Methodology and limitations"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
LABEL = "Independent assessment: Eqwitty open methodology (not an official Eqwitty platform report)"

def validate(report):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(report)
    if [s["heading"] for s in report["sections"]] != HEADINGS:
        raise ValueError("Sections must appear once in the declared order")
    ids = {s["id"] for s in report["sources"]}
    if len(ids) != len(report["sources"]):
        raise ValueError("Duplicate source identifiers")
    for section in report["sections"]:
        if not set(section["source_ids"]) <= ids:
            raise ValueError("Unknown source identifier")
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

CSS = """
@page { size: A4; margin: 18mm 17mm 20mm;
  @bottom-left { content: 'eqwitty. | Open methodology v1.0'; font: 8pt 'DM Sans'; color: #666666; }
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

def report_html(report):
    validate(report)
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Independent company assessment</title><style>', CSS, '</style></head><body>',
        '<header><div class="brand">eqwitty<span class="dot">.</span></div><h1>', esc(report["company"]), '</h1><p>', esc(report["objective"]), '</p><p class="muted">As of ', esc(report["as_of"]), '</p><p class="notice">', esc(LABEL), '</p></header>']
    for section in report["sections"]:
        parts += ['<section><h2>', esc(section["heading"]), '</h2>']
        parts += ["<p>"+esc(p)+"</p>" for p in section["paragraphs"]]
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
    return "".join(parts)

def verify_fonts():
    for family in ("Space Grotesk", "DM Sans"):
        matched = subprocess.run(["fc-match", "-f", "%{family}", family], check=True, capture_output=True, text=True).stdout
        if family.casefold() not in [x.strip().casefold() for x in matched.split(",")]:
            raise RuntimeError("Required font unavailable: "+family)

def deny_fetch(url, *args, **kwargs):
    raise ValueError("External and local document resource fetching disabled")

def safe_csv(s):
    return "'" + s if re.match(r"^[=+@\-\t\r\n]", s) else s

def write_missing(report, path):
    keys=["priority","item","period","why","conclusion","action","availability"]
    with path.open("w",encoding="utf-8",newline="") as f:
        out=csv.DictWriter(f,fieldnames=keys)
        out.writeheader()
        for item in sorted(report["missing_information"], key=lambda x: PRIORITIES.index(x["priority"])):
            out.writerow({k:safe_csv(item[k]) for k in keys})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=pathlib.Path)
    p.add_argument("--out",type=pathlib.Path,required=True)
    p.add_argument("--html-only",action="store_true",help="Create HTML and CSV only; not a PDF")
    a=p.parse_args()
    if a.input.stat().st_size>2_000_000: raise ValueError("Input exceeds 2 MB")
    report=validate(json.loads(a.input.read_text(encoding="utf-8")))
    output=report_html(report)
    a.out.mkdir(parents=True,exist_ok=True)
    if not a.html_only:
        verify_fonts()
        from weasyprint import HTML
        pdf=HTML(string=output,url_fetcher=deny_fetch).write_pdf()
        if not pdf.startswith(b"%PDF-") or not pdf.rstrip().endswith(b"%%EOF"):
            raise RuntimeError("Invalid PDF output")
        (a.out/"assessment.pdf").write_bytes(pdf)
    (a.out/"assessment.html").write_text(output,encoding="utf-8")
    write_missing(report,a.out/"missing-information.csv")
    print("HTML and missing-information CSV written" if a.html_only else "PDF, HTML and missing-information CSV written")
if __name__=="__main__":
    main()

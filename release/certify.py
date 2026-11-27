"""Build or verify a v2.0 release evidence package from a pinned source revision."""

import argparse
from decimal import Decimal
from hashlib import sha256
from importlib.metadata import version
import json
import platform
from pathlib import Path
import re
from shutil import copyfile
from subprocess import run
import sys
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-kit"))

from benchmark import evaluate
from conformance import COMMIT, PROFILE, check, json_document, renderer, source_commit
from contract import require
from to_report import convert
from validate import validate

MANIFEST = "release-manifest.json"
CHECKSUMS = "SHA256SUMS.txt"
REVIEW = "verification.json"


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def digest(value):
    return sha256(value).hexdigest()


def query(command, *args):
    process = run([command, *map(str, args)], check=True, capture_output=True, encoding="utf-8")
    return process.stdout


def review_pdf(path, report, markers, commit):
    info = query("pdfinfo", path)
    require(re.search(r"^Tagged:\s+yes$", info, re.MULTILINE), f"{path.parent.name}: PDF lacks tags")
    text = " ".join(query("pdftotext", "-layout", path, "-").split())
    for marker in (*markers, "Independent assessment", "Methodology v"):
        require(marker in text, f"{path.parent.name}: missing PDF text {marker}")
    # Technical provenance remains in the report JSON and release manifest.
    require(report["methodology"]["standard_commit"] == commit, "Report provenance differs from source")
    require("\u2014" not in text, f"{path.parent.name}: PDF contains an em dash")
    for phrase in ("Bundle SHA-256", "Standard commit", "Renderer v", "fallback export", "Lato substitute"):
        require(phrase.lower() not in text.lower(), f"{path.parent.name}: PDF contains implementation language")
    require("\ufffd" not in text, f"{path.parent.name}: PDF has unreadable characters")
    fonts = [line.split() for line in query("pdffonts", path).splitlines()[2:] if line.strip()]
    for family in ("Space-Grotesk", "DM-Sans"):
        require(any(family in row[0] and row[-5:-2] == ["yes", "yes", "yes"] for row in fonts),
                f"{path.parent.name}: {family} is not embedded with Unicode mapping")
    urls = set()
    destinations = query("pdfinfo", "-dests", path)
    for source in report["sources"]:
        require(f'"source-{source["id"]}"' in destinations,
                f"{path.parent.name}: missing PDF destination for {source['id']}")
        if source["url"]:
            urls.add(source["url"])
    actual_urls = {row.split(maxsplit=2)[-1] for row in query("pdfinfo", "-url", path).splitlines()[1:] if row.strip()}
    require(urls <= actual_urls, f"{path.parent.name}: missing PDF source links")
    for gap in report["missing_information"]:
        require(f'"gap-{gap["id"]}"' in destinations, f"{path.parent.name}: missing PDF destination for {gap['id']}")

    coordinates = query("pdftotext", "-bbox", path, "-").encode()
    pages = ElementTree.fromstring(coordinates).findall(".//{*}page")
    require(bool(pages), f"{path.parent.name}: PDF has no readable pages")
    for index, page in enumerate(pages, 1):
        width, height = (Decimal(page.get(key)) for key in ("width", "height"))
        words = page.findall("{*}word")
        require(len(words) > 15, f"{path.parent.name}: page {index} is blank or clipped")
        for word in words:
            left, top, right, bottom = (Decimal(word.get(key)) for key in ("xMin", "yMin", "xMax", "yMax"))
            require(0 <= left < right <= width and 0 <= top < bottom <= height,
                    f"{path.parent.name}: page {index} has text beyond the page bounds")
    return {"pages": len(pages), "source_links": len(urls), "gap_links": len(report["missing_information"]),
            "tagged": True, "embedded_fonts": ["Space Grotesk", "DM Sans"], "text_and_bounds": "pass",
            "text_sha256": digest(text.encode()), "page_coordinates_sha256": digest(coordinates)}


def passes_percent(value, minimum):
    hits, total = value["count"], value["out_of"]
    return 0 <= hits <= total and total > 0 and 100 * hits >= minimum * total


def check_pilot(result, policy):
    require(result["fingerprint"] == policy["fingerprint"], "Benchmark fingerprint differs from the release profile")
    grouped = {s["track"]: s for s in result["summaries"]}
    require(len(grouped) == len(result["summaries"]) and grouped.keys() == policy["tracks"].keys(),
            "Published pilot requires one recorded configuration in each track")
    require(result["reviewer_agreement"] == {"count": policy["reviewer_pairs"], "out_of": policy["reviewer_pairs"]},
            "Published pilot reviewer agreement differs from the release baseline")
    for track, required in policy["tracks"].items():
        summary = grouped[track]
        require(summary["trials"] == required["sessions"] and summary["trial_cases"] == required["case_responses"],
                f"{track}: incorrect pilot size")
        require(summary["hard_gate_clear"] == {"count": required["sessions"], "out_of": required["sessions"]},
                f"{track}: hard-failure gate triggered")
        metrics = summary["metrics"]
        coverage = summary["calibration"]
        require(metrics["answer_coverage"]["out_of"] == coverage["eligible"] == required["answers"] and
                metrics["contradiction_recall"]["out_of"] == required["contradictions"],
                f"{track}: incorrect answer denominator")
        checks = {**metrics, "answer_agreement": summary["answer_agreement"],
                  "decision_agreement": summary["decision_agreement"],
                  "confidence_coverage": {"count": coverage["scored"], "out_of": coverage["eligible"]}}
        for metric, threshold in policy["minimum_percent"].items():
            if metric == "contradiction_recall" and required["contradictions"] == 0:
                continue
            require(passes_percent(checks[metric], threshold), f"{track}: {metric} below {threshold}%")
        brier = Decimal(coverage["squared_error_sum"]) / coverage["scored"]
        require(0 <= brier <= Decimal(policy["maximum_brier_mean"]), f"{track}: calibration threshold missed")


def build_reference(base, case, commit, profile, render):
    directory = base / "reference" / case["id"]
    directory.mkdir(parents=True)
    bundle, _ = json_document(ROOT / case["bundle"])
    bundle["standard_commit"] = commit
    snapshot = json_bytes(bundle)
    bundle_path = directory / "bundle.json"
    bundle_path.write_bytes(snapshot)
    report = convert(bundle, digest(snapshot), report_version=profile["report_version"])
    report_path = directory / "report.json"
    report_path.write_bytes(json_bytes(report))
    (directory / "calculations.json").write_bytes(json_bytes(validate(bundle)))
    if bundle["version"] == profile["analysis_bundle_version"]:
        receipt = check(bundle_path, report_path, commit)
        (directory / "conformance.json").write_bytes(json_bytes(receipt))
    pdf = directory / "assessment.pdf"
    pdf.write_bytes(render.pdf_bytes(report))
    (directory / "assessment.html").write_bytes(render.report_html(report).encode())
    render.write_missing(report, directory / "missing-information.csv")
    return {"bundle_version": bundle["version"], **review_pdf(pdf, report, case["pdf_markers"], commit)}


def artifact_name(profile):
    return f"eqwitty-v{profile['release']}-reference.zip"


def contract_hashes(profile):
    return {path: digest((ROOT / path).read_bytes()) for path in profile["contracts"]}


def build(output, profile, commit):
    if (ROOT / ".git").exists():
        dirty = query("git", "-C", ROOT, "status", "--porcelain", "--untracked-files=no")
        require(not dirty, "Build from a clean, committed source tree")
    require(not output.exists() or (output.is_dir() and not any(output.iterdir())), "Use a new, empty output directory")
    suite = ROOT / profile["benchmark"]["path"]
    pilot = evaluate(suite)
    require(json_bytes(pilot) == (suite / "results.json").read_bytes(), "Exact benchmark replay differs")
    check_pilot(pilot, profile["benchmark"])
    render = renderer()

    with TemporaryDirectory() as temp:
        staged = Path(temp)
        reports = {case["id"]: build_reference(staged, case, commit, profile, render) for case in profile["references"]}
        checks = {"benchmark_replay": "pass", "benchmark_thresholds": "pass", "pdf_checks": reports}
        (staged / REVIEW).write_bytes(json_bytes(checks))
        (staged / "benchmark-results.json").write_bytes(json_bytes(pilot))
        archive_name = artifact_name(profile)
        archive = staged / archive_name
        asset_hashes = {}
        with ZipFile(archive, "w") as package:
            for path in sorted(staged.rglob("*")):
                if path.is_file() and path != archive:
                    name = path.relative_to(staged).as_posix()
                    contents = path.read_bytes()
                    asset_hashes[name] = digest(contents)
                    package.writestr(ZipInfo(name), contents, compress_type=ZIP_DEFLATED)
        manifest = {
            "standard": profile["standard"], "release": profile["release"], "source_commit": commit,
            "component_versions": {name: profile[name] for name in
                                   ("analysis_bundle_version", "financial_model_version", "report_version")},
            "benchmark_fingerprint": pilot["fingerprint"],
            "contracts": contract_hashes(profile), "archive": archive_name, "files": asset_hashes,
            "build_environment": {"platform": platform.platform(), "python": platform.python_version(),
                                  "weasyprint": version("weasyprint"), "jsonschema": version("jsonschema"),
                                  "poppler": run(["pdfinfo", "-v"], check=True, capture_output=True,
                                                 text=True).stderr.splitlines()[0]},
        }
        output.mkdir(parents=True, exist_ok=True)
        (output / MANIFEST).write_bytes(json_bytes(manifest))
        copyfile(archive, output / archive_name)
        checksums = "".join(f"{digest((output / name).read_bytes())}  {name}\n" for name in (MANIFEST, archive_name))
        (output / CHECKSUMS).write_text(checksums, encoding="ascii")
    return verify(output, profile, commit)


def verify(output, profile, commit):
    archive_name = artifact_name(profile)
    names = (MANIFEST, archive_name)
    checksums = "".join(f"{digest((output / name).read_bytes())}  {name}\n" for name in names)
    require((output / CHECKSUMS).read_text(encoding="ascii") == checksums, "Release asset checksum mismatch")
    manifest, _ = json_document(output / MANIFEST)
    require(manifest["standard"] == profile["standard"] and manifest["release"] == profile["release"] and
            manifest["source_commit"] == commit and manifest["archive"] == archive_name,
            "Release provenance differs from the selected source")
    require(manifest["contracts"] == contract_hashes(profile), "Release contract checksum mismatch")
    require(manifest["benchmark_fingerprint"] == profile["benchmark"]["fingerprint"], "Release benchmark seal differs")
    with ZipFile(output / archive_name) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and set(names) == manifest["files"].keys(), "Release archive entries differ")
        for name in names:
            require(digest(archive.read(name)) == manifest["files"][name], f"Release file checksum mismatch: {name}")
        results = archive.read("benchmark-results.json")
        stored = ROOT / profile["benchmark"]["path"] / "results.json"
        require(results == stored.read_bytes(), "Release benchmark results differ from the archived baseline")
        check_pilot(json.loads(results), profile["benchmark"])
        checks = json.loads(archive.read(REVIEW))
        require(checks["benchmark_replay"] == checks["benchmark_thresholds"] == "pass" and
                checks["pdf_checks"].keys() == {case["id"] for case in profile["references"]},
                "Release verification record is incomplete")
    return {"release": profile["release"], "source_commit": commit, "checked_files": len(names), **checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify"))
    parser.add_argument("--out", type=Path, required=True, help="Directory for the manifest, archive and checksums")
    parser.add_argument("--commit", help="Full commit SHA of a verified source archive")
    args = parser.parse_args()
    profile, _ = json_document(PROFILE)
    commit = source_commit(args.commit)
    require(COMMIT.fullmatch(commit) and commit != "0" * 40, "A full source commit SHA is required")
    result = (build if args.action == "build" else verify)(args.out, profile, commit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

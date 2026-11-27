"""Check an analytical bundle or reconciled report against the v2.0 release profile."""

import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re
from subprocess import run

from jsonschema import ValidationError

from contract import require
from to_report import verify_projection
from validate import validate

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "release/v2.0.0/profile.json"
COMMIT = re.compile(r"[0-9a-f]{40}")


def renderer():
    spec = spec_from_file_location("eqwitty_report_renderer", ROOT / "report-kit/render.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_document(path, max_bytes=5_000_000):
    with path.open("rb") as file:
        raw = file.read(max_bytes + 1)
    require(len(raw) <= max_bytes, f"{path.name} exceeds the supported size")
    return json.loads(raw), sha256(raw).hexdigest()


def source_commit(supplied=None):
    if (ROOT / ".git").exists():
        checkout = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True,
                       capture_output=True, text=True).stdout.strip()
        require(supplied is None or supplied == checkout, "Source commit does not match this checkout")
        dirty = run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                    check=True, capture_output=True, text=True).stdout
        require(not dirty, "Source checkout has uncommitted tracked changes")
        return checkout
    require(supplied is not None, "Supply --commit for a verified release source archive")
    return supplied


def check(bundle_path, report_path, commit):
    require(COMMIT.fullmatch(commit) and commit != "0" * 40, "A full source commit SHA is required")
    profile, profile_hash = json_document(PROFILE)
    bundle, bundle_hash = json_document(bundle_path)
    require(isinstance(bundle, dict) and bundle.get("version") == profile["analysis_bundle_version"],
            f"v{profile['release']} conformance requires analytical bundle v{profile['analysis_bundle_version']}")
    require(bundle.get("standard_commit") == commit, "Bundle standard_commit differs from the source commit")

    result = {
        "standard_release": profile["release"],
        "profile_sha256": profile_hash,
        "source_commit": commit,
        "level": "analytical-bundle",
        "bundle_sha256": bundle_hash,
    }
    if report_path is None:
        validate(bundle)
    else:
        report, report_hash = json_document(report_path, max_bytes=10_000_000)
        require(isinstance(report, dict) and report.get("version") == profile["report_version"],
                f"v{profile['release']} conformance requires report v{profile['report_version']}")
        renderer().validate(report)
        verify_projection(report, bundle, bundle_hash)
        result.update(level="reconciled-report", report_sha256=report_hash)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--report", type=Path, help="Check the structured report and its exact bundle projection")
    parser.add_argument("--commit", help="Full commit SHA of a verified release source archive")
    args = parser.parse_args()
    try:
        result = check(args.bundle, args.report, source_commit(args.commit))
    except (ValueError, ValidationError, OSError) as error:
        parser.exit(1, f"Conformance failed: {getattr(error, 'message', str(error))}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

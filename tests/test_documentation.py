"""Check current public documentation's simple Markdown local links and anchors."""
from collections import Counter
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    "README.md", "AGENT.md", "AGENTS.md", "prompts/evaluate.md",
    "evaluation-protocol.md", "methodology/execution.md", "methodology/evidence.md",
    "methodology/research-playbooks.md", "financial-analysis/guide.md", "valuation/guide.md",
    "report-spec.md", "report-kit/README.md", "analysis-kit/README.md", "GOVERNANCE.md",
    "release/COMPATIBILITY.md", "release/RECOVERY.md", "benchmarks/prospective-evaluation.md",
)
LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


def prose(path):
    """Exclude fenced examples, not actual Markdown navigation."""
    fenced = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*(" + chr(96) + r"{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fenced is None:
                fenced = marker
            elif marker[0] == fenced[0] and len(marker) >= len(fenced):
                fenced = None
            continue
        if fenced is None:
            yield line


def anchors(path):
    seen = Counter()
    result = set()
    for line in prose(path):
        match = HEADING.match(line)
        if match:
            slug = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
            number = seen[slug]
            result.add(f"{slug}-{number}" if number else slug)
            seen[slug] += 1
        result.update(re.findall(r'(?:id|name)="([^"]+)"', line))
    return result


class DocumentationTests(unittest.TestCase):
    def test_relative_links_in_current_public_docs(self):
        failures = []
        for name in DOCS:
            document = ROOT / name
            for number, line in enumerate(prose(document), 1):
                for raw in LINK.findall(line):
                    link = urlsplit(raw)
                    if link.scheme or link.netloc:
                        continue  # External sources require separate online checks.
                    target = (document.parent / unquote(link.path)).resolve() if link.path else document
                    if not target.is_relative_to(ROOT) or not target.exists():
                        failures.append(f"{name}:{number}: missing {raw}")
                    elif link.fragment and target.suffix.lower() == ".md":
                        if unquote(link.fragment) not in anchors(target):
                            failures.append(f"{name}:{number}: unknown anchor {raw}")
        self.assertFalse(failures, "\n".join(failures))

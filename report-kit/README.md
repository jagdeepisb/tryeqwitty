# Portable Report Kit (v1.0)
This offline kit generates an independent branded PDF and missing-information CSV from structured evaluation results. It does not run company research, connect to the hosted Eqwitty platform, or issue official platform scores or publication identifiers. The included reference fixture is fictional.

Clone the repository or download these files into one local folder:
- https://raw.githubusercontent.com/jagdeepisb/tryeqwitty/main/report-kit/render.py
- https://raw.githubusercontent.com/jagdeepisb/tryeqwitty/main/report-kit/schema.json
- https://raw.githubusercontent.com/jagdeepisb/tryeqwitty/main/report-kit/requirements.txt
- https://raw.githubusercontent.com/jagdeepisb/tryeqwitty/main/report-kit/example.json

Read the protocol and report spec first. Write a company-specific report JSON matching the schema (ordered sections, actual source IDs, source locators, evidence limitations and company-specific missing information). The synthetic example is a structural fixture, not a source of company facts. Keep private source documents and the report JSON on the machine performing the analysis; the renderer performs no network request.

Use Python 3.11+, the WeasyPrint platform dependencies and fontconfig. Install licensed Space Grotesk and DM Sans from trusted upstream (e.g. Google Fonts); font binaries are not included. Verify actual font installation. Then:
```sh
python -m pip install -r requirements.txt
python render.py report.json --out output
```
Result: assessment.pdf, assessment.html, missing-information.csv. If fonts or WeasyPrint are unavailable, run with `--html-only` and explicitly disclose that no PDF was produced. Do not reuse a stale PDF after a failed run; write to a fresh output directory each time. Review every PDF page, verify fonts, source links, financial figures and the missing-information CSV. Do not describe the document as an official hosted Eqwitty platform report.

# Executable analytical contract v1.1
Create an analysis JSON using the schema at ../schemas/analysis-bundle.json. Use ../benchmarks/ as synthetic structural examples only. Keep real company data private. Install dependencies and run:
```sh
python -m pip install -r analysis-kit/requirements.txt
python analysis-kit/validate.py analysis.json
python analysis-kit/to_report.py analysis.json report.json
python -m pip install -r report-kit/requirements.txt
python report-kit/render.py report.json --out output
```
The converter preserves the original v1.0 renderer schema for compatibility and embeds v1.1 methodology and pinned commit in the narrative. A valid bundle is not a certification of evidence truth. Formula eligibility is bounded; the code does not browse, source facts, verify factual relevance, assess model-specific economics automatically, or implement official Eqwitty scoring. Check all reports against evidence and retain the analytical bundle and hash. See the methodology and finance/valuation guides.
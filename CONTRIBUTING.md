# Contributing

Use [issues](https://github.com/jagdeepisb/tryeqwitty/issues) for proposals and corrections. Describe the decision or calculation affected, the applicable release and a minimal reproducible example. Use synthetic, public, or permissioned evidence. Link public source records and identify their origin, attribution and access date. Keep private company data outside the public repository.

Open a pull request against `main` and link the issue. For a methodology change, explain which inputs, decisions or reports change and how reviewers can verify them. For an implementation change, run the validation workflow locally and include an example that exercises the changed behavior.

```sh
python -m pip install -r report-kit/requirements.txt
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
python analysis-kit/benchmark.py
```

Contribute material you have the right to submit under the applicable terms. Identify any separate permission or attribution in the pull request. [License and notices](NOTICE.md) · [Governance](GOVERNANCE.md)

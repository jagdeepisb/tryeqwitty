# Governance

Eqwitty maintains the public standard in this repository. Public issues and pull requests record proposed changes, review evidence, decisions and exceptions. The repository maintainer resolves disputes, approves license changes and authorizes immutable releases.

| Change | Review record |
|---|---|
| Methodology or contract | Report the compatibility impact, show the affected calculations or decisions, and run the contract checks. |
| Benchmark content or grading | Review the evidence permissions, independently recompute the reference values, freeze the inputs and grading rules, and archive the runs used to substantiate claims. |
| Release | Link the reviewed commit, passing CI, replayed benchmarks, PDF review, file checksums and remaining limitations. |

Correct a published material error through a documented issue, a pull request and a new version. Preserve the earlier release and publish the correction and compatibility impact in the changelog. The public standard's release checks are administered by the maintainers. An independent certification claim requires an identified certifying party and an independently reviewable decision. [Compatibility policy](release/COMPATIBILITY.md) · [Release acceptance](release/v2.2.1/README.md)

Performance claims beyond the archived pilot require a prospectively registered evaluation and documented independent review. See [prospective evaluation requirements](benchmarks/prospective-evaluation.md). Do not describe automated or AI-only review as human or third-party certification.

## Repository controls

Require pull requests and the passing `contract` check for updates to `main`; prohibit force pushes and deletion. For a solo maintainer, require zero approving reviews until another qualified maintainer is available; do not count self-review as independent review. Apply these controls in an active GitHub ruleset (including administrators; no standing bypass). The maintainer must verify the live settings rather than treating this document as enforcement. Record exceptions in a public issue. [Draft release recovery](release/RECOVERY.md).

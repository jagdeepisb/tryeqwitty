# Governance

Eqwitty maintains the public standard in this repository. Public issues and pull requests record proposed changes, review evidence, decisions and exceptions. The repository maintainer resolves disputes, approves license changes and authorizes immutable releases.

| Change | Review record |
|---|---|
| Methodology or contract | Report the compatibility impact, show the affected calculations or decisions, and run the contract checks. |
| Benchmark content or grading | Review the evidence permissions, independently recompute the reference values, freeze the inputs and grading rules, and archive the runs used to substantiate claims. |
| Release | Link the reviewed commit, passing CI, replayed benchmarks, PDF review, file checksums and remaining limitations. |

Correct a published material error through a documented issue, a pull request and a new version. Preserve the earlier release and publish the correction and compatibility impact in the changelog. The public standard's release checks are administered by the maintainers. An independent certification claim requires an identified certifying party and an independently reviewable decision. [Compatibility policy](release/COMPATIBILITY.md) · [Release acceptance](release/v2.2.2/README.md)

Performance claims beyond the archived pilot require a prospectively registered evaluation and documented independent review. See [prospective evaluation requirements](benchmarks/prospective-evaluation.md). Do not describe automated or AI-only review as human or third-party certification.

## Repository controls

While the repository has a sole contributor and maintainer, the maintainer has elected not to enable a GitHub branch ruleset. Use pull requests and confirm a successful `contract` check before merging changes into `main`. Avoid force pushes and deletion of `main`. These are voluntary maintainer procedures, not GitHub-enforced controls: direct pushes or changes without passing CI remain technically possible. Do not count self-review as independent review. Record exceptions in a public issue. Revisit enforceable branch protections if additional contributors or maintainers receive write access. [Draft release recovery](release/RECOVERY.md).

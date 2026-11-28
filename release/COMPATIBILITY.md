# Compatibility and migration

The release number identifies a reviewed set of instructions, executable contracts, tests and reference artifacts. The versions inside JSON identify their formats.

| Input or output | Behavior in the v2.0 kit |
|---|---|
| Analysis bundle 1.1 or 1.2 | Validate in its original format. The bridge defaults to report 1.0 and accepts `--report-version 1.3`. |
| Analysis bundle 1.3 | Validate in its original format and generate structured report 1.3 by default. |
| Analysis bundle 1.4 | Validate the research, analytical and financial contract and generate structured report 1.3 by default. Record the exact v2.0 source commit for v2.0 conformance. |
| Financial model 1.2 | Use the existing definitions and schema. Preserve both formula versions and source-linked operands. |
| Report 1.0 or 1.3 | The renderer accepts both. The v2.0 reconciled-report level uses 1.3 with the original bundle. |

## Move an existing assessment to v2.0

1. Preserve the original bundle and report together with their hashes and standard commit. Choose the published v2.0 revision and read its profile.
2. A bundle below v1.4 needs the v1.4 research playbook, selected factors, scoped questions, actual attempt ledger, source origins, unresolved points and correction routes. Reconstruct these from contemporaneous records where available. Disclose missing evidence and research access. Reassess unsupported conclusions before adding the new fields. [Research contract](../methodology/research-playbooks.md)
3. For a v1.4 bundle, review the assessment under the v2.0 profile. Set `standard_commit` to the verified release commit in the new record. Validate and regenerate the report with the locked revision.
4. Retain both snapshots. Run `analysis-kit/conformance.py` on the new analytical bundle and same-bundle structured report. Export with the renderer's `--bundle` option. [Release procedure](v2.0.0/README.md)

For future releases, a patch preserves accepted formats and intended behavior and documents corrections. A minor version can add backward-compatible capability. A breaking change needs a new major release, explicit migration instructions, and stated support for earlier contracts. Previously published releases retain their files and checksums.

## v2.1 publication migration

The v2.1 release keeps the same analytical, financial and report JSON versions. Review an existing bundle under the selected release, preserve the old snapshot, set the new reviewed source commit, and regenerate the reader-facing memo. The original v2.0 artifacts remain available. See the [v2.1 profile](v2.1.0/README.md).

## v2.1.1 evidence review

Use the same JSON formats. Revisit a fully supported factor if an open research result still requests evidence for that factor. Record the narrower finding or complete the missing work before regenerating the memo. [Patch profile](v2.1.1/README.md)

## v2.2 decision briefs

No JSON format or financial formula changes. The optional `--brief` output is an additional presentation of the validated report, not a new analytical contract. Keep the full assessment and prior snapshots. See the [v2.2 profile](v2.2.0/README.md).

## v2.2.1 editorial patch

The accepted JSON formats and financial formulas remain unchanged. Preserve the earlier assessment, review it under the new published commit and regenerate both report formats if needed. [Patch profile](v2.2.1/README.md).

# Eqwitty report specification
This specification defines the standalone open-standard investment memo format and accompanies the portable offline renderer. It is distinct from the hosted Eqwitty platform renderer.

Required final artifacts: a company-specific investment memo PDF; where valuation is eligible, a valuation analysis or clearly marked valuation section; and a prioritised missing-information checklist. Source links must be clickable where possible. The memo should have scope and input inventory, executive assessment, business and product, team, market/competition, thesis reconciliation, financial analysis and reproducible calculations, factors and evidence coverage, material risks, valuation and sensitivities (if available), management questions, missing information, methodology limitations and sources. Use clear units, currencies, as-of dates and status for unavailable values. No invented app scores or IDs.

For the verified Eqwitty brand, use Space Grotesk for headings and numbers and DM Sans for body/table/notes. Palette: #3B82F6 blue, #111111 ink, #666666 secondary, #FFFFFF background, #F5F5F5 soft panel, #E5E5E5 divider. Use the eqwitty. text wordmark with blue dot only when authorised; disclose independent public-methodology output rather than presenting it as an official app publication. Verify actual loaded fonts and readable page rendering; never silently substitute and claim fidelity.

Export integrity rules: preserve one frozen analysis snapshot through validation and report generation. Use the validator's deterministic calculation results with the original assumptions and sources. Validate outputs against the JSON schema, verify page-level rendering, check numerical consistency and clickable source links, and label the document clearly as an independent open-methodology assessment rather than an official hosted Eqwitty platform report. If PDF creation is unavailable, return the structured report and missing-information list without claiming a PDF exists.

## Portable report-generation kit
Use https://raw.githubusercontent.com/jagdeepisb/tryeqwitty/main/report-kit/README.md and the accompanying schema, renderer and example in the `tryeqwitty` repository to generate an independent PDF and missing-information CSV offline. Verify all pages and source references; if the required fonts or PDF tools are unavailable, explicitly report that PDF generation could not be completed.

## v1.1 analytical bundle compatibility
Use the validated v1.1 analysis bundle and [bridge](analysis-kit/README.md) to create the legacy v1.0 report JSON. The report includes the analytical version and commit plus the bundle hash. Renderer footer/schema remain v1.0 for compatibility; v1.1 is the analytical contract version, not a claim that the old renderer implements new typed tables or charts. Retain the original bundle as an audit artifact. A passing renderer is not proof of factual correctness.

## v1.2 financial model reporting

The same bridge accepts v1.2 bundles and records the analytical version, commit and bundle hash. The financial section includes the accounting context, monthly scenario summaries, liquidity and financing effects. The valuation section includes annual FCFF, WACC, enterprise and equity value and sensitivity when applicable. Unavailable components cite the linked information requests. Retain the full validation output for detailed schedules, operand IDs, sources and holder-level changes. See the [analysis kit](analysis-kit/README.md).

## v1.3 structured exhibits

The report bridge turns a validated bundle into exhibits with raw decimal values, display units, operand IDs and evidence references. Cash charts use the numeric cells of their companion table. The PDF shows the evidence matrix, like-for-like comparisons, cap table and round changes, scenario summaries, monthly cash schedules and enterprise and equity sensitivities when supported. Evidence IDs link directly to the source record and missing-information IDs link to its checklist entry. The HTML export includes the complete operand register and exposes raw numeric exhibit values in the markup. The report records the methodology version, review commit, bundle hash and renderer version.

A competitor comparison specifies its scope, comparison companies and criteria. Identify the assessed company with the ID `subject` and use its profile name. Each criterion supplies the same definition for all companies in that comparison and exactly one cell per company. A reported observation needs a source. An independently supported observation needs independent grade A or B evidence. Use a null value, a rationale and applicable gap references for an unknown or inapplicable cell. [Analysis schema](schemas/analysis-bundle-v1.3.json)

Review each rendered PDF page for legibility and verify the figures, references, source links and both fonts. The tagged PDF and semantic HTML use the same exhibits. Preserve the structured inputs and output JSON so readers with permission can trace the calculations. [Report schema](report-kit/schema-v1.3.json) · [Reference reports](report-kit/README.md)

## v1.4 research disclosure

The v1.3 renderer displays the v1.4 methodology version. The report records actual activity by channel, capabilities, question outcomes, distinct evidence origins, corrections and limitations. Planned research without an attempt is disclosed as such. The independent thesis shows its current evidence status. Keep the plan and attempt ledger with the analysis so readers can trace the disclosed work. [Research playbooks](methodology/research-playbooks.md)

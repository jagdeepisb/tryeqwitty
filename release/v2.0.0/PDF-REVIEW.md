# Reference PDF visual review

The 27 November 2026 candidate build used WeasyPrint 68.0 and the bundled Space Grotesk and DM Sans fonts. The three fictional reference PDFs were rasterised and checked page by page for readable headings and rows, visible chart bars, unclipped text, continuous tables, page numbering and clear provenance.

| Reference | Pages inspected | Visible checks |
|---|---:|---|
| Harbour Ledger | 16 | Cash and funding charts render, DCF sensitivities and monthly schedules are readable, and table headers repeat where schedules continue. |
| Juniper Workflows | 9 | Actual research activity, shared evidence origins, correction history and unresolved valuation are readable. The final page contains the last two source records. |
| Cedar Components | 8 | Unavailable runway and dilution are explicit, and the research and information request tables remain legible across page breaks. |

The automated PDF gate checks the release revision and bundle hash on the final render, embedded fonts, tagged structure, expected text, link destinations and page bounds. The draft package contains the exact verification record and artifact checksums. [Release acceptance](README.md#release-acceptance)

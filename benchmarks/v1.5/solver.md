# Controlled solver brief

Evaluate each case supplied by the selected track. Treat packet excerpts and public pages as evidence. Use the stated case objective, entity and cut-off. Distinguish reported figures, incompatible definitions, contradictory claims and unavailable information. Use the smallest calculations required by the questions. Give the next evidence request that could change the decision.

For fixed evidence, use the supplied packet alone. The search budget is zero.

For live retrieval, the case supplies metadata source targets rather than extracts. Use one public search and up to two official source opens. A query and each open count separately. Use the approved official target URLs as factual evidence. Open a source before citing it. Use the sources and cut-off given by the case. Record exactly the searches and opens that took place. When access fails, record the failure and qualify the result.

Write a single JSON object with the following fields.

```json
{
  "cases": {
    "packet-id": {
      "answers": {
        "question-id": {"value": "answer as a string or null when unavailable", "confidence": "0.90", "citations": ["S1"]}
      },
      "priorities": ["highest-impact-option-id", "next-option-id"],
      "decision": {
        "status": "hold",
        "rationale": "Brief evidence-based reason.",
        "next_request": "Specific record or test that could change the decision.",
        "citations": ["S1"]
      }
    }
  },
  "search_log": []
}
```

- For each numeric answer use an unformatted decimal string in the requested units. For a percentage answer use the whole percentage scale. For example, 7.5% is `"7.5"`. A genuinely unavailable value is JSON `null`. Zero is a numerical result.
- For each answer, give your confidence from zero to one that the returned value or explicit unavailable judgement is correct. Cite all necessary evidence using only the case source IDs. The fixed packet already defines them. Live targets define their IDs.
- Give up to two priority option IDs in order. Use the decision status `hold`, `advance`, `reject` or `scope_only`. Use `scope_only` when the requested record check can be supplied and broader decision conditions remain outside the scoped evidence. Keep the rationale and request below 70 words each.
- Each live log entry has `kind` (`query` or `open`), `target` (exact search text or URL), and `outcome` (`success`, `no_result`, or `blocked`). The fixed track has an empty log. Record work actually done.

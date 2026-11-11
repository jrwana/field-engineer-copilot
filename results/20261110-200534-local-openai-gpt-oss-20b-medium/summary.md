# Eval: local:openai/gpt-oss-20b, effort=medium, n=24

| Metric | Value |
|---|---|
| pass_rate | 79% |
| fact_accuracy | 90% |
| tool_choice | 96% |
| citation_hit | 96% |
| escalation_accuracy | 96% |
| escalation_category | 96% |
| no_forbidden_claims | 96% |
| grounding | 92% |
| drafts_returned | 96% |
| mean_latency_s | 6.1 |
| mean_cost_usd | $0.0000 |
| total_cost_usd | $0.000 |

## Failures

- **E04** (lifecycle, status=draft): missed facts ['HX-R5016']
- **E07** (known_issue, status=draft): missed facts ['\\bB0\\b']
- **E08** (compatibility, status=draft): missed facts ['hot[- ]?plug']
- **E13** (escalate, status=draft): grounded
- **E24** (spec_lookup, status=max_turns): tools, citation, escalation, forbidden_ok, grounded, missed facts None
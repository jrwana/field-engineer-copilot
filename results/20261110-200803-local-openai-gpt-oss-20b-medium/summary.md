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
| grounding | 88% |
| drafts_returned | 96% |
| mean_latency_s | 6.1 |
| mean_cost_usd | $0.0000 |
| total_cost_usd | $0.000 |

## Failures

- **E06** (how_to, status=draft): grounded
- **E07** (known_issue, status=draft): missed facts ['\\bB0\\b']
- **E10** (multi_part, status=draft): grounded
- **E13** (escalate, status=draft): missed facts ["not (found|in (our|the) catalog|a (valid|recognized|known))|no (such|record)|does(n't| not) (exist|appear|match)|(couldn't|could not|unable to) find|confirm the part number"]
- **E24** (spec_lookup, status=max_turns): tools, citation, escalation, forbidden_ok, grounded, missed facts None
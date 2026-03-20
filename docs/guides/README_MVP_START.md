# MVP Starter Pack for Dify

This folder contains three starting artifacts for the Lab Safety Assistant MVP:

1. `templates/knowledge_base_template.csv`
- A CSV template for building the Dify Dataset.

2. `templates/eval_set_template.csv`
- A minimal evaluation set template for testing accuracy and safety.

3. `safety_rules.yaml`
- A rules library for high-risk intent handling and safe responses.

Optional helper files:
- `templates/knowledge_entry_template.json`
- `templates/knowledge_entry_schema.json`
- `docs/guides/safety_rules_guide.md`

How to use
1. Fill `templates/knowledge_base_template.csv` with real sources.
2. Import the CSV into Dify Dataset.
3. Use `safety_rules.yaml` to build your safety guardrails in the workflow.
4. Use `templates/eval_set_template.csv` as your test set.

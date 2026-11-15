# Contributor instructions

Keep this repository focused on a portable Parkinson's patient/care-partner advocacy skill, not a diagnostic or prescribing system.

- Read the skill, care reference, behavior checks, and relevant code before editing.
- Preserve diagnostic uncertainty and exact prescribed medication details. Never add dose conversions, withdrawal instructions, autonomous clinical decisions, or claims of trial eligibility.
- Verify medical guidance against current official sources; link evidence where used. Clearly separate symptom relief, disease modification, and experimental evidence.
- Keep patient data out of source, fixtures, logs, search queries, and CI. Use synthetic examples. Do not add analytics or transmit private records.
- Keep the trial helper standard-library-only and Python 3.9 compatible. Preserve clear study/site status labels, unverified status, geography handling, pagination, and truncation notices.
- Rank research by relevance to the user's goal; do not treat drug class, phase, or study type as proof of value or eligibility.
- Test meaningful code changes offline, including error paths. Avoid live API calls in CI. The CLI must report request failures with a nonzero exit code; do not log patient input or add telemetry.
- Update README, agent metadata, and behavior checks when behavior changes. Retain upstream MIT attribution.

Before completing code changes, run:

```sh
python3 -m compileall -q skills tests
python3 -m unittest discover -s tests -v
```

For workflow changes, run the applicable synthetic scenarios in `skills/fuck-parkinsons/eval.md`. Do not claim medical validation from software tests. Report any unverified live integrations or behavior.

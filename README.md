# Fuck Parkinson's

A Parkinson's care-navigation skill for patients and care partners. Turn reports, appointment notes, medication lists, and scattered updates into one concise, living brief with a manageable next step.

Adapted from [Peter Yang's Fuck Cancer](https://github.com/petergyang/fuck-cancer), upstream commit `ecaef1a3fa5bbee50798942011db508ccdffd5f0`. Retains the original MIT license and attribution. This is an independent adaptation, not an endorsement by the original author or a medical organization.

## What changes for Parkinson's

- Preserve suspected versus confirmed diagnoses and distinguish Parkinson's disease from parkinsonism.
- Keep exact prescribed medication times, formulations, and clinician-directed changes. Flag conflicting lists for reconciliation rather than inventing a regimen.
- Track ON/OFF patterns, dyskinesia, freezing, falls, daily function, and non-motor concerns such as sleep, cognition, constipation, and dizziness.
- Prepare focused questions for movement-disorder visits, rehabilitation, swallowing assessments, and hospital admissions.
- Research relevant trials without automatically favoring drugs or later phases over rehabilitation or observational studies.
- Prioritize urgent changes before document upkeep or research; keep medical decisions with the treating team.

## The living brief

1. **Patient information:** Useful care-team contacts, care-partner preferences, and supplied coordination details.
2. **What to do next:** At most three specific actions, with short questions for the next appointment.
3. **What we know:** Confirmed facts, meaningful uncertainty, function and goals, and the prescribed medication schedule when supplied.
4. **Medical terms:** Optional plain-language explanations of relevant terms.
5. **Care log:** Dated, decision-relevant updates, newest first.

Reuse the same brief over time. A Google Doc is supported when connected tools are available; chat works immediately, and Markdown is available on request. Never automatically share a brief or send records to a clinic.

## Install from this checkout

From a downloaded or cloned copy of this repository:

```sh
cd fuck-parkinsons
npx skills add . --skill fuck-parkinsons --global --yes
```

Alternatively, ask a skill-capable agent to install `skills/fuck-parkinsons` from this checkout. Installation commands depend on the host; the skill itself requires no account or API key. Creating a Google Doc requires a connected document integration.

If you received a Git bundle, recover the complete repository first:

```sh
git clone --branch main ./fuck-parkinsons.bundle fuck-parkinsons
```

The bundle contains source and history; it does not create a hosted GitHub repository or install the skill automatically.

## Use

Invoke `/fuck-parkinsons` or `$fuck-parkinsons`, according to your agent:

```text
/fuck-parkinsons My dad has a suspected diagnosis and a specialist visit next month. Help us prepare.
/fuck-parkinsons Update our brief with these neurology notes and the new prescribed medication schedule.
/fuck-parkinsons Help me describe my OFF periods and prepare questions for my neurologist.
/fuck-parkinsons We have a planned hospital admission. Help us prepare our care summary.
/fuck-parkinsons Find research studies near Toronto focused on freezing of gait.
```

Do not put patient names, birth dates, addresses, record identifiers, or private documents into public searches or trial-search command arguments.

## Trial search helper

Python 3.9+; standard library only; no API key. Searches ClinicalTrials.gov API v2. The default condition is `Parkinson Disease`.

```sh
python3 skills/fuck-parkinsons/scripts/search_trials.py \
  --country USA --state CA \
  --near 34.05,-118.24 --radius-miles 50 \
  --terms "freezing of gait" --limit 5
```

Use `--condition` for a different condition, `--full-criteria` to avoid the eligibility preview truncation, or `--output trial-results/candidates.json` to save JSON locally. Use broad-area coordinates rather than a home address. Exact city matching can omit nearby sites. Geographic filtering excludes sites without coordinates.

Results include study type, phase if applicable, interventions, criteria, update date, and `candidate_sites`. A candidate site can be recruiting, not yet recruiting, invitation-only, or unverified when the record omits site status. Always confirm current access and full criteria with the site. A text match can occur in exclusion criteria. Ranking indicates text relevance, not eligibility, evidence quality, medical benefit, or a treatment recommendation. The helper caps retrieval at 5,000 studies and flags truncated searches; no results does not prove no studies exist. ClinicalTrials.gov does not cover every local registry or research opportunity.

## Evidence and medical boundaries

The workflow uses current local clinical guidance and regulator labels, [NINDS](https://www.ninds.nih.gov/health-information/disorders/parkinsons-disease), [NICE NG71](https://www.nice.org.uk/guidance/ng71), [Parkinson's Foundation](https://www.parkinson.org/), [Parkinson's UK](https://www.parkinsons.org.uk/), primary research, and [ClinicalTrials.gov](https://clinicaltrials.gov/data-api/api). See [care checkpoints and source selection](skills/fuck-parkinsons/references/parkinsons-care.md).

This supports care navigation and clinician conversations. It does not diagnose, prescribe, adjust medication or DBS settings, determine trial eligibility, predict an individual prognosis, or replace medical care. A future agent using the skill must verify current medical claims; the repository is not a clinical guideline. Automated tests verify software behavior, not clinical safety or effectiveness.

## Repository contents

- [SKILL.md](skills/fuck-parkinsons/SKILL.md): Care-navigation workflow and brief format.
- [Care checkpoints](skills/fuck-parkinsons/references/parkinsons-care.md): Parkinson's-specific questions, urgent changes, and official sources.
- [Trial helper](skills/fuck-parkinsons/scripts/search_trials.py): Registry searches and clearly labeled candidate-site access.
- [Behavior checks](skills/fuck-parkinsons/eval.md): Synthetic evaluation scenarios.
- [Tests](tests/test_search_trials.py): Offline tests for geography, site status, pagination, criteria, query defaults, and relevance ranking.
- [AGENTS.md](AGENTS.md): Contributor requirements and validation commands.

## Development

```sh
python3 -m compileall -q skills tests
python3 -m unittest discover -s tests -v
```

CI runs offline tests on Python 3.9 and 3.13. Live registry availability and clinical behavior require separate verification. Do not commit patient records or real care briefs.

## License

[MIT](LICENSE). Copyright (c) 2026 Peter Yang; see [NOTICE](NOTICE) for adaptation provenance.

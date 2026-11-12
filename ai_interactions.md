# AI Interactions Log

Reasoning traces from the agentic workflow (stretch feature). Each trace is the real output of `python -m src.vibefinder "<query>" --trace`; full files are in [`assets/`](assets/).

## Trace 1: normal request (`assets/sample_run_1.txt`)
```
Request: "something to study to on a rainy night"
Trace:
  - guardrail: OK
  - retrieve: rainy(0.31), study(0.27), drive(0.16)
  - plan: prefs={'genre': 'classical', 'mood': 'melancholy', 'energy': 0.3}
  - check: top score 3.92/4, confidence 0.90
```
Plan: energy is the score-weighted average of the guides within 60% of the top score (rainy 0.22 and study 0.40 gives 0.30).

## Trace 2: self-correction when the catalog has a gap (`assets/sample_run_5_catalog_gap.txt`)
```
  - check: top score 1.00/4, confidence 0.55
  - retry: genre 'lofi' -> 'ambient', confidence 0.83
  - retry: accepted 'ambient'
```
The check step noticed that no song matched the planned genre, so the agent tried a related genre from `genre_relations.json` and kept the better attempt.

## Trace 3: guardrail stops the pipeline early (`assets/sample_run_3.txt`)
```
  - guardrail: REJECT (Request looks like an attempt to change my instructions; ignored.)
```

## Trace 4: conflicting signals (`assets/sample_run_4.txt`)
```
Request: "some jazz for the gym"  ->  Preferences: {'genre': 'jazz', 'mood': 'intense', 'energy': 0.9}
Status: ok | confidence: 0.74
```
The explicit genre was honored; confidence dropped because the only jazz song has energy 0.37.

## Development notes: where AI output needed human review
- Retry logic originally overwrote an explicitly requested genre ("metal for sleep" became rock). Fixed, with a test.
- Retry threshold of 0.60 never triggered (any genre match already scores at least 2.0/4). Raised to 0.80 after checking real traces.
- Harness first reported 18/18 by counting known failures as passes. Now reports 16/18 plus 2 expected failures.

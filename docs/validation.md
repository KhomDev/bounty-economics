# Validation record — 0.6.1 self-audit

This page records what the 0.6.1 audit actually ran, what each check covers, and
what it does not prove. It exists because the 2026-11-10 review rated the
repository's engineering without naming a defect, and a rating is not a bug
report: the honest response is to measure the surface and publish the gaps.

Audit date: 2026-11-10. Audited commit: `93bb147` (v0.6.0). Platform: Windows,
Python 3.12. The release commit adds only the documentation and test changes
listed in the changelog; no validator, schema, taxonomy or example behaviour
changed.

## What was run

| Check | Command | Result |
|---|---|---|
| Full test suite | `python -m pytest tests/ -q` | 175 passed, 0 skipped |
| Lint | `python -m ruff check .` | clean |
| Shipped examples | `python scripts/validate.py examples/ledger.example.yaml` and `examples/tier-shapes.example.yaml` | 6 entries, 0 errors, 10 warnings (the documented warnings) |
| Taxonomies | `python scripts/validate.py --taxonomy` (text and JSON) | 5 tier shapes, 14 clause classes, 11 gate tokens |
| Generic-name guard | `python scripts/check_generic.py` | clean |
| Hygiene | `python scripts/check_hygiene.py --no-history` | clean (history check skipped: private inputs absent, same as CI) |
| Links | `python scripts/check_links.py` | clean |
| Markdown | `python scripts/check_markdown.py` | clean |
| Cross-repo contract | `python -m pytest tests/test_compat_viability_gate.py` | 13 passed against the pinned viability-gate v0.5.0 |
| Wheel install | `pip install .` in a clean venv, run from outside the checkout | validator and taxonomies resolve |
| CODE_GUIDE references | `python -m pytest tests/test_code_guide.py` | every line count, line-range reference and explicit reference re-derived from the tree |

## What the checks cover

- **Validator behaviour.** The suite exercises the schema, the floor-status
  rules, the placeholder-host rules, the citation and date rules, the regex
  dialect check, the JSON verdict, and the multi-ledger paths.
- **Data and documentation drift.** Counts, vocabularies, the README's numbers
  and the CODE_GUIDE's line references are re-derived from the files, so a
  stale claim fails the suite instead of shipping.
- **The cross-repo contract.** `vg init` output satisfies this schema once
  filled in; an unstated, missing or conflicting floor fails viability-gate's
  G1; every shipped exclusion pattern compiles in its G2. This is tested against
  the pinned tag, not against `main`.

## What this does not prove

- **That a taxonomy class describes a real program's clause.** No labelled
  corpus of program pages is shipped, so the classes are a reading method, not a
  measured classifier.
- **That a citation is true.** The validator checks that a source and a date
  exist and are well formed; it cannot read the source.
- **Anything above the pinned viability-gate tag.** The contract is v0.5.0; a
  newer release is not covered until the pin is bumped.
- **The CI matrix.** The audit ran on Windows/Python 3.12. CI covers 3.10-3.13
  on Ubuntu; those cells were not reproduced locally.
- **Prose outside the enumerated checks.** `tests/test_code_guide.py` guards
  the CODE_GUIDE's references; other prose is reviewed by hand and can drift.

## Reproduce

```bash
python -m pytest tests/ -q
python -m ruff check .
python scripts/validate.py examples/ledger.example.yaml
python scripts/validate.py examples/tier-shapes.example.yaml
python scripts/validate.py --taxonomy
python scripts/check_generic.py
python scripts/check_hygiene.py --no-history
python scripts/check_links.py
python scripts/check_markdown.py
```

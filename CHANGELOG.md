# Changelog

All notable changes to this repository are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions track the ledger schema.

Nothing here has been published to a package index. Publishing is a human decision, not a
build step.

## Repository history reset - 2026-10-10

Repository history was reset on 2026-10-10 to remove identifying material from
earlier commits; earlier versions are no longer available.

The tree itself is unchanged except for the tripwire fix recorded here.

### Fixed

- **The identity-token matcher used the wrong boundary.** It compared the
  character either side of a hit against a set that treated `-`, `_` and `.` as
  separators, so an ordinary English word that merely contained a token was
  reported as that token. The matcher is now a word boundary; the per-file
  allowlist and the line-level exemption for sentences that disclaim an ecosystem
  are both gone, and `tests/test_token_scan.py` pins both directions: words that
  contain a token pass, and every declared token fails.
- The vocabulary now lives in one module, `scripts/token_scan.py`, imported by
  both checks and by the fixtures, so the scan CI runs and the scan the tests run
  cannot drift apart.

## [Unreleased] — 0.2.0

### Fixed

- **The README no longer reads "the page states no floor" as `low_and_above`.** That reading
  turned an unread page into a permissive-looking floor. An unstated floor now keeps
  `tier_shape: unknown` and is recorded as `floor_status: unstated`.
- **The CI step "Assert no program data" was red, and the cause was the repository's own schema.**
  The step grepped `data/*.yaml schemas/*.json` for `github\.com/`, and
  `schemas/ledger.schema.json` line 3 sets `$id` to this project's canonical
  `github.com/KhomDev/...` URL. Exactly one line tripped it. The check is now
  `scripts/check_generic.py`, which bans third-party platforms and any repository that is not
  ours, and still permits the project's own `$id` and documentation links.
- **An unquoted `retrieved` date was a latent schema violation.** YAML resolves
  `2026-10-01` to a date object; the JSON Schema declares a string. The validator now warns, and
  the shipped examples quote their dates.
- **The README advertised "six fictional entries, one per tier shape" for a file with five
  entries.** Every count now matches the file it describes.

### Added

- `floor_status: documented | unstated | conflicting` on ledger entries, plus validator errors
  for the contradictions (an unstated floor beside a shape other than `unknown`, a documented
  floor with no severity, a documented floor beside `unknown`).
- `schema_version` on ledger entries, and a versioned schema `$id`
  (`schemas/v1/ledger.schema.json`).
- `validate.py --format json`, and `--taxonomy --format json`. The JSON result is produced by
  the same pass as the text output, so the two cannot disagree.
- Several ledger paths in one run, so `python scripts/validate.py examples/*.yaml` works.
- `scripts/check_generic.py`, the genericity check that CI and the test suite now share.
- Test suites: `tests/test_counts.py` (count and vocabulary drift), `tests/test_generic.py`,
  and `tests/test_compat_viability_gate.py` (the cross-repo contract, skipping cleanly when the
  sibling checkout or its pinned tag is absent).
- `bounty-econ-validate` console script; CI on Python 3.10, 3.11, 3.12 and 3.13; ruff.
- ```SECURITY.md```, `CONTRIBUTING.md`, `CHANGELOG.md`, `CITATION.cff`, and correction and
  takedown issue templates.
- README: a schema/cross-repo version matrix, a license table recording the current MIT state, and
  a "Known limitations" section.

### Changed

- `requires-python` lowered to `>=3.10` to match the CI matrix.
- Package version `0.1.0` → `0.2.0`. The ledger format changes are additive, so a ledger
  written for 0.1.0 still validates.

### Removed

- The claim that `privileged_role` / `human_error` are the "single largest category of wasted
  submissions industry-wide". No measurement of that exists here.
- The claim that the removed `any` shape "never occurred in practice". It was never counted, so
  the removal note no longer asserts a frequency.
- The unhedged "highest-yield escape" claim about unknowing admin harm. It is now presented as an
  argument that often loses to the `human_error` clause.

### Migration

Ledgers written before this version keep validating. Two warnings may appear:

1. `floor_status is missing` — add it. Use `documented` when you read the reward table,
   `unstated` when the page states no floor, `conflicting` when the program's own materials
   disagree.
2. `retrieved` was written unquoted — quote it (`retrieved: "2026-10-08"`).

If you wrote `tier_shape: low_and_above` for a program whose page simply never mentioned a
floor, that entry is now an **error**: set `tier_shape: unknown` and
`floor_status: unstated` until you find the reward table.

## [0.1.0] — 2026-10-08

- Payout-tier and exclusion-clause taxonomies, shipped as data under `data/`.
- `schemas/ledger.schema.json` and `scripts/validate.py`, with a worked example and a test
  suite.
- The `any` tier shape was removed: a program documenting no severity floor is `low_and_above`.
  (Superseded — see the unstated-floor fix above.)

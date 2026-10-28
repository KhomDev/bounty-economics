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

## [Unreleased]

## [0.4.0] — 2026-10-28

A re-review release with one new capability.

### Added

- **Gate cross-reference — the two repos now compose.** `data/gate-crossref.yaml`
  maps the shared gate vocabulary onto this repo's catalogs for the gates decided
  by the program's own terms: `G1_severity_floor → tier-shapes`,
  `G2_exclusion_clause → clause-classes`, with `program_ceiling` and
  `P16_below_floor` also resolving to tier-shapes and `G4_prior_audit` to the
  prior-audit surface. `scripts/crossref.py` resolves a gate token to the catalog
  that reads the program page for it; `tests/test_crossref.py` keeps every gate
  token inside the shared vocabulary and every catalog reference resolvable. Gates
  whose signal is not in the program's terms are listed as *not answered here*, so
  the cross-reference is honest about its edges. Closes the loop:
  anti-pattern (viability-gate) → gate token → program-terms catalog (here).

### Changed

- **Compatibility pin bumped to viability-gate `v0.4.3`** (`PINNED_VG_TAG`). The
  ledger format is unchanged since `v0.4.1`; `v0.4.2` and `v0.4.3` were docs/CI
  releases, so the cross-repo contract is unchanged — the pin just tracks the
  current tag.

### Reviewed — no change

- **Still no new clause class.** The rejections logged since the 0.3.0 review were
  re-read for an exclusion-clause pattern not already among the fourteen classes.
  Both were no-attacker-win / permanent-liveness rejections, not exclusion-clause
  rejections, so the "theft or permanent lock of principal" scoping flagged at the
  0.3.0 review did **not** recur with program-authored wording — it remains a one-off.
  `data/clause-classes.yaml` stays at fourteen; `data/tier-shapes.yaml` stays at
  five.

## [0.3.0] — 2026-10-21

A taxonomy-review release. I re-read the economics-relevant rejections in my own log — the ones
whose earliest catchable gate was the severity floor, an exclusion clause, a below-floor severity,
a program-level ceiling, or a cooperating-party precondition, including the most recent
smart-contract batch — and asked whether any of them described an exclusion-clause pattern not
already in `data/clause-classes.yaml` or a payout-tier structure not already in
`data/tier-shapes.yaml`.

**They did not.** Every floor rejection resolved to one of the five existing shapes
(`critical_only` for the DualDefense / Critical-only programs, `high_and_above` for the valid
Mediums that paid nothing), and every exclusion rejection mapped to one of the fourteen existing
classes (`privileged_role`, `human_error`, `admin_input`, `dos_no_extraction`, `front_run_only`,
`best_practice`, `design_issue`, `testing_limits`, `user_input`, `non_standard_token`, and the
rest). The nearest thing to a new pattern — a program scoping payouts to "theft or permanent lock
of principal," so that loss of undelivered yield or un-emitted rewards does not count — appeared
as a single program's positive scope definition and otherwise as an internal no-extraction triage
judgement, not as a recurring, program-authored exclusion clause with industry-standard wording.
That is too thin to add a fifteenth class for, so no taxonomy entry was added and the counts stay
at 5 tier shapes and 14 clause classes. Recording the "no new entry" conclusion, with its
reasoning, is the point of this release.

### Changed

- **Cross-repo compatibility pin bumped `v0.4.0` → `v0.4.1`.** viability-gate published `v0.4.1`
  (a LICENSE/README-only change; no code or ledger-format change), so the pin now tracks the
  latest release. All nine cross-repo assertions pass at the new tag, in both directions. The pin
  still lives only in `tests/test_compat_viability_gate.py`; the README "Current state" note and
  the "Known limitations" entry are updated to match.
- **Package version `0.2.0` → `0.3.0`.** No change to the schema (still v1), the taxonomies, or
  the validator behaviour, so every ledger written for 0.2.0 still validates unchanged.

### Added

- **README worked note, "the floor, not the bug, decides."** A first-person note under the
  payout-tier section, grounded in the log review above: the costliest entries were neither
  misread exclusions nor duplicates but confirmed, PoC-backed findings sitting one tier below the
  floor (a valid Medium on a `high_and_above` program, a valid Low on a `critical_only` program).
  The lesson it draws — classify the tier shape before building the PoC, and treat the floor as a
  cliff rather than a slope — is why `tier_shape` is the first ledger field. It names no program,
  chain, or amount.

## [0.2.0] — 2026-10-14

The first tagged release in this repository. The ledger schema is still v1. It
contains everything below, the history-reset fix above, and these release fixes:

### Release fixes (2026-10-14)

- **The cross-repo compatibility test never ran.** It was pinned to
  viability-gate `v0.1.0`, a tag that does not exist, so every run skipped. It is
  now pinned to `v0.4.0`, and all nine assertions pass at that tag, in both
  directions. CI clones viability-gate with its tags rather than by
  `--branch <tag>`, so the pin is declared only in
  `tests/test_compat_viability_gate.py`. A failed clone is now a red build
  instead of a silent skip. `VG_SIBLING` points the test at a checkout under
  another folder name.
- **GitHub could not identify the licence.** `LICENSE` carried a "No third-party
  data" section after the MIT text, which defeats licence detection. `LICENSE` is
  now the MIT text alone, and the paragraph moved, unchanged, to the README's
  License section.
- **Mangled backticks**: eleven code spans in the compat test's docstrings were
  wrapped in triple at-signs instead of double backticks, and a code span in
  `CONTRIBUTING.md` had two stray backticks.
- **Added `scripts/check_markdown.py`** to CI (mangled or unbalanced fences, and
  any README pin that differs from the version), plus **Dependabot** for pip and
  GitHub Actions. CI moved to `actions/checkout@v7` and `actions/setup-python@v7`.

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

## 0.1.0 — 2026-10-08 (untagged; predates the history reset)

- Payout-tier and exclusion-clause taxonomies, shipped as data under `data/`.
- `schemas/ledger.schema.json` and `scripts/validate.py`, with a worked example and a test
  suite.
- The `any` tier shape was removed: a program documenting no severity floor is `low_and_above`.
  (Superseded — see the unstated-floor fix above.)

[Unreleased]: https://github.com/KhomDev/bounty-economics/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/KhomDev/bounty-economics/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/KhomDev/bounty-economics/releases/tag/v0.2.0

# CODE_GUIDE — a line-level walkthrough of the code and data

Technical companion to the [README](README.md). The README explains the method and how to use the
tools; this document explains what every file, field, function, check and test actually is, with
file-and-line references into the tree it describes. Read the README first; read this when you want
to change something.

**Accuracy pin.** Written against version 0.6.1 (2026-11-10). `python -m pytest tests/ -q -rs`
collects 175 tests and `python scripts/validate.py --taxonomy` prints 5 tier shapes and 14 clause
classes. Line numbers refer to that tree and drift as the files change; the identifiers they point
at are stable in practice. Every count in this document was derived from the files themselves (see
[How this document is verified](#how-this-document-is-verified)).

**What this is not.** Not an API reference in the documentation-generator sense: the package ships
no doc build. Not a second README: method, judgement and hunting advice stay there. This is the
map you want when you are editing `scripts/validate.py`, adding a taxonomy entry, or wondering
why CI has a job that builds a Rust binary from a sibling repository.

---

## Repository layout

Nine directories and the repository root, each with one job:

| Path | Role |
|---|---|
| `data/` | The three taxonomy data files: [tier-shapes](data/tier-shapes.yaml) (5 payout-tier shapes), [clause-classes](data/clause-classes.yaml) (14 exclusion-clause classes), [gate-crossref](data/gate-crossref.yaml) (the viability-gate token cross-reference). These are DATA, not prose: `validate.py` reads them at runtime, so the docs, the schema and the validator cannot drift apart (README.md:51-52). |
| `schemas/` | One file, [ledger.schema.json](schemas/ledger.schema.json): JSON Schema (draft 2020-12) for the private ledger format, version v1. Enforced by the validator since 0.5.0. |
| `scripts/` | Eight Python modules: the validator ([validate.py](scripts/validate.py)), the gate-token resolver ([crossref.py](scripts/crossref.py)), the identity-token vocabulary ([token_scan.py](scripts/token_scan.py)), and the four repository guards ([check_generic.py](scripts/check_generic.py), [check_hygiene.py](scripts/check_hygiene.py), [check_links.py](scripts/check_links.py), [check_markdown.py](scripts/check_markdown.py)). [`__init__.py`](scripts/__init__.py) makes the directory importable as the installable package `bounty_economics`. |
| `docs/` | [validation.md](docs/validation.md): the 0.6.1 audit record — what was run, what it covers, what it does not prove. |
| `examples/` | Two fictional ledgers: [ledger.example.yaml](examples/ledger.example.yaml) (1 full entry) and [tier-shapes.example.yaml](examples/tier-shapes.example.yaml) (5 entries, one per tier shape). Every URL uses the reserved `.invalid` TLD. |
| `tests/` | Seven pytest suites, 175 collected tests: [test_validate.py](tests/test_validate.py) (validator behaviour), [test_counts.py](tests/test_counts.py) (count/vocabulary drift), [test_compat_viability_gate.py](tests/test_compat_viability_gate.py) (the cross-repo contract), [test_crossref.py](tests/test_crossref.py), [test_generic.py](tests/test_generic.py), [test_token_scan.py](tests/test_token_scan.py), [test_code_guide.py](tests/test_code_guide.py). |
| `.github/workflows/` | [ci.yml](.github/workflows/ci.yml): the two CI jobs, `validate` and `compat`. |
| `.github/ISSUE_TEMPLATE/` | [correction.md](.github/ISSUE_TEMPLATE/correction.md) and [takedown-request.md](.github/ISSUE_TEMPLATE/takedown-request.md): structured intake for "a claim is wrong" and "this text identifies a target". |
| `.github/` | [dependabot.yml](.github/dependabot.yml): weekly, grouped bump PRs for the pinned Python tools (pip) and the GitHub Actions versions (github-actions). |
| Root | [README.md](README.md) (the method, the schema docs, the cross-repo matrix), [CHANGELOG.md](CHANGELOG.md) (Keep-a-Changelog, versions track the ledger schema), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CITATION.cff](CITATION.cff) (version 0.6.1, released 2026-11-10), [LICENSE](LICENSE) (MIT), `pyproject.toml`, `requirements-ci.txt`, `.gitattributes`, `.gitignore`. |

Two conventions shape the whole tree:

- **No target data, anywhere.** No program names, chains, reward tables, quoted program clauses or
  prior-audit lists; examples must be fictional and use `.invalid` (CONTRIBUTING.md:8-10). Three
  scanners enforce the machine-checkable part (see [The repository guards](#the-repository-guards)).
- **Vocabularies are data files, not code and not prose.** The closed enums a ledger may use live in
  `data/*.yaml`; the JSON Schema mirrors them; the tests assert the mirror stays exact
  (tests/test_counts.py:188-205). Changing one means changing all of them in the same PR
  (CONTRIBUTING.md:41-51).

## The schema dialect, field by field

[schemas/ledger.schema.json](schemas/ledger.schema.json) is the published contract for the ledger.
The validator enforces it directly (since 0.5.0; CHANGELOG.md:120-122) and the tests pin its
properties.

**Root.** `"type": "array"` (line 6): the ledger is a YAML **list** of entries, never a mapping —
viability-gate deserializes the file as a sequence, so a mapping root would break the other reader
of the same file (README.md:381-384, CONTRIBUTING.md:55-57). `$id` is
`https://github.com/KhomDev/bounty-economics/schemas/v1/ledger.schema.json` (line 3): versioned
(`/v1/`), asserted by tests/test_counts.py:176-180. `$schema` is draft 2020-12 (line 2).

**Entry object** (`items`, lines 7-125). `additionalProperties: false` (line 9) — a key the
schema does not list is an error, not a warning; `required` is exactly
`["id", "tier_shape", "source_url", "retrieved"]` (line 10), asserted at
tests/test_counts.py:208-209, and the closed-to-unknown-fields rule at 212-214. Twelve properties (lines 11-124):

1. **`schema_version`** (12-16) — integer, `const: 1`. Optional; absent means 1. "A validator
   that does not implement the pinned version must reject the entry rather than mis-read it."
2. **`id`** (17-21) — string matching `^[a-z0-9][a-z0-9._-]*$` (19). Your own slug for the
   program, stable across rounds.
3. **`tier_shape`** (22-32) — string, enum of the 5 tier-shape ids (24-30), in taxonomy order:
   `critical_only`, `high_and_above`, `medium_and_above`, `low_and_above`, `unknown`. The
   long description (31) encodes two dialect rules: an unstated floor is `unknown`, not
   `low_and_above`; a page that explicitly states "SEVERITY FLOOR: NONE"/"any" IS
   `low_and_above` with `floor_status: documented`. "There is deliberately no 'any' value."
4. **`floor_status`** (33-37) — string, enum `documented | unstated | conflicting` (35). Whether
   the floor was READ. "Strongly recommended: the validator warns when it is absent."
5. **`floor_severity`** (38-42) — string or null; enum `critical | high | medium | low | null`
   (40). Only meaningful when `floor_status` is `documented`. "'informational' is not a valid
   floor: no program pays it in practice."
6. **`source_url`** (43-48) — string, `format: uri`, `minLength: 1`. "Required: an uncited
   entry is rejected." (The semantic layer additionally requires an http(s) scheme — the schema's
   `uri` format is only checked when the jsonschema installation provides a checker for it.)
7. **`retrieved`** (49-53) — string, `format: date`, ISO YYYY-MM-DD. "Required, because program
   terms change without notice."
8. **`conflicts`** (54-58) — array of strings. Where the program's own materials disagree;
   "record the conflict rather than resolving it silently."
9. **`exclusions`** (59-96) — array of objects, each closed (`additionalProperties: false`,
   line 63) with required `["class", "clause"]` (64) and three properties:
   - **`class`** (66-84) — string, enum of the 14 clause-class ids (68-83).
   - **`clause`** (85-89) — string, `minLength: 1`, "Verbatim from the program's scope page."
   - **`pattern`** (90-93) — string, optional; case-insensitive regex over your own finding
     description. "A match is a prompt to check, not an automatic reject."
10. **`prior_audits`** (97-118) — array of objects, each closed (101) with required `["firm"]`
    (102) and four properties: **`firm`** (104, string), **`url`** (105, string),
    **`covers`** (106-110, array of strings — files and functions covered), **`known_issues`**
    (111-115, array of strings, the program's own list verbatim).
11. **`post_audit_delta`** (119-122) — string. "What changed after the last audit. The richest
    surface, and the least likely to be a duplicate."
12. **`notes`** (123) — string, free text.

**Schema ↔ data equality is tested, not assumed.**
`test_the_schema_tier_enum_matches_the_taxonomy` (tests/test_counts.py:188-190) and
`test_the_schema_clause_enum_matches_the_taxonomy` (193-195) assert the enums equal `list(TIERS)`
and `list(CLAUSES)` as loaded from the data files; `test_the_schema_floor_status_enum_matches_the_validator`
(198-200) and the floor-severity twin (203-205) pin the same for the validator's tuples;
`test_the_schema_declares_the_current_version` (183-185) pins `schema_version.const == 1` to the
validator's `SCHEMA_VERSION`; `test_the_shipped_examples_validate_against_the_json_schema`
(217-224) runs both examples through raw `jsonschema.validate`, and two negative tests
(227-255) prove the schema rejects an unknown field and an out-of-enum `floor_status`.

### The one-dialect contract with viability-gate

Two repositories read the same private ledger file. The contract, as the code states it:

> bounty-economics (this repo) owns the schema: schemas/ledger.schema.json, plus the validator and
> the taxonomies. viability-gate (../viability-gate) owns the CLI. Its vg init scaffolds a ledger,
> and its LedgerEntry model deserializes one. Nothing enforces that those two agree except this
> file. — tests/test_compat_viability_gate.py:6-13

"One dialect" is enforced mechanically, at a pinned tag, in both directions:

- The pin: `PINNED_VG_TAG = "v0.5.0"` (tests/test_compat_viability_gate.py:59). It must be declared
  exactly once in the repository — `test_the_pin_is_declared_exactly_once` (151-163) fails if the
  string appears in any other `.py` file — and look like a tag (166-167).
- Forward: `vg init`'s scaffold, filled in the way a researcher would, must produce zero errors
  from this repo's validator (`test_vg_init_ledger_satisfies_our_schema`, 210-241), and the
  scaffold must offer no shape or clause class this repo does not ship
  (`test_vg_init_offers_no_shape_or_class_we_do_not_have`, 245-266) — including the removed
  `any` shape, whose reappearance in the scaffold is an explicit assertion (256).
- Reverse: this repo's shipped example ledger must be parseable by `vg`
  (`test_our_example_ledger_is_readable_by_vg`, 273-291 — `vg gates` exit 2 is the parse-failure
  signal), and additive fields vg does not read (`schema_version`, `notes`) must not break it
  (295-322).
- Semantics, not just parsing: an unstated floor must FAIL vg's G1
  (`test_vg_fails_an_unstated_floor`, 346-369); every exclusion pattern this repo ships or
  suggests must compile in vg's G2 (373-396); and vg's G2 must actually run a ledger pattern over
  a draft and name the clause (400-413).

The regex dialect is the concrete artifact of "one dialect": viability-gate compiles patterns with
Rust's `regex` crate, case-insensitively, which has no lookaround and no backreferences, so the
validator rejects them here too (`_dialect_problem`, scripts/validate.py:159-230) and compiles
every accepted pattern with `re.IGNORECASE` (scripts/validate.py:242). The in-repo half of the
contract always runs: the examples, the schema and the taxonomies must agree with each other
(tests/test_compat_viability_gate.py:178-203).

## The data files

### data/tier-shapes.yaml — the 5 tier shapes

Header comment (lines 1-20) states the file's contract: it is DATA and the shared source of truth;
it contains no program data; and it names the two things it deliberately does not say (no `any`
shape; an unstated floor is not `low_and_above`). Top level: `version: 1` (22) and `shapes:`
(25), ordered "narrowest floor first" (24). Each entry carries:

- `id`, `pays` (the severities paid), `floor` (the lowest severity paid, null for unknown);
- `implication` and `risk` — one-line and longer judgement text;
- `detection` — a list of signals for classifying a reward table into this shape;
- `verify` — what to do before hunting.

The five, with their `pays`/`floor` as loaded:

| id | line | pays | floor |
|---|---|---|---|
| `critical_only` | 26 | critical | critical |
| `high_and_above` | 43 | critical/high | high |
| `medium_and_above` | 55 | critical/high/medium | medium |
| `low_and_above` | 66 | critical/high/medium/low | low |
| `unknown` | 99 | (nothing) | null |

Two load-bearing comment blocks: the removal rationale for the `any` shape under
`low_and_above` (82-97) — "A shape that reads as a green light is worse than no shape" — and the
`unknown` entry itself, whose `risk` field says "THE DANGEROUS VALUE" (105-108). The 0.5.0
release removed a platform product name from the `critical_only` detection signals
(line 35 of the 0.4.x file; the rewritten wording is data/tier-shapes.yaml:37 today); the
identity token now lives only in `scripts/token_scan.py` and in
git history (see
[The repository guards](#the-repository-guards)).

### data/clause-classes.yaml — the 14 exclusion-clause classes

Header (1-13): classes only, "industry-standard wording that appears in almost identical form
across programs", nothing quoted from a specific program; `suggested_pattern` is a starting regex
where "a match is a prompt to check, not an automatic reject". Top level: `version: 1` (15) and
`classes:` (17). Each entry carries `id`, `kills` (what the clause excludes), 
`typical_wording` (list of generic example wordings), `escape` (the escape hatch — the argument
that the finding survives the clause; for `known_issue` it reads "None"), and
`suggested_pattern` (all 14
classes ship one, and `test_every_suggested_pattern_is_in_the_common_dialect`
tests/test_validate.py:611-617 asserts each compiles in the common dialect).

The fourteen, in file order (id → start line → what it kills, abbreviated):

| # | id | line | kills (abbreviated) |
|---|---|---|---|
| 1 | `privileged_role` | 18 | anything requiring an admin, owner, operator or capability to act |
| 2 | `human_error` | 31 | admin mistakes, including unknowing admin harm |
| 3 | `admin_input` | 43 | unvalidated parameter supplied by a trusted role |
| 4 | `dos_no_extraction` | 53 | freezes/griefing/liveness attacks that do not transfer funds |
| 5 | `front_run_only` | 64 | attacks that need to win a mempool ordering race |
| 6 | `best_practice` | 74 | style, gas and convention deviations |
| 7 | `design_issue` | 84 | intentional tradeoffs you disagree with |
| 8 | `off_chain` | 95 | root causes in node logic, relayers, signers, backends |
| 9 | `third_party` | 105 | issues in oracles, bridges, external dependencies |
| 10 | `user_input` | 116 | findings whose precondition is the victim's own input |
| 11 | `known_issue` | 126 | anything in the prior-audit surface or known-issues list |
| 12 | `testing_limits` | 136 | proofs that require live-network execution |
| 13 | `non_standard_token` | 146 | fee-on-transfer, rebasing, unusual tokens |
| 14 | `scope_boundary` | 157 | root causes outside the named in-scope tree |

`escape` notes worth knowing as code, not prose: `privileged_role` (24-28) distinguishes "admin
acted maliciously" (out) from "reasonable admin action with a destructive second-order effect" (a
code defect, possibly in); `human_error` (36-40) explicitly says it "closes the privileged-role
escape hatch"; `known_issue` (131-134) is the one clause with no escape — "worth treating as
absolute".

### data/gate-crossref.yaml — the gate cross-reference

Header (1-19): the four repos share one gate vocabulary (documented in
rejection-taxonomy/data/SCHEMA.md and used by viability-gate); viability-gate's mapping runs one
way (anti-pattern → gate token); this file closes the loop from the other side for the gates
decided by the program's own terms. "It is a JUDGEMENT about which catalog answers a gate … not a
re-derivation against any dataset" (17-19). Two mappings:

- `answered_here` (25-52): five gates. `G1_severity_floor`, `program_ceiling` and
  `P16_below_floor` → catalog `tier-shapes`; `G2_exclusion_clause` → `clause-classes`;
  `G4_prior_audit` → `prior-audit-surface`, which the README documents in prose — "there is no
  catalog file for it yet, because an audit list, unlike a tier or a clause, cannot be published
  generically without naming the program" (48-52).
- `not_program_terms` (57-71): eleven gates whose signal lives elsewhere, each with a note saying
  where: `D1_duplicate_check`, `G3_scope_tree`, `G5_test_intent`, `P7_best_practice`,
  `P12_no_persisted_impact`, `P17_no_attacker_win`, `P18_design_tradeoff`,
  `P19_headline_mismatch`, `P20_cooperating_party`, `design_review`, `REALISM`.
  `design_review` was missing from both halves until 0.6.0, so the helper called a real shared
  token unknown. It is a no-impact review of the finding; the program-terms side of a design
  exclusion is the `design_issue` class, reached through `G2_exclusion_clause`.

[tests/test_crossref.py](tests/test_crossref.py) pins the file: every token must be inside the
hardcoded shared vocabulary `VALID_GATES` (27-44, 16 tokens, "Hardcoded on purpose"), no gate in
both halves (62-64), every answered gate names a real catalog with a `read` note (67-70),
catalog references resolve to real entries (73-80), the load-bearing pair
`G1 → tier-shapes` / `G2 → clause-classes` is present (83-87), and `scripts/crossref.py`
exits 0 for every known gate and non-zero for an unknown one (90-109).

The **cross-reference fields to the rejection-taxonomy vocabularies** are exactly these gate
tokens: the gate vocabulary itself is authored in `rejection-taxonomy/data/SCHEMA.md`; this repo
consumes it via `VALID_GATES` and `data/gate-crossref.yaml` and contributes no tokens of its
own. The README's rejection statistics (38% duplicates, 43/113; 23% out of scope, 26/113,
README.md) are quoted from the published rejection-taxonomy dataset at v0.6.0 (38.1% duplicates,
43/113; 23.0% out of scope, 26/113) and labelled as one researcher's log, "not an industry census".
v0.6.0 of that dataset did not change the triage counts.

## scripts/ — the validator, the resolver, the guards

### scripts/validate.py (768 lines)

The ledger validator and the tool that prints the taxonomies. Module docstring documents usage and
exit codes: 0 valid, 1 validation errors, 2 usage/parse error (20-23). PyYAML and jsonschema are
required imports with explicit exit-2 messages (36-46).

**Layout and data resolution.** `_data_root() -> Path` (49-60) finds the directory holding
`data/tier-shapes.yaml`: the repository (running from a checkout) or the package (installed —
the data ships inside `bounty_economics`). `ROOT`, `TIER_FILE`, `CLAUSE_FILE`,
`SCHEMA_FILE` are module constants (63-66); `SCHEMA_VERSION = 1` (71) is the ledger format
version this validator implements. Vocabulary constants: `FLOOR_SEVERITIES` (73),
`FLOOR_STATUSES` (82), `SLUG_RE` (84), `DATE_RE` (85), placeholder-host lists
`RESERVED_EXAMPLE_DOMAINS` / `PLACEHOLDER_HOSTS` / `PLACEHOLDER_SUFFIXES` / `PLACEHOLDER_LABELS`,
`STALE_DAYS = 180`, `today()` (UTC, the same clock viability-gate uses), and `_SCHEMA_COVERED`
(`{"required", "enum", "const", "pattern", "minLength"}` — schema findings the semantic layer
re-reports with better messages, so they are suppressed in `schema_errors`). The regex dialect
is a scan (`_dialect_problem`), not five probes over the pattern text: a probe for `*+` also
matched inside a character class.

**Functions, in call order:**

- `placeholder_host(url: str) -> str | None` — the placeholder host in a URL, or None.
  Matches the URL's HOST (via `urlparse`), never a substring. Reserved documentation domains
  `example.com`, `example.org` and `example.net`, including every subdomain; exact hosts
  `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`; suffixes `.invalid` and `.localhost`; or a
  `todo`/`tbd`/`changeme` host label. `myexample.com` is a different name and is not flagged.
  Host matching (rather than a substring of the whole URL) is the 0.5.0 fix for "a real
  repository called todo-list is not a placeholder"; subdomains of the reserved example domains
  are the 0.6.0 fix.
- `regex_problem(pattern: str) -> str | None` — why a pattern is unusable by BOTH tools. The
  scan rejects lookaround, atomic groups, comment groups, conditionals, backreferences
  (including `\0` and `\g`), Python-only flags `(?a)` / `(?L)`, the `\Z` end marker, and
  possessive quantifiers (`++`, `*+`, `?+`, `{n}+`). Possessive `++` compiles in Rust regex
  1.13 as a nested quantifier, so both engines accept the text and disagree on the language.
  A character class such as `[*+]` and a literal brace `a}+` are not possessive and are
  accepted. Anything else must compile under `re.IGNORECASE`. A blank pattern, or one with
  surrounding whitespace, is an error in `validate_entry`: viability-gate trims before
  compiling and treats a blank pattern as untested.
- `load_taxonomies() -> tuple[dict[str, dict], dict[str, dict]]` (248-260) — parses both data
  files and returns id-keyed maps; exit 2 if either file is missing. This is the function the
  other scripts and the tests import.
- `entry_validator() -> jsonschema.protocols.Validator` (266-275) — lazily builds a validator for
  ONE entry: the schema's `items` plus the top-level `$schema`, with the format checker
  attached. Cached in `_ENTRY_VALIDATOR` (263).
- `schema_errors(entry: dict, where: str) -> list[str]` (278-285) — sorted schema findings: iterates `entry_validator().iter_errors`, skips validators in `_SCHEMA_COVERED`,
  formats each as `{where}: schema: {path}: {message}`.
- `validate_entry(...)` (288) — the semantic pass over one entry; returns (errors, warnings).
  Checks, in order: mapping-ness and a slug-shaped `id` (308-314); JSON Schema on a copy whose YAML
  date is normalized to ISO text and whose citation strings are stripped, so one mistake is not
  reported twice; `schema_version` (331) — a version this validator does not implement is an
  error naming CHANGELOG.md; `tier_shape`, including the removed `any` migration (344-353), which
  distinguishes an explicit NONE floor from an absent one; a warning when the shape is
  `unknown` ("NOT permissive") or pays two or fewer severities; `floor_severity`, including the
  rejection of `informational` (372-379) and a warning when it disagrees with the shape (G1 uses
  the stricter of the two); `floor_status` (401-456), with the unstated/documented/conflicting
  contradictions as errors; citation (459-485), placeholder host as an error or, in example mode, a
  warning; `retrieved` (487-523), age counted by `today()` in UTC, future as an error, older than
  180 days as a warning; exclusions (525-563), including an empty or padded `pattern`; prior audits
  (565-585), warning when `url` or `covers` is missing.
- `print_taxonomy` (590) — the text rendering CI smoke-tests.
- `taxonomy_payload` (600) — the machine-readable form: `schema_version`, then `tier_shapes`
  and `clause_classes`, each with `source`, `count` and full `items`.
- `main` (617) — argparse: zero or more ledger paths, `--strict`, `--example-mode`,
  `--taxonomy`, `--format {text,json}`. `--taxonomy` prints and returns 0. Each file is read
  as a single YAML document (`utf-8-sig`, 675); a second document is exit 2. The value must be
  a list. `example_mode` is explicit or the filename ends `.example.yaml`. Duplicate ids are
  tracked only when `id` is a string, so a list or mapping is a schema error rather than a
  crash. JSON output carries `schema_version`, `ok`, `strict`, `ledgers`, `entries`, `errors`,
  `warnings`, plus a single `ledger` key only when exactly one file was given (741-742). Exit 1
  when any error exists or when `--strict` promotes warnings.

  **Error-report behaviour.** Text mode: warnings to stdout prefixed `WARN `, errors to stderr
  prefixed `ERROR `, then a blank line and a per-file and total count line (750-762). JSON mode:
  one object; usage failures (`fail`, 645-650) print `{"ok": false, "error": ..., "exit_code": …}`
  and return the code. The JSON verdict is produced by the same pass as the text verdict — pinned
  by `test_json_format_is_the_same_verdict_as_text` (tests/test_validate.py:408-414).

### scripts/crossref.py (165 lines)

Resolves a gate token to this repo's catalogs. `CATALOGS` (49) maps the three catalog names —
`tier-shapes`, `clause-classes`, `prior-audit-surface` (the last "(prose only — see the
README)"). `load_crossref()` (56) parses the data file (exit 2 if missing);
`catalog_entries()` (63) returns the ids a catalog publishes, via `load_taxonomies` — empty for
the prose catalog. `print_gate()` (97) prints the mapping and its `read` note, the entries for
data-backed catalogs, or — for a gate in `not_program_terms` — "not answered by this repo's
catalogs" plus where the signal lives; an unknown token prints the sorted known-gate list to
stderr and exits 1. `gate_record()` (73) is the same resolution as a dict.
`print_all(cross: dict) -> int` renders both halves. `gate_record` is the one-gate JSON object.
`main` takes an optional gate token and `--format {text,json}`. JSON with no gate dumps the whole
mapping; JSON with a gate dumps that record, and an unknown token exits 1. The data path is
`validate.ROOT`, so a wheel import finds `gate-crossref.yaml` inside the package. Verified output:
`python scripts/crossref.py G2_exclusion_clause` prints the clause-classes catalog with its 14
entries; `G1_severity_floor` the 5 tier-shape ids; `NOT_A_GATE` exits 1.

### scripts/token_scan.py (100 lines)

The identity-token vocabulary and the one matcher everything else imports. `TOKENS` (32-39) is a
35-entry tuple of chain, ecosystem, platform and platform-rule tokens; `PLATFORM_TOKENS`
(46-62) is the 15-entry subset that names a third-party bug-bounty platform, a platform product
or a platform-specific rule term (added in 0.5.0 after a product name shipped undetected through
0.4.x; CHANGELOG.md:111-116). The matcher implements an explicit word boundary —
`(?<![A-Za-z0-9_]) TOKEN (?![A-Za-z0-9_])` (docstring 9-23; `pattern(token)` 67-71) — the fix
for the old matcher that flagged words merely containing a token (a `suite`/`nearest` class of
false positive; pinned in tests/test_token_scan.py:29-52). `compiled(tokens)` (77-80) caches;
`scan_line` (83-85), `scan_text` (88-94) and `scan_tokens` (97-100) are the three scan
entry points. This module is the ONLY file allowed to contain the tokens
(check_hygiene.ALLOWED, scripts/check_hygiene.py:69-71).

### The repository guards

Four scripts CI runs as steps; each is also importable so the tests run the same check.

- **[check_generic.py](scripts/check_generic.py) (102 lines)** — the shipped data stays generic.
  `scan(text) -> list[str]` (49-62) reports three failure classes: a `PLATFORM_TOKENS` hit
  (via `token_scan.scan_tokens`), the literal host fragment `gitlab.com/` (37), and any
  `github.com/<org>/<repo>` URL whose slug does not start with the project's own `khomdev/`
  namespace (39-44, 58-61) — so the schema's own `$id` is allowed. Default targets are
  `data/*.yaml` and `schemas/*.json` (46); exit 0 clean / 1 problems / 2 usage (18-21).
- **[check_hygiene.py](scripts/check_hygiene.py) (260 lines)** — the whole repository, including
  prose and scripts. `iter_files()` (76-103) lists exactly what git would commit (tracked plus
  untracked-not-ignored; falls back to a directory walk skipping `SKIP_DIRS`, 38-48). Three
  working-tree checks plus one history check:
  - `check_encoding`: reads bytes. A leading UTF-8 BOM and a file that is not valid UTF-8 are
    errors (a non-UTF-8 file used to be skipped). Eight mojibake sequences — the UTF-8-as-cp1252
    signatures — are still checked in the decoded text.
  - `check_tripwires` (135-150): every `TOKENS` hit outside the one allowlisted file.
  - `check_private` (153-167): six private-path prefixes (61-64).
  - `check_history` (170-206): re-scans every blob in every commit — "a token deleted in a later
    commit is still in the history forever" — using the same allowlist. Running it today reports
    20 hits: the platform product name removed in 0.5.0, still present in tags up to and including
    `v0.4.1` (the 0.5.0 changelog records that "Earlier tags still contain the old text; git
    history is not rewritten here", CHANGELOG.md:116-117). This is why CI runs the script with
    `--no-history` (.github/workflows/ci.yml:68-73): published history is an owner decision, not
    a CI fix.
  `main` (209-256): `--json`, `--no-history`; exit 0 only when clean.
- **[check_links.py](scripts/check_links.py) (106 lines)** — every relative link in every
  repository `.md` file resolves. `LINK_RE` (25) extracts markdown links; http(s), mailto and
  pure-fragment targets are ignored (29); a relative target must exist on disk (61-63), and a
  `#fragment` on a `.md` target must match one of its headings under a simplified, best-effort
  slug rule (32-41, 65-73). Exit 0 clean / 1 problems. This is the check this document itself must
  pass.
- **[check_markdown.py](scripts/check_markdown.py) (102 lines)** — tracked `.md` files render:
  no line starting with a backtick-at ("a code fence is three backticks", 57-61), no line holding
  a lone backtick (62-66), an even number of ```` fence lines per file (67-69), and every
  `bounty-economics/tree/vX.Y.Z` link in README.md names the version in pyproject.toml (78-80).
  Built after a shell rewrite mangled fences across the sibling repositories (docstring 4-16).

## examples/

Both files are FICTIONAL, use the reserved `.invalid` TLD, and auto-enable example mode by
filename (scripts/validate.py:672), so the placeholder-host check warns instead of erroring.

- **[ledger.example.yaml](examples/ledger.example.yaml)** (43 lines, 1 entry) — the shape of a
  full entry: every optional block populated. `example-lending-v2` (11) is
  `medium_and_above`/`documented`/`medium` with a quoted `retrieved` date (17), a one-item
  `conflicts` list (18-19), four exclusions (20-32: `privileged_role`, `dos_no_extraction`,
  `best_practice`, `scope_boundary`, each class + verbatim clause + pattern), one prior audit
  (33-41: firm, url, two covered files, two verbatim known issues), a `post_audit_delta` (42)
  and a `notes` decision line (43).
- **[tier-shapes.example.yaml](examples/tier-shapes.example.yaml)** (131 lines, 5 entries) — one
  entry per tier shape, in taxonomy order, "the fastest way to learn to classify a reward table"
  (README.md:64-66). The contrast is the content: `example-perps-critical-only` (15) carries a
  DECISION note not to hunt Medium theses; `example-vault-high-and-above` (48) asks whether a
  mechanism composes to High; `example-lending-medium-and-above` (68) notes the Medium amount
  sets whether the work pays; `example-dex-low-and-above` (100) notes duplicate risk on a wide
  floor; `example-untranscribed` (121) is the load-bearing one — `tier_shape: unknown` +
  `floor_status: unstated` + `floor_severity: null` + `exclusions: []`, "do not hunt until the
  rewards page has been read". `test_the_worked_example_has_one_entry_per_shape`
  (tests/test_counts.py:52-56) pins the one-entry-per-shape, 5-in-total structure, and
  `test_the_unstated_example_keeps_tier_shape_unknown` (86-91) pins entry 5's exact posture.

## tests/

Seven suites, 175 collected tests. Collected counts by file: test_validate.py 99, test_counts.py
27, test_compat_viability_gate.py 13, test_generic.py 10, test_crossref.py 11, test_token_scan.py
9, test_code_guide.py 6. test_validate.py collects 99 cases from 66 functions; the extra cases are the parametrized
regex, real-URL and placeholder-host rows.

- **[test_validate.py](tests/test_validate.py) (769 lines, 66 test functions; 99 collected)**
  pins validator behaviour, grouped by section headers: taxonomies (75-120 — five shapes, no
  `any`, `low_and_above` is the widest, no informational floor, fourteen classes, every class
  has `kills` and an `escape` key); citation (126-169 — missing `source_url`/`retrieved`
  fail; the unquoted-YAML-date case is accepted with a warning; a placeholder host fails in a
  real ledger and only warns in example mode); tier shape (175-214 — the `any` migration message
  names the replacement; `informational` floors are rejected with a 'low' suggestion; a
  shape/floor mismatch warns); floor_status (224-291 — the whole unstated-floor doctrine as
  pass/fail facts); schema_version (297-304); exclusions (310-341); prior audits (347-356);
  `--format json` (362-465 — valid, failing and missing-file ledgers, machine-readable taxonomy,
  text/JSON verdict equality, several ledgers in one run, one failure failing the run, `--strict`
  promotion); and a runner (474-533) so the file also works without pytest. The 0.5.0 audit-fix
  tests (542-765) each pin a reproduced defect: unknown top-level and nested keys, wrong types,
  no double report for a missing citation, five unsupported-regex constructs, real URLs containing
  placeholder words, placeholder hosts caught by host, future dates, a conflicting floor beside a
  settled shape, the any-migration wording, and README/schema agreement on an explicit NONE floor.
- **[test_counts.py](tests/test_counts.py) (255 lines, 27 functions)** — the drift alarm. Exists
  because "the README advertised 'six fictional entries, one per tier shape' for a file that has
  five" (docstring 4-7). Sections: the worked example (52-91), the README (116-170 — quotes real
  counts, no retracted claims; `RETRACTED_CLAIMS` at 141-148 is a five-entry tuple of exact
  removed sentences), the schema (176-255 — versioned `$id`, enums equal the taxonomies,
  required fields, closed to unknown fields, examples validate, negatives fail). This is the suite
  that forces a taxonomy change to update the data file, the schema enum and the README together.
- **[test_compat_viability_gate.py](tests/test_compat_viability_gate.py) (413 lines, 13
  functions)** — the cross-repo contract, described in
  [The one-dialect contract with viability-gate](#the-one-dialect-contract-with-viability-gate).
  Operationally: `SIBLING` is `$VG_SIBLING` or `<repo parent>/viability-gate` (63);
  `_skip_reason()` (72-87) returns why the cross-repo half cannot run (no sibling, no git, no
  pinned tag, no cargo); `REQUIRED` (91) flips every skip into a failure when
  `BE_COMPAT_REQUIRED=1`; the module-scoped `vg_binary` fixture (99-145) extracts the sibling
  at the tag with `git archive` — "a test must not add state to somebody else's checkout" — and
  builds it with `cargo build --locked`. Locally the cross-repo half SKIPS with the reason
  printed by `-rs` (CI sets `BE_COMPAT_REQUIRED=1` and runs it for real,
  .github/workflows/ci.yml:111-143); the in-repo half (178-203) always runs.
- **[test_crossref.py](tests/test_crossref.py) (160 lines, 11 functions)** — the gate
  cross-reference stays inside the shared vocabulary and composes with the catalogs (the
  [data/gate-crossref.yaml](data/gate-crossref.yaml) section above describes every assertion).
- **[test_generic.py](tests/test_generic.py) (67 lines, 10 functions)** — the genericity check:
  shipped files clean, the schema's `$id` allowed, platform names caught (including
  case-insensitively), foreign GitHub and gitlab links caught, our own repo links allowed, and
  the command's exit codes (1 for a bad file, 2 for usage errors, 2 when there is nothing to
  scan).
- **[test_token_scan.py](tests/test_token_scan.py) (111 lines, 9 functions)** — the matcher
  fixtures: 15 English words containing a token pass (`CONTAINS_A_TOKEN`, 29-45); every declared
  token fails when standing alone, read from the vocabulary so the fixtures cannot drift from the
  list (55-60); the boundary is a word boundary, not a substring (63-66); the allowlist is exactly
  `{"scripts/token_scan.py"}` (69-70); the checks and the tests share one matcher —
  `check_hygiene.scan_text is token_scan.scan_text` (73-78); every platform token is caught by
  the genericity scan (81-83); and a leak in a temporary tree is reported (104-111).
- **[test_code_guide.py](tests/test_code_guide.py) (210 lines, 6 functions)** — the guide's own
  references and counts stay current: every "(N lines)" claim, every function or constant line
  range in the script and test sections, the collected-test and suite counts, and the stated
  version are re-derived from the files, so a stale reference fails the suite.

## CI, release and versioning

**[`.github/workflows/ci.yml`](.github/workflows/ci.yml)** (153 lines) — two jobs, `on:`
push to main and all pull requests, `permissions: contents: read`:

- **`validate`** (12-109): a `fail-fast: false` matrix over Python 3.10/3.11/3.12/3.13 on
  ubuntu-latest. Steps: install exact tool versions from requirements-ci.txt (PyYAML 6.0.3,
  jsonschema 4.26.0, pytest 9.1.1, ruff 0.17.0; Dependabot proposes bumps); `pytest tests/ -q
  -rs` (the `-rs` "prints the reason for every skip, so a skipped cross-repo assertion is
  visible rather than invisible", 29-30); `ruff check .`; `validate.py examples/*.yaml`;
  `validate.py --taxonomy` and its `--format json` variant; `check_generic.py` (step comment
  45-53 explains why this replaced the old raw grep for `github.com/`, which flagged the
  schema's own `$id`); `check_links.py`; `check_markdown.py`;
  `check_hygiene.py --no-history` (comment 69-72 explains the flag); a placeholder-host
  negative test (75-92: a real-mode ledger citing `example.invalid` must FAIL validation);
  and a wheel-install test (94-109): build a clean venv, `pip install .`, run
  `bounty-econ-validate --taxonomy` and a ledger through `--format json` from OUTSIDE the
  checkout, and assert no top-level `validate` module landed in site-packages — the 0.5.0 fix
  for the broken non-editable install (CHANGELOG.md:133-138).
- **`compat`** (111-143): Python 3.12, env `BE_COMPAT_REQUIRED: "1"` ("Every skip reason (no
  sibling, no pinned tag, no cargo) fails instead", 122-123), clones viability-gate with
  `--filter=blob:none` (carrying every tag, so the pin stays in exactly one place) into the
  workspace's parent directory, and runs `pytest tests/test_compat_viability_gate.py -q -rs`.

**Packaging** (pyproject.toml): `bounty-economics` 0.6.1, `requires-python >= 3.10`, runtime
deps `pyyaml>=6` and `jsonschema>=4.18`; `dev` extras pytest and ruff. The packaging trick
is at 43-53: `scripts/` is mapped to the package `bounty_economics` (`[tool.setuptools.package-dir]`),
with `data/` and `schemas/` re-mounted inside it as package data — that is why
`_data_root()` finds the taxonomies in an installed copy and why nothing is installed as a
top-level module. Console script: `bounty-econ-validate = "bounty_economics.validate:main"`
(32-33). Ruff config: py310 target, line-length 100, `E501` ignored, rule set
`E,F,W,I,UP,B,RUF`, `B011` ignored in tests (60-73). Pytest config: testpaths tests,
pythonpath scripts (55-58) — which is how the tests import the scripts without installing
anything.

**Release and versioning** (CHANGELOG.md:1-7): Keep-a-Changelog format; "versions track the
ledger schema"; "Nothing here has been published to a package index. Publishing is a human
decision, not a build step." History note at 9-14: repository history was reset on 2026-10-10 to
remove identifying material from earlier commits. Tag history on main: 0.2.0 (2026-10-14), 0.3.0
(2026-10-21), 0.4.0 (2026-10-28), 0.4.1 (2026-11-05), 0.5.0 (2026-11-06), 0.6.0 (2026-11-09),
0.6.1 (2026-11-10); each release's notes record what changed and, for the taxonomy-review
releases (0.3.0, 0.4.0), the explicit "no new class" conclusion. `CITATION.cff` carries the
same version (0.6.1) and
release date. `scripts/check_markdown.py` fails if that version, the latest CHANGELOG heading
and `pyproject.toml` disagree. A README
link pinning a tag must name the current version or `check_markdown.py` fails
(scripts/check_markdown.py:69-77).

**SECURITY.md** (41 lines) defines the two realistic issue classes for a repo with no server — a
code-execution/file-write flaw in the scripts reachable via a hostile ledger, and a disclosure
(an identifying token in a public file) — and routes reports through GitHub private vulnerability
reporting, not public issues (16-21).

## Known limitations

As documented (README.md:475-492), verbatim in substance: this is a reading aid, not a
measurement — the taxonomies have not been validated against a labelled corpus of program pages
because no such corpus is shipped; the rejection figures describe one researcher and are not an
industry census; the unknowing-admin-harm framing is unproven (no successful instance in the
author's log; some programs exclude it via `human_error`); the compat test covers exactly one
viability-gate tag (`v0.5.0`) until the pin is bumped; no example has been checked against a
real program page (all use `.invalid`); the ledger format is a convention, not an enforcement
mechanism — "Nothing stops you writing a floor you never read; `floor_status` only makes the
gap visible"; and `floor_status: conflicting` is reported, not resolved.

Two structural limits worth knowing when extending this document's subjects: the JSON Schema's
`uri` format assertion depends on the jsonschema installation's format checkers (the validator's
own http(s) check does not), and `check_history` reports tokens that exist in published history
by design — removing them is a history rewrite, which CHANGELOG.md:116-117 explicitly declines.

## How this document is verified

Every factual claim above was checked against the 0.6.1 tree:

- Path:line references were written from a full read of every file they cite.
- Counts were derived by loading the files: 5 tier shapes and 14 clause classes
  (`load_taxonomies()` over data/*.yaml), 12 entry properties, 3 exclusion properties, 4
  prior-audit properties (schemas/ledger.schema.json), 35 identity tokens and 15 platform tokens
  (scripts/token_scan.py), 5 answered and 11 not-answered gates (data/gate-crossref.yaml; 16 tokens in total),
  1 + 5 example entries, and the per-suite collected counts (pytest --collect-only per file;
  175 in total).
- Behaviour claims were exercised: `python scripts/validate.py` on the examples (6 entries, 0
  errors, 10 warnings), `--taxonomy` text and JSON, `crossref.py` for answered, not-answered
  and unknown tokens, the placeholder-host negative case, a clean-venv wheel install run from
  outside the checkout, and the full local suite — pytest (including the cross-repo half, via the
  documented `VG_SIBLING` override), ruff, and all four guards.
- This file is itself subject to the repository checks: every relative link here must resolve
  (`check_links.py`), it must not trip the identity-token or mojibake scanners
  (`check_hygiene.py`), and CI re-runs the whole suite with this file present.

[v0.5.0]: https://github.com/KhomDev/bounty-economics/releases/tag/v0.5.0

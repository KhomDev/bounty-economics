# bounty-economics

**A framework for reading a bug-bounty program's terms before you hunt: payout tiers,
exclusion-clause classes, and prior-audit surfaces.**

The most expensive lesson in bug bounty is not "you missed a bug." It is:

> **You found a real, working, PoC-backed bug — and the program could not pay you for it.**

This repo is the *method* for avoiding that, plus a schema for building your own private ledger
of the programs you hunt.

**It ships no program data.** No names, no chains, no reward tables. Your ledger is yours.

---

## Why the method matters more than a dataset

A published table of "program → payout floor" would be useless within a month: programs change
their reward tables without notice, and a stale floor is worse than no floor because you trust it.

What does not go stale is the **structure** of the problem:

- Every program's reward table resolves to one of a small number of **tier shapes**.
- Every program's scope page contains exclusions that fall into a small number of **clause classes**.
- Every program has a **prior-audit surface** that is already closed.

Learn the three taxonomies, apply them to the live program page, and you get the answer yourself —
current, and cited.

## What is in here

`
data/tier-shapes.yaml               the 5 tier shapes, with detection and risk notes
data/clause-classes.yaml            the 14 exclusion-clause classes, with escape hatches
schemas/ledger.schema.json          JSON Schema (v1) for a private ledger
scripts/validate.py                 validates a ledger; --taxonomy prints the vocabularies
scripts/check_generic.py            fails if a taxonomy or the schema names a platform or a foreign repo
examples/ledger.example.yaml        one fictional entry, showing the shape
examples/tier-shapes.example.yaml   five fictional entries, one per tier shape
`

Both vocabularies are **data**, not prose, so the documentation, the schema and the validator
cannot drift apart. `validate.py` reads them at runtime.

```bash
python scripts/validate.py --taxonomy                     # print both vocabularies
python scripts/validate.py my-ledger.yaml                 # validate your ledger
python scripts/validate.py my-ledger.yaml --format json   # machine-readable result
python scripts/validate.py examples/tier-shapes.example.yaml
```

`examples/tier-shapes.example.yaml` is worth reading once: five fictional programs, one per tier
shape, each with the decision the shape forces written out. It is the fastest way to learn to
classify a reward table.

## 1. Payout tier shapes

The single most consequential field. Classify every program you consider:

| Tier shape | Pays | Implication |
|---|---|---|
| `critical_only` | Critical | **Everything below Critical is worth $0.** A Medium-class thesis has an expected value of zero here, however correct it is. |
| `high_and_above` | Critical, High | Medium and below are unpaid. |
| `medium_and_above` | Critical, High, Medium | The most common shape. Low and informational unpaid. |
| `low_and_above` | Critical → Low | Low is the lowest tier that pays, and the reward table has to say so. |
| `unknown` | — | **The dangerous one.** Not yet transcribed. Treat as an unhedged bet, never as permissive. |

### "No severity floor" is not a shape — and it is not evidence

Two situations look alike on a scope page. They are not the same ledger entry, and collapsing
them is the defect this field exists to prevent:

| What the page says | `floor_status` | `tier_shape` |
|---|---|---|
| A reward table with a Low row and a non-zero amount | `documented` | `low_and_above` |
| `SEVERITY FLOOR: NONE` or `SEVERITY FLOOR: any`, in those words | `documented` | `low_and_above` |
| Nothing about a floor anywhere on the page | `unstated` | `unknown` |
| Two of the program's own pages disagree | `conflicting` | `unknown` |

An **unstated** floor is not evidence that Low pays. It is evidence that the rewards page has
not been read. Transcribing it as `low_and_above` manufactures a permissive-looking floor out
of an unread page — and a floor you invented is worse than no floor, because you will act on it.
That is the same failure as reading `unknown` as "pays everything", one step earlier.

So an unstated floor keeps `tier_shape: unknown`. `validate.py` **errors** if you write
`floor_status: unstated` beside any other shape, and **warns** even when you get it right,
because the entry is a gap in your ledger rather than a property of the program.

An explicit `NONE` / `any` floor is different. The program has *stated* something, you have
read it, and the statement is that no severity bar applies. Informational findings are still
acknowledged rather than paid, so the lowest tier that actually pays is Low:
`low_and_above`, with `floor_status: documented`.

### Why there is no `any` shape

An earlier version of this taxonomy carried a sixth shape, `any`, for programs whose reward
table assigns a non-zero amount to informational findings. It was removed for a reason worth
keeping: the shape put an informational floor in the ledger, which made a hardening note look
payable and made a genuinely wide-floor program look narrower than it is.

**A shape that reads as a green light is worse than no shape**, whether or not anyone has met a
program that fits it. This repository ships no count of how often such a program was met, so it
makes no claim about that — and no claim should be read into the removal.

### The two failure modes this prevents

**Mode 1 — the floor is above your finding.** You confirm a real Medium with a working PoC. The
team agrees it is real. The reward table has no Medium row. Payout: zero.

**Mode 2 — you misread "unknown" as "pays everything".** A program whose reward table you never
read is not a program that pays everything. It is a program you know nothing about.

### How to transcribe a tier

1. Open the program's live scope/rewards page.
2. Find the reward table. Record **every** severity row and its amount or range.
3. Note the **lowest severity with a non-zero reward** — that is the floor.
4. If the page states no floor anywhere, set `floor_status: unstated` and leave
   `tier_shape: unknown`. Do **not** write `low_and_above`: that is a claim you have not
   earned. If the program states `NONE` / `any` explicitly, set `floor_status: documented`
   and record the shape those words imply.
5. Record the URL and the date you read it.
6. Re-check before submitting anything. A floor read three months ago is a guess.

> **The trap:** some programs publish two different numbers — a "prize pool" and a "rewards" total,
> or a scope table that labels an asset `Critical` while the reward table pays it at `High`. When
> the two disagree, the **reward table** governs what you are paid. Record the conflict explicitly
> rather than resolving it silently.

## 2. Exclusion clause classes

Almost every program's scope page carries a list of out-of-scope categories. They are worded
differently everywhere and mean one of a dozen things. Classify each clause you find:

| Class | Typical wording | What it kills |
|---|---|---|
| `privileged_role` | "attacks requiring access to privileged addresses" | Anything needing admin/owner/capability action |
| `human_error` | "human-based errors and rogue privileged users" | Admin mistakes, including *unknowing* admin harm |
| `admin_input` | "issues requiring admin input validation" | Unvalidated parameters supplied by a trusted role |
| `dos_no_extraction` | "DoS without enabling direct fund extraction" | Freezes, griefing, liveness attacks |
| `front_run_only` | "vulnerabilities exploitable through front-running only" | Mempool races — unless the attack is atomic |
| `best_practice` | "best-practice critiques", "optimization suggestions" | Style, gas, convention deviations |
| `design_issue` | "design issues that are not necessarily a security risk" | Intentional tradeoffs you disagree with |
| `off_chain` | "off-chain components are out of scope" | Node logic, relayers, signers, backends |
| `third_party` | "issues in external dependencies" | Oracles, bridges, other protocols |
| `user_input` | "issues arising from user input construction" | Self-inflicted preconditions |
| `known_issue` | "previously reported or acknowledged issues" | Anything in the prior-audit surface |
| `testing_limits` | "no mainnet or public-testnet testing" | PoCs that require live-network execution |
| `non_standard_token` | "fee-on-transfer/rebasing tokens" | Token-integration findings, unless listed |
| `scope_boundary` | "only files under `src/` are in scope" | Root causes outside the named tree |

Which classes actually waste submissions is a question about **your own** log. The numbers most
often quoted next to these classes — duplicates at 37% of rejections, exclusion-clause mismatches
at 27% — come from the author's private submission log. That is one researcher's log, **not an
industry census**, and it is not reproducible from this repository. Treat it as a prior, not a
number you can cite.

### Sometimes argued: unknowing admin harm

`privileged_role` and `human_error` are often argued to be a large source of wasted
submissions. Treat that as an argument, not a measurement:

- **It is not measured here.** This repository ships no industry-wide count of wasted submissions
  by category, and the author's own log contains **no successful instance** of the
  unknowing-admin-harm framing.
- **Many programs exclude it explicitly.** `human_error` ("human-based errors and rogue
  privileged users") is written to close exactly this door.
- **So read the clause, in full, on the program you are hunting** before spending hours on the
  framing. A regex match is a prompt to check, not a verdict — in either direction.

The distinction the argument rests on is still worth checking, because where it survives the
clause it is a real code defect:

- A finding that **requires** an admin to act maliciously is out of scope.
- A finding where a **reasonable admin action** has a non-obvious destructive second-order effect
  can be in scope — the admin is not misbehaving, the code is.

It is not a loophole; it is the difference between "the admin attacked the protocol" and "the
protocol broke when the admin did their job." It is also not a reliable payout:
`human_error` exists to exclude it, and usually does.

### Turning a clause into a test

Transcribe each clause as a **regex over your own finding description**, then run it. A match is a
prompt to check, not an automatic reject — over-trusting a regex manufactures false negatives,
which is its own expensive failure. [viability-gate](https://github.com/KhomDev/viability-gate)
implements exactly this.

## 3. Prior-audit surface

The surface that is already closed. Before hunting:

1. Collect every linked audit report, contest result and disclosure for the target.
2. Note which **files** and **functions** each one covers — not just the titles.
3. Record the **known issues** section verbatim (it is the program's own list of things not to
   report).
4. Note the **post-audit delta**: what changed after the last audit. That is where the unpicked
   fruit is.

Two traps:

- **A prior audit naming a file is not the same as covering your function.** Read the finding, not
  the table of contents.
- **Post-audit rewrites are the richest surface.** A large rewrite after the last audit is where
  new bugs live — and it is also where you are least likely to be duplicating.

## 4. The ledger schema

Build your own. Keep it **private** — it will contain program names, and your judgement about
them is not something to publish.

```yaml
# my-ledger.yaml  — PRIVATE, never commit
- id: <your-slug>
  schema_version: 1              # optional; absent means 1
  tier_shape: medium_and_above
  floor_status: documented       # documented | unstated | conflicting
  floor_severity: medium         # only when floor_status is 'documented'
  source_url: https://...        # the live rewards page
  retrieved: 2026-10-08
  conflicts: []                  # e.g. "scope table says Critical, rewards pay High"
  exclusions:
    - class: privileged_role
      clause: "<verbatim from the scope page>"
      pattern: "owner|admin|capability"
    - class: dos_no_extraction
      clause: "<verbatim>"
      pattern: "dos|freeze|lock"
  prior_audits:
    - firm: <name>
      url: https://...
      covers: ["src/Vault.sol", "src/Oracle.sol"]
      known_issues: ["<verbatim>"]
  post_audit_delta: "<module> +878 lines, <module> +182 lines"   # what changed since the last audit
```

An entry with no floor statement looks like this instead — and note that it is `unknown`, not
`low_and_above`:

```yaml
- id: <your-slug>
  schema_version: 1
  tier_shape: unknown            # the page has not been read
  floor_status: unstated         # no floor statement exists
  floor_severity: null
  source_url: https://...        # still required: cite the page you looked at
  retrieved: 2026-10-08
```

Write `retrieved` **quoted** (`retrieved: "2026-10-08"`). An unquoted YAML date is read as a
date object rather than a string, and the schema declares a string, so the validator warns — and
any JSON-Schema consumer would reject the entry.

`scripts/validate.py` checks a ledger against [`schemas/ledger.schema.json`](schemas/ledger.schema.json)
and against the shipped taxonomies: required fields, closed vocabularies for `tier_shape`,
`floor_status` and exclusion `class`, valid regexes, and a non-empty `source_url` +
`retrieved` date on every entry. **An uncited entry fails validation** — including yours and mine.

```bash
python scripts/validate.py my-ledger.yaml          # your private ledger
python scripts/validate.py my-ledger.yaml --strict # warnings become errors
python scripts/validate.py my-ledger.yaml --format json
python scripts/validate.py examples/ledger.example.yaml
python scripts/validate.py --taxonomy              # print both vocabularies
python scripts/validate.py --taxonomy --format json
```

`--format json` writes the same verdict as a JSON object — `ok`, `entries`, `errors`,
`warnings` — so a CI job or another tool can consume it without parsing prose. It is not a
second implementation: the exit code and the error list come from the same pass as the text
output.

It warns on the things that cost the most:

- **`floor_status: unstated`** — the floor is not evidence-backed. Do not read it as "Low pays";
  open the rewards page.
- **`floor_status` missing** — the validator cannot tell a floor you read from one you assumed.
- **`tier_shape: unknown`** — not permissive. An untranscribed program is an unhedged bet.
- **`tier_shape: critical_only` / `high_and_above`** — pays nothing below that bar, so confirm
  your thesis can reach it before hunting.
- **`retrieved` older than 180 days** — program terms change without notice; re-read the page.
- **`prior_audits[].covers` missing** — a report naming a file is not the same as covering your
  function.

It **errors** on the contradictions: an unstated floor beside a shape other than `unknown`, a
documented floor with no `floor_severity`, a documented floor beside `unknown`, a
`schema_version` this validator does not implement, and of course a missing citation.

It also flags a **floor conflict**: if `tier_shape` implies a floor of `medium` but
`floor_severity` says `high`, one of them is wrong and it says so.

Placeholder hosts (`example.invalid`, `localhost`, `todo`) are an **error** in a real ledger
and a warning in a file named `*.example.yaml`, so the shipped examples validate while a
copied-and-not-edited ledger does not.

### Tests

```bash
python -m pytest tests/ -q     # or: python tests/test_validate.py
```

Four suites:

- `tests/test_validate.py` — the validator's behaviour: an uncited entry fails, a placeholder
  host fails outside example mode, the removed `any` shape gets a migration message, an unstated
  floor cannot be written as `low_and_above`, and `--format json` reports the same verdict as
  the text output.
- `tests/test_counts.py` — the README, the taxonomy files, the schema and the worked example
  quote the same counts and the same vocabularies. This is the suite that keeps the counts in
  this README tied to the files they describe.
- `tests/test_generic.py` — the shipped taxonomies name no platform and no foreign repository.
- `tests/test_compat_viability_gate.py` — the cross-repo contract below.

### Schema and cross-repo version matrix

The ledger is a YAML **list** of entries, and the version lives in the schema's `$id` plus an
optional `schema_version` on each entry. The list shape is deliberate: `vg`
([viability-gate](https://github.com/KhomDev/viability-gate)) deserializes the file as a sequence,
so changing the root to a mapping would break a tool that reads the same ledger.

| bounty-economics schema version | viability-gate ledger version | Status |
|---|---|---|
| v1 | ledger v1 (`vg init`) | current |
| v1 | ledger v1, pre-versioning | entries with no `schema_version` are read as schema version 1; the validator warns if `floor_status` is absent |

`floor_status` and `schema_version` are **additive**. `vg` ignores fields it does not read,
so a v1 ledger written here stays parseable by it — but note that `vg` will *silently ignore*
`floor_status`, which is why the validator, not `vg`, is the thing that enforces the unstated
floor rule.

The pin lives in exactly one place: `PINNED_VG_TAG` in
[tests/test_compat_viability_gate.py](tests/test_compat_viability_gate.py). That test checks both
directions at the pinned tag — `vg init` output must satisfy this repo's schema once filled in,
and a ledger this repo accepts must be readable by `vg` — and it **skips rather than fails**
when the sibling checkout `../viability-gate` is absent, when the pinned tag has not been
published, or when `git` is unavailable. The in-repo half of the contract (schema ↔ taxonomy ↔
example) always runs.

> **Current state:** the pinned tag `v0.1.0` does not exist in the sibling repository yet, so
> the cross-repo assertions **skip**. See "Known limitations".

### Install

```bash
python -m pip install -e ".[dev]"
bounty-econ-validate --taxonomy
bounty-econ-validate my-ledger.yaml --format json
```

CI runs pytest, ruff, the taxonomy print, the genericity check, the placeholder-host negative
test and the compatibility test on Python 3.10 through 3.13.

## What this repo deliberately does not contain

- **No program names.** Not one, not anonymised, not as an example.
- **No chains or ecosystems.** Which chains a researcher works on is itself identifying.
- **No reward tables.** They go stale, and republishing them detached from the live page invites
  reliance on a stale number.
- **No exclusion clauses quoted from any specific program.** Only the generic *classes*, which are
  industry-standard and appear across programs in almost identical wording.
- **No prior-audit lists.** Naming which audits cover which program identifies the program.

The taxonomies are the contribution. The instances stay with whoever read the page.

## How this relates to the other repos

| Repo | Question it answers | Ships |
|---|---|---|
| **bounty-economics** (this) | *Can this program pay for what I found?* | Taxonomies of program terms + ledger schema |
| [rejection-taxonomy](https://github.com/KhomDev/rejection-taxonomy) | *Why do findings fail after submission?* | Outcome taxonomy + aggregate stats |
| [viability-gate](https://github.com/KhomDev/viability-gate) | *Should I submit this specific draft?* | The CLI that runs both against your private inputs |

All three are methodology. None ships target data.

## Known limitations

- **This is a reading aid, not a measurement.** The taxonomies have not been validated against a
  labelled corpus of program pages, because no such corpus is shipped here.
- **The rejection figures are not reproducible from this repository.** The 37% duplicates / 27%
  exclusions split comes from the author's private submission log. It is not an industry census
  and it is not something you should cite as one.
- **The unknowing-admin-harm framing is unproven.** The author's log contains no successful
  instance; some programs exclude it explicitly via `human_error`.
- **The cross-repo compatibility test skips in this checkout**, because the pinned viability-gate
  tag is not published yet. Until it is, the two repos' formats are compatible by inspection, not
  by test.
- **No example has been checked against a real program page.** Every example uses the reserved
  `.invalid` TLD, and every program in them is invented.
- **The ledger format is a convention, not an enforcement mechanism.** Nothing stops you writing a
  floor you never read; `floor_status` only makes the gap visible.
- **`floor_status: conflicting` is reported, not resolved.** The schema gives you a place to
  record the disagreement; deciding which reading governs is still your call.

## Caveats

- **Program rules change without notice.** Every taxonomy here is a reading aid, not a substitute
  for the live scope page, which always outranks it.
- **This is not legal or financial advice.**
- **The classes are a starting vocabulary, not a closed set.** Widen them as you find clauses that
  do not fit; PRs adding a class with a generic, unattributed example are welcome.

## License

**The repository is MIT, as it stands.** This table records the *current* state; it does not
change any license.

| Path | License | Notes |
|---|---|---|
| `data/**` | MIT (`LICENSE`) | the two taxonomy data files |
| `schemas/**` | MIT (`LICENSE`) | `ledger.schema.json` (schema v1) |
| `scripts/**` | MIT (`LICENSE`) | `validate.py`, `check_generic.py` |
| `tests/**` | MIT (`LICENSE`) | pytest suites |
| `examples/**` | MIT (`LICENSE`) | fictional entries, `.invalid` hosts |
| `.github/**` | MIT (`LICENSE`) | CI workflow and issue templates |
| `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CITATION.cff` | MIT (`LICENSE`) | documentation |

No third-party program data is included or redistributed, so no third-party license applies to
anything shipped here. `SECURITY.md` carries a contact placeholder that is deliberately
unfilled — see that file.

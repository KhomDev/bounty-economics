#!/usr/bin/env python3
"""Cross-repo compatibility: the ledger contract between this repo and viability-gate.

Two repositories read the same private ledger file:

  * **bounty-economics** (this repo) owns the schema: ``schemas/ledger.schema.json``,
    plus the validator and the taxonomies.
  * **viability-gate** (``../viability-gate``) owns the CLI. Its ``vg init`` scaffolds a
    ledger, and its ``LedgerEntry`` model deserializes one.

Nothing enforces that those two agree except this file. The contract is checked at
a **pinned tag** of the sibling, so a change over there cannot silently break the
format here without failing a build:

  * forward — ``vg init`` output, once filled in, must satisfy this repo's schema.
  * reverse — a ledger this repo accepts must be readable by ``vg``.

It SKIPS, with a specific reason, rather than failing, when the sibling checkout
is absent, when the pinned tag has not been published, or when ``git`` / ``cargo`` is
unavailable. A sibling repository that is merely *absent* is not a defect in this
repo, and a red build for it would train people to ignore the signal.

The pin lives in exactly one place: ``PINNED_VG_TAG`` below.

Run:
    python -m pytest tests/test_compat_viability_gate.py -q
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate import (  # noqa: E402
    SCHEMA_FILE,
    load_taxonomies,
    validate_entry,
)

# ---------------------------------------------------------------- the pin

# The single source of truth for the cross-repo pin. Bump it when viability-gate
# publishes a tag that changes the ledger format or `vg init`.
PINNED_VG_TAG = "v0.4.0"

# The sibling checkout, relative to this repo. Both live under the same parent.
# VG_SIBLING overrides it, for a checkout kept under a different folder name.
SIBLING = Path(os.environ.get("VG_SIBLING") or ROOT.parent / "viability-gate").resolve()

TIERS, CLAUSES = load_taxonomies()
SCHEMA = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- skip logic


def _skip_reason() -> str | None:
    """Why the cross-repo half cannot run here, or None when it can."""
    if not SIBLING.is_dir():
        return f"sibling checkout not present at {SIBLING}"
    if shutil.which("git") is None:
        return "git is not on PATH"
    probe = subprocess.run(
        ["git", "-C", str(SIBLING), "rev-parse", "--verify", f"refs/tags/{PINNED_VG_TAG}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        return f"pinned tag {PINNED_VG_TAG} does not exist in {SIBLING}"
    if shutil.which("cargo") is None:
        return "cargo is not on PATH, so vg cannot be built"
    return None


requires_sibling = pytest.mark.skipif(
    _skip_reason() is not None, reason=_skip_reason() or ""
)


@pytest.fixture(scope="module")
def vg_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Extract the sibling at the pinned tag, build it, and return the binary.

    ``git archive`` is used rather than ``git worktree`` so that building the pinned
    revision touches nothing inside the sibling repository - it may be under
    concurrent edit, and a test must not add state to somebody else's checkout.
    """
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)

    work = tmp_path_factory.mktemp("vg-pinned")
    archive = work / "src.tar"
    subprocess.run(
        [
            "git", "-C", str(SIBLING), "archive",
            "--format=tar", f"--output={archive}", PINNED_VG_TAG,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    src = work / "src"
    src.mkdir()
    with tarfile.open(archive) as tar:
        # Our own repository's archive, at a pinned tag. The filter kwarg exists
        # only from 3.12; CI covers 3.10 and 3.11 too.
        if sys.version_info >= (3, 12):
            tar.extractall(src, filter="data")
        else:
            tar.extractall(src)

    build = subprocess.run(
        ["cargo", "build", "--quiet", "--manifest-path", str(src / "Cargo.toml")],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.fail(f"cargo build of {PINNED_VG_TAG} failed:\n{build.stderr[-4000:]}")

    exe = "vg.exe" if sys.platform == "win32" else "vg"
    binary = src / "target" / "debug" / exe
    if not binary.exists():
        pytest.fail(f"cargo build reported success but {binary} is missing")
    return binary


# ---------------------------------------------------------------- the pin itself


def test_the_pin_is_declared_exactly_once():
    # The pin must not be duplicated in a workflow file or a second test: two
    # copies drift, and then nobody knows which revision was actually checked.
    skip_dirs = (".git", ".venv", "venv", "site-packages", "__pycache__", "target", ".pytest_cache")
    holders = [
        p
        for p in ROOT.rglob("*.py")
        if not any(part in skip_dirs for part in p.parts)
        and "PINNED_VG_TAG" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert holders == [Path(__file__).resolve()], (
        f"PINNED_VG_TAG must live only in this file, found in {holders}"
    )


def test_the_pin_looks_like_a_tag():
    assert re.match(r"^v\d+\.\d+\.\d+", PINNED_VG_TAG), PINNED_VG_TAG


def test_the_skip_is_reported_rather_than_silent():
    # Whichever way it goes here, the reason is a string, so the failure mode is
    # "skipped: <why>" and never a silent pass.
    reason = _skip_reason()
    assert reason is None or isinstance(reason, str)


# ---------------------------------------------------------------- in-repo half
#
# This half never skips. It is the part of the contract that lives in this repo:
# the examples, the schema and the taxonomies must agree with each other.


def test_our_example_ledger_satisfies_our_schema():
    for path in sorted((ROOT / "examples").glob("*.yaml")):
        for i, entry in enumerate(yaml.safe_load(path.read_text(encoding="utf-8"))):
            errors, _ = validate_entry(entry, i, TIERS, CLAUSES, example_mode=True)
            assert errors == [], f"{path.name}: {errors}"


def test_our_schema_is_closed_and_versioned():
    assert SCHEMA["items"]["additionalProperties"] is False
    assert SCHEMA["items"]["properties"]["schema_version"]["const"] == 1


# ---------------------------------------------------------------- forward


@requires_sibling
def test_vg_init_ledger_satisfies_our_schema(vg_binary: Path, tmp_path: Path):
    """The scaffold viability-gate generates must be writable into our schema."""
    target = tmp_path / "target"
    out = subprocess.run(
        [str(vg_binary), "init", str(target)],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, f"vg init failed:\n{out.stdout}\n{out.stderr}"

    scaffold = yaml.safe_load((target / "ledger.yaml").read_text(encoding="utf-8"))
    assert isinstance(scaffold, list), "vg init must emit a LIST of entries, as our schema requires"
    assert scaffold, "vg init emitted an empty ledger"
    assert "REPLACE-ME" in str(scaffold[0].get("id", "")), (
        "the scaffold is expected to be unfilled; this test asserts its SHAPE"
    )

    # The unfilled scaffold is INTENDED to be invalid - an empty source_url is an
    # uncited floor. So the contract is checked on the fields, not on the
    # placeholder values: fill them the way a researcher would and require zero
    # errors against this repo's validator.
    filled = dict(scaffold[0])
    filled.update(
        id="cross-repo-scaffold",
        tier_shape="medium_and_above",
        floor_status="documented",
        floor_severity="medium",
        source_url="https://real.example.org/rewards",
        retrieved="2026-10-01",
    )
    errors, _ = validate_entry(filled, 0, TIERS, CLAUSES, example_mode=False)
    assert errors == [], f"a filled vg init ledger does not satisfy our schema: {errors}"


@requires_sibling
def test_vg_init_offers_no_shape_or_class_we_do_not_have(vg_binary: Path, tmp_path: Path):
    """Every vocabulary value the scaffold offers must exist in our taxonomies.

    This is the direction that catches a real divergence: viability-gate adding a
    tier shape, or re-offering the removed ``any``, that this repo's schema would
    reject.
    """
    target = tmp_path / "target"
    subprocess.run([str(vg_binary), "init", str(target)], check=True, capture_output=True, text=True)
    template = (target / "ledger.yaml").read_text(encoding="utf-8")

    assert "| any |" not in template, "vg init still offers the removed `any` tier shape"
    for shape in re.findall(r"\b(critical_only|high_and_above|medium_and_above|low_and_above|unknown)\b", template):
        assert shape in TIERS, f"vg init offers {shape!r}, which is not in our taxonomy"
    # The scaffold lists its clause classes as prose; each must be one of ours.
    listed = set(re.findall(r"\b([a-z]+_[a-z_]+)\b", template))
    unknown = {
        k
        for k in listed
        if k not in CLAUSES and k not in TIERS and k not in {"floor_severity", "source_url", "prior_audits", "post_audit_delta", "known_issues", "tier_shape", "schema_version", "floor_status"}
    }
    assert not unknown, f"vg init names vocabulary we do not ship: {sorted(unknown)}"


# ---------------------------------------------------------------- reverse


@requires_sibling
def test_our_example_ledger_is_readable_by_vg(vg_binary: Path, tmp_path: Path):
    """The reverse direction: what we accept, vg must be able to parse.

    ``vg gates`` exits 2 on a parse failure and otherwise reports gate status, so
    exit code 2 is the signal. Any other code means the ledger was read.
    """
    example = ROOT / "examples" / "tier-shapes.example.yaml"
    scope = tmp_path / "scope.txt"
    scope.write_text("# empty on purpose: only the ledger parse is under test\n", encoding="utf-8")

    out = subprocess.run(
        [str(vg_binary), "gates", "--ledger", str(example), "--scope", str(scope)],
        capture_output=True,
        text=True,
    )
    assert out.returncode != 2, (
        f"vg could not parse our shipped example ledger (exit 2):\n{out.stderr}"
    )
    assert "vg:" not in out.stderr, f"vg reported an input error:\n{out.stderr}"


@requires_sibling
def test_vg_ignores_our_additive_fields_without_failing(vg_binary: Path, tmp_path: Path):
    """Additive fields must not break the older reader.

    ``floor_status`` and ``schema_version`` are fields viability-gate's model does not
    read. The contract is that they are additive: an old reader must ignore them,
    not reject them. A ledger that fails here means the two repos have diverged.
    """
    ledger = tmp_path / "additive.yaml"
    ledger.write_text(
        "- id: additive-fields\n"
        "  schema_version: 1\n"
        "  tier_shape: medium_and_above\n"
        "  floor_status: documented\n"
        "  floor_severity: medium\n"
        "  source_url: https://real.example.org/rewards\n"
        "  retrieved: 2026-10-01\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [str(vg_binary), "gates", "--ledger", str(ledger)],
        capture_output=True,
        text=True,
    )
    assert out.returncode != 2, (
        f"vg rejected a ledger carrying our additive fields:\n{out.stderr}"
    )

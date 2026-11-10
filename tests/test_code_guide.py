#!/usr/bin/env python3
"""CODE_GUIDE.md's line references and counts stay true to the tree.

CODE_GUIDE.md is a line-level walkthrough: it cites files, line ranges and
collected-test counts. Before 0.6.1 several of those references were stale - a
reader following `load_taxonomies()` landed in an unrelated constant block, and
the guide's own line count for one script was wrong - because nothing re-derived
them when the code grew. This suite pins the claims that can be checked
mechanically:

  - every "(N lines)" count the guide gives for a tracked file;
  - every `name` (start-end) reference in a script or test section, against the
    actual function or module constant in that file;
  - the total collected-test count and the suite count the guide quotes;
  - the version the guide says it was written against.

A reference the parser cannot resolve to a definition is left to review: this
suite does not pretend to check prose.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = (ROOT / "CODE_GUIDE.md").read_text(encoding="utf-8")
LINES = GUIDE.splitlines()

# A heading that opens a script section and states its line count.
SCRIPT_HEADING = re.compile(r"^### (scripts/[\w.]+\.py) \((\d+) lines\)")
# A bullet that opens a guard or test file section.
GUARD_BULLET = re.compile(r"^- \*\*\[([\w.]+)\]\((scripts/[\w.]+\.py)\)")
TEST_BULLET = re.compile(r"^- \*\*\[([\w.]+)\]\((tests/[\w.]+\.py)\)")
# A backticked name followed by a line range, e.g. `main` (196-243).
LINE_RANGE_REF = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)(?:\([^`]*\))?`[,\s]*\((\d+)(?:-(\d+))?\)")
# A backticked name followed by an explicit file:line reference.
EXPLICIT_PAREN = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`\s*\(([\w./-]+\.py):(\d+)(?:-(\d+))?\)")
EXPLICIT_BARE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`\s+([\w./-]+\.py):(\d+)(?:-(\d+))?")
# Line-count claims: headings, file bullets, and the SECURITY.md sentence.
COUNT_HEADING = re.compile(r"^### (scripts/[\w.]+\.py) \((\d+) lines\)", re.MULTILINE)
COUNT_BULLET = re.compile(
    r"\*\*\[[^\]]+\]\(([\w./-]+\.(?:py|yaml|yml))\) \((\d+) lines", re.MULTILINE
)
COUNT_BOLD = re.compile(r"\*\*([A-Z][A-Z0-9_]*\.md)\*\* \((\d+) lines\)")


def definitions(path: Path) -> dict[str, tuple[int, int]]:
    """Module-level functions and assignments, by name, with their line ranges."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = (node.lineno, node.end_lineno or node.lineno)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = (node.lineno, node.end_lineno or node.lineno)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out[node.target.id] = (node.lineno, node.end_lineno or node.lineno)
    return out


def sections() -> list[tuple[int, Path]]:
    """(line number, file) for every line inside a script or test section."""
    out: list[tuple[int, Path]] = []
    current: Path | None = None
    mode = ""
    for number, line in enumerate(LINES, start=1):
        heading = SCRIPT_HEADING.match(line)
        if heading:
            current = ROOT / heading.group(1)
            mode = "script"
            out.append((number, current))
            continue
        if line.startswith("### The repository guards"):
            current, mode = None, "guards"
            continue
        if line.startswith("## tests/"):
            current, mode = None, "tests"
            continue
        if line.startswith("## ") or line.startswith("### "):
            current, mode = None, ""
            continue
        if mode == "guards":
            bullet = GUARD_BULLET.match(line)
            if bullet:
                current = ROOT / bullet.group(2)
        elif mode == "tests":
            bullet = TEST_BULLET.match(line)
            if bullet:
                current = ROOT / bullet.group(2)
        if current is not None:
            out.append((number, current))
    return out


def test_the_guide_states_the_current_version():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE).group(1)
    stated = re.search(r"Written against version (\d+\.\d+\.\d+)", GUIDE)
    assert stated, "CODE_GUIDE.md must state the version it was written against"
    assert stated.group(1) == version, (
        f"CODE_GUIDE.md says it was written against {stated.group(1)}, "
        f"but pyproject.toml is {version}"
    )


def test_every_line_count_the_guide_quotes_is_current():
    claims = []
    for pattern in (COUNT_HEADING, COUNT_BULLET, COUNT_BOLD):
        for match in pattern.finditer(GUIDE):
            claims.append((match.group(1), int(match.group(2))))
    assert claims, "no line-count claims found in CODE_GUIDE.md"
    problems = []
    for name, claimed in claims:
        path = ROOT / name
        if not path.is_file():
            problems.append(f"{name}: cited but not a file")
            continue
        actual = len(path.read_text(encoding="utf-8").splitlines())
        if actual != claimed:
            problems.append(f"{name}: guide says {claimed} lines, file has {actual}")
    assert not problems, "\n".join(problems)


def test_every_script_line_range_points_at_its_definition():
    problems = []
    for number, path in sections():
        if not path.is_file():
            continue
        defs = definitions(path)
        for match in LINE_RANGE_REF.finditer(LINES[number - 1]):
            name, start, end = match.group(1), int(match.group(2)), match.group(3)
            if name not in defs:
                continue
            actual_start, actual_end = defs[name]
            if end is None:
                if start != actual_start:
                    problems.append(
                        f"CODE_GUIDE.md:{number}: {name} cited at {start}, "
                        f"defined at {actual_start} in {path.name}"
                    )
            elif (start, int(end)) != (actual_start, actual_end):
                problems.append(
                    f"CODE_GUIDE.md:{number}: {name} cited at {start}-{end}, "
                    f"defined at {actual_start}-{actual_end} in {path.name}"
                )
    assert not problems, "\n".join(problems)


def test_every_explicit_reference_points_at_its_definition():
    problems = []
    for pattern in (EXPLICIT_PAREN, EXPLICIT_BARE):
        for match in pattern.finditer(GUIDE):
            name, rel, start, end = match.group(1), match.group(2), int(match.group(3)), match.group(4)
            path = ROOT / rel
            if not path.is_file():
                problems.append(f"{rel}: cited but not a file")
                continue
            defs = definitions(path)
            if name not in defs:
                continue
            actual_start, actual_end = defs[name]
            if end is None:
                if start != actual_start:
                    problems.append(
                        f"{rel}:{start}: {name} cited, defined at {actual_start}"
                    )
            elif (start, int(end)) != (actual_start, actual_end):
                problems.append(
                    f"{rel}:{start}-{end}: {name} cited, defined at "
                    f"{actual_start}-{actual_end}"
                )
    assert not problems, "\n".join(problems)


def test_the_collected_test_count_the_guide_quotes_is_current():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    collected = re.search(r"(\d+) tests? collected", result.stdout)
    assert collected, result.stdout[-2000:]
    actual = int(collected.group(1))
    quoted = {int(n) for n in re.findall(r"(\d+) (?:collected tests|tests collected|in total)", GUIDE)}
    quoted |= {int(n) for n in re.findall(r"collects (\d+) tests", GUIDE)}
    assert quoted, "CODE_GUIDE.md must quote the collected-test count"
    assert quoted == {actual}, (
        f"CODE_GUIDE.md quotes {sorted(quoted)} collected tests, pytest collects {actual}"
    )


def test_the_suite_count_the_guide_quotes_is_current():
    suites = sorted((ROOT / "tests").glob("test_*.py"))
    stated = re.search(r"(\w+) pytest suites", GUIDE)
    assert stated, "CODE_GUIDE.md must state the number of test suites"
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    assert words[stated.group(1).lower()] == len(suites), (
        f"CODE_GUIDE.md says {stated.group(1)} suites, tests/ has {len(suites)}"
    )

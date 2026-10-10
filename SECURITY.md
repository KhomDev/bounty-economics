# Security policy

## Reporting a security issue

This repository is documentation, taxonomy data and a small Python validator. There is no server,
no runtime service and no handled personal data. The realistic security issues are therefore:

- a **code-execution or file-write flaw** in `scripts/validate.py` / `scripts/check_generic.py`
  reachable by handing the tool a hostile ledger file, and
- a **disclosure** — a program name, chain, reward table, or quoted clause that identifies a real
  target. The repository promises to ship none of those, so a genuine instance of one is a
  security report about this repository, not a style complaint.

## Contact

> **STOP GATE — the maintainer must fill this in.**
>
> `TODO(human): contact`
>
> No address is invented here on purpose. Until this line is replaced, **this repository has no
> working private security contact**, and reporters should open an issue that does not itself
> contain anything sensitive. Choosing and publishing a contact address is a human decision.

## What to include

- The file and line, or the command you ran.
- For a validator flaw: the smallest ledger that triggers it.
- For a disclosure: which file, and the exact text you believe identifies a target. Do not paste
  the target's own materials — a pointer is enough.

## Scope

In scope: ```scripts/**```, `schemas/**`, `data/**`, `examples/**`, ```.github/**```.

Out of scope: the accuracy of the taxonomies as advice (that is a correction — see the issue
template), and anything about a program you are hunting (this project has no relationship with any
program).

## Response

There is no formal SLA. This is a small methodology repository maintained by one person; expect a
good-faith reading rather than a guaranteed turnaround.

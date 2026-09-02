# Which licence covers which file

This repository is generated, and its files come from three places with three
different licences. Rather than pick one and flatten the difference, here is the
map. It is the same rule the source repository states: **each generated file
carries the licence of the file it was generated from.**

## The format and the installer text: CC BY 4.0

| file | generated from |
| --- | --- |
| `references/spec-schema.md` | the passport specification |
| `references/vocabulary.md` | the capability vocabulary |
| `references/passport-template.md` | the passport template |
| `references/resolution.yaml` | the resolution table |
| `references/installer-core.md` | the installer text |
| `references/installer-branches/*.md` | the per-platform installer branches |

Full terms: `LICENSE` in this repository is the verbatim CC BY 4.0 legal code.
`LICENSE-FORMAT.md` is the project's own notice explaining why the format is
licensed this way. https://creativecommons.org/licenses/by/4.0/

These are open on purpose. They are the interoperability contract: anybody
writing a competing host, a different capture tool, or their own renderer needs
the format and the install steps for the same reason. Attribution is the only
condition.

## The scripts: Apache License 2.0

| file | what it does |
| --- | --- |
| `scripts/scrub.py` | finds and removes credentials before anything is shared |
| `scripts/validate.py` | checks a passport against the format |
| `scripts/preflight.py` | predicts whether the upload endpoint will accept it |
| `scripts/assemble.py` | inserts installer text into a passport |
| `scripts/publish.py` | uploads a passport and returns its link |
| `references/judge-prompt.md` | the grading prompt, **inserted by `assemble.py` into section 5 of every assembled passport**, so this Apache component travels in the passports you produce |

Full terms in `LICENSE-Apache-2.0.txt`, with `NOTICE` beside it.

## SKILL.md: CC BY 4.0

`SKILL.md` is the skill itself: the instructions the model follows during a
capture. It is authored rather than generated.

It carries the same CC BY 4.0 licence as the format, under its own notice in
`LICENSE-SKILL.md`, which is in this repository rather than referenced from
somewhere you cannot reach.

Until 2026-08-18 this file was proprietary and no licence was granted for it.
That was a deliberate decision and it was deliberately reversed; the reasoning is
in `LICENSE-SKILL.md`.

## The remaining files, so this map is actually the tiebreak

Every notice here names this file as the authority where two of them differ. That
only works if the map covers everything, and it did not: `README.md`, `NOTICE`
and the licence texts themselves appeared in no table, which left `README.md`
Apache 2.0 by one notice and CC BY 4.0 by another with nothing to settle it.

| file | licence | why |
|---|---|---|
| `README.md` | CC BY 4.0 | prose about the skill, authored here, same terms as the rest of the prose |
| `LICENSE-MAP.md` | CC BY 4.0 | this file, also prose |
| `LICENSE-FORMAT.md` | CC BY 4.0 | our own notice about the format |
| `LICENSE-SKILL.md` | CC BY 4.0 | our own notice about the skill |
| `LICENSE` | reproduced verbatim under its own terms | the CC BY 4.0 legal code, not ours to relicense |
| `LICENSE-Apache-2.0.txt` | reproduced verbatim under its own terms | the Apache 2.0 legal code, not ours to relicense |
| `NOTICE` | reproduced as Apache 2.0 section 4(d) requires | it travels with the Apache-licensed scripts |
| `.gitignore` | CC BY 4.0 | two lines, so that importing the scripts does not leave compiled bytecode in your clone |

That is all 24 files: 16 in the tables above, and these 8.

## Your passports

Nothing here claims any interest in a passport this skill produces, in the agent
it describes, or in anything either of them outputs. Those are yours.

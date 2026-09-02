Agent Passport capture skill
Copyright 2026 Raffael Hueberli

SPDX-License-Identifier: CC-BY-4.0

Licensed under the Creative Commons Attribution 4.0 International License
(CC BY 4.0), the same licence as the passport format specification and the
installer text, which travel with it.

    Human-readable summary:  https://creativecommons.org/licenses/by/4.0/
    Full legal code:         https://creativecommons.org/licenses/by/4.0/legalcode


WHAT THIS COVERS

`SKILL.md`, and anything else authored in this directory directly.


WHY THIS CHANGED, BECAUSE IT REVERSES A DECISION MADE ON PURPOSE

Until 2026-08-18 this notice read "NOT OPEN SOURCE" and granted no licence at
all. A decision of 2026-08-11 held that the
capture skill stayed closed, and this notice was written to implement that
refusal rather than to leave the question open.

Raffael reversed it deliberately, so that the skill can be published as a
repository people install by cloning and update by pulling. Three reasons, and
none of them is that the earlier decision was wrong:

  A copy handed out by hand carries installer text frozen on the day it was
  made. `git pull` retires that, and it is the accepted limitation the product
  plan has carried since the beginning.

  The product's central claim is that secrets never travel. A claim like that is
  worth more when a stranger can check it than when they have to trust it, and
  they cannot check what they cannot read.

  CC BY rather than Apache 2.0, matching the format and the installer text: this is
  a prose instruction document rather than software, Apache's terms turn on
  "Source form" and "Object form" which have no meaning for it, and its
  attribution requirement is the recognition that makes giving it away
  sustainable.


WHAT THIS DOES NOT COVER

- The browser capture prompt is unaffected and remains proprietary, all rights
  reserved. Nothing in this change reaches it. Where it is published for
  people to run, publishing it is not a licence to redistribute or modify it.
- `references/` and `scripts/` are GENERATED from the project's source files. Each carries the licence of the file it was generated from, whatever
  that licence is. This notice does not narrow it and did not before.
- The **code** is Apache 2.0: the validator, the scrubber, the preflight check,
  the assembler and the publisher, wherever they sit. In the published skill
  repository that is `scripts/`, and the licence text and `NOTICE` ship beside
  it. `LICENSE-MAP.md` maps every file and is the authority if this notice and
  it differ.


YOUR PASSPORTS ARE NOT COVERED EITHER

A passport produced by this skill belongs to whoever ran it. Nothing in this
notice claims any interest in the passports, the agents they describe, or the
output of either. That was true when this directory was proprietary and it is
true now.

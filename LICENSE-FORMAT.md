Agent Passport format specification
Copyright 2026 Raffael Hueberli

Licensed under the Creative Commons Attribution 4.0 International License
(CC BY 4.0).

    Human-readable summary:  https://creativecommons.org/licenses/by/4.0/
    Full legal code:         https://creativecommons.org/licenses/by/4.0/legalcode

You are free to share and adapt this material for any purpose, including
commercially, provided you give appropriate credit, link to the licence, and
indicate whether changes were made.


WHAT THIS COVERS

The format specification, the capability vocabulary, the passport template and
the resolution map.

These files define the format. They are licensed permissively on purpose: a
format that only one company is allowed to read is not a format. Anyone may
write a tool that produces or consumes Agent Passports, and nothing here asks
their permission or takes a cut.


WHAT THIS DOES NOT COVER

- The installer text is CC BY 4.0 as well, and this notice covers it. It has no
  separate notice of its own; this is the notice for it.
- **Both of those travel inside a passport.** `assemble.py` inserts the installer
  text and the grading prompt into every assembled passport, so a passport
  carries a CC BY component and an Apache 2.0 one. Each asks what its own licence
  asks of whoever redistributes the passport. Neither is a claim on the
  passport's own content, which belongs to whoever ran the capture.
- The project's **code** is licensed separately under the Apache License 2.0,
  with the `NOTICE` that accompanies it. That is the validator, the scrubber,
  the preflight check, the assembler and the publisher: every executable part,
  wherever it sits. In the published skill repository they are `scripts/` and
  the licence text is `LICENSE-Apache-2.0.txt`; `LICENSE-MAP.md` there maps
  every file to its licence and is the authority if this notice and it differ.
- The capture skill's `SKILL.md` is **CC BY 4.0**, relicensed on 2026-08-18 so
  that the skill can be published and installed by cloning. Its own notice
  travels beside it and states the terms.
- The browser capture prompt is **not** open source. It is proprietary, all
  rights reserved. Where it is published for people to run, publishing it is not
  a licence: you may use it to capture your own agent, and you may not
  redistribute or modify it.

The worked example passport is CC BY 4.0 too, wherever you obtain it. It is the
conformance fixture the tooling reads, so anyone implementing the format wants it
for the same reason they want the vocabulary. **It does not ship with the
published skill**, which means a reader of this notice cannot currently run the
fixture the specification is written around. That is a gap rather than a
decision, and the licence is stated here so that it is settled when it closes.

**`LICENSE-MAP.md` is the authority.** It maps every file in the published tree
to its licence, and where it and this notice differ, it wins. This notice
explains the reasoning; the map settles the file. Nothing falls under proprietary
terms by omission.

The split is deliberate: the format, the installer text and the capture skill
are given away, because a format nobody can implement is not a format. The
browser capture prompt is not.

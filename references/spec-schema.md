# Agent Passport, format specification v0.1

**Status:** normative for `passport: "0.1"`. Every other artifact that produces or consumes a passport (the capture skill, the installer text, the validator) is a client of this file. Changes here are version changes, not edits.

**What a passport is:** one Markdown file describing an agent well enough that a second person, on a different platform, can recreate a working version of it inside their own assistant, using their own credentials, with an honest account of what did not survive the move.

**What a passport is not:** a backup, an export, or a runtime artifact. It carries no code, no secrets, and no promise of fidelity. It carries structure, intent, evidence, and the questions that must be asked of the new owner.

**A and B, used throughout this file and its clients.** **A** is the person whose agent is being captured: they built it, it runs on their machine or their account, and the passport is written from their files. **B** is the person installing it afterwards: a different person, usually on a different platform, with their own accounts and their own credentials. Everything the format does follows from A and B being two people who may never speak. This convention was used in this document and in three others for months without ever being written down.

---

## 1. File shape

UTF-8 Markdown. YAML frontmatter delimited by `---` on the first line and a second `---` within the first 40 lines. Then six body sections, in fixed order, each heading appearing exactly once and matching verbatim:

```
## 1. What this agent is
## 2. What it needs from you
## 3. Functional spec
## 4. Golden examples
## 5. Installer
## 6. Losses
```

Ordering is human-first, machine-last: a person reading top to bottom meets the agent, sees what it will ask of them, and only then reaches structured detail. Validators check order because the order is a promise about who the file is for.

---

## 2. Frontmatter

| key | type | constraint |
|---|---|---|
| `passport` | string | exactly `"0.1"` |
| `name` | string | slug, `^[a-z0-9][a-z0-9.-]{0,63}$` |
| `title` | string | human name, one line |
| `created` | date | `YYYY-MM-DD`, the capture date |
| `capture_path` | enum | `file` or `browser` |
| `source_stack` | string | one abstracted line, informational only |
| `owner_confirmed` | bool | `true` only after the owner passed the check-in |
| `scrub` | string | method chain, e.g. `"regex+llm, owner-reviewed"` |
| `envelope` | enum | v0.1 constant: `read-notify` |

`source_stack` is the only place provider or product names belong (e.g. "python scripts on macOS, launchd schedule, local model"). It exists so B can weight the passport, not so the installer can branch on it. Installers MUST NOT read it.

`owner_confirmed: false` is a valid, shareable state. It means capture completed but the owner never reviewed. The passport page and every installer must surface that fact rather than hide it.

`scrub` must contain the substring `owner-reviewed` if the body contains any `[SCRUBBED:` marker. That is the scrub gate expressed in the format: a passport carrying redactions that nobody looked at is invalid.

---

## 3. Body sections

### `## 1. What this agent is`

Three sentences, addressed to B the human, no jargon: what it does, when it does it, what the output is for. Written for someone deciding in fifteen seconds whether to install.

### `## 2. What it needs from you`

The consent table, rendered before anything is installed. One row per capability the agent uses:

| column | meaning |
|---|---|
| Capability | plain language, not the vocabulary id |
| Why | what breaks without it, in the agent's terms |
| Required / Optional | core vs optional per the functional spec |
| If you skip it | the concrete degraded behaviour |
| Installable in v0.1 | whether the **envelope** permits installing it: `yes`, or `no, declared only`. A statement about the format, never about the installer's platform |

Capabilities outside the read-and-notify envelope (see §5) appear here as declared-only rows. They are shown, never installed. Hiding them would misrepresent the agent; installing them would break the envelope.

**`Installable in v0.1` is platform-blind, and the installer must resolve it before asking for consent.** `yes` means the envelope allows this capability to be installed. It is not a promise that the platform in front of the installer can do it. Those are two different questions, and reading the column as the second one is what broke: a table saying "run on a schedule: yes" sat next to a branch appendix saying that platform has no scheduler, and the contradiction landed at the exact moment the person was being asked to agree.

So the table is rendered twice in effect: capture writes the envelope answer, and the installer resolves every row against its own branch before showing it, marking any row the branch downgrades. Installable by the envelope and unavailable or degraded here is a normal, sayable result, in the branch's own words for what happens instead. A row the branch cannot deliver is a losses row waiting to happen, and the person consenting is entitled to know that before agreeing, not after.

### `## 3. Functional spec`

One fenced YAML block, schema in §4. This is the machine core.

### `## 4. Golden examples`

One to three real outputs from A's agent, dated, scrubbed, each in its own fenced block, and **nothing else fenced**. Elision rules stated in prose above the blocks (e.g. "items 4-11 removed, shape preserved"). The verification checks live in the functional spec (section 3), not here, because the validator counts fenced blocks in this section to enforce the one-to-three rule.

**Golden examples are templates of shape, never expected content.** A captured at 10:00, B installs at 15:00, the world moved. Anything in a golden example that reads as an expectation of specific content is a capture error.

### `## 5. Installer`

The platform-agnostic installer core, followed by the branch appendix for each supported platform. Written to be read aloud by B's assistant, addressed to that assistant, with every authority claim marked as text-to-surface rather than instruction-to-obey.

### `## 6. Losses`

An empty template at capture time. The install fills it in and renders it to B even when it is empty. One row per capability, plus one line of what that means in practice.

**The status words belong to the installer, not to this section.** `delivered`, `substituted` and `lost` are the three every install needs. The set actually in force is defined at `references/installer-core.md` step 8, it is larger than three, and it grows whenever a platform forces a distinction this format did not anticipate: `delivered, unverified`, `delivered, unreliable`, `available, not installed` and `placeholder, not yet connected` are already in it, and §4 of this document endorses the second by name. A passport carrying a status that step 8 names and this section does not is valid.

`available, not installed` is the newest and was added because the format could not express what a real install actually did. A source existed, the installer reached it, and it went unused because it could not meet the agent's own standard for a figure it would state. Rendered as `lost`, that reads as a gap in the world and sends the recipient looking for a breakage; the truthful row says a choice was made and names it. **The distinction is between what could not be had and what was not taken**, and only the second one is anybody's decision.

Do not copy the three words above into an instrument as a closed set. A normative document propagates that kind of mistake through diligence rather than carelessness: whoever does it is following the spec closely, and ends up with an instrument that scores the correct answer as unmapped and the wrong answer as clean.

---

## 4. Functional spec schema

Fenced YAML inside section 3. Every field carries `confidence: high | medium | low`. The block as a whole carries `confirmed_by_owner: true|false` mirroring the frontmatter.

```yaml
goal:                 # one line, outcome-phrased, not mechanism-phrased
trigger:              # scheduled(cadence, time, flexibility) | on_demand | event(description)
inputs:               # list
  - what:             # the role this input plays in the output, never the original's system or metric name
    capability_ref:   # vocabulary id, see vocabulary.md
    access:           # open | credentialed
    binding:          # optional, a personal_slots id; REQUIRED when access is credentialed
    tag:              # beat/topic tag, used for source substitution on B's side
    criticality:      # core | optional
    fidelity:         # optional, exact | lossy; how the original read this, see below
processing:
  sections:           # the structure of the output
  style:              # register, person, formality
  length:             # a band, not a number ("120-200 words per section")
  ordering:           # what determines order, and why
output:
  format:
  delivery:           # the channel that reaches the installer, chosen at install; the original's channel is context, never a requirement
  audience:
comparison_mode:      # structural | exact | input_relative
capabilities:         # list, each {capability_ref, status: used|declared_only}
  - capability_ref: web.fetch
    status: used
personal_slots:       # list, see below
state:                # optional block, see below; required before any verification check may compare runs
  keeps:              # what is remembered between runs, in plain language
  granularity:        # per run | per day | per period
  why:                # what in the output breaks without it
  confidence:
tacit_notes:          # free text, owner voice, verbatim, quoted not paraphrased
verification:         # 2-4 agent-specific checks, see below
```

### `inputs`, and the `binding` field

An input describes a **role in the output**. What fills that role is a question for the installer, not a fact inherited from the original.

`what` states what the input is *for*: "a headline growth number for the week", "the two sources that decide what leads the brief". It never names the original's system, product, provider or metric. Carrying "new signups from the owner's app database" into a passport hands the installer somebody else's business and leaves them nothing to do with it but record a loss. Carrying the role hands them a question they can answer about their own.

`binding` names a `personal_slots` id, and it is **required for any input with `access: credentialed`**. Anything behind the original's login is guaranteed to be unavailable to the installer, so an unbound credentialed input is a dead row: the passport asserts a need and asks nobody how to meet it.

`fidelity` is optional and says how the original obtained this input, which the capability id cannot. `web.fetch` covers a script parsing integers out of a JSON endpoint and a summarising model answering a question about a page, and those are not the same instrument: the first errors when it fails, the second returns a confident wrong answer that no reader can distinguish from a right one. `exact` means the original got the source's own data and knew when it did not. `lossy` means a model or a heuristic stood between the source and the value. Omit it when the input is prose, where the distinction does not bite.

It exists so the install can be honest about a downgrade rather than silent about it. An input captured as `exact` and rebuilt through a lossy instrument is a real loss of quality even though the section still fills, and without this field the losses table has no way to say so: the installer sees `delivered` and cannot tell an exact integer from a plausible one. With it, the row reads `delivered, unreliable` and names the swap. This matters most for quantities, which is where a failed read renders as a zero and gets believed every morning.

The field alone will not produce the behaviour. The pairing does, so write both:

```yaml
inputs:
  - what: a headline growth number for the week
    capability_ref: web.fetch
    access: credentialed
    binding: growth_number
    tag: growth
    criticality: core
    fidelity: exact
    confidence: high

personal_slots:
  - id: growth_number
    question: "What is your headline growth number, and where does it live?"
    why: "the original read one company's own database; yours is a different system, and probably a different number"
    default: none
    required: true
```

The input says what the number is for. The slot asks what supplies it. Read alone, either half is useless: the input is an unfillable demand, the slot is a question with no place to put the answer.

The `binding` value must be the `id` of a slot that exists in the same passport. Two inputs may share one slot when one answer supplies both. The installer reads this pairing as a ladder, in order: the installer's own system that already serves the role, then an open equivalent, then a loss. An unbound credentialed input skips straight to the last rung, which is how an install can tell someone they have lost inputs that were merely unbound.

The same rule applies to the agent's name and title. Capture proposes a name for the role the agent plays, not one carrying the original's domain, and the installer may rename at install.

### `comparison_mode`

Set at capture, consumed by verification. It is the single field that decides how a judge is allowed to compare B's first run against A's golden example.

- `structural`: content varies every run by design (news, weather, market summaries). Compare shape, counts, register. Never content.
- `exact`: same input produces the same output (formatters, converters, extractors). Content is comparable.
- `input_relative`: output depends on the owner's private data (inbox, calendar, notes). Compare structure, plus evidence that the right inputs were read. Never content.

Capture sets it. The installer never guesses it. When capture cannot tell, the answer is `structural`, tagged `confidence: low`, and pushed onto the check-in.

### `personal_slots`

The design answer to "tacit context does not travel". Every value in A's agent that is about A rather than about the agent becomes a slot: the passport carries the *question*, not A's answer.

```yaml
personal_slots:
  - id: location
    question: "Which city's weather should the brief use?"
    why: "the original used its owner's home city"
    default: none          # or a safe generic default
    required: true
```

Rule: if copying A's value into B's install would be wrong, embarrassing, or merely inherited-by-accident, it is a slot. Locations, topic lists, priority senders, delivery times, employer names, tone anchors tied to A's job.

**The delivery target is always a slot.** A passport never carries an address, a channel id, a phone number or a file path belonging to the original owner. See §5.

### `state`

Optional. Present when the agent remembers something between runs.

```yaml
state:
  keeps: "yesterday's figure for each metric, so today's line can show the change"
  granularity: per day        # per run | per day | per period
  why: "without it every number renders with no delta and the output loses its point"
  confidence: high
```

It exists because the format had nowhere to say that an agent has a memory, while passports were already demanding that it did. A passport whose verification checks require a period-over-period comparison, with no declaration anywhere of where yesterday's numbers live, cannot be installed honestly: the installer must either invent a snapshot mechanism the spec does not describe, or quietly drop a check the passport calls essential. Both are wrong answers, and the installer was being asked to pick one.

`state` is a declaration, not a design. It says what is remembered and why the output breaks without it. Where the snapshot actually lives is the branch's business, and a platform that cannot persist anything at all makes `state` a losses row rather than a refusal.

**The guard.** Capture may not write a `verification` check that compares against an earlier run unless the passport declares `state`. `scripts/validate.py` enforces the checkable form of this and names the offending check. Either the memory is declared or the check is rewritten to be judgeable from a single run, and either is a legitimate answer. A check that silently assumes a memory nobody declared is not.

### `verification`

Two to four concrete, checkable statements derived at capture time from the goal, the capabilities and `comparison_mode`. Capture generates them because capture is the only step that understands the agent; the installer never invents criteria.

```yaml
verification:
  - check: "each chosen topic has at least two items"
    evidence: "count items under each topic heading"
  - check: "items are dated within 24h of the run"
    evidence: "compare item dates to B's run time, not the golden example's date"
```

---

## 5. The envelope

v0.1 passports declare `envelope: read-notify`. The installer installs only capabilities that are read-only, plus delivery of the agent's own output to the installer. Any capability that writes to the world, sends mail to somebody else, posts, messages third parties, moves money or writes to external systems, renders in the consent table as **declared only**, which is the `no, declared only` value of the Installable in v0.1 column in §3.

**Delivery is inside the envelope whatever the channel carrying it.** Getting the agent's own output to the person who installed it is `chat.notify`: the chat reply, mail to the installer's own address, a platform push notification, a file the installer designated. What sits outside the envelope is composing something for somebody else. The test is the recipient, not the transport, and mail is not a special case in either direction. The installer offers the channels their platform actually has, asks which one, and records the answer in `output.delivery`.

**The delivery target is always a personal slot.** A passport never carries an address, a channel id, a phone number or a file path belonging to the original owner. This is the control that makes the paragraph above safe: without it, widening `chat.notify` to cover mail would let a passport name a recipient and have the install deliver to a stranger. Capture that finds a delivery address turns it into a slot and does not carry it. The instruction text the installer writes must say that the agent delivers to that one target and composes no other recipient, because a mail connector grants sending as a bundle and the boundary then lives only in the instructions.

This is a product boundary, not a technical one. It bounds the consent screen, the verification problem and the liability while the format earns trust. Widening it is a spec version change with a new `envelope` value, never a per-passport favour.

---

## 6. Secrets

Passports carry credential **types**, never values: "needs read access to your mailbox", not a token, not an address, not a provider account id. Granting happens on each platform's own consent screen, clicked by B.

Capture must never read: directories with `0700` permissions, `.env*`, `credentials*`, `*token*`, `*secret*`, `*.pem`, `*.key`, browser or session profile directories, bulk data caches. Denied paths are named in the scrub note as denied; their contents never enter the file.

A passport is public the moment its link exists. The format assumes no confidentiality and no access control.

---

## 7. Validation

`scripts/validate.py` is the executable form of this specification. Where the two disagree, this file is normative and the validator is a bug. The validator checks: frontmatter presence and constraints, section presence and order, exactly one `comparison_mode` line, every `capability_ref` in the vocabulary, the scrub gate, one to three golden blocks, the absence of denied-path names in the body, a real and non-future `created` date, a five-column consent table with readable verdict columns, a `binding` on every credentialed input, a declared `state` behind any verification check that compares against an earlier run, and `fidelity`, where present, being one of the two words that mean something here.

**Two keys must carry their value on the same line: `comparison_mode:` and `capability_ref:`.** The validator finds them by regex, and its whitespace class crosses newlines, so a key left dangling with its value indented beneath silently captures whatever token comes next and fails in a way that reads as nonsense. Never nest either key, never leave either one empty, and never write the literal string `comparison_mode:` anywhere in a passport except the single line in the functional spec. If you record confidence for the mode, it goes on its own `comparison_mode_confidence:` line, which the regex does not see. It is optional and the template does not carry one.

**The delta-language check is deliberately narrow, and narrowing it further is a bug, widening it is a worse one.** The validator cannot read a check and decide whether it needs a memory, so it matches a fixed list of phrases that only mean comparison against an earlier run: "vs prev", "previous run", "since last run", "compared to yesterday", "period over period" and their near neighbours, matched over the `verification` block alone and after collapsing punctuation, so a hyphen or a full stop cannot slip a phrase past it. Phrases, never single words: matching "previous" or "last" on its own would refuse legitimate captures, and a false positive here blocks a passport somebody has already finished. Bare "since last" is deliberately absent for the same reason, since "published since last week" needs no memory at all. The escape hatch is real and cheap, so a passport that genuinely does compare runs should take it: declare `state`.

Validation is a floor. It cannot check fidelity, and a passing passport can still be wrong about the agent. That is what the check-in is for.

---

## 8. Versioning

`passport: "0.1"` is the format contract. Readers must refuse versions they do not know rather than guessing. Breaking changes bump the version; new optional fields do not. The vocabulary (`vocabulary.md`) is versioned with the format: adding a capability id is a format change because installers switch on it.

**`binding` and `state` were added under this rule, and the version is unchanged on purpose.** Both are optional fields. A reader that has never heard of either still parses every passport correctly, and a passport that uses neither is still valid, which is what "new optional fields do not bump the version" means. Written down here because the change is visible enough that a later reader would otherwise assume the rule was quietly broken.

The honest qualification: both fields carry a conditional requirement. `binding` is required on an input that declares `access: credentialed`, and `state` is required behind a verification check that compares against an earlier run. So a passport captured before these existed, which does either of those things, can now fail validation. That is a tightening of what capture may emit, not a new obligation on readers, and the fix for a stored passport that fails is to re-capture it, not to bump the version.

The `chat.notify` widening in §5 is likewise not a version change. No id was added, removed or renamed, and every passport written under the old reading still validates: one that filed owner-directed mail under `email.send` is unchanged as a document, it simply describes a declared-only row where it could now describe an installable one. Re-capture is what fixes that, and what it buys is a delivery channel the install would otherwise have skipped.

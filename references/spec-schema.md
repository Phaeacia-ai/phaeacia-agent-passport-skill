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

`scripts/validate.py` is the executable form of this specification. Where the two disagree, this file is normative and the validator is a bug. The validator checks: frontmatter presence and constraints, section presence and order, exactly one `comparison_mode` line, every `capability_ref` in the vocabulary, the scrub gate, one to three golden blocks, the absence of denied-path names in the body, a real and non-future `created` date, a five-column consent table with readable verdict columns, a `binding` on every credentialed input, `access` being one of the two words the vocabulary allows, a declared `state` behind any verification check that compares against an earlier run, `fidelity`, where present, being one of the two words that mean something here, and the envelope floor below.

**The envelope floor: a declared-only capability may not be marked installable.** Section 5 has always said this, and until now it said it only in prose. A passport declaring `envelope: read-notify` while marking `email.send` installable passed every gate and rendered to its recipient as a granted, installable write capability. The rule is now executable, and it is three checks because the format gives an id three different amounts of context:

1. **Status.** In the `capabilities` block, any entry whose `capability_ref` is a declared-only id from `vocabulary.md` (`email.send`, `msg.send`, `social.post`, `ext.write`, and any `money.` prefix) must carry `status: declared_only`. `status: used` is a refusal, and **so is no status at all**: the field is mandatory in the schema, and treating its absence as acceptable made this check opt-out by deleting a line.
2. **Backticked rows.** When any of a consent row's five cells carries a declared-only vocabulary id in backticks, that row's Installable column must start with `no`. **All five cells are read, and within a cell every backticked token, not the first.** Until 2026-09-05 the Capability cell was the only one read, while the Installable cell travels verbatim into the renderer, which turns backticks into a code element: `yes (via `money.transfer`)` put the id in front of the reader in monospace beside a granted stamp on a row both gates called clean. The Why and If-you-skip cells reach the same page. **The cost, which is a real one:** an installable row for `files.read` whose Why cell honestly says "so the digest can later be handed to `email.send`" is now refused, because nothing in the format says whether a backticked id in that cell is the row talking about itself or about something else. The author drops the backticks and the row passes, which is the same cheap authoring fix the filename rule asks for; the alternative was leaving four of five cells able to put a write id in front of a reader in monospace beside a granted stamp. Each cell is split on every backtick rather than paired: a stray third backtick (``Charge the card`s `email.send` ``) or a double-backtick span around a single-backticked id (`` `money.transfer` ``) shifted the pairing so the id was never enumerated while the page rendered it; every segment between backticks, and the whole cell when it has none, is tested as a token, **and every word of a segment that lies between two backticks is tested on its own**, a word here being separated by anything outside printable ASCII 0x21 to 0x7E rather than by space and tab, since a vocabulary id is printable ASCII by definition and `` `email.send<NBSP>now` `` split on space and tab is one word, equal to no fixed id, and reached a granted stamp in four of five cells with the id itself in byte-identical ASCII. The word reading is what closes a write id with a word beside it inside one span: the four fixed ids are compared by equality, so `` `email.send now` ``, `` `run money.transfer now` `` and `` `use ext.write here` `` were matched by nothing, while `` `money.transfer daily` `` was refused the whole time because the `money.` test is a prefix. **What that means for bare prose, stated precisely because the first version of this sentence was wrong.** The WORD reading applies inside backticks only, so "the original used email.send to mail the digest" in a row that installs nothing but `files.read` is accepted: the format links no consent row to an id unless the author backticks one. The SEGMENT reading applies everywhere, so a segment that is nothing but the id is read wherever it lies. Until 2026-09-05 this paragraph said flatly that bare prose naming an id is not read, which was false in the direction that hides a refusal from its author. Measured, in a Why cell: `the original used email.send to mail the digest` and `it used email.send \`see docs\`` are accepted; a cell that is nothing but `email.send`, and `email.send \`see docs\`` and `` \`see docs\` email.send`` where the id is the whole run before the first backtick or after the last, are refused. Before a word or a segment is compared, every character that is **not an ASCII letter or digit** is trimmed from both of its ends, since an id begins and ends with one. That is a whitelist of what an id may end with rather than a list of punctuation marks, so it needs no Unicode table, and it therefore trims non-ASCII too: `` `money.transfeг` `` with a Cyrillic er on the end trims to `money.transfe`, which carries the `money.` prefix and is refused, as are a CJK character, a fullwidth stop or a zero-width space in the same position. This paragraph said "ASCII punctuation" until 2026-09-05, which described the opposite of a tightening built on purpose. Trimmed: `` `(email.send)` ``, `` `use email.send, here` `` and `` `email.send.` `` all name the id. The trim is an addition and never a substitution, so a candidate is compared both as written and as its trimmed core; comparing only the core would accept `` `money.` ``, which the prefix test refuses as written. Nothing inside a word is trimmed, so a lookalike or a zero-width space in the middle of one is left for the opacity rule below, which reads all five cells and applies the same trim to the ends. Both scans trim and only one of them did until 2026-09-05, which left a lookalike with sentence punctuation around it read by neither: a division of labour is only a division if the two halves are stated together. **A word is read inside backticks, and "inside backticks" means bounded by a backtick on each side, which the prose BETWEEN two code spans also is.** The cell is split on every backtick and never paired, so it cannot tell the two apart; only the text before the cell's first backtick and after its last is outside, and only there is a word of prose unread. That is a real cost to an honest author and it is why the refusal message names those two positions. A `money.` token is read as an id **unless it is shaped like a data file**: the cell is prose, and a backticked `money.csv` is a filename. Shaped like a data file means the token is exactly `money.` followed by one of the file extensions the validator lists (`csv`, `xlsx`, `json`, `sqlite` and the rest of a short set held in one place in each implementation): the whole of the text after the prefix, not the last dot segment, so `money.transfer.csv` is an id and `money.ledger.csv` is refused as one. A token the passport itself declares as a `capability_ref` is an id whatever its shape. Until 2026-09-04 the rule ran the other way, a `money.` token counted only when the passport declared it, and that read the ambiguity in favour of accept: a row offering an undeclared `money.transfer` as installable passed both gates and rendered as granted, because a passport that lies does not declare. The cost of the rule as it stands now falls on an honest author whose ledger has an extension the list lacks or a second dot in its name; that passport is refused with a message saying to write the filename without backticks, which is a cheap fix on the author's side and a visible one, where the previous behaviour was a silent accept of a payment capability. The extension list is a floor that gets raised, never a boundary that holds. **And the renderer's own reading, in addition to the split one.** The renderer pairs backticks and emits one code element per pair, so `` `email.``send` `` reaches the page as two code elements with nothing between them, which reads as the single unbroken monospace string `email.send`, while the validator's split reading saw `email.`, the empty string and `send` and found no id in any of the three. Measured by a critic and reproduced: 30 of 35 combinations accepted, four fixed ids across three split points across four of the five cells, both gates. Each maximal run of ADJACENT code spans is therefore concatenated and tested as well, a run continuing only across an empty gap, since one space between two spans is two words to a reader. Both readings run; a candidate found by either is refused. A gate and a renderer reading the same bytes differently is a hole by construction whatever either one does.

   **What a backticked token may contain.** In a row whose Installable column starts with `yes`, every word of every backtick-bounded segment of **all five cells** is read after stripping ASCII space and tab, and only those, and the row is refused as opaque if that word CONTAINS an ASCII control character (0x00 to 0x1F, 0x7F), which is not text, or if it is **shaped like a write id**. Shaped like one means a word containing at least one non-ASCII character which, under either of two readings, lands on a fixed declared-only id or on the `money.` prefix: **delete** every non-ASCII character, which catches an insertion such as a zero-width space inside `email.send` or a byte-order mark after `money.csv`; or **replace** each non-ASCII character with a single-character wildcard and compare position by position after a length test, which catches a substitution such as a Cyrillic `о`, a one-dot leader or a fullwidth stop. Neither is enough alone: deletion cannot see a substitution, because deleting the impostor shortens the word past the id, and the wildcard cannot see an insertion, because it changes the length. A wildcard match must also be ANCHORED: at least one position has to match by equality on an ASCII letter or digit, or the reading is not evidence. Without that, six consecutive non-ASCII characters matched `money.` at every position, and this rule refused `Приложение.csv`, `プロジェクト.csv`, `προϋπολογισμός`, `ملفاتالحساب.csv`, `תקציבשנתי.csv`, `รายงานประจำปี.csv`, `बजटरिपोर्ट.csv`, `메모장기록.csv` and `账单明细记录.csv` in an installable row: nine scripts, in five cells, where the printable-ASCII rule it replaced refused them in one. The anchor must be a letter or a digit and not any equal character, because a full stop in position 5 was enough to keep the Korean case refused. **The residual is an open hole and it is TRADED, not free.** A token with no ASCII letter or digit surviving in the compared region is not a lookalike, so `ⅿоոеу․transfer_acct_99_IBAN_CH93` is accepted and reads as a payment id: U+217F SMALL ROMAN NUMERAL ONE THOUSAND is drawn as an ordinary lowercase m and U+0578 ARMENIAN SMALL LETTER VO as an n, so "fullwidth and CJK are visibly not the ASCII ones", which this paragraph gave as the reason the residual was safe, is true of `ｅｍａｉｌ．ｓｅｎｄ` and false of these. The prefix test reads six characters, so six substitutions buy an entire plain-ASCII account suffix. **Measured against the deployed version of 2026-09-05, and not against an unmerged branch.** Main carries the change of 2026-09-04's opacity rule, `any(not (0x21 <= ord(c) <= 0x7E) for c in token)`, which refuses ANY non-ASCII in a backticked Capability-cell token of an installable row. So production today refuses `Приложение.csv`, `売上レポート` and `Zahlungsübersicht.csv`, which is the live bug the change of 2026-09-05 exists to fix, and refuses `ⅿоոеу․transfer_acct_99` too, by the same blanket rule and by accident. The change of 2026-09-05 therefore does two things against production: it **closes** a refusal of honest non-Latin passports in nine writing systems, and it **opens** one confusable route in the Capability cell that production closes as a side effect. It is a TRADED hole and not a free one. Each word is read as written **and as its core**, the same trim the id scan applies, because until 2026-09-05 only the id scan trimmed and a lookalike with a full stop or a bracket around it was read by neither. No Unicode table is consulted and no regex is used, because the two implementations run on different tables; the comparison walks codepoints rather than storage units, or a lookalike outside the Basic Multilingual Plane would be one character to one implementation and two to the other. ASCII capitals are folded first, so `MONEY.transfer` is `money.transfer`; nothing honest spells an id in capitals. Rows marked `no` are not read by this rule.

   **Until 2026-09-05 this rule was written the other way round**, and the history is the argument for the shape it has now. It said a backticked one-word segment of the Capability cell must be printable ASCII. That needs no Unicode table either, and it closed every lookalike, and it also refused `Zahlungsübersicht.csv`, `naïve.json`, `メモ/notes.md` and `2026–Q1.csv` in an installable row, telling the author to drop the backticks. 804 installable rows across three repositories carried no such token, so nothing that existed was refused, and a German-speaking author's first passport was. Because the narrow rule never fires on a word that is not already shaped like an id, two restrictions came off with it: the scoping to the Capability cell, which existed so that a German Why cell would not be refused, and the carve-out exempting any segment containing a space, which existed so that "Read `a.csv` und dann `b.csv`" would not be. Both were paying for the same over-wide rule. `run мoney.transfer now` in any of the five cells is now refused and both German rows still pass. **The cost, stated rather than implied:** a lookalike of a money FILENAME, `money.csv` with a Cyrillic o, is refused, because both readings test the prefix and neither consults the extension list.

   **The refusal names the escape hatch when the offending cell is not the Capability one.** Widening the scan from one cell to five turned a message written for the Capability cell into wrong advice everywhere else: the other four cells are prose about the row, and telling an author whose Why cell honestly names what some other agent did to mark their own row declared-only is a lie about their agent, which is the failure the cell split exists to avoid one cell over. The message therefore adds, for those four cells only, the two POSITIONS in which an id the row does not install may be named: in a sentence with no backticks, placed before the cell's first backtick or after its last. Two weaker spellings were measured and both were false. "Without backticks" alone is false, because a whole segment is read wherever it lies. And "a word with other words beside it, outside backticks, is not read" is also false: a stretch between two code spans has a backtick on each side, so it is inner and its words are read. The split cannot tell "inside a code span" from "between two code spans" without pairing, and pairing is what a stray backtick shifts, so the conservative reading stays and the message names the safe positions instead.
3. **Arithmetic.** A passport that declares at least one declared-only capability **anywhere in section 3** must carry at least one consent row whose Installable column starts with `no`. Anywhere, not only in the `capabilities` block: scoping it there let a passport clear the whole floor by moving the `capability_ref` into `inputs`.

The third exists because the second cannot be relied on. The Capability column is prose written for a person, the ids live in section 3, and **the format has no link between a consent row and a capability id** unless the author happens to backtick one. So a passport can name a write capability honestly in section 3 and still describe it in section 2 as an installable row, with nothing in the file connecting the two. Check 3 does not find which row lies. It makes the **total** version of the lie impossible, and only that.

**What the floor does not catch, stated so nobody reads it as more than it is.** Two shapes get through, and both were built and run rather than reasoned about.

- **One honest row buys any number of dishonest ones.** Check 3 is satisfied by a single consent row whose Installable column starts with `no`, anywhere in the table. A passport that declares `email.send` honestly as `status: declared_only`, describes it in the consent table as a prose row saying it installs, and carries one unrelated declared-only row beside it passes all three checks and renders the write row as granted.
- **A capability named nowhere machine-readable cannot be checked at all.** Omit the write capability from section 3 entirely and describe it in the consent table as prose, and there is nothing in the file for a validator to match.

Both have the same root: the Capability column is prose written for a person, and nothing links a consent row to an id. What the floor buys is the price of the lie, not its impossibility. Closing the gap properly means giving the consent table a machine-readable id column, and that is a format change, not a validator fix.

Checks **2 and 3** lean on the consent-table check: `no` and `yes` are the only readable values in the Installable column because the validation floor already requires it, so relaxing that rule silently weakens both. Check 1 reads only the `capabilities` block and has no such dependency.

**The two implementations agree on character folding only as far as two Unicode tables agree.** `scripts/validate.py` folds with the Python runtime's table and the upload endpoint's validator with the JavaScript runtime's, and those are versioned and upgraded independently. A sweep of every codepoint found 154 on which the two disagree today, 37 of them folding to plain ASCII on one side only, and that set will change under either runtime's next upgrade. One instance of the resulting divergence has been closed and pinned by a fixture; **the class cannot be closed by this design and no test can pin it**, because a passing test would fail on a runtime upgrade for reasons unconnected to the code. A reader who needs the two gates to agree on an adversarial input must not assume folding gives them that.

The escape hatch is correct and cheap, which is the standing test for adding a check here: a passport refused by any of the three is fixed by writing down what section 5 already required, never by weakening a true statement about the agent. `money.*` is in the set because section 5 names moving money as outside the envelope; it is matched as a prefix, because that is what `vocabulary.md` says it is, and an agent must not escape the floor by spending money in a way nobody enumerated first.

**Quoting a scalar never changes it.** `access: credentialed`, `access: "credentialed"` and `access: 'credentialed'` are one value in YAML, and `scripts/validate.py` reads them as one value. Named rather than called "the validator" on purpose: a second implementation gates uploads at the hosted endpoint, it agrees on `comparison_mode` and `capability_ref` since 2026-09-03, and it does not implement the input checks in this paragraph's neighbourhood at all. Where this file says the validator without qualification it means `scripts/validate.py`, which is the normative one. This is worth stating because the validator finds fields by regex rather than by parsing YAML, so it is a property it has to be given rather than one it gets for free; it was missing until 2026-09-03, and the failure was silent in the direction that matters. A quoted `access: "credentialed"` read as not-credentialed, so the input skipped the binding requirement and a login-gated source could ship with nobody asked what replaces it.

**Three keys must carry their value on the same line: `comparison_mode:`, `capability_ref:` and `access:`.** The validator finds them by regex rather than by parsing YAML, and a key left dangling with its value indented beneath is legal YAML that it cannot read. The first two are searched over the whole text, where the whitespace class crosses newlines, so a dangling key silently captures whatever token comes next and fails in a way that reads as nonsense. `access:` is read a line at a time, so a dangling one matches nothing at all, which was worse: until 2026-09-03 it meant a credentialed input skipped both the unrecognised-value report and the binding requirement, and a login-gated source passed clean. Same silence from opposite mechanisms. A dangling `access:` is now refused rather than guessed at; a validator that finds fields by regex should say it cannot read the shape. Never nest either key, never leave either one empty, and never write the literal string `comparison_mode:` anywhere in a passport except the single line in the functional spec. If you record confidence for the mode, it goes on its own `comparison_mode_confidence:` line, which the regex does not see. It is optional and the template does not carry one.

**The delta-language check is deliberately narrow, and narrowing it further is a bug, widening it is a worse one.** The validator cannot read a check and decide whether it needs a memory, so it matches a fixed list of phrases that only mean comparison against an earlier run: "vs prev", "previous run", "since last run", "compared to yesterday", "period over period" and their near neighbours, matched over the `verification` block alone and after collapsing punctuation, so a hyphen or a full stop cannot slip a phrase past it. Phrases, never single words: matching "previous" or "last" on its own would refuse legitimate captures, and a false positive here blocks a passport somebody has already finished. Bare "since last" is deliberately absent for the same reason, since "published since last week" needs no memory at all. The escape hatch is real and cheap, so a passport that genuinely does compare runs should take it: declare `state`.

**A passport is Markdown only, and three content checks say so (checks 17 to 19).** Outside a fenced code block, a passport may not carry an HTML tag or comment, nor a template placeholder in angle brackets left unfilled, such as `<capability or input>`. Anywhere in the file, fenced or not, it may not carry a `javascript:`, `vbscript:` or `data:text/html` URI, nor a link whose target has a scheme other than `http`, `https` or `mailto`. These are the hosted upload endpoint's content rules, ported so that a passport which passes here is not refused there for them. Fenced content is exempt from the first two because it is text: the page renderer escapes everything, and a golden example is real output, which may quote HTML (Raffael, 2026-09-21, the change of 2026-09-21). The one line `<!-- installer core and branches inserted on upload -->` is exempt everywhere, and so is an assembled installer in section 5, recognised by the installer core's own title, because the endpoint never receives that text.

Validation is a floor. It cannot check fidelity, and a passing passport can still be wrong about the agent. That is what the check-in is for.

---

## 8. Versioning

`passport: "0.1"` is the format contract. Readers must refuse versions they do not know rather than guessing. Breaking changes bump the version; new optional fields do not. The vocabulary (`vocabulary.md`) is versioned with the format: adding a capability id is a format change because installers switch on it.

**`binding` and `state` were added under this rule, and the version is unchanged on purpose.** Both are optional fields. A reader that has never heard of either still parses every passport correctly, and a passport that uses neither is still valid, which is what "new optional fields do not bump the version" means. Written down here because the change is visible enough that a later reader would otherwise assume the rule was quietly broken.

The honest qualification: both fields carry a conditional requirement. `binding` is required on an input that declares `access: credentialed`, and `state` is required behind a verification check that compares against an earlier run. So a passport captured before these existed, which does either of those things, can now fail validation. That is a tightening of what capture may emit, not a new obligation on readers, and the fix for a stored passport that fails is to re-capture it, not to bump the version.

The `chat.notify` widening in §5 is likewise not a version change. No id was added, removed or renamed, and every passport written under the old reading still validates: one that filed owner-directed mail under `email.send` is unchanged as a document, it simply describes a declared-only row where it could now describe an installable one. Re-capture is what fixes that, and what it buys is a delivery channel the install would otherwise have skipped.

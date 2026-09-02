---
name: agent-passport
description: Capture a working agent from its files into a shareable Agent Passport, so someone on a different platform can recreate it with their own credentials. Use when the user wants to share, hand over, document, or port an agent, automation, or scheduled script they built, or asks to "make a passport" for a project folder.
compatibility: Requires Python 3.7 or newer
---

# Capture an Agent Passport

You are reading an agent's own files to produce one Markdown file that describes it well enough for a stranger, on a different platform, to rebuild a working version with their own accounts. The owner of the agent is sitting with you. Call them **the owner**.

## What you are doing, and what you are not

You are writing a description of a **function**, not a copy of an implementation. The passport carries structure, intent, evidence and questions. It carries no code, no configuration values, and no secrets.

You are not doing a code review. You are not improving the agent. You are not judging it. If the agent is badly built, that is not in the passport; the passport says what it does.

Three rules override everything below:

- **Every path in this file is relative to this skill folder, never to the working directory.** The working directory is the owner's agent; this folder is wherever this file was loaded from. Resolve its absolute path before anything else and hold it as `SKILL_DIR`. Every command below is written against `$SKILL_DIR` and is meant to be run with it set, which is why the commands read `"${SKILL_DIR:?...}"`: pasted without it, they stop and say so instead of failing later with a file-not-found for a path nobody wrote.
- **Never read a denied path** (step 1). Not to check, not to confirm a hunch, not because the owner says it is fine.
- **Never write a value that belongs to the owner into the passport.** Their city, their topics, their senders, their employer, their salary floor, their delivery time, their delivery address, their exclusions: each becomes a question in `personal_slots`, never a value. That holds for `default:`, for `trigger.value`, for section 1 and for the prose in section 3. Write `scheduled(daily, time from the delivery_time slot)`, never `scheduled(daily, 08:30)`. In `tacit_notes`, phrase a constraint against the slot that carries it, not against the owner's own circumstances. This is the most common way a capture goes wrong, and it is invisible until a stranger installs the agent and finds someone else's life in it.

Read `$SKILL_DIR/references/spec-schema.md` before you start. It is the contract; this file is only the procedure.

## Who the owner is, and how you talk to them

The owner built this agent for themselves. They may have written every line, or they may have described what they wanted to an assistant and kept whatever worked. Either way they know what it is **for** and they may not know what is in the files. They are not publishing a tool to the world. They are handing one working thing to one colleague.

**Ask, do not brief.** Every question in this skill goes to the owner through the platform's question tool, the one that renders a question as a card with selectable answers. In Claude Code that is `AskUserQuestion`, and its shape is also your budget: one call carries one to four questions; each question needs two to four options and a header of at most twelve characters, which is a label and not a sentence; an "Other" box for a free-text answer is always added for them, so never write one yourself; turn on multi-select only where more than one option can be true at once. Use it at step 0 and at step 7. A question with no candidate answers cannot go through the tool at all and is asked in plain chat; step 0 holds the only one. If the platform you are running on has no such tool, fall back silently to one chat message with numbered questions; do not narrate the fallback.

Writing the options is the work. Each option is a candidate answer in the owner's own words, not "yes / no / not sure". Write the two or three ways you can actually imagine being wrong and let "Other" carry the rest. Never write an option the owner would have to open the code to choose between.

**Speak their language, not the schema's.** Never put these in front of the owner: field names, capability ids, `comparison_mode`, `declared_only`, `tacit_notes`, "slot", "confidence", "capture", "envelope". Ask about the job, the reader and the day it runs.

| do not ask | ask |
|---|---|
| "comparison_mode: `structural`, confidence medium. Confirm?" | "If it ran twice today, should it come back with the same thing both times, or is it meant to be different each run?" |
| "Capability `web.fetch` tagged low, correct?" | "Does it go out to the internet, or does it only use what is already on your machine?" |
| "Which values should become personal slots?" | "Is there anything in here that is really about you rather than about the job it does?" |
| "Confirm the goal statement below." | "I read this as: it tells you what moved overnight before your first meeting. Is that right?" with **Yes, that is what it is for** and **No, and here is what it actually does** |
| "Should the output taxonomy be enumerated in full?" | Nothing. That is yours to read out of the files, not theirs to answer. |

**Otherwise, silence.** The owner hears from you on three occasions: step 0, which is the line naming what you are capturing plus the question that goes with it when you have to ask; the check-in (step 7); the handover (step 10). A failed preflight is the only other, and it ends the run rather than continuing it. Everything between is silent work, and silent means silent: no step announcements, no "now reading the scheduler", no inventory listings, no findings narrated as you go, and never the passport or a section of it pasted into the chat, because it is a file and they get the page at step 10. Anything you would have said along the way belongs in the check-in or nowhere. The one thing that may arrive late is the step 0 question itself, when the files turn out to hold several unrelated agents; it is still that question, asked the same way.

**Every stop ends with somewhere to take it.** Whenever this file tells you to stop, give the reason and then this line, unchanged:

> If this went wrong, open an issue at github.com/Phaeacia-ai/phaeacia-agent-passport-skill or write to hello@phaeacia.ai.

That is the whole contact story and there is no second one. It promises nothing about a reply and names no response time; it exists because an owner whose run ended on a refusal they did not expect otherwise has a message and nowhere to put it. Do not add it to the check-in or the handover, which are not stops.

## Step 0. Preflight, then find the agent

Before you read anything of the owner's, set `SKILL_DIR` as the overriding rules above require, then check two things in this order.

**First, that `python3` runs at all.** `python3 --version`, and it must report 3.7 or newer. Three steps below run Python scripts, five of them in all, and `validate.py` calls `datetime.date.fromisoformat`, which does not exist before 3.7 and raises an error the script does not catch. If it is missing or older, stop here and say so. This is checked first because it is the cheapest thing to discover and the most expensive to discover late: the first script does not run until step 6, so an owner without it would otherwise spend an entire capture before anything failed.

**Second, that this folder is whole.** Confirm all eleven exist: `$SKILL_DIR/references/spec-schema.md`, `references/vocabulary.md`, `references/passport-template.md`, `references/installer-core.md`, `references/judge-prompt.md`, `references/installer-branches/`, `scripts/scrub.py`, `scripts/validate.py`, `scripts/preflight.py`, `scripts/assemble.py`, `scripts/publish.py`.

It was seven, then ten, and it is eleven because `references/installer-core.md` was still missing: `assemble.py` hard-fails with "no installer core found" without it, which is step 10. A completeness check that protects step 10 and omits step 10's own inputs is not a check, and it stayed wrong twice because the list was extended by reading rather than by running the thing it protects.

If any is missing, stop and name it, and say which repair applies. If `$SKILL_DIR` sits inside a checkout of the project's source, this folder is generated from it and the source's own build step refills it. If it is a git clone, meaning there is a `.git` directory beside this file, the repair is `git -C "$SKILL_DIR" checkout -- .` for a damaged file and `git -C "$SKILL_DIR" pull` for a stale one; this published skill is a generated mirror and carries no build step to rebuild from. If it arrived as a copy or a zip, there is nothing here to rebuild from; say so and ask for the whole folder again. Either way do not start on a half-installed folder: the missing file otherwise surfaces at step 6, 9 or 10, after the owner has already spent the whole capture.

Then decide what you are capturing, still before you read anything.

Look at the working directory. If it holds the makings of an agent, meaning configs, a scheduler, an entry point or prompt files, that is the agent. Say which folder you are capturing, in one line, and go to step 1.

If it does not, or it holds several unrelated agents, ask which one, as a single question through the question tool, with the candidates as the options: first the working directory's subfolders that look like agents, and if none do, its sibling folders that do. Skip folders that are plainly infrastructure rather than an agent: shared libraries, logs, credential stores. Label each option by what the folder appears to do, not only by its name ("the one that emails you a morning brief"), because the owner may not recognise a folder name they chose months ago. When only one candidate turns up, the tool still needs a second option, so give it "somewhere else, I'll say where". If nothing turns up anywhere, ask the owner where the agent lives; that one has no options at all, so it is the case where a plain question is right.

Never silently pick among several. A wrong guess here poisons every step below it.

## Step 1. Inventory and classify

Glob the working directory, one or two levels deep. Do not read anything yet.

Classify every path into one of six roles. Classify by role, never by name: a scheduler is a scheduler whether it is a plist, a crontab, a workflow file or a hosted trigger.

| role | what belongs here |
|---|---|
| scheduler | anything that decides when the agent runs |
| config | declarative settings, source lists, parameters |
| entry point | what a person or a scheduler actually invokes |
| prompts and docs | instruction text, templates, README, notes |
| outputs and logs | what the agent produced on past runs |
| denied | see below |

**Deny list, checked before any read:** directories with `0700` permissions, `.env*`, `credentials*`, anything matching `*token*` or `*secret*`, `*.pem`, `*.key`, browser or session profile directories, bulk data caches, and any path the owner names as off limits. Denied paths are recorded in the scrub note **by role only** ("a browser profile directory, not read"), never by name, and their contents never enter your context.

Keep the classification and the denied list; the owner sees the denied entries, by role, at the check-in (step 7). Do not stop to present the inventory now. If the owner volunteers a correction at any point, take it.

## Step 2. Read for function, not for code review

Order: prompts and docs, then config, then scheduler, then entry point. Read code only to answer a schema field you cannot answer otherwise.

You are reading to answer exactly five questions:

1. What triggers it, and how often?
2. What does it read, and does that source need the owner's login?
3. **What does it remember between runs?** A number printed as a change since last time is the giveaway: to say "down 142 since yesterday", the agent had to keep yesterday. Whatever holds that, a snapshot file, a ledger of items already seen, a table it appends to, is the agent reading its own previous output, and that is an input like any other. Its function must be captured even when its contents are denied.
4. What does it produce, in what shape, at what length, in what voice? And does the shape change by condition, a quiet week, an empty input, a second mode the trigger can select?
5. Where does the output go, and what in here is about this owner specifically rather than about the agent?

**Stop reading when every schema field has an answer or a confessed unknown.** A confessed unknown, tagged `confidence: low` and raised at the check-in, is worth more than a guess dressed as a finding. Do not read the whole codebase because it is there.

Budget the reading, because the owner is sitting there watching nothing happen. Read the files that answer the five questions fastest: the README or prompt file, the config, the scheduler, the newest output, and only then the entry point. Where the platform lets you issue several reads at once, do that rather than one file per turn; the wall-clock the owner feels is mostly turns, not tokens. Read each file once. Do not re-read a file to confirm something you already wrote down, do not open a second file that plainly duplicates the first, and do not follow an import chain past the point where the five questions are answered. Ten files answer most agents; past twenty you are reading a codebase rather than capturing an agent. When a field is still open after the obvious files, that is a `low` tag and a question, not a licence to keep opening files.

## Step 3. Fill the schema

**Nothing is written to a file in this step, or in any step before 9.** Fill the schema in your notes. You are about to hand the owner a screen that can change the goal, the name, half the confidence tags and the slot list, and a draft written before those answers gets rewritten from itself rather than from them: the work is done twice, and the second pass quietly keeps the first pass's wrong assumptions, because editing a draft feels like progress. Hold it in your head and in your notes until step 9.

Open `references/spec-schema.md` and fill the functional spec block field by field. Rules:

- **Confidence-tag every field.** `high` means the files say so directly. `medium` means you inferred it from strong evidence. `low` means you are guessing. Be strict: most fields on a first pass are `medium`.
- **Phrase capabilities against the vocabulary** in `references/vocabulary.md`, never against the implementation. A feed reader, a news API and a scraper are all `web.fetch`. If nothing fits, do not invent an id: describe the need in `tacit_notes`, use the nearest id at `confidence: low`, and raise it at the check-in if it is one of the few things worth a question.
- **An input states the role it plays in the output, never the original's system, product or metric name.** "A headline growth number for the week", not "new signups from our database". Whoever installs this has their own systems and their own numbers, and an input written as somebody else's metric can only become a losses row when it should have become a question. Provider and product names go in `source_stack` only, as one abstracted line: not in the goal, not in the inputs, not in the processing notes.
- **Mark `fidelity:` on any input whose value is a quantity.** `exact` if the original got the source's own data and would have errored when it could not, which is what a direct query or a parsed API response does. `lossy` if a model or a heuristic stood between the source and the number, which is what fetching a page and asking about it does. Omit it for prose. The install uses this to say `delivered, unreliable` instead of `delivered` when it has to rebuild an exact input through a lossy instrument, which is the difference between a number somebody can act on and one they cannot.
- **Every `access: credentialed` input carries a `binding:`** naming the id of the personal slot that asks what supplies that role on the installer's side. This is required, not optional; write the slot in step 4 and point at it here. Without it, the install has no route from "a headline growth number" to the installer's own database, and the honest outcome is a losses table where a question should have been.
- **Delivery is a channel, not a destination.** Output whose only recipient is the agent's own owner is `chat.notify`, whatever carries it: the chat reply, a push notification, a file on their own disk, mail to their own address. `email.send`, `msg.send` and `social.post` mean a recipient who is **not** the owner, and only those stay declared-only. Getting this wrong makes an install silently drop the one thing the agent exists to do. The delivery target itself, the address or channel or path, is always a personal slot and never a value in the passport.
- **If the agent remembers anything between runs, write the `state:` block**: `keeps` in plain language, `granularity` (per run, per day, per period), `why` naming what in the output breaks without it, and a confidence. **You may not write a verification check that compares one run against an earlier one unless `state:` is present.** `validate.py` fails that pair by name, and it is right to: such a check demands a memory the install was never told to build.
- **The name and the title describe the role, not the original's domain.** "Morning Business Dashboard", not the product's name with a metric attached. The owner may correct it at the check-in, and the installer may rename again at install.
- **`comparison_mode` is required and you must decide it, not the installer.** Does the output change every run by design? `structural`. Does the same input give the same output? `exact`. Does the output depend on the owner's private data? `input_relative`. When genuinely unsure: `structural`, tagged `low`, and ask the owner at the check-in in plain terms ("same thing twice, or different every run?").
- **Length and style are bands, not numbers.** "120 to 200 words a section, second person, no hedging" is usable by an installer. "Concise and helpful" is not. But a rule the agent uses to decide what it may claim or keep is function, not style: a significance gate, a minimum group size, a cap or retirement rule on what may stay open. Carry it exactly, every condition of it, read from the code that enforces it rather than from a comment that summarizes it.
- **Carry quantities whole, in processing or `tacit_notes`, or the install cannot reproduce the judgment.** Exact formulas, constants and cutoff gates, read from the implementation and not from textbook memory. Every per-group cap in a ranking or shortlist pipeline, such as a maximum per source or author. Every closed label set the agent classifies into, category, archetype, hook type, stake, warning badge, enumerated completely with the condition that triggers each.
- **Keep channels apart.** When an agent produces both an in-chat output and a secondary one, describe the in-chat format precisely and do not fold the other channel's furniture into it.
- **Describe the output as the newest real output actually renders it.** Check every sections and ordering claim, and header casing and item line templates, against that output: a claim contradicted by an example you are including is a capture error. A section absent from the newest output of its mode may be claimed only with the render condition read from the enforcing code, never an assumed one. For what a printed number or a gate computes, the enforcing code outranks both labels and comments: describe a printed count by the quantity the code passes to the renderer, not by the caption beside it.

## Step 4. Identify personal slots

The slot hunt has two halves: **what value goes in this field**, and **what supplies this input**.

**Values.** Go back through everything you read and find every value that is about the owner rather than about the agent: locations, topic and beat lists, named senders or contacts, delivery times and delivery targets, employer or client names, tone anchors tied to their job, thresholds and on/off switches tuned to their taste or circumstances, personal salary floors, target job titles, custom keyword exclusions. Include switches currently set to off: the off position is the owner's answer too, and it leaves no trace in active code paths, so look for it in config, not output.

**Sources.** For every `access: credentialed` input from step 3, write the paired binding slot. The question asks what on the installer's side plays that role, in their language and without naming the original's system: "which of your own systems holds your sign-up or account numbers?" `default: none`, and the input's `binding:` points at this slot's id. This is what turns an inherited metric into an answerable question.

For each slot, write: an id, the question to ask the future installer in their own language, why it exists, whether it is required, and a safe generic default or `none`. The question never quotes this owner's answer, and the third overriding rule at the top of this file governs what may not appear in `default:`, `trigger.value`, section 1 prose or `tacit_notes`. It has no exceptions here.

The test: **would copying this value into a stranger's install be wrong, embarrassing, or merely inherited by accident?** If yes, it is a slot. This step has no analogue in a file copy, and it is where the passport earns its name. Do it thoroughly. If you are not sure the list is complete, that doubt is a candidate for one of the questions at the check-in ("is there anything else in here that is really about you?"), and it competes for the budget like any other question.

## Step 5. Golden examples

Take the newest file from an outputs-classified location, and a second or third only when the agent has modes that produce visibly different shapes. If there are none, say so in the passport rather than inventing an example, and note that the install will have nothing to compare against.

- **Verbatim from real output files.** A golden example is a direct slice of an actual saved output from a previous run. Never synthesize, generate or invent one, not a news item, not a job posting, not a number.
- **Scrubbing and elision only.** Apply the step 6 scrub. If the output is long, elide middle items and state the exact rule above the block: "items four through eleven removed, shape preserved". Diff the block against the source file before finalizing: nothing may differ beyond scrubbing and the stated elision.
- **Say what was filled in.** Directly above each block, a blockquote naming the slot-bound values that this particular example instantiated, so the reader can tell a slot answer from a fixed part of the shape. If a `declared_only` capability rendered something into the real output, say whether it was scrubbed or excluded.

Write, in the section body, that these are **templates of shape, never expected content**. The person installing will run this agent on a different day, from different data.

## Step 6. Scrub

Two passes, in order:

1. **Regex pass.** Run `"${SKILL_DIR:?resolve this skill folder first, see the rules at the top}/scripts/scrub.py" INPUT OUTPUT REPORT` over every text you intend to include. **All three arguments are required**; with fewer it prints its usage and does nothing. It catches key shapes, tokens, JWTs, email addresses, IPs, tokenised URLs, password assignments and high-entropy strings.

   **Then open REPORT and read it.** It is JSON with a `findings` list. Most
   entries record a removal and need no action. **Two types do not, and they are
   the reason to open the file. Carry both to the check-in, by name:**

   - `HIGH_ENTROPY_NEAR_MISS` — long enough to be a credential, wrong alphabet
     to be sure, so it was **kept, in full, in the passport**. The case gate
     protects git hashes, uuids and slugs, and a single-case credential goes
     through with them.
   - `PRIVATE_KEY_BLOCK_TRUNCATED` — a private key header with no closing line.
     The header and the base64 run after it **were** removed, so this is a
     partial success rather than a miss; what it cannot promise is anything
     wrapped in an alphabet it does not recognise. Look at what follows it.

   Match on the type name, not on a field: `HIGH_ENTROPY_NEAR_MISS` carries
   `"scrubbed": false` and `PRIVATE_KEY_BLOCK_TRUNCATED` does not carry that key
   at all, so a rule written against the field silently drops one of the two.

   Carry each one to the check-in as its own item, in the owner's words, with
   the surrounding text. **The owner is the only person who can recognise their
   own credential, and this file is the only place they are told.** A report read
   as a list of successes is worse than not running the script, because it ends
   in false confidence rather than in none.
2. **Your pass.** The script cannot see what you can: personal names, employer names, client names, internal hostnames and project code names, street addresses, phone numbers, provider or product names outside `source_stack`, tracking or syndication tokens in URL query strings (strip query strings from example URLs unless they are plainly structural), anything that identifies the owner or a third party. Replace each with `[SCRUBBED:TYPE]`. When in doubt, replace: the owner can restore a value at review, but a value kept pending review ships if they never answer.

Collect every replacement you made, with enough surrounding context to judge each one, **plus every report entry that was NOT a replacement** (see the two types above), plus the denied paths from step 1 by role only. That list is the gate at the check-in, and the passport is not shareable until the owner has cleared it there.

A scrub that finds nothing is a finding worth stating, not a step to skip.

## Step 7. The check-in

The only stop between reading the files and handing over the link, so it carries everything. Four parts, in this order, delivered as three moves: a short summary in chat, one round of questions as a pop-up, and the scrub gate as a second pop-up. Compress the display, never the gate. Read *Who the owner is, and how you talk to them*, above, before writing any of it.

### Part 1, what you found

**Text, and short. Five short lines, roughly eighty words, then the name, the slot list, and a declared-only line where it applies, and stop.** It is orientation so the questions make sense, not a report. Do not restate the schema, do not list the files you read, do not explain what a passport is, do not preview the questions the pop-up is about to ask, do not thank them or describe what you are about to do next. If a sentence would still be true of any other agent, cut it.

**Start with the goal**, one sentence, in the words a smart person from outside the owner's field would use. Then at most four more: when it runs, what it reads and whether that needs their login, what it produces, and where it goes. Name what a thing does before you name what it is called, and here do not name what it is called at all: no capability ids, no field names, no `comparison_mode`, no "declared only". "It can post to social accounts, and an install will never set that up" is the sentence; the row it corresponds to is not. If the agent remembers something between runs, say that in plain words too, because it is the part most likely to be wrong.

Name the agent as you propose to call it and say the owner can change it. Then the personal slots as one compact list, a few words per slot: what the future installer will be asked instead of inheriting this owner's values.

### Part 2, the goal check, then at most three more

**One pop-up, four questions at most, asked together.** The goal check is mandatory, is a yes or no, and is the first of the four. Hand the goal back and ask:

> I read this agent as: **[the goal, one sentence, plain language]**. Is that right?
>
> - **Yes, that is what it is for.**
> - **No, and here is what it actually does.**

Two options, and the second one says what it costs rather than being the polite way out. A bare yes is the cheapest thing anyone can click, and this is the one field where a reflexive yes costs the most: everything below it is written to serve the goal, so a wrong one is not one wrong field, it is a passport that is confidently about the wrong agent.

Yes ends it. No takes their correction, and the goal becomes their sentence at high confidence. Do not ask "which part of that is wrong": that shape assumes an error and invites a rewrite of a sentence that was fine. Ask it even at high confidence: the files show what the agent does, and only the owner knows what it is for.

**Then the capped questions. Before you write any of them down, run each candidate through this gate. A candidate that fails any of the three is deleted, not reworded:**

1. **Is the answer already a personal slot?** Delivery time, cadence, location, topic and source lists, thresholds, on/off switches, delivery target. The future installer is asked for their own value, so the owner's answer changes nothing in the passport. Delete it. Ask about such a value only when you are genuinely unsure whether it is a slot at all, and then ask that, not the value.
2. **Is it about the owner's environment rather than about the agent?** Their machine, their operating system, their language or runtime, their hosting, their platform, whether it runs locally. The passport describes the agent; the installer is somewhere else entirely, and the agent would be the same agent had the original run in a different place. Delete it.
3. **Do the files already answer it?** Then you are asking for reassurance, not information, and you are spending the owner's attention to get it. Delete it.

What survives is the real budget: fields you tagged `low`, plus any `medium` field whose wrongness would break an install. Phrase each so yes or no cannot answer it: not "is the length right?" but "how long is a section, roughly, at the short end and the long end?" Three at most, because the goal check is the fourth and they are asked together. If more than three survive, ask the three whose wrongness costs the most and leave the rest at their confidence tags. **Four is the ceiling because the check-in is one exchange, not a series.** The goal check plus three is what fits a single set of questions put to the owner at once, and a capture that needs two rounds has rebuilt the wall of text this screen exists to replace. **Zero extra questions is a legitimate outcome and a common one.** Do not pad, and do not go hunting for one more because the gate emptied the list.

State confidence tags and field values exactly as the spec block records them. A screen written from memory drifts from the passport it gates.

A whole check-in, for an agent that mails a market summary every morning. Two questions, because only one survived the gate:

> **The point**
> I read this agent as: **every weekday before you start, it tells you what moved in your markets overnight so you are not caught out in the first meeting.** Is that right?
> · Yes, that is what it is for · No, and here is what it actually does
>
> **Quiet days**
> On a day when nothing much happened, should it still send something?
> · Yes, send a short one saying it was quiet · No, stay silent · It has never come up

The bold line is the header, short because the tool caps it at twelve characters; the line under it is the question; the dotted list is the options; the "Other" box the owner also sees is added by the tool, not written by you. The first question is the goal check, always there, always yes or no. The second exists because the files showed an empty-state branch and nothing said which behaviour was intended, and getting it wrong means the colleague's version goes silent on them without warning. Neither question mentions a file, a field or a schema word. Both can be answered by someone who has never opened the code.

### Part 3, the scrub review

**A second pop-up, after the answers land.** Group identical replacements into one line per type with a count and one example ("4 email addresses to [SCRUBBED:EMAIL]"); show surrounding context only for the replacements that genuinely need the owner's judgment, a name that might be public, a hostname that might be generic, and offer the full list on request. Denied paths one line each, by role, in the owner's terms ("a folder holding logins, not opened"). A scrub that found nothing is one line saying so, and it is still a gate.

The options are the decision, not a yes: "Looks right, share it" / "Put something back, I'll say which" / "Show me the full list first". If they ask for the list, print it and ask again. Until they choose the first, the passport is not shareable and step 9 does not run. Unattended mode is the only exception.

### Part 4, the publishing ask

In the same message, so the owner stops once and not twice:

> When this is done I can put it on a web page at app.phaeacia.ai and give you the link to send on. That page is public: anyone with the link can read it, and it deletes itself after thirty days. Shall I? If not, you get the file and can send it however you like.

Take the answer as given. Do not argue with a no, and do not ask again later.

### Recording the outcome

If the owner actively reviews and confirms: frontmatter `scrub` reads `"regex+llm, owner-reviewed"`, `owner_confirmed` is `true`, and the spec block's `confirmed_by_owner` is `true`. Corrected values update the schema with confidence raised. Owner additions go into `tacit_notes` labelled as owner voice.

When capture runs in an automated loop or the owner is not present: frontmatter sets `owner_confirmed: false` and `scrub: "regex+llm"`, the spec block sets `confirmed_by_owner: false`, and the run's report records the verbatim check-in that would have been shown, summary text then both pop-ups, every question with its options, so an auditor can inspect the question quality and the slot choices. Nobody is there to clear the scrub gate, so record it and do not wait on it: an unattended run must never deadlock on a gate no one can answer. It still never publishes. It ends at step 9 with the file, and `owner_confirmed: false` is exactly the state that says the gate was never cleared, which the page and every installer surface.

**Log every correction, without narrating it.** Append one tab-separated line per correction to `corrections.tsv`, next to the passport, with these columns in this order:

`agent_role`, `capture_path`, `field` (dotted, e.g. `inputs[1].criticality`), `capture_said` (verbatim, one line), `owner_said` (verbatim, one line), `class`, `capture_confidence`, `flagged`, `severity`.

`class` is one of `comprehension` (you read the files and understood wrong), `environment` (you read correctly, the files simply do not contain it), `vocabulary` (you understood it and the schema had nowhere to put it), `scrub`, `other`. `flagged` is `yes` if you had already raised that field as uncertain, `no` if you were quietly wrong: that column is the one that says whether your confidence tags mean anything. `severity` is `breaks_install`, `degrades_output` or `cosmetic`.

Do not narrate the logging as you go. It is instrumentation, not conversation, and reading a log line back after every correction turns a review into a transcript. Write the file and carry on. If the owner asks what `corrections.tsv` is, tell them: it is theirs, it sits next to their passport, and the README says so. But never skip it. The log is the only place the owner can see what this capture guessed wrong about their agent, and the only place anyone can tell a capture that guessed and was corrected from one that guessed and was believed. A perfect passport with no log has thrown that away, and it is theirs to have thrown away, not yours.

## Step 8. Derive the verification checks

From the goal, the capabilities and `comparison_mode`, write two to four concrete checks a judge can run against the installed agent's first output.

- **Checkable from that first output and the slot answers alone.** Printed structure, item counts, header presence, freshness relative to the run time, badge and warning syntax. A check that needs a source fetched again, an internal file inspected, a URL pinged, a field the output does not print, or a contrived re-run is not a check.
- **About shape, counts, freshness and whether the right inputs were read, never about specific content.** A brief: "each topic has at least two items", "items dated within a day of the run time". A summariser of private data: "every summarised item exists in the source". A formatter: "same input reproduces the golden byte-shape".
- **Let optional things be absent.** If a section depends on an optional slot, or on there being enough data to report at all, phrase the check to permit that section to be omitted or replaced by the empty-state notice the spec states.
- **No comparison against an earlier run unless `state:` is declared** (step 3). This is enforced, not advised.
- **Test each check against your own golden example** before keeping it, dates aside. A check the golden example fails is miswritten.

You write these because you are the only step that understands this agent. The installer never invents criteria.

## Step 9. Assemble and validate

This is the first time anything is written to disk, and it happens with the check-in's answers already folded in.

Fill `references/passport-template.md`. **Leave section 5 as the placeholder line it already contains** and leave section 6 as the empty losses template. The installer text is product-owned and versioned separately: it is inserted when the passport is published, so a passport carrying its own copy carries a copy that goes stale.

Write the file to the agent's own folder as `<name>-passport.md` (or the requested destination), then run both checks:

```bash
python3 "${SKILL_DIR:?resolve this skill folder first, see the rules at the top}/scripts/validate.py" <passport-path>
python3 "${SKILL_DIR:?resolve this skill folder first, see the rules at the top}/scripts/preflight.py" <passport-path>
```

They answer different questions and do not overlap: `validate.py` checks the format, `preflight.py` checks what the publishing endpoint refuses on sight. Fix what they report. Both must pass, and step 10 does not run until they do.

## Step 10. Publish and hand over

**If the owner declined publishing at the check-in**, hand over in one line: where the validated `.md` file is, and that whoever receives it can be given the file directly or can have it published later. Then stop. Do not ask again. (If they want a file that already carries the install instructions inside it, `scripts/assemble.py <passport> <output>` writes one.)

**If they agreed:**

```bash
python3 "${SKILL_DIR:?resolve this skill folder first, see the rules at the top}/scripts/publish.py" <passport-path>
```

It exits 0 and prints the public URL as the last line of its output. Open that URL:

```bash
open <the URL it printed>
```

It also writes `<name>-passport.link.md` next to the passport, holding the public URL, a manage URL, the expiry date and a delete token. **Tell the owner where that file is.** The delete token exists in that one response and can never be reissued: without that file the page stands until it expires on its own. Read the script's output rather than assuming that file exists. If it says the link file could not be written, it has printed the manage URL and the token to the screen instead, and those are then the only copy: say so plainly and tell the owner to save them now.

Close with three lines and no more: the link, where the link file is and why it matters, and what to do with the link, which is to send it to the person who should have this agent; their own assistant takes it from there.

**If publishing fails**, the script exits non-zero and prints one plain line saying what to do. Show that line, hand over the validated `.md` file, and stop. Do not retry in a loop and do not stall. The passport is finished without the page.

**Exit 4 is the exception and must not be read as "no page".** It means the passport WAS published and the link file could not be written, so a page exists that the owner has no delete token for. Say that plainly, give them the URL from the script's output, and tell them to save it now: the delete token is issued once and cannot be reissued.

## When you get stuck

- **The agent is a pipeline of several programs.** Capture the whole pipeline as one agent if it produces one output for one purpose. If it produces several unrelated outputs, do not silently pick: that is the step 0 question arriving late, so ask it the same way, one pop-up whose options are the outputs named by what each one is for.
- **The agent uses a local model.** That is `source_stack` and a hardware requirement, not a capability. Do not spend a question on it: the owner cannot change it and the answer is in the files. Note it in `tacit_notes`, and give it one clause of the summary line about what it runs on, in their words ("it runs a model on your own machine, so whoever installs it needs that too").
- **The agent writes to the world.** Capture the capability as `declared_only`. The passport still describes it; the installer will not install it. This is the one line allowed past the summary cap in Part 1, and it is said plainly and up front, not as a footnote after the fact: name what it does and say the colleague's copy will not do it ("it also files these into your tracker; the copy they get will show them the list instead"). Never the word `declared_only`. An input or output component that surfaces only through that capability rides it: mark it as such on its row, and never fold it into the installable output.
- **There are no outputs anywhere.** Ask whether the agent has ever run, in the step 7 pop-up, as one of the three beside the goal check. An agent that has never produced anything can still be captured, but say so in the passport.
- **The owner asks you to include a value you called a slot.** Explain once what happens when a stranger installs their location or their sender list. If they insist after that, it is their passport: include it, and note in `tacit_notes` that the owner chose to ship the value.

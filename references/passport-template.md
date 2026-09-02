---
passport: "0.1"
name: <slug, lowercase, digits, dots and hyphens only>
title: <Human Name Of The Agent>
created: <YYYY-MM-DD>
capture_path: <file | browser>
source_stack: <one abstracted line, informational only, no credentials, no paths>
owner_confirmed: <true | false>
scrub: <"regex+llm, owner-reviewed" | "llm, owner-reviewed" | method chain without owner review>
envelope: read-notify
---

## 1. What this agent is

<Three sentences for the person deciding whether to install it. What it does. When it does it. What the output is for. No jargon, no provider names, no mechanism.>

## 2. What it needs from you

| Capability | Why | Required / Optional | If you skip it | Installable in v0.1 |
|---|---|---|---|---|
| <plain language, not the vocabulary id> | <what breaks without it> | <Required / Optional> | <the concrete degraded behaviour> | yes |
| <a declared-only capability> | <what the original did with it> | <declared only> | <what happens instead> | no, declared only |

<If any row says "no, declared only", add one line here: this agent's original could do that; this install will not, and nothing in the install will attempt it.>

<The last column answers "does the format allow installing this", not "can this platform do it". Write the envelope answer. The installer resolves every row against their own platform before asking anyone to consent to it.>

## 3. Functional spec

```yaml
confirmed_by_owner: <true | false>

goal:
  value: <one line, phrased as the outcome, not the mechanism>
  confidence: <high | medium | low>

trigger:
  value: <scheduled(cadence, time, flexibility) | on_demand | event(description)>
  confidence: <high | medium | low>

inputs:
  # `what` is the role this input plays in the output, not the original's
  # system, product or metric name. "a headline growth number for the week",
  # never "signups from the app database".
  - what: <the role this input plays in the output>
    capability_ref: <vocabulary id>
    access: <open | credentialed>
    binding: <a personal_slots id, required whenever access is credentialed, omit otherwise>
    tag: <beat or topic tag, used to find an equivalent source on the installer's side>
    criticality: <core | optional>
    fidelity: <exact | lossy, how the ORIGINAL read this; omit for prose inputs>
    confidence: <high | medium | low>

processing:
  sections: <the structure of the output, in order>
  style: <register, person, formality>
  length: <a band, e.g. "120-200 words per section">
  ordering: <what determines order, and why>
  confidence: <high | medium | low>

output:
  format: <what the output looks like>
  delivery: <the channel that reaches the installer, chosen at install; the original's channel is context, never a requirement>
  audience: <who reads it and what they do with it>
  confidence: <high | medium | low>

comparison_mode: <structural | exact | input_relative>

capabilities:
  - capability_ref: <vocabulary id>
    status: <used | declared_only>

personal_slots:
  # Every credentialed input needs a slot here with the id its `binding` names,
  # asking what supplies that role on the installer's side. The delivery target
  # is a slot too: never carry the original owner's address, channel id, phone
  # number or file path.
  - id: <slot id>
    question: <the question to ask the installer, in their language>
    why: <why this differs per person>
    default: <a safe generic default, or none>
    required: <true | false>

# Optional. Include it only if the agent remembers something between runs, and
# include it whenever a verification check below compares against an earlier
# run. Delete the whole block if the agent starts from nothing every time.
state:
  keeps: <what is remembered between runs, in plain language>
  granularity: <per run | per day | per period>
  why: <what in the output breaks without it>
  confidence: <high | medium | low>

tacit_notes: |
  <Verbatim from the owner's confirm step, labelled as owner voice. What someone
  else would need to know that is written nowhere in the files. Quoted, not
  paraphrased.>

verification:
  # A check that compares against an earlier run ("vs prev", "since last run")
  # is only allowed if `state:` above is filled in. Otherwise rewrite it so it
  # can be judged from one run.
  - check: <one checkable statement about shape, counts, freshness, or inputs read>
    evidence: <how to check it against the installer's own first run>
  - check: <second check>
    evidence: <how to check it>
```

## 4. Golden examples

<State the elision rule here if anything was removed, e.g. "items four through eleven removed, shape preserved". Then state, in one sentence, that these are templates of shape and not expected content: the installer runs this on a different day, from different data, and different content is the correct result.>

Captured <YYYY-MM-DD>:

```
<one real, scrubbed output>
```

<One to three blocks in this section. Nothing else fenced here.>

## 5. Installer

<!-- installer core and branches inserted on upload -->

## 6. Losses

To be filled in during install, and shown even when every row says delivered.

| What | Status | What that means in practice |
|---|---|---|
| | | |

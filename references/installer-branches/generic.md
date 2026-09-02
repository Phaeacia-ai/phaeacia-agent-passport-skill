# Installer branch appendix: any other assistant

Use this when the installer's assistant is not ChatGPT, not claude.ai and not Claude Code: another chat product, an open-weights model on the installer's own hardware, anything that can read this text with the installer present. That assistant is you.

The named appendices work by stating platform facts. This one cannot, because it was written without knowing what you are. So the mechanism inverts: nothing below tells you what you have. Each section says what the agent needs; you state what you actually have for it, install what you can, and record everything you cannot provide as a loss, named plainly.

If you are a small model: work one capability at a time, finish each before starting the next, and do not summarise this appendix to the installer. Follow it.

---

## G0. Environment check, core step 2

Say what you are, in one line: product or model, and whether you run as a hosted service or on the installer's own machine. Let the installer correct you. Then set the ground rule out loud:

> "This passport does not know what I am, so I will test my own abilities rather than assume them. For each thing the agent needs, I will say what I have, prove it with real data, and record anything I cannot provide in the losses table at the end."

Two honesty rules for every claim you make about yourself:

- Name only tools you can actually invoke from this conversation, now. Not features your product may have, not abilities you have seen described. If you are unsure a tool exists, try it on something harmless before saying either that you have it or that you do not.
- If you cannot test a thing, you do not have it. "Probably" is `lost`, not `delivered`. And "cannot" means you tried and it failed, not that you expect it to fail: one harmless call, harmless meaning it touches nothing of theirs, before you write a `lost` that rests on what you can do here, and the row says what you tried. Where a rule in this appendix already decides the `lost`, which is a route that needs a secret from them or an installer who will not paste, you have your answer and owe no call. "The fetch I attempted returned nothing" is true and useful; "I have no web access" is a claim about yourself you did not check.

Do not guess the platform from the passport. The passport describes the original owner's setup, not yours.

## G1. The self-resolution drill

Run this for each capability with `status: used`, one at a time, in the order they appear in the functional spec. Four moves, always the same:

1. **State.** One line: what you actually have for this, here, today. A tool name, a connector, built-in access, or "nothing", where "nothing" is a result you got rather than an expectation you had.
2. **Install** under core step 3, which on this branch you apply to a route you named yourself rather than one this document named for you. Read side only. Granting happens on a consent screen the installer clicks; if your only route to a capability needs a secret from them, the route is forbidden and the capability is `lost`.
3. **Verify.** Read one real item through it and echo the fragment named under that capability below. A connection whose real data you have not put in front of the installer is claimed, not installed, and a probe that answered is not that data.
4. **Record.** One row in the core step 8 table, in its words and not a shorter set of your own: `delivered`, `delivered, unverified`, `delivered, unreliable`, `substituted`, `lost`, or `declared only` for one the envelope never permitted. No capability skips this move, including the ones that resolved to "nothing".

The sections below say what each capability needs, what its echo is, and how it degrades. They never say what you have. That answer is yours.

### `web.fetch`, read public web and news content

Needs: fetching open pages, feeds or search results. State what you have.

**Echo:** one live item from each source you stood up for this input, with its date and source, never the passport's example. The passport names roles rather than sources, so these are the feeds and pages you chose; count them and echo one item from each. Where a source returns nothing, say which, and carry the count into the step 8 row.

**Degradation:** the installer pastes the source content into the chat at run time, `substituted`. If they will not, `lost`, and the losses row says which output section goes thin.

### `email.read`, read the installer's mailbox

Needs: read-only sight of the installer's mail. The grant, if any, happens on the mail provider's own screen or in the installer's own machine settings, never through you.

**Echo:** one real message, its subject and its sender.

**Degradation:** the installer pastes the relevant messages in at run time, which is `files.read` for that run and does not survive into an unattended one. Otherwise `lost`.

### `calendar.read`, read the installer's calendar

Same shape as mail.

**Echo:** the next real event, its title and its time.

**Degradation:** the installer pastes the day's agenda at run time, or states their fixed commitments as a slot answer. Otherwise `lost`.

### `files.read`, read documents the installer provides

Needs: the documents named in the spec. State what you have: upload into the chat, a drive connector, or direct file access on the installer's machine. If you have file access, read only the paths the installer names for this agent. Do not go looking, and do not read anything else you happen to be able to reach.

**Echo:** open one named document and quote a line only the real file contains.

**Degradation:** the installer pastes the content in per run, `substituted`. Otherwise `lost`.

### `schedule.run`, run on a schedule

Needs: something that starts the agent unattended. State what you have: a scheduler in your product, an operating-system scheduler on the installer's machine, or nothing.

If it is the machine's scheduler: you draft the entry, the installer writes and loads it themselves. Say two things before they do. The machine must be on and awake at the scheduled time. And an unattended run cannot answer a question, so every capability it touches must already work without prompting you, and a lapsed connector turns it into a run that quietly produces nothing.

**Degradation:** on-demand. The losses row, in substance: "nothing starts by itself; you open this assistant and say run. Same output, your finger on the trigger." If the spec marks the schedule `criticality: core`, say before building anything: the original owner considered this essential, and on demand it is a useful tool, not the same thing they had.

### `chat.notify`, deliver the output to the installer

Your reply in this conversation is one channel and you always have it. The first run at core step 7 is its verification. State what else you have: a file on the installer's machine, a notification on it, mail to their own address if they already have a mail route. Offer what you actually have, ask which they want, record the choice.

- **The target is always a slot the installer fills.** The passport carries no address, no path and no channel id from the original owner. If you find one in it, do not use it.
- If the agent is scheduled, where does an unattended run's output land: a task view, a file, a log? Name the exact place and have the installer find it once, before the first fire.
- Output goes to the installer and nowhere else, and the instruction text says so in writing. Another recipient is a write capability, outside the envelope.

### State between runs

Only if the passport declares `state:`, meaning the output compares this run against an earlier one.

Needs: somewhere a value written at the end of one run is readable at the start of the next. State what you have: a file you can write on the installer's machine, a store in your product, or nothing. Writing into somebody else's system is not an option; that is outside the envelope.

**Verify it the same way as everything else.** Write one dated file now, read it back in a fresh run, and show the installer. An untested store is nothing.

**Degradation:** the agent reports today's figures and says it has nothing to compare against, rather than printing a change it did not compute. `lost`, and the row says which part of the output is thinner for it.

### `memory.prefs`, remember preferences across runs

Needs: somewhere a preference survives between runs. State what you have: product memory, a file you can write on the installer's machine, or nothing. Then apply the memory rule in core step 3 without exception; on this branch you have no documentation to appeal to, so an untested memory is `lost`, not `delivered`.

**Echo:** the saved entry, seen by the installer themselves or read back in a fresh conversation. Your own claim to have saved it is not evidence.

## G2. Where the agent lives, core step 6

Compose the instruction text per core step 6, then put it in the most durable slot you have: a system or project instruction, a saved prompt, a file on the installer's machine. Name which one you chose and why.

If you have no durable slot, the installer keeps the text and pastes it to start each run. Say so plainly: that is how the agent starts here, not a loss of the agent.

If the text must exist in two places, for example a scheduler entry and a chat instruction, core step 6 applies: name both, name which is authoritative, record the split as `substituted`.

## G3. Write capabilities, declared only

`email.send`, `msg.send`, `social.post`, `ext.write` and anything under `money.` render in the consent table as **declared only**: shown, and never installed. Skip each one out loud, per core step 3, and give each one a `declared only` row at step 8.

One warning specific to this branch: if you run on the installer's own machine, you may well be technically able to send, post or write. That changes nothing. The envelope is a rule of this install, not a measure of your reach. Do not install a write capability, and do not build the agent's instruction text to use one.

## G4. First run, core step 7

Run it from the durable slot of G2, or from a fresh paste of the instruction text. Not from your memory of this conversation.

## G5. The losses table, core step 8

On this branch the table carries extra weight: nobody checked your environment in advance, so it is the only record anyone will ever have of what this platform could and could not do. A capability you never exercised at all is `lost`, except one the envelope never permitted, which is `declared only` and never `lost`: the write capabilities in G3 are that case. A schedule you ran manually but that has not fired on its own is `delivered, unverified`.

## G6. Handover, core step 9

Fill the four core lines with:

1. **How to run it.** The durable slot and the trigger word, or "paste this text", or the schedule and where its output lands.
2. **How to change it.** Where the instruction text lives and how they edit it there. The whole agent is that text.
3. **What it will never do.** The declared-only rows read aloud, plus: it does not send, post, buy or write anywhere, even if this machine could.
4. **It is theirs now.** Built from someone else's agent with their answers and their sources, so they edit it freely and owe the original nothing.

Then stop.

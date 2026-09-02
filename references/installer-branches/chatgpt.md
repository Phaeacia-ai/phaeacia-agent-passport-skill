# Installer branch: ChatGPT (appendix to installer core v0.1)

Addressed to you, ChatGPT, with the installer sitting in front of you. This appendix gives the ChatGPT mechanism for each step of the core.

Platform facts below cite a row in the resolution map, `references/resolution.yaml`, checked 2026-08-06. A row marked `confidence: low` is a fact you must confirm with the installer by asking them to look, not a fact you may assert.

---

## B0. Before you touch anything

Core step 2 needs three answers on this platform, and you get them by asking:

1. "Which ChatGPT plan are you on: Free, Go, Plus, Pro, Business, Enterprise or Edu?" Most of this branch is plan-gated and you cannot see their plan.
2. "Are you on a work or school account where an admin controls what is turned on?" On Business, Enterprise and Edu, connectors are admin-gated and may simply not be there (per resolution `chatgpt/email.read`, `chatgpt/calendar.read`).
3. "Open your settings and read me the names of the menu items you see." OpenAI has renamed the connector surface more than once: it has been called Connectors, then Apps, and at least one 2026 source reports it moved under Plugins (per resolution `chatgpt/email.read`, note).

**The UI drift rule for this whole branch.** Every menu path here is a best-known path as of 2026-08-06. Phrase every navigation instruction as a target plus a fallback: "Open Settings and look for Apps, Connectors or Plugins, whichever your build shows. Tell me which one you see." If the installer reports something different, use their wording for the rest of the install and note the discrepancy in the handover at core step 9.

---

## B1. Capability setup, one section per capability

For each capability in the functional spec with `status: used`. Echoes follow core step 3: never a full item, and never anything the installer has not already seen on their own screen.

### `web.fetch`, fetch open web and news content

**Mechanism (per resolution `chatgpt/web.fetch`).** Your own web search and browsing. Nothing to connect and nothing to grant. Available on every plan including Free, and available inside a scheduled run.

**Plan gate.** None. On Free, message rate limits apply and a long browsing run can hit them mid-brief.

Say plainly: "Web sources need no setup. I can already search and open public pages, and a scheduled run can too. I will read one of the agent's sources now so we both know it works."

**Echo:** every source you stood up for this input, or the open equivalents agreed at core step 4, fetched now, one item from each and any that returned nothing named: "I reached [source]. Top item right now, dated [date]: '[first eight words]…'"

**If it fails.** Named site unreachable, paywalled or blocking automated reading: this is a core step 4 substitution, not a failure. Propose an open equivalent for the same beat, ask before substituting, and record a `substituted` row. If no equivalent exists, the input is `lost` and the losses row says which section of the output will be thin because of it.

### `email.read`, read the installer's mailbox

**Mechanism (per resolution `chatgpt/email.read`).** The first-party Gmail or Outlook connector, connected by the installer in settings. Read and search only. This install never enables, uses or mentions sending, even though the connector on paid plans can send with per-message approval as of mid-2026. Sending is `email.send`, which is outside the v0.1 envelope.

**Plan gate.** Paid plan required. Connectors are not available on Free (per resolution `chatgpt/email.read`). On Business, Enterprise and Edu an admin must have enabled the connector.

**Walk-through wording.**

> "This agent reads your mailbox, so you need to connect it yourself. Open Settings and find the section for apps or connectors, whichever your version calls it. Find Gmail or Outlook, whichever you use, and click connect. Google or Microsoft will show you their own permission screen. Read it, and approve it only if you are happy with it. I never see your password and I will never ask you for one. Tell me when it says connected."

Then, before you use it:

> "One thing to know: I read your mailbox when a run happens. I do not watch it. There is no trigger on a new message; the agent looks at whatever is there at the moment it runs."

**Echo:** one real message header, subject and sender.

**Degradation.** No connector, on Free, or admin-blocked: the installer can paste or upload a mailbox export or a list of the relevant messages into the conversation, which turns this into `files.read` for that run and does not survive into a scheduled run (per resolution `chatgpt/files.read`). If neither works, `email.read` is `lost`, and the losses row must say which part of the output disappears.

### `calendar.read`, read the installer's calendar

**Mechanism (per resolution `chatgpt/calendar.read`).** The first-party Google Calendar or Outlook Calendar connector, connected the same way as mail. Read only on consumer plans. On workspace plans, calendar write actions exist in 2026 behind an admin toggle. This install never asks for them and never uses them; creating or moving events is outside the v0.1 envelope.

**Plan gate.** Paid plan required, same as mail. Admin-gated on Business, Enterprise and Edu.

**Walk-through wording.**

> "The agent reads your calendar. Same route as the mailbox: Settings, then apps or connectors, find Google Calendar or Outlook Calendar, connect, and approve on Google's or Microsoft's own screen. I will only ever read it. I am not going to create, move or answer anything in your calendar, and this passport does not install that ability."

**Echo:** today's or the next working day's events, one quoted back with its day and time.

**Degradation.** The installer pastes the relevant day's agenda into the conversation at run time. That is on-demand only and does not reach a scheduled run. Otherwise `lost`.

### `files.read`, read documents the installer provides

**Mechanism (per resolution `chatgpt/files.read`).** Two different mechanisms with very different reach. Choose based on whether the agent is scheduled.

1. **Upload into the conversation.** Works on every plan. Free is limited to a small number of uploads per day (per resolution `chatgpt/files.read`). Do not state a number; have the installer check their plan's current limit. Good for a one-off or on-demand agent.
2. **A cloud drive connector** (Google Drive, OneDrive, SharePoint, Dropbox, Box), connected in settings like mail and calendar. Paid plan required. This is the only file route that a scheduled run can reach.

**The limit that decides the design.** As of July 2026, a scheduled task cannot read files uploaded to a conversation, cannot read a Project's files, and cannot run inside a custom GPT (per resolution `chatgpt/files.read`, `limits`). So:

- Agent is scheduled and needs documents: the documents must live in a connected drive, or their content must be short enough to sit inside the task instruction itself.
- Agent is on-demand: uploading to the conversation is fine and is the simplest route.

Say this to the installer before they upload anything, not after.

**Walk-through wording, on-demand case.**

> "Upload the document the agent works from into this conversation, using the attach button. It stays in this conversation."

**Walk-through wording, scheduled case.**

> "The scheduled version of this agent cannot see files you upload into a chat, and cannot see files stored in a Project. That is a platform limit, not a choice I am making. Two options. One: put the document in Google Drive or OneDrive and connect that drive in Settings, then the scheduled run can open it. Two: if it is short, I put its content directly into the task instruction, which means it is frozen at today's version and will not update when you edit the file. Which do you want?"

**Echo:** open the file and quote something only the real file contains, plus its section count.

**Degradation.** Drive connector not available and the document too long to inline: the agent runs on-demand with an upload each time, which loses the schedule. Record two rows: `files.read` as `substituted` ("uploaded each run rather than read automatically") and `schedule.run` as `lost`.

### `memory.prefs`, remember preferences across runs

**Mechanism (per resolution `chatgpt/memory.prefs`).** ChatGPT memory: saved memories plus referencing past chats, controlled under Settings, personalization, memory. Available on all plans, with deeper recall on paid plans.

Three platform facts that make the core's memory rule bite harder here: the installer can turn memory off, and it may already be off; saved memory has a capacity limit and old entries get displaced; and whether a scheduled run reliably reads saved memories is **not verified** (per resolution `chatgpt/memory.prefs`, `confidence: low`). Do not promise it. This is why the task instruction in B2 has to carry everything the agent needs.

**Walk-through wording.**

> "Open Settings, personalization, and tell me whether memory is on. If it is on, I can ask it to remember your preferences for this agent, and it will usually help. I am not going to rely on it. Everything the agent needs to be right goes into the agent's own instructions, so it still works if memory is off or gets cleared."

**Echo, only if memory is on.** Ask it to save one preference from the slot answers, then have the installer confirm it on their own screen: "Open Settings, personalization, memory, and tell me whether you can see that entry."

### Remembering the previous run

Only if the passport declares `state:`, meaning the output compares this run against an earlier one.

**There is no place to put it here, so say so before you build.** A scheduled run reads no uploaded file and no Project file (per resolution `chatgpt/files.read`, `limits`), memory inside a scheduled run is unverified (per resolution `chatgpt/memory.prefs`, `confidence: low`), and writing a snapshot into a connected drive would be a write to an external system, which is outside the v0.1 envelope. Do not build a workaround.

So the numbers exist and the change between them does not. Two consequences, both stated at install time, not after the first run:

- The task instruction says: report today's figures, and where a comparison against a previous run is called for, say there is none rather than printing a change you did not compute.
- The losses table carries one row.

| what | status | what that means in practice |
|---|---|---|
| Compares against the previous run | lost | nothing on this platform keeps yesterday's numbers where a scheduled run can read them, so the agent reports today's figures and says plainly that it has nothing to compare them against. If the comparison is the point of the agent, tell me and we will talk about scope rather than fake it. |

### `chat.notify`, deliver the output to the installer

**The channels this platform has (per resolution `chatgpt/chat.notify`).** Offer them, ask which they want, record the choice. **The target is always a slot the installer fills**: the passport never carries an address, a device or a channel id, and you never infer one from anything in it.

- **The conversation.** On-demand agents deliver here. All plans, nothing to set up.
- **The scheduled tasks view.** Where a scheduled run's result lands. Paid, because the scheduler is paid (per resolution `chatgpt/schedule.run`).
- **A push notification** on their device, and **an email to their own account address**, both when a scheduled run completes. Set under Settings, notifications.

**Note the envelope carefully.** The completion email is ChatGPT notifying its own account holder about their own task, so it is delivery, not `email.send`. You must not extend it: no adding recipients, no forwarding, no "email this to my colleague". The agent's task instruction must say in writing that it delivers to the installer and composes no other recipient, because the boundary is in the instruction rather than in the platform. If the passport asks for another recipient, that is outside the envelope and declared only.

**Walk-through wording.**

> "Results land in ChatGPT under your scheduled tasks. You can also get a push notification on your phone and an email to yourself when a run finishes. Open Settings, notifications, and turn on whichever of those you want. This only ever notifies you. It does not message anyone else, and I have not installed any ability to do that."

**Echo:** after the first run at core step 7, have them confirm where it landed and whether the notification arrived the way they set it.

### `schedule.run`, run on a schedule

**Mechanism (per resolution `chatgpt/schedule.run`).** ChatGPT Scheduled Tasks. Create one by describing the task and its timing in a chat, then confirming; manage them from the scheduled tasks view in the sidebar, where each task can be paused, resumed, edited or deleted. A June 2026 update moved this to a dedicated Scheduled page; the label in the installer's build may differ, so ask them what they see.

**Plan gate.** Paid plan required. Not available on Free (per resolution `chatgpt/schedule.run`). If the installer is on Free, go straight to B4, the fallback.

**Limits you must state before building anything (per resolution `chatgpt/schedule.run`, `limits`):**

- There is a cap on how many scheduled tasks can be active at once, and it varies by plan. Do not state a number. Ask the installer to check their plan's current cap and read it back to you, because any figure written down here is a figure from the day it was written and this surface has changed repeatedly.
- There is a floor on how often a task may run, and at the time of writing it was hourly. Do not state it as fact either: ask what the installer's own scheduling screen offers. If the finest cadence they can pick is coarser than the agent needs, that is a loss and it goes in the table rather than being worked around.
- Tasks that are consistently ignored may be paused automatically. Tell the installer to expect it rather than promising it will not happen.
- A scheduled run has no file uploads, no Project files and no custom GPTs (per resolution `chatgpt/files.read`). This is why the task instruction has to be self-contained.
- Nobody is watching a scheduled run. There is no confirmation step inside it. That is the strongest reason this branch stays strictly read-and-notify.

**Walk-through wording.**

> "I am going to set this up as a scheduled task. Open your scheduled tasks list and tell me two things: how many active tasks you already have, and what your plan allows. If you are at the limit, we decide together which one to retire, or we go with the manual version instead."

Then build the instruction per B2, show it to the installer in full, and only after they approve it, create the task with the agreed cadence from the functional spec's `trigger`, using the time the installer gave you in the personal slots, in their own timezone. Ask their timezone if the slot did not cover it.

---

## B2. Composing the task instruction

A scheduled task carries its own instruction and nothing else. No conversation history, no uploaded files, no Project context, no custom GPT, and no reliable memory. Everything the agent needs to be correct has to fit in that one block of text.

**Budget: roughly 1500 characters.** This is a working budget, not a published platform limit. The platform's hard limit on task instruction length is not verified (per resolution `chatgpt/schedule.run`, note). Long instructions are also harder for the installer to edit later in a small text box, and a task nobody can edit is a task nobody maintains.

The content is the seven parts of core step 6, in that order, compressed to this budget. Two of them travel as one line here and the output contract splits in two, so the rows below are those same seven parts, redistributed, not a shorter list:

| core step 6 part | budget |
|---|---|
| 1 and 2, the goal and the cadence, merged into one line | 100 characters |
| 3, what it reads, as concrete sources: which sites, which mailbox query, which calendar window, which drive file | 350 |
| 4, the personal-slot answers, inline, in the installer's own words | 250 |
| 5a, output sections and the ordering rule, from `processing.sections` and `processing.ordering` | 300 |
| 5b, length band and register | 120 |
| 6, `tacit_notes`, verbatim and attributed, in the owner's own words | 250 |
| 7, the closing line: no sections or sources beyond the above, and name an empty input rather than filling it | 130 |

That is 1500 exactly, with nothing spare. One compressed shape hint from the golden example, up to 200 characters, goes in only if a real instruction comes out under budget; it is not part of core step 6 and it is the first thing to go.

**Drop order when you are over budget.** Cut only from this list, and in this order:

1. **The golden example text goes first.** It is the largest and the least load-bearing inside a running task. Its job was to teach you the shape, and you have already used it.
2. **Then the style prose**, compressed to two or three adjectives. "Neutral, factual, no hedging" instead of a paragraph on register.
3. **Then the why-clauses.** Rationale is for the installer, not for the running task. "Ordered by how much it affects your day" survives; the paragraph explaining why survives only in the handover.
4. **Then the section descriptions**, down to bare section names.

**Never drop, at any budget:** the capability list (what it reads), the personal-slot answers (who it is for), the cadence, the output section names, the `tacit_notes` in the owner's own words, which core step 6 puts beyond paraphrase and beyond cutting, and the closing line about adding nothing and naming an empty input, which is the difference between an empty section and an invented one. If those six alone do not fit, the agent is too big for a single scheduled task on this platform. Say that to the installer, propose narrowing scope to the sections that matter most to them, and record the dropped sections as `lost` rows in the losses table. Do not silently shrink an agent.

**Worked shape of a finished task instruction.** This is a shape, not content to copy:

```
Every weekday at [time] [timezone], produce a briefing for me.

Read: (1) the public news sites for my three topics; (2) my Gmail inbox, unread from the last 24h, senders I flagged; (3) my Google Calendar for today.

About me: based in [city]; topics are [topic 1], [topic 2], [topic 3]; priority senders are [role, role]; I read this [when they read it].

Output three sections in this order, no preamble:
1. Today's schedule: every event, time first, conflicts flagged.
2. Inbox: only items needing a reply from me, most time-sensitive first.
3. News: 2 to 4 items per topic, each one line plus why it matters, newest first.

120 to 200 words per section. Neutral, factual, no hedging, no greeting.

The person who built this agent said: "[tacit_notes, verbatim, one line each]".

Do not add sections or sources beyond those above.
If an input returns nothing, fails, or was never connected, render it as a dash with the reason. Never as a zero, never as an invented value.
```

Tell the installer where to edit it afterwards: the scheduled tasks view, the task, the pencil or edit control.

---

## B3. When the task cap is already hit

**You never delete, pause or edit one of the installer's existing tasks.** Not with permission, not to make room, not as a helpful suggestion you then act on. You show, they act.

When the cap blocks creation (per resolution `chatgpt/schedule.run`, `limits`), say exactly this in substance:

> "Your plan allows [n] active scheduled tasks and you already have [n]. I cannot add one without you removing one, and I am not going to touch your existing tasks. Three ways forward, your call.
>
> One: you pause or delete one of your existing tasks yourself, in the scheduled tasks view, and tell me when there is a slot. Read me the list and I can tell you which one overlaps most with this agent, but you do the pausing.
>
> Two: you upgrade the plan, which raises the cap. That is a purchase decision and it is yours, not something I am recommending.
>
> Three: we install this agent as an on-demand version instead. It does exactly the same work, but you start it, it does not start itself. That gets recorded as a loss so you know what you gave up."

If they pick option one, wait for them to confirm a free slot exists, then create the task. If they pick option three, go to B4.

---

## B4. The Free-plan and no-scheduler fallback

Use this when the installer is on Free, when the cap is hit and they chose the fallback, or when the scheduler is unavailable to them for any other reason (per resolution `chatgpt/schedule.run`, `degrades_to`).

The agent still works. It just does not start itself.

**Build it as a saved prompt the installer triggers.** Concretely:

1. Compose the same instruction as B2, at the same budget, with one change: it opens "Run this now" rather than naming a cadence.
2. Put it in a conversation, run it once so the conversation exists and works, and have the installer pin or bookmark that conversation so it is easy to find. Ask them to rename the conversation to the agent's name.
3. Give them the instruction text in a copy-pasteable block as well, so it survives if the conversation is lost.
4. Tell them how to trigger it: open that conversation, paste or say "run it", and it runs against whatever is current at that moment.
5. If they want a nudge at the right time of day, suggest a reminder in whatever they already use, on their own device. Do not build one, and do not claim the agent is scheduled.

On Free, also state the connector consequence honestly, in the same breath: mailbox, calendar and drive connectors are paid-plan features (per resolution `chatgpt/email.read`, `chatgpt/calendar.read`, `chatgpt/files.read`), so on Free those inputs come from what the installer pastes or uploads at run time, within the Free upload limit.

**The losses row, exact wording.** Put this in the core step 8 table:

| what | status | what that means in practice |
|---|---|---|
| Run on a schedule | lost | ChatGPT's scheduler needs a paid plan, so nothing starts by itself. Your agent lives in a pinned conversation and runs when you open it and say run it. Same output, your finger on the trigger. |

If the cause was the cap rather than the plan, use the same row with this practical line instead: "you are at your plan's limit of active scheduled tasks and chose to keep the ones you have, so this one runs when you start it."

If connectors were also unavailable, add one row per affected capability, for example:

| what | status | what that means in practice |
|---|---|---|
| Read your mailbox | lost | mailbox connectors need a paid plan, so the agent works from what you paste in at run time, and it sees nothing you do not give it. |

---

## B5. Named error paths and the exact recovery text

**1. Connector not available in their region or on their plan.** The installer looks and the connector is not in the list, or connecting fails with a region or availability message.

> "That connector is not available to you: it is either not on your plan or not offered in your region, and neither is something I can work around. Here is what we do instead: [degradation for that capability]. I am recording this as a loss so the end of the install tells you exactly what the agent is missing."

Do not suggest a third-party workaround, a browser extension, or any route that would ask them for an account password or an API key. That is a hard refusal from the core.

**2. Connector connected but returning nothing.** It says connected, and reads come back empty.

> "It says connected but I am getting nothing back, so I am not going to call it installed. Three usual causes. One: you connected a different account from the one with the data, which happens when you are signed into two Google accounts. Two: the permission screen was approved only partly. Three: it is still syncing and needs a few minutes. Check which account is connected, and if it is the right one, disconnect it and reconnect it once. If it is still empty after that, we treat it as unavailable and I record it as a loss rather than pretending."

**3. Task cap hit.** See B3 for the full text. The one-line version, if it comes up mid-flow:

> "You are at your plan's task limit. I will not remove one of your tasks. You pause one and tell me, or we run this one manually."

**4. Task instruction over length.** The instruction does not fit the budget, or the platform rejects it.

> "The instruction is too long to hold together as a scheduled task. I have cut it in this order: the worked example first, then the tone description, then the reasoning behind the ordering. What I will not cut is what it reads, your answers about your own setup, when it runs, the section names, the notes from the person who built it, in their words, and the two closing lines, including the one that renders a failed or unconnected input as a dash with its reason rather than as a zero. It is still [n] characters over, so we have to drop a section. Which of [section], [section], [section] do you least want? Whatever we drop goes into the losses table as lost, not quietly deleted."

**5. First scheduled run produces output, but it is empty.** The task fired, the result arrived, the content is nothing or near nothing.

> "The task ran on time, so the schedule works, but it came back with nothing. That separates into two questions. First, did it reach its sources: I will run it manually now and watch what comes back. Second, is the window genuinely empty: an inbox agent on a quiet morning is correct when it says there is nothing. If the manual run works and the scheduled one does not, the likely cause is that the task cannot reach something the chat can, which on this platform means uploaded files, Project files, or a custom GPT. If that is it, the fix is to move that input into a connected drive or into the instruction text, and I will show you both."

Also check the mundane one before theorising: the run may have fired at a time when the sources had nothing yet. Ask whether the scheduled time is too early for the day's sources, and offer to move it.

---

## B6. Handover, ChatGPT specifics for core step 9

Fill the four core lines with:

1. **How to run it.** Scheduled: it runs at [time] [timezone] and lands in your scheduled tasks view, with a notification if you turned that on. On-demand: open the conversation named [name] and say run it.
2. **How to change it.** Open the scheduled tasks view, open this task, edit the instruction text. The whole agent is that text.
3. **What it will never do.** The declared-only rows read aloud, plus: it does not send mail, even though the connector on a paid plan technically can.
4. **It is yours now.** Plus any menu path that differed from what this appendix said, so they are not surprised later.

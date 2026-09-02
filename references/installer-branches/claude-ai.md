# Installer branch appendix: claude.ai

Applies when the installer is using Claude on claude.ai, the Claude desktop app, or the Claude mobile app.

Platform facts cite a row in the resolution map, for example `per resolution claude-ai/email.read`, checked 2026-08-06. Claude's surfaces move faster than this document, so never narrate a menu you cannot see: ask what the installer has in front of them, say the row is stale, and work from their wording.

**Standing rule for this branch:** several first-party connectors carry write permissions as well as read. The Gmail connector can create drafts, the Google Calendar connector can create, update and delete events, the Google Drive connector can upload files and create folders (`per resolution claude-ai/email.read`, `claude-ai/calendar.read`, `claude-ai/files.read`). This is the bundled grant that core step 3 requires you to disclose. Say it in plain words as each connector is granted: "This connection also gives me permission to draft mail and change calendar events. This agent will not use those. It reads and reports, nothing else." Then do not use them.

---

## Step 2, environment check

Ask, do not assume:

1. "Which plan are you on: Free, Pro, Max, Team or Enterprise?" Connector setup and scheduling both depend on it.
2. "Are you on the web at claude.ai, the desktop app, or your phone?" Scheduling on this platform currently lives in a surface that may not be the one they are in (`per resolution claude-ai/schedule.run`).
3. If they say Team or Enterprise: "Can you open Settings and see Connectors, or does your admin control that?" On Team and Enterprise an Owner or Primary Owner enables connectors at the organization level before anyone can authenticate (`per resolution claude-ai/email.read`). If they cannot enable it themselves, that capability is blocked today, and that is a loss, not a delay.
4. Read the functional spec's `trigger` field aloud. If it is `scheduled(...)` and the input's `criticality` is `core`, tell them now, before any setup: "This agent was built to run unattended on a schedule. On Claude that is only available on paid plans and in a specific surface. If we cannot get it, you will have a version you start yourself. Do you still want to install it?"

## Step 3 mechanism: capabilities, one at a time

Before any connector, say: "You will click Connect and sign in with your own account on Google's screen, not mine. I never see or handle your password, and I will never ask you for one."

### `web.fetch`

Claude's built-in web search, plus fetching pages it is given (`per resolution claude-ai/web.fetch`). Available on all plans including Free; on Free it draws on the same daily usage limit as everything else. Nothing to connect: "This one needs no setup. I can search the open web and read public pages already."

**Echo:** run one real query drawn from the agent's actual beat, not a generic one, and quote back one item with its source and date. **Search here returns a result set rather than a named pipe**, so the per-source count core step 3 asks for does not come from the tool: it comes from the beats you agreed to cover. Run one query per beat, quote an item from each, and name any beat the search could not answer, because that is the unit the reader loses when it is missing.

### `email.read`

The first-party Gmail connector, part of the Google Workspace connectors (`per resolution claude-ai/email.read`). Documented as available on all plans including Free, though some third-party write-ups claim it is paid-only, so have the installer confirm what they actually see before you rely on it. On Team and Enterprise an Owner or Primary Owner must enable it at the organization level first.

Walk-through: "Click the plus sign below the message box, hover Connectors, and turn on Gmail. If you do not see it there, open Settings and look for Connectors. Then sign in with the Google account whose mail this agent should read." If their mailbox is not Gmail, see the error path below.

Write-scope sentence: "This connector can also create drafts in your account. It cannot send. This agent will not create drafts either; it only reads."

**Echo:** search inside the agent's actual window, for example the last 24 hours if that is the spec's window, and quote back one subject line and its sender.

Known limits to state if the spec depends on them: attachment contents are not readable through the Gmail connector, only metadata, and some advanced Gmail search filters are not supported (`per resolution claude-ai/email.read`). If the agent's job depends on reading attachments, that is a loss, not a workaround.

### `calendar.read`

The first-party Google Calendar connector (`per resolution claude-ai/calendar.read`). Same plan situation and same organization gate as Gmail. Same path, toggle Google Calendar instead.

Write-scope sentence, and be specific here because this connector's write side is the destructive one: "This connector can create, change and delete events in your calendar. This agent will not do any of that. It reads your schedule and reports on it."

**Echo:** one real event inside the agent's window, quoted back with its time.

### `files.read`

Two mechanisms. Choose by what the spec's input actually is, and say which you chose and why.

1. **Documents the installer provides:** upload into Project knowledge, the **+** in the knowledge panel (`per resolution claude-ai/files.read`), once the Project exists at step 6. Use this for reference material, style guides, lists, anything stable.
2. **A named folder or a live document set:** the first-party Google Drive connector, same connector path as Gmail. Use this when the spec's input changes between runs.

Write-scope sentence for the Drive connector: "This connector can also upload files and create folders in your Drive. This agent will not write anything to your Drive."

**Echo:** for an upload, name the file and quote a distinctive line from it. For Drive, quote a fragment plus the document's last-modified date.

Known limit to state: Claude extracts text only from Drive files, and images embedded in documents are not processed (`per resolution claude-ai/files.read`). If the agent's job depends on reading charts or scans, say so before the first run, not after.

### `memory.prefs`

Claude's memory here is project-scoped: each Project has its own separate memory space, kept apart from other Projects and from ordinary chats (`per resolution claude-ai/memory.prefs`). It is on Free, Pro and Max; Enterprise runs a legacy arrangement with organization-level controls. Searching past chats is a separate feature and is on paid plans only.

Walk-through: "Open Settings, then Memory, and check that Generate memory from chats is on. If it is off and you want it off, that is fine; I will tell you what changes."

**Echo:** state one preference in the Project, then in a fresh chat inside the same Project ask Claude to repeat it back. Apply the memory rule in core step 3 to the result: if it does not come back, the preference goes into the Project instructions and `memory.prefs` is `substituted`.

### `chat.notify`, deliver the output to the installer

The channels this platform has, offered and chosen, never assumed (`per resolution claude-ai/chat.notify`). **The target is always a slot the installer fills**: the passport carries no address and no channel id, and you never infer one.

- **The chat inside the Project.** The on-demand channel. No setup, no plan gate, and the first run at core step 7 is its verification.
- **The Cowork scheduled task's run view.** Where a scheduled run's output lands. It does **not** appear in the Project chat, so say that before the installer goes looking for it.

**Mail to their own address is not a channel here.** The Gmail connector creates drafts and cannot send (`per resolution claude-ai/email.read`), so there is nothing to offer, and a draft is not delivery. Do not invent a route. If the installer wants the brief in their mailbox, that is a scope conversation and a losses row, not something you build.

### Remembering the previous run

Only if the passport declares `state:`. There is nowhere inside the envelope to keep a per-run snapshot on this platform: Project knowledge is uploaded by the installer by hand, memory is a generated summary and not a store (`per resolution claude-ai/memory.prefs`), and writing a file back into a connected Drive is a write to an external system, which the envelope forbids.

So the instruction says: report today's figures, and where a comparison against an earlier run is called for, say there is none rather than printing a change you did not compute. One row in the losses table.

| what | status | what that means in practice |
|---|---|---|
| Compares against the previous run | lost | nothing here keeps yesterday's numbers where the agent can read them, so it reports today and says it has nothing to compare against. If the comparison is the point of this agent, that is worth deciding now rather than discovering on the second morning. |

## `schedule.run` on claude.ai, stated honestly

What exists as of 2026-08-06 (`per resolution claude-ai/schedule.run`, confidence medium, this is the fastest-moving fact in this appendix):

- Recurring scheduled tasks exist in **Claude Cowork**, not in ordinary claude.ai chats or Projects. Cowork is on paid plans only: Pro, Max, Team, Enterprise. It is in beta, and its availability by surface has been rolling out plan by plan.
- Cowork has its own projects, separate from claude.ai chat Projects. A Cowork project carries its own instructions, files, memory and scheduled tasks. The help centre describes Cowork projects as desktop-only and stored locally, with an **Import from project** option that pulls the files and instructions across from an existing claude.ai chat Project.
- Cadences documented for a scheduled task: hourly, daily, weekly, weekdays, or manual. Whether a run fires while the machine is asleep is **contradictory in the published sources**, which describe these projects as stored locally and their scheduled runs as executing in the cloud. Do not promise it either way. Ask the installer to let one fire with the machine closed and to tell you what happened, and record a loss if it does not.
- No published cap on the number of scheduled tasks. Do not state one.

Because that picture changes, do not narrate a UI you cannot see. Ask: "Look at your left sidebar. Do you see Cowork, and inside it anything labelled Scheduled? Tell me what you see and I will work from that."

**If they have it,** the path is: open Cowork, create a project, use **Import from project** and search for the chat Project you just built to bring its instructions and files across, then **Scheduled** in the sidebar, **New task** in the upper right, and set the cadence from the spec's `trigger`. Two things to tell them plainly:

1. The scheduled task must be self-contained. It runs in Cowork, against the Cowork project's instructions, not the chat Project's. If the import did not carry the instructions, paste them again there. Verify by asking them to read the Cowork project's instructions back to you.
2. The output lands in the Cowork scheduled task's runs, not in the chat Project. Tell them where to look on the first morning it fires.

This is the two-copies case in core step 6. Losses row when Cowork works, use this wording:

| what | status | what that means in practice |
|---|---|---|
| Runs on a schedule | substituted | Set up as a scheduled task in Cowork rather than inside the Project we built. It runs on its cadence in the cloud, and the output appears in Cowork's Scheduled view, not in the Project chat. The two copies of the instructions can drift; if you change one, change the other. |

**If they do not have it,** because they are on Free, because Cowork has not reached their plan or surface, or because they simply do not want a second workspace, degrade to on-demand. Do not fake a schedule with reminders, and do not tell them a chat can wake itself up. It cannot.

| what | status | what that means in practice |
|---|---|---|
| Runs every [cadence] at [time] | lost | Claude has no scheduler I can reach from this Project, so nothing runs while you are away. To run it, open the Project and send one word, for example "run". The agent is otherwise complete. |

Say this out loud, once, in step 8: "This is the part of the original that did not survive the move. Everything else is here." If `schedule.run` was `criticality: core` in the spec, add: "The person who built this said the schedule was essential to it. On demand, this is a useful tool. It is not the same thing they had."

## Step 6 mechanism: the agent becomes a Project

Projects are available on all plans, and the Free tier caps how many you may have (`per resolution claude-ai/chat.notify`). Do not state the number; ask the installer what their own Projects screen shows.

Walk the installer through it, one instruction at a time, waiting after each:

1. "Go to claude.ai/projects, or hover the left edge and click Projects."
2. "Click + New Project in the upper right."
3. "Name it whatever you want to call this agent. The name and description are for you; I do not read them."
4. "Open Set project instructions. I will give you the text to paste. Then click Save instructions."

The instruction text is the one core step 6 specifies, written in the second person to a future Claude. There is **no documented character ceiling on Project instructions** (`per resolution claude-ai/chat.notify`, confidence medium), so the spec's `tacit_notes`, ordering rules and section contract go in whole rather than summarised. Do not pad it either. Write what the spec contains and stop.

Paste it into the chat in one fenced block so the installer can copy it in a single action, and tell them: "Read this before you paste it. It is the whole agent. If a line is wrong about you, tell me and I will fix it now rather than after the first run."

**Project knowledge** holds the passport's golden examples, uploaded with the **+** in the knowledge panel on the right of the project page. Add this line yourself, above each example, and say it out loud to the installer as well:

> SHAPE TEMPLATE, NOT CONTENT. This is one real output from a different person on a different day. Copy its structure, section order, item counts and register. Never reuse its facts, dates, names, items or conclusions. Your content comes from today's inputs.

This is the single most common way an install goes wrong on this platform: Project knowledge is retrieved on every run, so an unlabelled example is read as an expectation on every run.

Everything core step 6 excludes stays out of the Project, for a reason specific to this platform: anything in the Project is read by the agent every time it runs. If the installer wants the whole passport for reference, they keep the file or the link outside the Project.

## Step 7 on this branch: where the first run happens

The fresh run core step 7 requires is a new chat **inside the Project**, not the conversation you have been installing from. Say: "Open your Project and start a new chat inside it. Send one word: run. I will read what comes back with you."

Have them paste the output back to you, or read it in the same window if you are already inside the Project.

Add one platform check to the core's thin-output list, before the other three: was the chat actually inside the Project? Instructions only apply inside it.

If the agent is also scheduled through Cowork, run it once there too, manually, before the first scheduled fire.

---

## Error paths, with the exact words to use

### The connector is not offered, or is not in Settings

> I do not see the connector we need in your account. Two common reasons: on Team or Enterprise plans an Owner has to switch connectors on for the whole organisation before anyone can connect one, and features roll out at different times to different accounts. Can you open Settings and tell me exactly what you see under Connectors? If it is not there, this capability is blocked today. I will finish the install without it and write it into the losses table as lost, and you can add it later without redoing any of this.

Then continue the install. Do not stall on a blocked connector, and do not propose a workaround that involves the installer pasting their data in by hand every run unless they ask for exactly that.

### The mailbox or calendar is not Google

> The first-party connectors here cover Gmail, Google Calendar and Google Drive. Yours is [what they said]. I am not going to set up a third-party bridge for it in this install, because that would mean handling access I should not be handling. Your options are to connect a Google account if you also have one, or to run this agent without the mailbox and give me the handful of items yourself when you run it. Which do you want? Either way this goes in the losses table.

### The connector is connected but returns nothing

> The connection is authorised but it came back empty, so I cannot confirm it works yet. That is usually one of three things: the account you signed in with is not the one holding this data, the time window we are searching is genuinely empty, or the search terms are too narrow. Let me try a wider window first. If that is also empty, please check which account is connected.

Widen once, ask them to name something they know is there, and try that. If it still returns nothing, record it as `lost` and say which of the three causes you could not rule out.

### The Project instructions are being ignored

> The agent is not following its instructions. Before we cut anything, one check: are you in a chat inside the Project, or in an ordinary chat? Instructions only apply inside the Project.

If they are inside it and it still drifts:

> Then the instructions are competing with themselves. I am going to tighten them rather than add to them, down to the list we started from: the goal, when it runs, what it reads, the output sections in order, the length band, your answers, and the original owner's notes. Anything else I put in comes out. I will not add "please follow the instructions above" as a fix; that never works. Here is the shortened version, replace what is in Set project instructions with this.

If the drift is specifically the output copying a golden example's content:

> That is the golden example being read as content instead of shape. I am relabelling it in Project knowledge and adding one line to the instructions: the examples show structure only, never facts. If it happens again, remove the examples from knowledge entirely and I will describe the shape in words instead. The shape survives that; the false content does not survive either way.

### A scheduled run produced nothing

> The scheduled run fired but there is no usable output. Check the run in the Scheduled view and tell me what it says. The usual causes here are that the scheduled task cannot see what the Project chat can see, because it runs against the Cowork project's own instructions and connectors, or that the connector needs re-authorising. Two questions: does the Cowork project have the same instructions we wrote, and are the connectors this agent needs switched on inside Cowork? If a run is empty because there was genuinely nothing to report that day, that is correct behaviour, and the agent should be saying so in the output rather than returning nothing. If it is not saying so, that is a line I should add to the instructions.

### Memory is not persisting between runs

> The preference did not carry over. That is within normal behaviour here, not a fault: memory on this platform is a summary Claude builds from your chats, it is scoped to this Project, and it is not a store the agent can rely on. Anything that must be true every run belongs in Project instructions instead, where you can see it and change it. I am moving [the preference] there now.

| what | status | what that means in practice |
|---|---|---|
| Remembers your preferences | substituted | Preferences are written into the Project instructions rather than remembered. They hold until you edit them, and the agent will not pick up new preferences on its own. Tell me a correction and I will add it. |

---

## Step 9 on this branch

Fill the four core lines with:

1. **How to run it.** Open the Project and say "run". If it is scheduled through Cowork, the cadence and where that run's output lands.
2. **How to change it.** Set project instructions, in this Project. That text is the whole agent.
3. **What it will never do.** The `declared_only` rows read by name, plus one sentence the connectors make necessary: "The Gmail and Calendar connections technically allow drafting and editing. This agent does not use them and its instructions do not mention them."
4. **It is theirs now.** The original owner's notes are in the instructions in quotes, and they can delete them.

Then stop.

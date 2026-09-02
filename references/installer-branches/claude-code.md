# Installer branch appendix: Claude Code

How the nine steps land on this platform. The installer here is technically capable and is running Claude Code on their own machine.

**Mechanism targeted, and why.** This branch writes a folder that satisfies two formats at once:

1. **Agent Plugins 1.0.0** (agent-plugins.org), verified 2026-08-06 against the published manifest schema, the MCP configuration schema and the 1.0.0 specification text. Root `plugin.json`, `skills/<name>/SKILL.md`, root `mcp.json`. This is the portable artifact the installer can carry elsewhere.
2. **Claude Code's own plugin layout**, verified 2026-08-06 against Anthropic's plugin, skills, MCP, memory and headless documentation. Manifest at `.claude-plugin/plugin.json`, MCP config at `.mcp.json` in the plugin root.

They agree on `skills/<name>/SKILL.md` and disagree on where the manifest and the MCP config live. **Anthropic's documentation does not mention agent-plugins.org, and Claude Code is not listed as a conformant client**, so do not tell the installer that Claude Code reads the Agent Plugins manifest. Write both manifests: the portable pair is the deliverable, the dotted pair is what makes it load today. Say that in one sentence and move on.

**Naming, used throughout this appendix.** `{plugin}` is the plugin name and `{skill}` the skill name, both agreed with the installer at step 6; the agent is invoked as `/{plugin}:{skill}`. Every path, label and filename below that carries a name is written with those placeholders, and anything else in braces (`{output-path}`, `{capability}`) is filled in the same way, from the installer's answers. Substitute before you write anything. One block is marked **worked example** and uses literal names: read it for shape, never copy its strings.

---

## Step 2 additions: environment check

Ask, do not assume:

- `claude --version`. Several behaviours cited below are version-gated; the placeholder MCP entry needs v2.1.208 or later (per resolution claude-code/email.read).
- Which authentication method is active: run `/status`. A claude.ai subscription login is required for claude.ai connectors to appear at all (per resolution claude-code/email.read). An `ANTHROPIC_API_KEY`, an `apiKeyHelper`, Bedrock, Google Cloud, or a `claude setup-token` token suppresses them.
- Operating system, and what their own app offers for scheduling. `schedule.run` has four candidate mechanisms here and they are not equivalent (per resolution claude-code/schedule.run). Do not narrate a scheduling surface you cannot see; ask what is in front of them.
- Where they want the folder written. Default below.

## Step 3 on this platform: capability resolution

### `web.fetch`

Built in. `WebFetch` and `WebSearch` need no setup and no MCP server (per resolution claude-code/web.fetch). Tell the installer: `WebFetch` prompts the first time it reaches a new domain unless a `WebFetch(domain:example.com)` rule allows it; `WebSearch` returns titles and URLs only and is capped at 200 calls per session.

**`WebFetch` is a summariser, not a reader, and that decides where it may be used.** It converts the page, puts your question to a small fast model, and returns that model's prose answer rather than the page. A wrong answer and a failed read are indistinguishable coming back. So: never serve an input whose value is a **quantity** through `WebFetch`. A count, an amount, a rate, a total, a version number. The failure renders as a confident zero, and a zero meaning "the read failed" looks exactly like a zero meaning "nothing happened yesterday", which is the distinction the owner's notes usually exist to protect. Use a deterministic read instead: an MCP server for that system, a query against a database the installer owns, or a documented JSON endpoint fetched with `curl` through `Bash` and parsed yourself. `WebFetch` is right for prose: a headline with its date, whether a status page says operational, the gist of an article. Core carries this rule platform-agnostically; this is what it means here.

**Echo:** fetch every source you stood up for this input and read back a headline plus its date from each. The spec names roles, not sources, so these are the ones you chose. Name any that returned nothing and carry the count into the step 8 row.

### `email.read`

No built-in tool. Two routes, in this order (per resolution claude-code/email.read):

1. A mailbox connector the installer has already added at `claude.ai/customize/connectors`. If their active auth is a claude.ai login, it appears in `/mcp` marked as coming from claude.ai. Nothing is written to the plugin.
2. A remote MCP server they add themselves: `claude mcp add --transport http <name> <url>`, then `/mcp` to complete the OAuth sign-in in their browser.

**You do not choose the server and you do not paste a URL you invented.** Point the installer at `claude.ai/directory` or the `/mcp` panel and let them pick.

**Echo:** one real message header, subject and sender.

### `calendar.read`

Identical to `email.read` in mechanism and identical in what you must not do (per resolution claude-code/calendar.read).

**Echo:** one real event, title and time.

### Authenticated reads from a system the installer owns

The case most passports actually need: a product database, a billing system, an analytics product, an internal API. The passport's input names a **role** and carries a `binding` to a slot; the installer names the system that fills it (core step 4, and the ladder there: their own system first, then an open equivalent, then a loss).

Mechanism is the `email.read` mechanism generalised. Two routes, both driven by the installer:

1. They add the server themselves: `claude mcp add --transport http <name> <url>`, then `/mcp` to complete the sign-in in their own browser.
2. They export an environment variable in their own shell profile, and `.mcp.json` references it as `${VAR}`. See that file below.

**You never see the value, never ask for it, never write it into a file.** You do not choose the server and you do not paste a URL you invented. If the only route to the system runs through the installer pasting a key, a token or a password into this conversation, that route is closed and the input is a losses row. Offering it to save time changes nothing.

**Prefer a connection they already have.** If a connection live in this session serves the role the input describes, use it. A direct query against the installer's own database returns exact integers with no summariser in the path, which is a better read than fetching the same numbers over HTTP, and is often better than what the original agent did. It is still a substitution. It goes in the losses table as `substituted`, with a practical line that says it improves the input rather than degrading it. Never let a better substitution go unrecorded because it is better.

If the server also exposes write tools, deny them by rule; see `.mcp.json` below.

**Echo:** one real figure with its label and its timestamp, and ask whether it looks right.

### `files.read`

Built in through `Read`, `Glob` and `Grep`, bounded by the working directory (per resolution claude-code/files.read). For documents elsewhere the installer adds the folder with `/add-dir <path>`, launches with `claude --add-dir <path>`, or sets `permissions.additionalDirectories` in `settings.json`. Reads outside those directories prompt every time, which is what breaks an unattended run.

**Echo:** name one file found and quote one line from it.

### `memory.prefs`

Partial, per core step 3, and here it is three different things that persist differently (per resolution claude-code/memory.prefs):

- **Slot answers** are written into `SKILL.md` at install time. That file is the durable copy the core rule asks for, and changing a preference means editing it.
- **CLAUDE.md** at `~/.claude/CLAUDE.md` or `./CLAUDE.md` carries standing preferences into every session. The plugin does not write it; offer to, and let the installer approve the diff.
- **Auto memory** at `~/.claude/projects/<project>/memory/` is written by Claude, is machine-local, is per repository, and only the first 200 lines or 25KB of `MEMORY.md` load per session.

None of the three is enforcement. It is context the model may or may not follow. None of the three is where a per-run snapshot belongs; that is a file, see "Remembering the previous run" below.

**Echo:** state one slot answer back and show the `SKILL.md` line it was written into.

### `chat.notify`, deliver the output to you

Delivery is a channel, not a capability to refuse. Offer what this platform actually has, ask which they want, record the choice (per resolution claude-code/chat.notify). **The target is always a slot the installer fills.** A passport never carries an address, a path or a channel id belonging to the original owner, and you never infer one.

- **The reply in this session.** Always present, nothing to install, and the first run at step 7 is its own echo. On-demand only: an unattended run has no session to speak into.
- **A file on disk.** The answer for an unattended run. The scheduled command appends to a path the installer names, and they open it. Tell them the path and the time it appears.
- **Mail to the installer's own address**, only if they already have a mail connection or an MCP server with a send tool, and only to an address they give you. This is the platform telling its own user that their own task ran, so it is delivery and stays inside the envelope. Two conditions, both mandatory: the recipient is the installer, and the instruction text at step 6 says in writing that the agent delivers to that one address and composes no other recipient. A mail connector grants send as a bundle and you cannot narrow the grant, so the boundary lives in the instructions and has to be written down.
- **A notification on this machine**, for example an `osascript -e 'display notification ...'` line in the scheduled command on macOS. It says only that the run finished and where the output is.

Anything addressed to somebody who is not the installer is `email.send`, `msg.send` or `social.post`: outside the envelope, declared only, skipped out loud.

### `schedule.run`

**Claude Code does have schedulers.**

**Observed on Claude Code 2.1.226 on macOS in August 2026:** `~/.claude/scheduled-tasks/` exists, and a scheduled task is stored there as one directory per task containing that task's own `SKILL.md`. Everything else in this section about scheduled tasks comes from one undocumented observation rather than from published documentation, so state it as such and work from what the installer's own app shows. Check the version they are on rather than assuming this one.

Four mechanisms, and the choice matters more than the setup:

1. **Scheduled tasks, the right answer.** Local to the app, cron expression in the installer's own timezone, one directory per task under `~/.claude/scheduled-tasks/`. Runs while the app is open and catches up on next launch if it was closed when the task was due, which suits a morning brief: the installer sees it when they sit down. They create it in their own app; confirm it exists by that directory appearing.
2. **`CronCreate`, wrong tool.** Session-only, held in memory, gone when the session ends, capped at seven days, fires only while the REPL is idle. Useless for a daily agent.
3. **Cloud routines via `/schedule`, wrong for a locally bound agent.** They execute in Anthropic's cloud, which has no path to this machine, its files or its local connections. Right only for an agent that reads public sources and delivers into that same cloud surface.
4. **launchd or cron, the headless fallback.** Still the most robust when the run has to happen with the app closed, and entirely the installer's to maintain. Recipes below.

**The two-copies problem, and the fix.** A scheduled task carries its own `SKILL.md`, so the agent would exist in two places and drift the moment the installer edits one. Core step 6 governs this. Keep one authoritative copy in the plugin and make the scheduled task a **thin caller**: its body is the single line

```
/{plugin}:{skill}
```

and nothing else. Then name both locations out loud, as core step 6 requires: `~/.claude/skills/{plugin}/skills/{skill}/SKILL.md` is the agent and the place to edit; `~/.claude/scheduled-tasks/<task-name>/SKILL.md` is a trigger, and editing it changes when the agent runs, never what it does.

**Unverified, and you must say so:** whether a plugin skill loads inside a scheduled run. Nobody has tested it. Do not assert it. Tell the installer how it proves itself on the first fire: the output either looks like the agent, or it does not, and if it does not, the plugin did not load and the fallback is launchd. Name the time of the first fire, name where the output will land, and give them that check before you hand over.

**macOS, launchd.** Write `~/Library/LaunchAgents/org.agentpassport.{plugin}.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>org.agentpassport.{plugin}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>claude -p "/{plugin}:{skill}" --allowedTools "WebFetch,WebSearch,Read,Glob,Grep" --permission-mode dontAsk >> "{output-path}" 2>> "{output-path}.err"</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/{user}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

`{output-path}` is the file the installer chose as their delivery target above, and the hour and minute come from their slot answers, in their timezone. Load and unload:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/org.agentpassport.{plugin}.plist
launchctl bootout gui/$(id -u)/org.agentpassport.{plugin}
```

**Elsewhere, cron.** Same command on one line, with cron's minimal `PATH` in mind:

```cron
0 7 * * * cd "$HOME" && /usr/bin/env claude -p "/{plugin}:{skill}" --allowedTools "WebFetch,WebSearch,Read,Glob,Grep" --permission-mode dontAsk >> "{output-path}" 2>&1
```

Two notes for either recipe: do not add `--bare`, which skips plugins, MCP servers, `CLAUDE.md` and auto memory; a personal-scope plugin under `~/.claude/skills/` loads in every project, so no `--plugin-dir` flag is needed.

**Losses row.** A schedule proves itself the first time it fires, which is after you are gone (core step 3). So:

| what | status | what that means in practice |
|---|---|---|
| Runs at 07:00 every weekday | delivered, unverified | it is set up but has not fired yet; if nothing is in `{output-path}` by 07:30 tomorrow, the check above tells you which half failed |

Never `delivered` on install day, and `lost` if they declined a scheduler. On the launchd or cron route add one clause: the job sits outside the plugin folder, so it does not travel with it and uninstalling takes its own command, below.

---

## Permission prompts, in two halves

**For the person, during the install.** Say this before the first prompt appears, not after: "Claude Code asks before it reaches a new domain, opens a folder outside this one, or uses a tool it has not used here. You are going to see several of these. That is the permission system working, not something going wrong. Approve the ones you recognise, and ask me about any you do not."

**For the unattended run.** It cannot answer a prompt. A prompt nobody answers is a run that quietly produces nothing, which is the failure mode hardest to notice, because there is no error to see. Everything the run touches is granted **before** it fires. Check each of these and tell the installer which you did:

- Every domain the agent fetches has a `WebFetch(domain:example.com)` rule in `settings.json`, one per domain (per resolution claude-code/web.fetch).
- Every folder the agent reads outside the working directory is in `permissions.additionalDirectories`, or the scheduled command passes `--add-dir`. Reads elsewhere prompt every time (per resolution claude-code/files.read).
- Every tool the run needs is named in `--allowedTools`, including `Bash` if a deterministic read uses `curl`, and including the scoped MCP tool names if it reads through a server.
- `--permission-mode dontAsk` denies whatever is not allowed instead of asking, which is the point of it. **`bypassPermissions` is refused here**, at any budget, for any reason, including the installer asking for it.
- Every connector and MCP server the run touches is signed in now. An expired claude.ai login or a lapsed OAuth token cannot be re-authorised without a person present, and turns the run into silence (per resolution claude-code/schedule.run).

Close by naming the file the first unattended output lands in and the time it should be there, so "nothing arrived" is a check the installer can make rather than a suspicion.

---

## Step 6 on this platform: what you write

### Where

Default: `~/.claude/skills/{plugin}/`. A folder there containing `.claude-plugin/plugin.json` loads as `{plugin}@skills-dir` on the next session, personal scope, in every project, no marketplace and no install step. Personal scope is what an unattended run needs (per resolution claude-code/schedule.run).

Alternative, inside a repository: any path, loaded with `claude --plugin-dir ./{plugin}`. Project-scope skills-directory plugins load only from the `.claude/skills/` of the directory Claude Code was started in, and require the workspace trust dialog.

Ask which. Do not write outside the folder you named.

### Exact layout

```
~/.claude/skills/{plugin}/
├── plugin.json                  Agent Plugins 1.0.0 manifest, portable
├── mcp.json                     Agent Plugins MCP config, placeholders only
├── skills/
│   └── {skill}/
│       └── SKILL.md             the agent
├── state/                       only if the passport declares state:
├── README.md
├── .claude-plugin/
│   └── plugin.json              Claude Code manifest, loader shim
└── .mcp.json                    Claude Code MCP config, placeholders only
```

Only `plugin.json` goes inside `.claude-plugin/`. Everything else sits at the plugin root. Skills are the immediate children of `skills/` and nothing deeper is searched.

### `plugin.json` (Agent Plugins 1.0.0)

`$schema` and `name` are the only required keys. `name` is 1 to 64 characters, lowercase alphanumerics with hyphens and dots, no leading or trailing separator and no doubled separator. No keys outside the published set.

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "{plugin}",
  "version": "0.1.0",
  "description": "One line, from the passport's goal.",
  "license": "UNLICENSED",
  "keywords": ["agent-passport", "read-only"]
}
```

No `author`: the passport carries the agent's shape, not the original owner's identity.

### `.claude-plugin/plugin.json` (Claude Code)

```json
{
  "name": "{plugin}",
  "description": "One line, from the passport's goal.",
  "version": "0.1.0"
}
```

`name` is also the skill namespace: the skill below is invoked as `/{plugin}:{skill}`.

### `skills/{skill}/SKILL.md`

The agent's instruction text: exactly what core step 6 lists, nothing else. Frontmatter adds `name` for the Agent Skills specification and `description` for Claude Code's own discovery.

**Worked example. Shape only. The names, topics and slot answers in it belong to a different agent, and copying them mis-namespaces the install.**

```markdown
---
name: brief
description: Produce today's brief. Use when the installer asks for their brief, or when this skill is invoked directly.
---

# Morning brief

Produce one brief for today. Read only. Deliver it to the file named below and nowhere else.

## Inputs
1. Public news for these topics, in this order: [topic 1], [topic 2], [topic 3].
   Use WebFetch and WebSearch. Public sources only.
   (Substituted at install: the original read a paid market wire for the third topic.)
2. Today's calendar, if the calendar connection verified. If it did not, skip that section
   and say so in one line rather than inventing it.

## Output
Three topic sections in the order above, then "Today" for the calendar.
Two to four items per topic, 40 to 70 words each, newest first, none older than 24 hours.
Neutral third person, no address to the reader, no closing summary.
Write the result to [the delivery path the installer gave]. That is the only place it goes.

## Slot answers, for a worked example
- Timezone: [the installer's timezone]
- Topics: [three topics the installer follows]

## Notes from the owner
The person who built this agent said: "[tacit_notes, verbatim, one line each]".

## Boundaries
Never send, post, reply, draft into the world, or write to any external system.
Do not add sections or sources beyond those above.
If an input returns nothing, fails, or was never connected, render it as a dash with
the reason. Never as a zero, never as an invented value.
```

### Remembering the previous run

Only if the passport declares `state:`. An agent that reports a change against yesterday needs yesterday's numbers, and instruction text is re-read from scratch on every run, so the snapshot is a file.

Put it under the plugin's own folder, `~/.claude/skills/{plugin}/state/`. In the portable `mcp.json` the same location is `${PLUGIN_DATA}`, one of the two variables the Agent Plugins standard expands; whether that expansion reaches a `Write` inside a skill run is **not verified**, so give the agent the absolute path and say which form you used.

Three lines in `SKILL.md`, no more:

- at the end of a run, write `state/YYYY-MM-DD.json` holding only the values the next run compares against
- at the start of a run, read the most recent file dated before today
- if there is none, say "no previous run to compare against" in the output rather than printing a delta you invented

The folder is inside the plugin and therefore inside a directory the run can already reach; if you place it anywhere else, it prompts, see the permissions checklist above.

### `mcp.json` (Agent Plugins) and `.mcp.json` (Claude Code)

**Placeholders only. No URLs that work, no tokens, no account identifiers, in either file.** The Agent Plugins specification is explicit that `env` values and `headers` values are visible package data and that plugins must not embed a secret in them.

`mcp.json`, portable:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "{capability}": {
      "type": "streamable-http",
      "url": "<YOUR_MCP_URL_HERE, from your own provider, never pasted into a chat>",
      "headers": {
        "Authorization": "<YOUR_TOKEN_HERE, set this yourself, never paste it into a chat>"
      }
    }
  }
}
```

One entry per capability that needs a server, same shape, named for the capability. This file is a form to fill in, not a working configuration, and the placeholder text is not a URI. Tell them so. Only `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` are expanded by the standard; anything else that looks like a variable stays literal.

`.mcp.json`, the copy Claude Code actually reads. Use an empty `url` here: a remote server with an empty `url` shows as `not configured` in `/mcp` and in `claude mcp list` and Claude Code does not try to connect, so the plugin loads clean instead of reporting a broken server (per resolution claude-code/email.read; needs v2.1.208 or later).

```json
{
  "mcpServers": {
    "{capability}": {
      "type": "http",
      "url": "",
      "headers": {
        "Authorization": "Bearer ${YOUR_TOKEN_VAR}"
      }
    }
  }
}
```

Claude Code expands `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url` and `headers`, so the installer exports the variable in their own shell profile. **You never see the value, never ask for it, never write it into a file.** An unset variable is not fatal; `claude mcp list` reports a missing-variable warning for that server.

If the capability comes from a claude.ai connector instead, delete both server entries rather than shipping empty ones, and say why.

**No write-capability server goes in either file.** If a candidate server exposes send, post or write tools alongside its read tools, the capability is still installed but those tools are denied: add the scoped tool name to `permissions.deny` in `settings.json`. Plugin server tools are scoped as `mcp__plugin_<plugin-name>_<server-name>__<tool>`. Verify the rule took effect in `/permissions` rather than assuming it.

### `README.md`

For a person who finds this folder in a year with no memory of the install: what the agent does in three sentences, the invocation `/{plugin}:{skill}`, the file map above, which capabilities verified and which did not, where the output is delivered, the scheduling choice they made, and the uninstall steps. Not the slot answers: one copy of those, in `SKILL.md`, so there is one thing to edit.

### Loading it

New session, or `/reload-plugins`. Edits to `SKILL.md` take effect immediately; edits to `.mcp.json`, `hooks/` or `agents/` need the reload. Confirm it loaded before claiming it did: `claude plugin validate ~/.claude/skills/{plugin}` prints `✔ Validation passed`, and a failed load shows in the `/plugin` manager's **Errors** tab.

### Uninstalling it

Say all three lines at hand-over:

```bash
claude plugin disable {plugin}@skills-dir      # stop loading it, keep the folder
rm -rf ~/.claude/skills/{plugin}               # remove it, including any saved state
launchctl bootout gui/$(id -u)/org.agentpassport.{plugin}   # only if they set up a launchd job
```

A scheduled task is removed in the app, or by deleting its directory under `~/.claude/scheduled-tasks/`. There is no `claude plugin uninstall` for a skills-directory plugin: nothing came from a marketplace. Removing the folder removes neither the scheduled task, the launchd job nor the crontab line, which is why the last two lines exist.

---

## Step 7 on this platform

The fresh run core step 7 requires is a new session invoking `/{plugin}:{skill}`, not a re-read of what you just wrote.

If it returns empty, report that as a result rather than a crash: "The run completed and produced no content, and I am not going to fill the gap with invented items. Here is what each input returned: <list each input and its outcome>." Then work the core's diagnosis order with two platform checks added: did `WebFetch` hit a first-use domain prompt, and did a `Read` reach outside the working directory. Do not re-run more than once before showing the installer what you found.

---

## Error paths, with the text to use

**No MCP server for a capability.** `/mcp` shows nothing for it and `claude mcp list` does not list it.

> "There is no server on this machine for <capability>. I will not pick one for you or paste a URL. Open `claude.ai/directory`, or your provider's own documentation, choose a read-only server, and add it with `claude mcp add --transport http <name> <url>`. Tell me when it is listed and I will verify it. If there is nothing suitable, we have two options: substitute, starting with a system you already have that plays the same role, then an open source of the same kind, and I will name exactly what changes; or install without it, in which case the sections that depended on it are missing and I say so in the output rather than filling them in. Either way it goes in the losses table as <substituted|lost>."

In the no-server case, delete that entry from both `mcp.json` and `.mcp.json` rather than shipping a broken one. A placeholder for a server that does not exist is clutter that reads as a promise.

**MCP server present but unauthenticated.** `claude mcp list` shows `! Needs authentication`, or `/mcp` shows the server needing sign-in.

> "The <name> server is configured but not signed in. Run `/mcp`, select <name>, and complete the sign-in in your browser. I cannot do this for you and I will not accept a token. When it shows `✔ Connected`, say so and I will read one item back to prove it works."

If it shows `connected · session token rejected`, the claude.ai login expired: run `/login`, then reconnect the connector from `/mcp`. Authorising the connector again does not clear that state.

**Plugin not picked up.** The skill does not appear and `/{plugin}:{skill}` is not recognised.

> "The plugin did not load. Three checks, in order. One: run `/reload-plugins`, and if that does not do it, restart Claude Code. Two: run `claude plugin validate ~/.claude/skills/{plugin}` and read me what it prints. Three: open `/plugin` and check the Errors tab. The most common cause is layout: only `plugin.json` belongs inside `.claude-plugin/`, and `skills/` and `.mcp.json` must sit at the plugin root."

For a project-scope folder add the trust dialog and the launch directory, both named above.

**The scheduled run produced nothing.** Nothing in the output file at the expected time.

> "The run either did not fire or fired and could not do its work. Four checks, in order. One: does the task still exist, and was the app open or launched since the due time. Two: is there anything in the error file next to the output. Three: run `/{plugin}:{skill}` here, now: if that works, the agent is fine and the trigger is not. Four: if the task fired but the output does not look like the agent, the plugin skill did not load inside the scheduled run, which was the one thing I could not test on install day, and the fix is the launchd job instead."

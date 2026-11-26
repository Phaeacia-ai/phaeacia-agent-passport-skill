# Agent Passport, capture skill

**Archived.** Phaeacia built this skill in 2026 and no longer develops it. It is
published as-is, under CC BY 4.0 for the skill and the format and Apache 2.0 for
the scripts, so the work stays available to study, run and fork. There is no
support, no roadmap and no security fixes. The source, including the hosted app,
is at https://github.com/Phaeacia-ai/phaeacia-agent-passport.

**Hosting at app.phaeacia.ai is closed to new uploads.** That site is read-only.
This skill now ends with the passport as a file on your machine, which you send
however you like. See *Publishing* below for what still works.

This folder is a skill for Claude Code. It reads an agent you already built, on
your machine, and writes an **Agent Passport**: one Markdown file describing what
the agent does, what it needs from whoever installs it, and what it cannot do.
Someone on a different platform can then rebuild it with their own credentials.

It never copies a credential. A passport names the *kind* of thing an agent needs
("a Gmail account you can read") and never the value.

## Install

You need [Claude Code](https://claude.com/claude-code) and Python 3.7 or newer.

```
git clone https://github.com/Phaeacia-ai/phaeacia-agent-passport-skill ~/.claude/skills/agent-passport
```

Claude Code loads skills from that folder, so cloning into it is the install.

**If that path already exists**, the clone fails with `destination path already
exists and is not an empty directory`. That is normal and it means something is
already there. Look first:

```
ls -l ~/.claude/skills/agent-passport
```

- **A symlink** (the line starts with `l` and shows `-> /some/path`): it points at
  a copy you already have, possibly a private checkout. Do not clone over it and
  do not `git pull` inside it, because you would be pulling that other
  repository. Decide which copy you want, then either leave it alone or
  `rm ~/.claude/skills/agent-passport` and clone.
- **A normal folder**: move it aside with
  `mv ~/.claude/skills/agent-passport ~/.claude/skills/agent-passport.old`, then
  clone.

**Installing it somewhere else instead does not avoid the problem.** The skill
declares its own name, so a second copy under a different folder name still
collides with the first. Whichever copy you keep, keep only one.

There will be no further updates to pull. The install instructions this skill
writes into a passport describe each platform as it was when the project was
archived, and platforms change; read them with that in mind.

## Use

In Claude Code, from the folder holding the agent you want to share:

```
/agent-passport
```

It reads the folder, asks what it cannot answer by reading, shows you what it
found, and writes a passport next to your agent as `<name>-passport.md`. That
file is the result. Send it to whoever should have the agent.

To give it the install instructions inside the file, so the recipient can paste
it straight into their own assistant:

```
python3 ~/.claude/skills/agent-passport/scripts/assemble.py <name>-passport.md <name>-install.md
```

**It writes a second file, `corrections.tsv`, next to the passport.** One
tab-separated line for every value you corrected during the review: the field,
what the capture said, what you said, and whether it had already flagged that
field as uncertain. It is there because a capture that guesses and is corrected
knows something a capture that guesses and is believed does not, and the only
place that shows up is the difference between the two columns.

It is a local file on your machine. It is not uploaded, it is not sent anywhere,
and `scripts/publish.py` never opens it: publishing sends the passport and
nothing else. Read it, keep it, or delete it. Nothing here depends on it existing.

## What it needs, and what happens without it

**Python 3.7 or newer**, which macOS and most Linux systems already have. Check
with `python3 --version`.

3.7 rather than 3.6 because `scripts/validate.py` calls
`datetime.date.fromisoformat`, which does not exist before 3.7. On 3.6 that
raises an error the script does not catch, and it happens at the validation step,
which is near the end. Five of the twenty-four files in the clone are Python and they use only the
standard library: nothing to `pip install`.

**The skill checks for Python before it reads anything of yours.** Step 0 runs
`python3 --version` and stops there if it is missing or older than 3.7, because
that is the cheapest thing to discover and the most expensive to discover late.
Without it you would spend a whole capture on work that could only fail at the
secret-scanning step near the end. So a missing interpreter costs you a message,
not a capture. Run `python3 --version` yourself if you want to know in advance.

## Publishing

The hosted site at `app.phaeacia.ai` no longer accepts uploads. Its upload
endpoint answers HTTP 410, and `scripts/publish.py` reports that as "hosting at
app.phaeacia.ai is closed to new uploads; your passport file is kept locally at
<path>", sends nothing else, writes nothing and exits 5. The passport file is
only ever read, never changed.

The skill does not offer to publish unless `PHAEACIA_UPLOAD_ENDPOINT` is set. If
you run your own deployment of the app, from the `web/` directory of
https://github.com/Phaeacia-ai/phaeacia-agent-passport, set that variable to its
upload address (`https://<your-host>/api/upload`) and the skill asks whether to
publish there. Everything below about the network applies to that case.

## Network: one call site, and the exact shape of it

The skill runs on your machine except for one thing. Being exact about it is more
useful than being reassuring, because you can check all of this yourself.

`scripts/publish.py` is the only file that opens a network connection. It POSTs
to the endpoint `PHAEACIA_UPLOAD_ENDPOINT` or `--endpoint` names, falling back to
`https://app.phaeacia.ai/api/upload`, which is closed. It runs **only when a
passport is being published to a link**. If you decline publishing, or no
endpoint is set, the passport is a file on your disk and nothing is sent.

Four details that a shorter version of this paragraph would have got wrong:

- **It can send two requests, not one.** If the endpoint answers that the owner
  has not confirmed, and you passed `--unconfirmed`, it POSTs a second time with
  an acknowledgement header. One call site, up to two requests.
- **Two things redirect it**, not one: the `--endpoint` flag and the
  `PHAEACIA_UPLOAD_ENDPOINT` environment variable. Either points it somewhere
  else, including at your own server.
- **"Only when you asked" is enforced by instruction, not by the code.**
  `publish.py` does not ask and does not check; its own docstring says it
  "assumes the answer was yes". What stops it running when you decline is
  `SKILL.md`, which the model follows. That is a real distinction and you should
  know which kind of guarantee you have.
- **Opening the finished link** makes your browser fetch the site, like any link.

You can verify the first sentence rather than trust it:

```
grep -rln urllib scripts/
```

One file comes back: `scripts/publish.py`. Everything else, including reading
your agent and scanning it for secrets, is local.

Search the whole folder rather than `scripts/` and two come back, because this
README contains the word `urllib` in the command above. Search `scripts/`, as
written, and you get the one file.

## Problems, changes and forks

**This repository is generated and archived.** Every file here is built from the
canonical files in https://github.com/Phaeacia-ai/phaeacia-agent-passport by its
export script. Nobody reads issues or merges pull requests in either repository now.

**To change something, fork the source repository**, edit the canonical file
there and rebuild; its README explains how. Editing a copy here works for your
own use, but the two copies then disagree. If you publish a fork, rename it: the
licences cover the text and the code, not the Phaeacia name or logo.

## Licence

Mixed, because the parts are different things. `LICENSE-MAP.md` has the per-file
detail.

- **`SKILL.md`, the format, and the installer text** are **CC BY 4.0**. Root
  `LICENSE` is the verbatim legal code. `LICENSE-SKILL.md` is the skill's own
  notice, and `LICENSE-FORMAT.md` explains why the format is licensed this way.
- **The five scripts, plus `references/judge-prompt.md`** are **Apache 2.0**:
  `LICENSE-Apache-2.0.txt` and `NOTICE`. `LICENSE-MAP.md` has the full six-row
  list.

A passport produced by this skill belongs to whoever ran it. Nothing here claims
any interest in your passports, the agents they describe, or their output.

One exactness, because the sentence above would otherwise be slightly wrong.
`scripts/assemble.py` puts two of our components into a passport: the installer
text, which is CC BY 4.0, and `references/judge-prompt.md`, which is Apache 2.0
and lands in section 5. So an assembled passport carries a CC BY component and an
Apache one, each asking what its own licence asks if you redistribute it. That is
a claim on our text travelling inside your file, never a claim on your file. The
passport you wrote, and everything your agent does, remain entirely yours.

## Credits

Agent Passport was built by Phaeacia, a project by Raffael Hüberli. Krunal Rathod
contributed to its design and code.

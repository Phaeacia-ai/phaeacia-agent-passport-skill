# Capability vocabulary v0.1

Closed list. A `capability_ref` outside this list fails validation. Closed is what makes the install branches buildable: every **installable** id here has a row per platform in `resolution.yaml`, and adding one means adding those rows. The five ids that write to the world (`email.send`, `msg.send`, `social.post`, `ext.write`, `money.*`) have no rows and are not meant to: v0.1 renders them as declared, never installs them, so there is nothing per-platform to resolve.

Capabilities describe **what the agent needs from its owner's environment**, in the owner's terms, never in provider terms. "Reads your mailbox" is a capability; "Gmail API with `gmail.readonly` scope" is a resolution.

## Installable in v0.1 (read-and-notify envelope)

| id | plain language | what it covers | what it excludes |
|---|---|---|---|
| `web.fetch` | fetch open web or news content | public pages, feeds, search results, anything reachable without the owner's credentials | anything behind the owner's login, anything posted or submitted |
| `email.read` | read the owner's mailbox | listing, searching, reading messages and metadata | sending, replying, drafting into the world, labelling as a side effect |
| `calendar.read` | read the owner's calendar | events, times, attendees, availability | creating, moving, or responding to events |
| `files.read` | read documents the owner provides | knowledge files, uploaded documents, a named local folder | writing files anywhere the owner did not designate as output |
| `schedule.run` | run on a schedule | recurring unattended execution | any outbound action during that run beyond `chat.notify` |
| `chat.notify` | deliver the output to you | any channel whose only recipient is the installer: the chat reply, mail to the installer's own address, a platform push notification, a file on the installer's own disk | any recipient who is not the installer, webhooks into other people's systems, anything that composes a message for somebody else |
| `memory.prefs` | remember preferences across runs | stated preferences, corrections, slot answers | storing the owner's data corpus, building a profile from inputs |

**Delivery is a channel, not a capability to refuse.** `chat.notify` is about reaching the installer, not about chat. Mail from an agent to its own owner's address is the same act as a chat reply: the recipient is the person who installed it, the agent composes no recipient, and the installer can change or switch off the channel in their own settings. So it is `chat.notify` on every platform and over every transport, for as long as the only recipient is the installer's own account. Platform notification mail for a finished scheduled run is one case of this rule, not an exception to it. The moment any other address, number or feed is involved, it is `email.send`, `msg.send` or `social.post`, and outside the envelope. Every branch must read it this way, or the same install would be legal on one platform and refused on another.

The test is the recipient, never the transport. An agent that mails its own owner is inside the envelope; an agent that mails a customer is not, even though both send mail.

**The delivery target is always a personal slot.** A passport never carries an address, a channel id, a phone number or a file path belonging to the original owner. It carries the question, and the installer answers it with their own target. This is the control that keeps the paragraph above safe: widen `chat.notify` to cover mail without it, and a passport could name a recipient and have the install deliver to a stranger. The original's channel may be stated as context, never as a requirement, and the instruction text the installer writes must say that the agent delivers to that one target and composes no other recipient.

`memory.prefs` is **partial** on every platform: what persists, where, and for how long differs enough that the installer must state the platform's actual behaviour rather than promise persistence. Treat a passport that depends on memory for correctness as a passport with a loss waiting to happen.

`schedule.run` **always has a degradation path**: where scheduling is unavailable or plan-gated, it degrades to on-demand and that degradation is recorded as a loss. An agent that is worthless without a schedule should say so in `criticality: core`, and the installer should say so to B before install rather than after.

## Declared only in v0.1 (outside the envelope)

| id | plain language |
|---|---|
| `email.send` | send email to somebody who is not the installer |
| `msg.send` | message somebody who is not the installer (chat, SMS, DM) |
| `social.post` | publish to a public or semi-public feed |
| `money.*` | any movement, commitment or authorisation of funds |
| `ext.write` | write to any external system (issue trackers, CRMs, databases, repos) |

The first three are narrower than they look. They mean the agent composes something for a third party. Getting the agent's own output back to the person who installed it is `chat.notify` above, whatever it travels over. Choosing `email.send` for an agent that mails its own owner is a capture error, and it costs the installer a working delivery channel.

These render in the consent table with **installable: no, declared only**. They are shown because hiding them would misrepresent the agent. They are not installed because the envelope (spec §5) says so.

`money.*` is a prefix, not an id: `money.transfer`, `money.trade`, `money.authorise` all validate. It is a prefix precisely so that nobody has to enumerate the ways an agent could spend someone's money before refusing to install one.

## Choosing a capability at capture time

1. Ask what the agent needs **from the owner**, not what the code calls. An RSS reader and a news API are both `web.fetch`. A Gmail scrape and an IMAP poll are both `email.read`.
2. If the agent reads something that requires the owner's login, it is credentialed, the input's `access` field says so, and the input needs a `binding` naming the slot that asks what plays that role on the installer's side. Nothing behind the original's login is ever the installer's.
3. For anything the agent sends, ask who receives it. The installer, over any channel, is `chat.notify`. Anybody else is `email.send`, `msg.send` or `social.post`. Do not classify by the transport the original happened to use.
4. If two ids both fit, pick the narrower one. `files.read` over `email.read` when the agent reads exported files rather than the live mailbox.
5. If nothing fits, do not invent an id. Describe the need in `tacit_notes`, mark the nearest capability `confidence: low`, and raise it on the check-in. Vocabulary gaps are format feedback, not capture problems to route around.

## Reading this vocabulary in code

Everything above is written for capture. This section is for anything that consumes a capability id afterwards: stores it, prints it, logs it, counts it or puts it in a record.

**This vocabulary is a closed set with exactly one wildcard in it.** Every id above is a fixed string except `money.*`, whose suffix is whatever the passport said. Both halves of that sentence matter, and it is the second half that gets dropped.

So: **a `money.*` id is not a vocabulary member, it is a prefix followed by text a stranger wrote.** Anything that would be unsafe to do with an arbitrary string is unsafe to do with a capability id. Treat the suffix as untrusted length and untrusted content. If a consumer needs to record that a passport declared a money capability, record `money.*` and not the id it arrived as.

This is written down because the inference went the other way in shipped code. A consumer described its own rule as admitting "a member of the closed vocabulary", which is true of every id here but one, and a stranger's text reached a store it should never have reached. That was found and fixed before this document was published; it is written down because the reasoning generalises and the mistake does not announce itself. The defect was not the wildcard. The defect was a consumer reading "closed vocabulary" as "bounded set of known strings" and building a guarantee on it.

**Do not close the prefix to fix this.** It is open on purpose: it is a refusal list, and the point of not enumerating it is that an agent cannot escape refusal by spending money in a way nobody wrote down first. Narrowing it would trade a real safety property for a convenience the consumer can have by collapsing the id on its own side.

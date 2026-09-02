#!/usr/bin/env python3
"""scrub.py — replace sensitive patterns in a text file with [SCRUBBED:TYPE] markers."""

import re
import json
import sys


# ── Invisible-character evasion, closed 2026-09-01 ───────────────────────────
#
# Normalisation matters most in this file, because this is the gate that
# REDACTS. A credential the other two gates merely fail to refuse, this one
# fails to remove: it gets written into the owner's passport in the clear, and
# the two downstream gates then miss it for the same reason.
#
# Kept character for character in step with preflight.py's INVISIBLE.
INVISIBLE = re.compile(
    "["
    # Generated from unicodedata, not typed: every Cf code point plus the
    # zero-advance marks and blank-rendering fillers. 437 code points in
    # 29 ranges, 8 of them above the BMP.
    "\u00ad\u034f\u0600-\u0605\u061c\u06dd\u070f\u0890-\u0891\u08e2\u115f-\u1160\u17b4-\u17b5\u180b-\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f\u2800\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff9-\ufffb\U000110bd\U000110cd\U00013430-\U0001343f\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0001\U000e0020-\U000e007f\U000e0100-\U000e01ef"
    "]")


# What this file stripped before 2026-09-01: U+FEFF alone. Kept as its own class
# so the legacy pass is the OLD behaviour exactly, not an approximation of it.
LEGACY_INVISIBLE = re.compile("[\ufeff]")


def normalise_for_scan(text):
    """Identical to preflight.normalise_for_scan. Used where only a boolean is
    wanted; anything that has to WRITE must go through _normalise_with_map."""
    return INVISIBLE.sub("", text).replace("\u0085", " ")


def _normalise_with_map(line, legacy=False):
    """Return (normalised, idx) for a single line.

    idx[i] is the index IN THE ORIGINAL LINE of the character that produced
    normalised character i, and idx[len(normalised)] == len(line).

    WHY THIS EXISTS AND THE OTHER TWO GATES DO NOT NEED IT. preflight.py and the
    upload endpoint normalise a copy, ask "did anything match", and throw the
    copy away. A boolean has no offsets to get wrong. This file writes a
    redaction back into the ORIGINAL text, so a match found at offset N in a
    string with characters removed points at offset N+k in the string being
    edited. Redacting at the un-translated offset cuts a span that is short by
    exactly the number of invisible characters to its left: it leaves part of the
    credential in the file and eats part of the text around it, silently, while
    the report says the line was scrubbed.
    """
    out, idx = [], []
    strip = LEGACY_INVISIBLE if legacy else INVISIBLE
    for i, ch in enumerate(line):
        if strip.match(ch):
            continue
        out.append(" " if ch == "\u0085" else ch)
        idx.append(i)
    idx.append(len(line))
    return "".join(out), idx


PATTERNS = [
    ("ANTHROPIC_KEY", re.compile(r"\bsk-ant-[A-Za-z0-9\-]{10,}\b")),
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # Both GitHub shapes. The classic token is a fixed 36 characters; the
    # fine-grained one is longer and variable, and omitting it meant a current
    # GitHub credential passed this file untouched.
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"
                                r"|\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("GOOGLE_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    # The BEGIN line of a PEM block. It is the most damaging single thing a
    # capture can carry and it was the most conspicuous absence here.
    #
    # This entry DEFINES what a block is; it does not redact one. The header is
    # the tell and the body is the secret, so matching the header alone redacts
    # the label and ships the key. _collapse_private_key_blocks looks this
    # pattern up BY NAME and removes the whole span before the per-line loop
    # runs, which is why the entry is not dead code and must not be inlined
    # there: --list-rules and the parity name map both read PATTERNS.
    #
    # The optional " BLOCK" matches PGP's armour as well as PEM's, because PGP
    # writes "-----BEGIN PGP PRIVATE KEY BLOCK-----" and a pattern ending at
    # "PRIVATE KEY-----" cannot see it.
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    # Anchored at the query delimiter rather than at the scheme. The scheme-tied
    # form needed a run between the two, and every bounded version of that run
    # cut off a parameter past the bound while the unbounded one was quadratic.
    # Anchoring at [?&] has no length axis and no backtracking site. One
    # consequence here: the match
    # now starts at [?&], so scrubbing keeps the URL base and removes only the
    # credential parameter onward, which is more useful to the owner than
    # destroying the whole endpoint address.
    # The signed-URL signature vocabulary added 2026-09-01 is held character
    # for character in step with preflight.py and the endpoint; the measurement
    # and the accepted misses are written out beside preflight's copy.
    ("TOKEN_URL", re.compile(r"(?<=\S)[?&](?:(?:token|key|secret|auth|apikey|api_key|access_token)=(?!(?:\$\{[A-Za-z_][A-Za-z_]{0,64}\}|\{\{[A-Za-z_][A-Za-z _.-]{0,64}\}\}|<[A-Za-z_][A-Za-z _.-]{0,64}>|\[[A-Za-z_][A-Za-z _.-]{0,64}\])(?=[\s&#]|$))\S+|(?:[Ss][Ii][Gg]|(?:[Xx]-[A-Za-z][A-Za-z0-9]{1,9}-)?[Ss][Ii][Gg][Nn][Aa][Tt][Uu][Rr][Ee])=(?!(?:\$\{[A-Za-z_][A-Za-z_]{0,64}\}|\{\{[A-Za-z_][A-Za-z _.-]{0,64}\}\}|<[A-Za-z_][A-Za-z _.-]{0,64}>|\[[A-Za-z_][A-Za-z _.-]{0,64}\])(?=[\s&#]|$))[^\s&#]{16,})")),
    # A WEBHOOK URL WHOSE PATH IS THE CREDENTIAL, added 2026-09-01. Nothing
    # above sees this shape, because there is no parameter and no assignment:
    # the secret is the path itself, and possession of the URL is the whole
    # authorisation. That makes it the one credential a passport is LIKELY to
    # carry honestly, because an owner describing how their agent posts to a
    # channel writes the URL down without thinking of it as a key.
    #
    # THIS RULE IS A LIST OF VENDORS AND THERE IS NO WAY AROUND THAT. Every
    # other rule here matches a shape; a webhook URL has no shape, only a host.
    # So the list is the rule's ceiling: a vendor not on it is not caught, and
    # adding one is a one-line change with its own false-positive round. Named
    # so nobody reads the absence of a fire as an absence of a webhook.
    #
    # MEASURED BEFORE ADDING: zero fires over the same 119,708 third-party
    # files, and zero over the 34 fixture documents. Ten probes, five real
    # shapes and five near misses (the API documentation host, a workspace
    # archive link, an invite link, a truncated path, and the bare hostname in
    # prose), identical in Python re and V8.
    #
    # ONE KNOWN AND ACCEPTED FALSE POSITIVE: the placeholder in a vendor's own
    # documentation, T00000000/B00000000/XXXXXXXX, fires. It is indistinguishable
    # from a live URL by anything this rule can see, and refusing it is the safe
    # direction at a public door.
    ("WEBHOOK_URL", re.compile(r"(?<![A-Za-z0-9_])[Hh][Tt][Tt][Pp][Ss]://(?:(?:[Hh][Oo][Oo][Kk][Ss]\.[Ss][Ll][Aa][Cc][Kk]\.[Cc][Oo][Mm]/(?:services|triggers|workflows)|(?:[Cc][Aa][Nn][Aa][Rr][Yy]\.|[Pp][Tt][Bb]\.)?[Dd][Ii][Ss][Cc][Oo][Rr][Dd](?:[Aa][Pp][Pp])?\.[Cc][Oo][Mm]/api/(?:v[0-9]{1,2}/)?webhooks|[A-Za-z0-9-]{1,63}\.[Ww][Ee][Bb][Hh][Oo][Oo][Kk]\.[Oo][Ff][Ff][Ii][Cc][Ee]\.[Cc][Oo][Mm]/webhookb2|[Oo][Uu][Tt][Ll][Oo][Oo][Kk]\.[Oo][Ff][Ff][Ii][Cc][Ee]\.[Cc][Oo][Mm]/webhook|[Hh][Oo][Oo][Kk][Ss]\.[Zz][Aa][Pp][Ii][Ee][Rr]\.[Cc][Oo][Mm]/hooks/(?:catch|standard))[/A-Za-z0-9_+=-]{0,4}/[A-Za-z0-9_/+=@.-]{16,}|[Aa][Pp][Ii]\.[Tt][Ee][Ll][Ee][Gg][Rr][Aa][Mm]\.[Oo][Rr][Gg]/bot[0-9]{6,}:[A-Za-z0-9_-]{20,})")),
    # A database URL carrying a password. Nothing else here sees this shape:
    # the EMAIL rule hit it by accident on the user:pass@host middle, and a
    # form with no @-shaped middle was caught nowhere.
    # Measured against a corpus of third-party markdown before adding it.
    # The negated classes all exclude \s, so THIS rule cannot span a line break.
    # Two rules here DO span a newline, a password assignment and a credential
    # assignment. That is deliberate; only this one is pinned single-line.
    #
    # The password part is [^\s:/@]{3,}, deliberately unbounded. An earlier
    # version bounded it at 256 against a quadratic form, and a comment survived
    # the bound saying so; it described a limit the pattern no longer had and a
    # bypass that no longer worked. Measured: passwords well past that length
    # are all caught, and the rule stays linear against
    # every seed in the project's ReDoS corpus. Unbounded is both safe and
    # correct here.
    # Do not reintroduce an upper bound to "fix" a cost that is not there.
    ("DB_URL", re.compile(r"\b[a-z][a-z0-9+.\-]{0,31}://[^\s:/@]+:(?!<(?:[Rr][Ee][Dd][Aa][Cc][Tt][Ee][Dd]|[Ss][Cc][Rr][Uu][Bb][Bb][Ee][Dd]|[Rr][Ee][Mm][Oo][Vv][Ee][Dd]|[Hh][Ii][Dd][Dd][Ee][Nn]|[Mm][Aa][Ss][Kk][Ee][Dd]|[Ee][Ll][Ii][Dd][Ee][Dd]|[Oo][Mm][Ii][Tt][Tt][Ee][Dd]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Yy][Oo][Uu][Rr][-_]?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Xx]+|\*+)(?:[:_ -][A-Za-z]+)*[-_0-9]*>@|\[(?:[Rr][Ee][Dd][Aa][Cc][Tt][Ee][Dd]|[Ss][Cc][Rr][Uu][Bb][Bb][Ee][Dd]|[Rr][Ee][Mm][Oo][Vv][Ee][Dd]|[Hh][Ii][Dd][Dd][Ee][Nn]|[Mm][Aa][Ss][Kk][Ee][Dd]|[Ee][Ll][Ii][Dd][Ee][Dd]|[Oo][Mm][Ii][Tt][Tt][Ee][Dd]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Yy][Oo][Uu][Rr][-_]?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Xx]+|\*+)(?:[:_ -][A-Za-z]+)*[-_0-9]*\]@|\*+@|\$\{[A-Za-z_][A-Za-z0-9_]*\}@|\$[A-Za-z_][A-Za-z0-9_]*@)[^\s:/@]{3,}@[^\s/]+")),
    # Bounded at the RFC 5321 limits, 64 for the local part and 255 for the domain,
    # because the unbounded form was QUADRATIC: [A-Za-z0-9._%+-]+ and
    # [A-Za-z0-9.-]+ overlap on dots, so a long dotted run made the engine try
    # every split looking for an @, which on a long dotted run is quadratic.
    # Found because the cost benchmark started covering every rule instead of
    # one, which is the only reason a quadratic rule nobody was looking at gets
    # noticed.
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Za-z]{2,24}\b")),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("PASSWORD_ASSIGN", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+")),
    # SendGrid. Named rather than left to CREDENTIAL_ASSIGN because its value is
    # three dot-separated segments, which is the exact shape CREDENTIAL_ASSIGN
    # now refuses in order to stop matching ordinary code like
    # forge.random.getBytesSync. A vendor whose format collides with the generic
    # exclusion gets a named rule; that is what the named rules are for.
    ("SENDGRID_KEY", re.compile(r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b")),
    # CREDENTIAL_ASSIGN catches by CONTEXT, not by shape, and that is the whole
    # point of it. Every other named rule here knows what a particular vendor's
    # key looks like, and the entropy rule knows what randomness looks like. Neither can
    # see a 64-character lowercase hex token, because it looks exactly like a
    # sha256. Nothing about the string distinguishes them.
    #
    # What distinguishes them is where they sit. A commit hash is never on the
    # right-hand side of DEPLOY_AUTH_TOKEN=. So this rule reads the NAME and
    # ignores the value's alphabet entirely: any run of 20 or more from a
    # credential-ish alphabet, assigned to something calling itself a token, a
    # secret, an auth, a credential or a key, goes.
    #
    # This is the rule that closes the hole the entropy rule's case gate leaves open,
    # and it closes it without touching the git-hash trade below, because a
    # hash in prose is not an assignment.
    # Measured against a large corpus of third-party markdown, the kind that
    # carries real code in fenced blocks. The rule is deliberately narrow: a
    # wider form matches far more than it should here, and a small number of
    # distinct strings account for what this one still matches.
    #
    # Three things were wrong, and a fixture suite written by the same person as
    # the rule cannot see any of them. A rule and its tests written together
    # share their author's assumptions:
    #
    # 1. The trigger word matched INSIDE other words. [A-Za-z0-9_.\-]* on both
    #    sides meant "key" matched in keyframes, keypair and keychain, and "auth"
    #    matched in WithAuth. That was most of the false positives. The word is now
    #    bounded by (?![A-Za-z]) and cannot run into a following letter.
    #    "authorization" is spelled out ahead of "auth" so it still matches, and
    #    a trailing plural s is allowed.
    #
    # 2. Bare "key" is too weak a name to convict on. `key: <40 hex>` in a README
    #    is a GPG fingerprint, which is public by design. The key branch now
    #    requires a qualifier in front of it, so API_KEY, DEPLOY_KEY and apiKey
    #    still match and a lone "key" does not.
    #
    # 3. The value alphabet contains ".", so any dotted code expression of 20+
    #    characters was a "credential". forge.random.getBytesSync and
    #    process.env.AXIOM_TOKEN were both scrubbed out of golden examples,
    #    taking the assigned name with them, because the match spans both sides.
    #    A value that is a plain dotted identifier chain is now refused.
    #
    # Documentation placeholders and paths-to-a-credential are refused for the
    # same reason: they are the shapes a person writes when deliberately NOT
    # writing a secret.
    #
    # What this deliberately still cannot do is separate a 40-character
    # lowercase hex token from a sha256 in prose. Nothing about the string tells
    # them apart, which is why this rule reads the name instead. A hash is never
    # on the right of AUTH_TOKEN=.
    ("CREDENTIAL_ASSIGN", re.compile(
        # No (?i). The key branch has to tell apiKey from monkey, and that is a
        # question about CASE, so every letter is spelled as a class instead.
        # It is also the only form guaranteed to mean the same thing in every
        # regex engine, which matters because this pattern is reimplemented
        # elsewhere and the copies must not drift.
        # Left boundary, and it is a SECURITY fix rather than a tidy-up.
        #
        # Without it the pattern opens with an unanchored [A-Za-z0-9_.\-]*, so on a
        # long run of name characters the engine starts a fresh scan at every
        # position and the whole thing goes quadratic, on an input carrying no
        # credential at all. The rule this replaced had the same flaw.
        #
        # The lookbehind makes every start position but the true beginning of an
        # identifier run fail in constant time. A large input scales
        # linearly. Verified behaviourally identical, not merely faster: the same
        # matched STRINGS over the whole corpus, not just the same counts.
        r"(?<![A-Za-z0-9_.\-])"
        r"(?:"
        r"[A-Za-z0-9_.\-]*(?:[Aa][Uu][Tt][Hh][Oo][Rr][Ii][Zz][Aa][Tt][Ii][Oo][Nn]"
        r"|[Tt][Oo][Kk][Ee][Nn]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Aa][Uu][Tt][Hh]"
        r"|[Cc][Rr][Ee][Dd][Ee][Nn][Tt][Ii][Aa][Ll]|[Pp][Aa][Ss][Ss][Pp][Hh][Rr][Aa][Ss][Ee])s?"
        r"|[A-Za-z0-9_.\-]*[Aa][Pp][Ii][_\-]?[Kk][Ee][Yy]s?"
        r"|[A-Za-z0-9_.\-]*[a-z0-9]Keys?"
        r"|[A-Za-z0-9_.\-]*[_\-.][Kk][Ee][Yy]s?"
        r")(?![A-Za-z])"
        r"[\"']?\s*[:=]\s*(?:Bearer\s+)?[\"']?"
        r"(?!(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*(?![A-Za-z0-9_\-+/=~.]))"
        r"(?!(?:[Yy][Oo][Uu][Rr]|[Mm][Yy]|[Ii][Nn][Ss][Ee][Rr][Tt]|[Rr][Ee][Pp][Ll][Aa][Cc][Ee]"
        r"|[Ee][Xx][Aa][Mm][Pp][Ll][Ee]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]"
        r"|[Cc][Hh][Aa][Nn][Gg][Ee][Mm][Ee]|[Ss][Aa][Mm][Pp][Ll][Ee]|[Dd][Uu][Mm][Mm][Yy]"
        r"|[Pp][Aa][Ss][Tt][Ee]|[Tt][Oo][Dd][Oo]|[Xx][Xx][Xx])[A-Za-z0-9_\-]*(?![A-Za-z0-9_\-+/=~.]))"
        r"(?![A-Za-z0-9_\-+/=~.]{0,128}[_\-]?[Hh][Ee][Rr][Ee](?![A-Za-z0-9_\-+/=~.]))"
        r"(?![A-Za-z0-9_\-+/=~.]{0,128}/[A-Za-z0-9_\-+/=~.]{0,128}\.[A-Za-z]{2,5}(?![A-Za-z0-9_\-+/=~.]))"
        r"[A-Za-z0-9_\-+/=~.]{20,}[\"']?"
    )),
    # ── Vendor prefixes, added 2026-08-31 ────────────────────────────────────
    #
    # Eight credential shapes over the seven rules below, held character for
    # character in step with preflight.py and the endpoint. The reasoning for
    # each bound is written out beside preflight's copy; what follows is why
    # they are HERE, in the scrubber, and not only at the two gates downstream.
    #
    # This file runs during capture, on the owner's own machine, in front of the
    # owner. The two downstream gates run later and refuse. That asymmetry is the
    # whole argument: a false positive here rewrites a file the owner is looking
    # at and hands them a finding naming what went, which they can read and undo.
    # A false positive at the public endpoint refuses a stranger's upload and
    # tells them to rotate something that was never a credential, about a rule
    # they cannot see. So a rule safe enough for the endpoint is safe here by a
    # wide margin, and a vendor rule the endpoint has and this file lacks is a
    # credential leaving the owner's machine unredacted.
    #
    # That last sentence is not hypothetical. A list of recorded gaps between
    # this file and the gates downstream once held exactly that situation for a
    # PEM private key block, a Slack token and a Google API key, described
    # rather than fixed, while the scrubber shipped them. Closing the gap is preferred to recording
    # it, and this block closes it on the same day the rules were written rather
    # than leaving the two tables out of step for a release.
    #
    # WHAT THIS BUYS ON TOP OF THE ENTROPY BACKSTOP. Rule 10 already redacted the
    # token this block was written for, but only as HIGH_ENTROPY. The owner's
    # scrub review then reads "high entropy string" where it can now read "a
    # Notion integration token". The one person able to recognise their own
    # credential is the owner, and a named finding is what lets them.
    ("NOTION_TOKEN",
     re.compile(r"(?<![A-Za-z0-9_])ntn_[A-Za-z0-9]{40,}(?![A-Za-z0-9_])")),
    ("NOTION_LEGACY_TOKEN",
     re.compile(r"(?<![A-Za-z0-9_])secret_[A-Za-z0-9]{32,}(?![A-Za-z0-9_])")),
    ("STRIPE_KEY",
     re.compile(r"(?<![A-Za-z0-9_])(?:sk|rk)_live_[A-Za-z0-9]{20,}(?![A-Za-z0-9_])")),
    ("SLACK_WEBHOOK",
     re.compile(r"hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]{20,}")),
    ("HUGGINGFACE_TOKEN",
     re.compile(r"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{32,}(?![A-Za-z0-9_])")),
    ("LINEAR_KEY",
     re.compile(r"(?<![A-Za-z0-9_])lin_api_[A-Za-z0-9]{36,}(?![A-Za-z0-9_])")),
    ("AIRTABLE_TOKEN",
     re.compile(r"(?<![A-Za-z0-9_])pat[A-Za-z0-9]{14}\.[0-9a-f]{64}(?![A-Za-z0-9_])")),
]

# The character class carries +, / and = so that a standard-base64 credential
# is seen as ONE run instead of being shattered into sub-32 fragments.
#
# Without them, the canonical AWS secret-access-key shape
# (mixed case, digits, two slashes, 40 chars) produced findall() == [] and was
# missed entirely: it never reached the case gate below, so the gate was not
# even the thing that failed it. Two independent holes in one rule.
#
# Written as explicit boundaries rather than \b, because \b is defined on word
# characters and would not fire correctly next to a trailing = or /.
HIGH_ENTROPY = re.compile(
    r"(?<![A-Za-z0-9_\-+/=])[A-Za-z0-9_\-+/=]{32,}(?![A-Za-z0-9_\-+/=])"
)


def _high_entropy_ok(s):
    """Return True if the candidate has lower, upper, AND digit."""
    has_lower = any(c.islower() for c in s)
    has_upper = any(c.isupper() for c in s)
    has_digit = any(c.isdigit() for c in s)
    return has_lower and has_upper and has_digit


def _prefix(match_str, max_len=8):
    return match_str[:max_len] + "..."


# The END line that closes a key block. Its BEGIN half is a named rule in
# PATTERNS and stays there, because the pre-pass below needs both halves and
# looks the BEGIN up by name.
PRIVATE_KEY_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")

# A PEM body line: base64 and nothing else. Used to bound the damage when a
# block has a BEGIN and no END anywhere. Prose does not match, because prose has
# spaces and punctuation and this does not.
# A PEM body line. The alphabet includes - and _ so that a base64url-encoded
# body does not drop the truncated path back onto the entropy backstop, which is
# the exact dependency this function exists to remove.
PEM_BODY_LINE = re.compile(r"^[A-Za-z0-9+/=_-]{4,}$")

# RFC 1421 headers, which sit between BEGIN and the body on an encrypted key:
# "Proc-Type: 4,ENCRYPTED" and "DEK-Info: AES-128-CBC,...", usually followed by
# a blank line. They are not base64, so a body scan starting at the line after
# BEGIN stops dead on them and leaves the body behind.
PEM_HEADER_LINE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*:\s*\S")


def _pem_run_end(text, offset):
    """End offset of the base64 run following a BEGIN with no END.

    Steps over RFC 1421 headers ("Proc-Type:", "DEK-Info:") and blank lines that
    sit between the header and the body, but only when real base64 follows them,
    so a PEM header quoted in prose loses its own line and not the paragraph.
    """
    lines = text[offset:].split("\n")
    consumed, i = 0, 0
    if lines and lines[0].strip():
        consumed += len(lines[0]) + 1
        i = 1
    # Step over RFC 1421 headers and blank lines, then over the body, and keep
    # stepping over interior blank lines for as long as base64 resumes after
    # them. Both skips are conditional on base64 actually following, which is
    # what stops a PEM header quoted in prose from eating the paragraph under
    # it: nothing base64-shaped comes next, so nothing past the header goes.
    while True:
        j = i
        while j < len(lines) and (PEM_HEADER_LINE.match(lines[j].strip())
                                  or not lines[j].strip()):
            j += 1
        if j >= len(lines) or not PEM_BODY_LINE.match(lines[j].strip()):
            break
        for k in range(i, j):
            consumed += len(lines[k]) + 1
        i = j
        while i < len(lines) and PEM_BODY_LINE.match(lines[i].strip()):
            consumed += len(lines[i]) + 1
            i += 1
    return min(offset + consumed, len(text))


def _collapse_private_key_blocks(text):
    """Remove whole private key blocks. Returns (lines, origin_line_numbers, findings).

    Every other rule here is per-line, and for every other rule that is right,
    because the credential and its tell are the same string. A key block is the
    one format where they are not: the tell is the BEGIN line and the secret is
    the several hundred base64 characters underneath it. A per-line rule on the
    header redacts the label and ships the key.

    ONE RULE, DELIBERATELY.

        A block runs from a BEGIN to the LAST END before the next BEGIN, or, if
        there is no END before that point, over the run of base64 that follows.
        Same rule whether the END is on the header's own line or four hundred
        lines down.

    Do not special-case the same-line form and run that branch first. It is the
    obvious shape for this code to take and it cannot be made safe. Such a
    branch has to decide whether an END on the header's own line really closes
    the block, and the only evidence available is what the text between them
    looks like. A decoy is indistinguishable from a body by any test of shape,
    so the branch accepts it, declares the block handled, and never runs the
    scan that would have found the real terminator.

    Taking the LAST END before the next BEGIN needs no such decision, because a
    decoy END is never the last one: the real terminator is. Two blocks on one
    line still separate correctly, since the second BEGIN bounds the search for
    the first. Where the input is genuinely ambiguous this over-redacts, which
    costs the owner a visible string they can put back rather than costing
    somebody else a key.

    Nothing here depends on the entropy backstop, and that is the point rather
    than a nicety. The backstop is for credentials nobody enumerated; leaning on
    it for one that IS enumerated hides whether the named rule works at all.
    """
    begin_re = dict(PATTERNS)["PRIVATE_KEY_BLOCK"]
    spans, pos = [], 0
    while True:
        b = begin_re.search(text, pos)
        if not b:
            break
        nxt = begin_re.search(text, b.end())
        limit = nxt.start() if nxt else len(text)
        # Grow the span until it stops growing, alternating two steps: swallow
        # any base64 run, then swallow the last END beyond it.
        #
        # The alternation is the point, and one step alone is not enough. An END
        # is a terminator only if nothing key-shaped follows it, so a block does
        # NOT end where base64 continues. Taking the last END in a single pass
        # looks equivalent and is not: put a decoy END on the header line of a
        # key with no real terminator, and the decoy IS the last END, so one
        # pass stops there and ships the body.
        stop, terminated = b.end(), False
        while True:
            grew = False
            ext = _pem_run_end(text, stop)
            if ext > stop:
                stop, grew = ext, True
            after = None
            for m in PRIVATE_KEY_END.finditer(text, stop, limit):
                after = m
            if after:
                stop, grew, terminated = after.end(), True, True
            if not grew:
                break
        stop = max(stop, b.end())
        kind = "PRIVATE_KEY_BLOCK" if terminated else "PRIVATE_KEY_BLOCK_TRUNCATED"
        spans.append((b.start(), stop, kind, b.group()))
        pos = stop

    # Rebuild, carrying each output character's INPUT line number, so every
    # finding downstream reports the line the text was on in what the owner
    # captured rather than in the shortened output they read afterwards.
    out, linemap, findings = [], [], []
    cur, last = 1, 0
    for s_off, e_off, kind, tell in spans:
        for ch in text[last:s_off]:
            out.append(ch); linemap.append(cur)
            if ch == "\n":
                cur += 1
        marker = "[SCRUBBED:PRIVATE_KEY_BLOCK]"
        for ch in marker:
            out.append(ch); linemap.append(cur)
        finding = {"type": kind, "line": cur, "match_prefix": _prefix(tell),
                   "lines_removed": text.count("\n", s_off, e_off) + 1}
        if kind == "PRIVATE_KEY_BLOCK_TRUNCATED":
            finding["why"] = ("no END line found. The header and the base64 run "
                              "after it are removed, which is everything that "
                              "looks like key material. Check what follows it "
                              "yourself")
        findings.append(finding)
        cur += text.count("\n", s_off, e_off)
        last = e_off
    for ch in text[last:]:
        out.append(ch); linemap.append(cur)
        if ch == "\n":
            cur += 1

    result = "".join(out)
    lines = result.split("\n")
    origin, idx = [], 0
    for ln in lines:
        origin.append(linemap[idx] if idx < len(linemap) else cur)
        idx += len(ln) + 1
    return lines, origin, findings


def scrub(text):
    """Apply every named rule in order, then the entropy rule last.

    Returns (scrubbed_text, findings_list). Deliberately counts nothing: this
    docstring said "all 10 rules" while the list held nine and a report, and
    the number went stale again the moment SENDGRID_KEY was added."""
    lines, origin, findings = _collapse_private_key_blocks(text)

    # The named rules, per-line, in list order.
    #
    # Right to left, and WITHOUT an offset. Those two are alternatives, not
    # partners, and carrying both is what made this function leave credentials
    # in its own output.
    #
    # Replacing right to left means every match still to be processed sits
    # entirely to the LEFT of the edit just made, so its recorded start and end
    # are still correct. That is the whole reason to iterate backwards. An
    # offset corrects for edits made BEFORE the current match, which is what a
    # left-to-right walk needs. Applying both shifted every match after the
    # first by the length of one marker.
    #
    # What that cost, on one line carrying two matches of the same rule: the
    # second replacement landed at the wrong index, cut the line in the wrong
    # place, and left the first secret in the output while the report said two
    # were scrubbed. Reproduced with two URL tokens, where the first survived
    # in full. A report that says "handled" over a file that still carries the
    # secret is worse than no scrubber, because it is the line the owner reads
    # before sending the passport to somebody.
    #
    # A fixture that puts every planted secret on its own line never exercises
    # this path at all, which is the arrangement most fixture suites default to.
    # Matching happens on the NORMALISED line and writing happens in the
    # ORIGINAL, so every span crosses _normalise_with_map on the way out. The
    # right-to-left walk is what keeps the untranslated spans valid: each edit
    # lands entirely to the right of every match still to be processed, so the
    # map built from the original line stays correct for all of them.
    #
    # The recorded prefix is taken from the ORIGINAL slice, not from the
    # normalised match, so the report shows what was actually in the file
    # including whatever invisible characters were hiding in it.
    for rule_type, pattern in PATTERNS:
        marker = "[SCRUBBED:" + rule_type + "]"
        new_lines = []
        for i, line in enumerate(lines):
            # Spans from BOTH the line as written and the normalised line.
            #
            # Removing an invisible character helps in one position and hurts in
            # another. Between the delimiter and the parameter name it restores
            # the adjacency the rule needs. Immediately BEFORE the delimiter it
            # destroys the non-space that satisfied (?<=\S), so a credential this
            # file used to redact would be written through untouched. The two
            # positions want opposite things from the same character.
            #
            # So collect spans from both passes and redact their union. Strictly
            # a superset of the behaviour before normalisation: it cannot leave a
            # credential that was previously removed.
            spans = []
            for m in pattern.finditer(line):
                spans.append((m.start(), m.end()))
            # The pre-2026-09-01 normalisation as its own pass. It strips only
            # U+FEFF, which makes it a THIRD normalisation rather than a subset of
            # the two around it, and it wins whenever a document needs U+FEFF gone
            # and another invisible kept. Without it this file stops redacting
            # credentials it used to redact.
            leg, leg_idx = _normalise_with_map(line, legacy=True)
            for m in pattern.finditer(leg):
                s_ = leg_idx[m.start()]
                e_ = leg_idx[m.end() - 1] + 1 if m.end() > m.start() else s_
                spans.append((s_, e_))
            norm, idx = _normalise_with_map(line)
            for m in pattern.finditer(norm):
                start = idx[m.start()]
                end = idx[m.end() - 1] + 1 if m.end() > m.start() else start
                spans.append((start, end))

            # Merge overlaps, then walk right to left so each edit lands entirely
            # to the right of every span still to be processed.
            merged = []
            for s, e in sorted(set(spans)):
                if merged and s <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                else:
                    merged.append((s, e))
            for start, end in reversed(merged):
                findings.append({
                    "type": rule_type,
                    "line": origin[i],
                    "match_prefix": _prefix(line[start:end]),
                })
                line = line[:start] + marker + line[end:]
            new_lines.append(line)
        lines = new_lines

    # The entropy rule, last, on text every named rule has already been
    # through, so anything left is a credential no pattern recognised.
    #
    # This rule REPLACES. An earlier form appended a finding and then appended
    # the line unchanged, so a secret nothing else matched was announced to the
    # owner and left in the file. A test that asserts the finding appears in the
    # REPORT does not catch that; only asserting the string is absent from the
    # FILE does, and that is the assertion here now.
    #
    # It matters more than the other rules put together, because it is the only
    # one that catches a credential format nobody enumerated. Every other rule
    # here knows a shape in advance; this one does not need to.
    #
    # THE TRADE, stated because it is a real one. Redacting means a false
    # positive now destroys text instead of merely mentioning it: any run of
    # 32 or more of [A-Za-z0-9_-] carrying lower, upper and a digit goes,
    # which a long mixed-case identifier could satisfy. That is the right way
    # round for this product. A false positive costs the owner one mangled
    # string they can see and put back; a false negative costs somebody else's
    # credential, permanently, in a document built to be handed to a stranger.
    # The finding still records a prefix, so what went is identifiable.
    #
    # No marker guard. The old one tested candidate.startswith("[SCRUBBED:"),
    # which could never fire: the pattern's character class has no bracket or
    # colon in it, so a match can neither start at "[" nor span one. Nor is a
    # guard needed. A marker's longest unbroken run of matchable characters is
    # PASSWORD_ASSIGN at fifteen, and this rule needs thirty-two.
    # THIS RULE GOES THROUGH THE SAME UNION AS THE NAMED ONES, added 2026-09-01.
    #
    # This is the rule that most needs the union: it is the only one that
    # catches a credential format nobody enumerated, so it is the backstop for
    # exactly the shapes the named rules cannot see. Running it on the raw line
    # alone leaves that backstop blind to the evasion below.
    #
    # One invisible character in the middle of a 40-character token split it into
    # two 20-character halves, each below the 32 floor. Nothing matched, so
    # nothing was redacted AND no finding was recorded, not even the near miss.
    # Both halves stayed in the file and the owner's scrub review showed a clean
    # screen. That is precisely the failure the comment below says this rule was
    # changed to avoid: it degraded into silence rather than into telling, on the
    # one rule whose whole purpose is to be the last thing between an unrecognised
    # credential and a passport.
    #
    # Spans come from the raw line AND the normalised line, mapped back and
    # merged, the same way the named rules above do it.
    result_lines = []
    for i, line in enumerate(lines):
        spans = [(m.start(), m.end()) for m in HIGH_ENTROPY.finditer(line)]
        leg, leg_idx = _normalise_with_map(line, legacy=True)
        for m in HIGH_ENTROPY.finditer(leg):
            s_ = leg_idx[m.start()]
            e_ = leg_idx[m.end() - 1] + 1 if m.end() > m.start() else s_
            spans.append((s_, e_))
        norm, idx = _normalise_with_map(line)
        for m in HIGH_ENTROPY.finditer(norm):
            start = idx[m.start()]
            end = idx[m.end() - 1] + 1 if m.end() > m.start() else start
            spans.append((start, end))
        merged = []
        for s, e in sorted(set(spans)):
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))

        class _Span:
            __slots__ = ("_s", "_e", "_t")
            def __init__(self, s, e, t): self._s, self._e, self._t = s, e, t
            def start(self): return self._s
            def end(self): return self._e
            def group(self): return self._t

        # The candidate is judged on the NORMALISED text of the span, so an
        # invisible sitting inside a token does not change the alphabet test.
        for m in reversed([_Span(s, e, normalise_for_scan(line[s:e]))
                           for s, e in merged]):
            candidate = m.group()
            if not _high_entropy_ok(candidate):
                # NEAR MISS. Long enough to be a credential, wrong alphabet to
                # be sure, so it is NOT scrubbed: the case gate exists to keep
                # git hashes, uuids and slugs intact, and the test suite pins
                # three of them.
                #
                # But silence here is what made the old behaviour dangerous.
                # A single-case token fell through this branch and appeared in
                # no report, so the owner's scrub review listed what WAS
                # removed and could not list what was skipped. The one human
                # able to recognise their own credential was shown a clean
                # screen.
                #
                # So it degrades into telling rather than into silence, which
                # is how the rest of this product behaves. The passport keeps
                # the string; the owner is handed it to look at.
                findings.append({
                    "type": "HIGH_ENTROPY_NEAR_MISS",
                    "line": origin[i],
                    "match_prefix": _prefix(candidate),
                    "scrubbed": False,
                    "why": "single case or no digit; kept so hashes and ids survive",
                })
                continue
            line = line[:m.start()] + "[SCRUBBED:HIGH_ENTROPY]" + line[m.end():]
            findings.append({
                "type": "HIGH_ENTROPY",
                "line": origin[i],
                "match_prefix": _prefix(candidate),
            })
        result_lines.append(line)

    return "\n".join(result_lines), findings


def main():
    # --list-rules prints this file's rule types, one per line, and takes no
    # input. A parity check maps them onto the preflight rule names so
    # that a rule present in one table and absent from the other has to be
    # recorded rather than merely true. This file was outside that comparison
    # while the other two were inside it, and the gap that produced was real:
    # credential formats the other two knew about passed this file untouched.
    # A rule set that is not compared is a rule set that drifts.
    if "--list-rules" in sys.argv[1:]:
        for rule_type, _ in PATTERNS:
            print(rule_type)
        sys.exit(0)
    if len(sys.argv) != 4:
        print("Usage: scrub.py [--list-rules] INPUT OUTPUT REPORT", file=sys.stderr)
        sys.exit(1)

    input_path, output_path, report_path = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, IOError) as e:
        print(f"Error reading {input_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        # A keystore, a .p12/.pfx/.jks, an image, or any latin-1 file. This
        # caught nothing before and produced a raw traceback, which is what the
        # model driving the capture would have seen: the one failure path in
        # this file that did not explain itself. It fails closed either way,
        # which is right; it now says why.
        print(f"Error reading {input_path}: not UTF-8 text.\n"
              "This scrubber reads text. A binary file (a keystore, an archive, "
              "an image) cannot be scanned by it and must not be copied into a "
              "passport at all. Exclude it and scan the text you are including.",
              file=sys.stderr)
        sys.exit(1)

    scrubbed, findings = scrub(text)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(scrubbed)
    except (OSError, IOError) as e:
        print(f"Error writing {output_path}: {e}", file=sys.stderr)
        sys.exit(1)

    counts = {}
    for f_obj in findings:
        t = f_obj["type"]
        counts[t] = counts.get(t, 0) + 1

    report = {"findings": findings, "counts": counts}
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f)
    except (OSError, IOError) as e:
        print(f"Error writing {report_path}: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""scrub.py — replace sensitive patterns in a text file with [SCRUBBED:TYPE] markers."""

import re
import json
import os
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
    ("ANTHROPIC_KEY", re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_\-]{10,}(?![A-Za-z0-9])")),
    ("OPENAI_KEY", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9])")),
    ("AWS_KEY", re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])")),
    # Both GitHub shapes. The classic token is a fixed 36 characters; the
    # fine-grained one is longer and variable, and omitting it meant a current
    # GitHub credential passed this file untouched.
    ("GITHUB_TOKEN", re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])"
                                r"|(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{22,}(?![A-Za-z0-9])")),
    ("GOOGLE_KEY", re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}(?:(?<=[-_])|(?![A-Za-z0-9]))")),
    ("SLACK_TOKEN", re.compile(r"(?<![A-Za-z0-9])xox[abprs]-[0-9A-Za-z-]{10,}(?![A-Za-z0-9])")),
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
    ("JWT", re.compile(r"(?<![A-Za-z0-9])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9])")),
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
    ("TOKEN_URL", re.compile(r"(?<=\S)(?:[?]|&(?:(?:[Aa][Mm][Pp]|#0*38|#[Xx]0*26);)*)(?:(?:[Tt][Oo][Kk][Ee][Nn]|[Kk][Ee][Yy]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Aa][Uu][Tt][Hh]|[Aa][Pp][Ii][Kk][Ee][Yy]|[Aa][Pp][Ii]_[Kk][Ee][Yy]|[Aa][Cc][Cc][Ee][Ss][Ss]_[Tt][Oo][Kk][Ee][Nn])=(?!(?:\$\{[A-Za-z_][A-Za-z_]{0,64}\}|\{\{[A-Za-z_][A-Za-z _.-]{0,64}\}\}|<[A-Za-z_][A-Za-z _.-]{0,64}>|\[[A-Za-z_][A-Za-z _.-]{0,64}\])(?=[\s&#]|$))\S+|(?:[Ss][Ii][Gg]|(?:[Xx]-[A-Za-z][A-Za-z0-9]{1,9}-)?[Ss][Ii][Gg][Nn][Aa][Tt][Uu][Rr][Ee])=(?!(?:\$\{[A-Za-z_][A-Za-z_]{0,64}\}|\{\{[A-Za-z_][A-Za-z _.-]{0,64}\}\}|<[A-Za-z_][A-Za-z _.-]{0,64}>|\[[A-Za-z_][A-Za-z _.-]{0,64}\])(?=[\s&#]|$))[^\s&#]{16,})")),
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
    ("WEBHOOK_URL", re.compile(r"(?<![A-Za-z0-9_])[Hh][Tt][Tt][Pp][Ss]://(?:(?:[Hh][Oo][Oo][Kk][Ss]\.[Ss][Ll][Aa][Cc][Kk]\.[Cc][Oo][Mm](?::[0-9]*)?/(?:[Ss][Ee][Rr][Vv][Ii][Cc][Ee][Ss]|[Tt][Rr][Ii][Gg][Gg][Ee][Rr][Ss]|[Ww][Oo][Rr][Kk][Ff][Ll][Oo][Ww][Ss])|(?:[Cc][Aa][Nn][Aa][Rr][Yy]\.|[Pp][Tt][Bb]\.)?[Dd][Ii][Ss][Cc][Oo][Rr][Dd](?:[Aa][Pp][Pp])?\.[Cc][Oo][Mm](?::[0-9]*)?/[Aa][Pp][Ii]/(?:[Vv][0-9]{1,2}/)?[Ww][Ee][Bb][Hh][Oo][Oo][Kk][Ss]|[A-Za-z0-9-]{1,63}\.[Ww][Ee][Bb][Hh][Oo][Oo][Kk]\.[Oo][Ff][Ff][Ii][Cc][Ee]\.[Cc][Oo][Mm](?::[0-9]*)?/[Ww][Ee][Bb][Hh][Oo][Oo][Kk][Bb]2|[Oo][Uu][Tt][Ll][Oo][Oo][Kk]\.[Oo][Ff][Ff][Ii][Cc][Ee]\.[Cc][Oo][Mm](?::[0-9]*)?/[Ww][Ee][Bb][Hh][Oo][Oo][Kk]|[Hh][Oo][Oo][Kk][Ss]\.[Zz][Aa][Pp][Ii][Ee][Rr]\.[Cc][Oo][Mm](?::[0-9]*)?/[Hh][Oo][Oo][Kk][Ss]/(?:[Cc][Aa][Tt][Cc][Hh]|[Ss][Tt][Aa][Nn][Dd][Aa][Rr][Dd]))[/A-Za-z0-9_+=-]{0,4}/[A-Za-z0-9_/+=@.-]{16,}|[Aa][Pp][Ii]\.[Tt][Ee][Ll][Ee][Gg][Rr][Aa][Mm]\.[Oo][Rr][Gg](?::[0-9]*)?/[Bb][Oo][Tt][0-9]{6,}:[A-Za-z0-9_-]{20,})")),
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
    ("DB_URL", re.compile(r"\b[A-Za-z][A-Za-z0-9+.\-]{0,31}://[^\s:/@]*:(?!<(?:[Rr][Ee][Dd][Aa][Cc][Tt][Ee][Dd]|[Ss][Cc][Rr][Uu][Bb][Bb][Ee][Dd]|[Rr][Ee][Mm][Oo][Vv][Ee][Dd]|[Hh][Ii][Dd][Dd][Ee][Nn]|[Mm][Aa][Ss][Kk][Ee][Dd]|[Ee][Ll][Ii][Dd][Ee][Dd]|[Oo][Mm][Ii][Tt][Tt][Ee][Dd]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Yy][Oo][Uu][Rr][-_]?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Xx]+|\*+)(?:[:_ -][A-Za-z]+)*[-_0-9]*>@|\[(?:[Rr][Ee][Dd][Aa][Cc][Tt][Ee][Dd]|[Ss][Cc][Rr][Uu][Bb][Bb][Ee][Dd]|[Rr][Ee][Mm][Oo][Vv][Ee][Dd]|[Hh][Ii][Dd][Dd][Ee][Nn]|[Mm][Aa][Ss][Kk][Ee][Dd]|[Ee][Ll][Ii][Dd][Ee][Dd]|[Oo][Mm][Ii][Tt][Tt][Ee][Dd]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Yy][Oo][Uu][Rr][-_]?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Xx]+|\*+)(?:[:_ -][A-Za-z]+)*[-_0-9]*\]@|\*+@|\$\{[A-Za-z_][A-Za-z0-9_]*\}@|\$[A-Za-z_][A-Za-z0-9_]*@)[^\s:/@]{3,}@[^\s/]+")),
    # Bounded at the RFC 5321 limits, 64 for the local part and 255 for the domain,
    # because the unbounded form was QUADRATIC: [A-Za-z0-9._%+-]+ and
    # [A-Za-z0-9.-]+ overlap on dots, so a long dotted run made the engine try
    # every split looking for an @, which on a long dotted run is quadratic.
    # Found because the cost benchmark started covering every rule instead of
    # one, which is the only reason a quadratic rule nobody was looking at gets
    # noticed.
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Za-z]{2,24}\b")),
    ("IPV4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    # A PASSWORD ASSIGNMENT. Rewritten 2026-09-01; the reasoning for every part
    # is here rather than beside the copies, and the copies point at it.
    #
    # WHAT THIS REPLACES AND WHY. The rule was
    # (?i)\b(password|passwd|pwd)\s*[:=]\s*\S+ . A \b sits between a word
    # character and a non-word character, and in DB_PASSWORD the character
    # before PASSWORD is an underscore, which is a word character. So the rule
    # saw `password: hunter2` and did not see DB_PASSWORD=hunter2,
    # PGPASSWORD=hunter2, MYSQL_ROOT_PASSWORD: hunter2, "dbPassword": "hunter2",
    # SMTP_PASSWD=hunter2 or smtp_pass: hunter2. Those are the docker-compose,
    # .env, launchd and application-config shapes, which is to say nearly every
    # place a password is actually written down. The fixture planted only the
    # bare form, so no test could see it. A rule and its fixture written
    # together share their author's assumptions.
    #
    # THE NAME, in two tiers, because the trigger words are not equally strong.
    #
    #   Strong: "password" and "passwd" take any prefix at all. No ordinary word
    #   ends in either, so DB_PASSWORD, PGPASSWORD and dbPassword are all safe to
    #   convict on with nothing in front of them.
    #
    #   "pwd" takes a prefix only up to a separator. OLDPWD is the shell's
    #   previous working directory, not a credential.
    #
    #   Weak: "pass" is a word that ends ordinary identifiers everywhere.
    #   bypass, compass, minipass, pkpass, SHOULD_PASS, allPass and
    #   checklist-pass are all code. So it needs a separator or a camel hump in
    #   front of it, AND a value that looks like a secret: eight or more
    #   characters with at least one digit in them. That is what the lookahead
    #   after the weak branch is for.
    #
    # THE VALUE, which is where the precision comes from. The old rule accepted
    # any \S+, so it fired on `password ===`, `password: z.string()`,
    # `password: {`, `password: true`, `password = ''` and `PWD: '$HOME'`.
    # The exclusions refuse the shapes a person writes when they are NOT writing
    # a secret: a structural opener, a language keyword, a dotted identifier
    # chain, a function call, a shell or template variable, a documentation
    # placeholder, a bare integer, a semver range, and an identifier that is
    # itself named like a password, which is a reference rather than a value.
    #
    # WHAT IT DELIBERATELY STILL DOES NOT DO, named so nobody reads the absence
    # of a fire as an absence of a password:
    #
    #   `password: string;` is a TypeScript annotation and still fires. That
    #   false positive is unchanged from before this rewrite and is not fixed
    #   here; it wants a list of type names, and a list of type names rots.
    #
    #   A value that is the bare word "password" still fires. That is on
    #   purpose: it is also the commonest weak password there is.
    #
    #   A password under three characters is no longer caught. A password made
    #   only of letters IS still caught; an earlier version of this rule refused
    #   those to buy precision and it cost `password: peanuts`, which is a real
    #   shape, so that exclusion was taken out again.
    #
    # NO (?i) AND NO \b ANYWHERE, and that is not a style choice. Both mean
    # different things in Python and in V8 without /u: Python's \b is
    # Unicode-aware and Python's re.I casefolds U+017F to s, so the old rule
    # refused `pa<U+017F>sword: hunter2` here and published it at the endpoint,
    # which is the unsafe direction. Every letter is spelled as a class so the
    # three copies of this rule mean one thing in both engines.
    #
    # THE LONG S IS SPELLED OUT RATHER THAN LEFT TO AGREE ON A MISS, and be
    # precise about which problem that solves. The parity story belongs to the
    # rule this replaces: that one carried re.I, Python folded U+017F to s, V8
    # without /u did not, so `pa<U+017F>sword: hunter2` was refused here and
    # published at the endpoint. THIS rule carries no re.I in either engine, so
    # the two already agree on it. They agree on publishing it. A divergence
    # closed by both sides missing is still a leak, so [Ss<U+017F>] here is a
    # RECALL widening and not a parity repair, and calling it a parity repair
    # was wrong in an earlier draft of this comment. Cost: measured over
    # 119,837 third-party files, +0 files and +0 occurrences, because no
    # ordinary text writes a long s.
    #
    # THE WHOLE FOLD SET, ENUMERATED RATHER THAN REASONED ABOUT. Over all
    # 1,114,112 codepoints, FOUR fold to an ASCII letter under Python's re.I,
    # reaching three letters:
    #
    #     s <- U+017F LATIN SMALL LETTER LONG S
    #     k <- U+212A KELVIN SIGN
    #     i <- U+0130 LATIN CAPITAL LETTER I WITH DOT ABOVE
    #     i <- U+0131 LATIN SMALL LETTER DOTLESS I
    #
    # An earlier version of this comment said "exactly two", having enumerated
    # as far as the two it already knew about and then stated the result as a
    # sweep. The conclusion survives the correction: p-a-s-s-w-o-r-d contains no
    # i and no k, so the long s is the only fold that can reach this rule, and
    # spelling it out makes this rule complete.
    #
    # V8 SPLITS FROM PYTHON ON ALL FOUR, WHICH IS WHY EVERY CLASS HERE IS SPELLED
    # OUT. Under bare /i, V8 folds NONE of them. Under /iu it folds U+017F and
    # U+212A and still not U+0130 or U+0131, so /u is not the repair it looks
    # like. Python re.I folds all four. Carrying no case flag and writing every
    # letter as a class is therefore the only spelling under which the two
    # engines cannot disagree. Do not fold these classes back to (?i) to shorten
    # the pattern; it would reintroduce a divergence in the unsafe direction.
    #
    # THE SAME GAP SAT ONE RULE DOWN UNTIL the change of 2026-09-04. CREDENTIAL_ASSIGN
    # spelled neither U+017F nor U+212A while carrying s in `secret` and
    # `passphrase` and k in `key` and `token`, so four of its keywords missed
    # under a homoglyph, byte-identically in both engines, which is the shape no
    # cross-engine comparison can see. Its classes now spell the long s and the
    # Kelvin sign the same way this rule does. Measured over 120,248 files from
    # the same four caches: the old and new rule match identical strings in
    # identical files (652 files, 1,891 hits, zero differing), because no
    # ordinary text writes either character. Landed in all three copies together
    # (this file, scripts/preflight.py, the upload endpoint's validator), after the change of 2026-09-04
    # merged, closing the window where the two engines could disagree.
    #
    # The change of 2026-09-09 CLOSED THE SAME GAP FOR THE OTHER TWO ASCII-REACHING
    # FOLDS. Two more codepoints fold to ASCII under Python's re.I: U+0130
    # (LATIN CAPITAL LETTER I WITH DOT ABOVE) and U+0131 (LATIN SMALL LETTER
    # DOTLESS I) both fold to `i`. This rule spelled `i` as a bare `[Ii]` in
    # `authorization` (both i's), `credential` and `api_key`, so
    # `authorızation:`, `credentıal:` and `authorİzation:` all released a
    # credential that both this rule and preflight's copy agreed they had never
    # seen, for the same reason the change of 2026-09-04 did: byte-identical patterns in both
    # engines cannot disagree on a codepoint neither one folds.
    #
    # WHICH SIDE EACH CHARACTER GOES ON, because the two sides fail in opposite
    # directions and this is the reasoning both the change of 2026-09-04 and the change of 2026-09-09 apply. A
    # homoglyph widening a TRIGGER widens what the rule refuses: get it wrong
    # and you refuse something benign, which the owner sees and can undo. A
    # homoglyph widening an EXCLUSION widens what the rule releases: get it
    # wrong and a credential publishes, silently. So `[Iiİı]` only replaces
    # `[Ii]` at TRIGGER positions -- both i's in `authorization`, the i in
    # `credential`, and the i in `api_key`. The `[Ii]` inside `idempotency`,
    # `insert` and `foreign` are EXCLUSIONS, spelled ASCII-only on purpose:
    # `ıdempotency_key: <20 chars>` is now REFUSED where ASCII
    # `idempotency_key: <20 chars>` is released, because the exclusion cannot
    # see the homoglyph and the trigger can. Nobody writes that; if somebody
    # does, they get a refusal they can read, not a leak they cannot.
    #
    # THE NEWLINE BRANCH IS INERT IN THIS FILE and is kept anyway. The named
    # rules here run per line, so nothing in scrub.py can ever span one; the two
    # gates downstream scan the whole body and do use it. It stays character for
    # character in step with them because the harness that compares the three
    # copies compares their SOURCE, not their behaviour.
    #
    # WHAT THE VALUE CLASS MUST NOT DO, learned the expensive way. An earlier
    # version of this rule counted the value's first three characters with a
    # class that excluded ! $ ` , ; and the closing brackets, on the theory that
    # those end a value. They do not: they are punctuation, which is what a
    # strong password is MADE of. DB_PASSWORD=Tr!ckyP4ss, =!QAZ2wsx9,
    # =$ecurePass1 and =a`b3cdefgh were all missed, two of them regressions
    # against the rule this replaces, and nothing else in this file caught them.
    # The length check now counts anything that is not whitespace and not a
    # quote. One consequence is accepted: a password whose first three
    # characters contain a double quote is still missed, because the quote is
    # the delimiter and nothing here can tell the two apart.
    #
    # The QUOTE positions carry a backtick as well as ' and ", because JS and
    # shell both quote with one, and a password assignment whose value is
    # wrapped in backticks was published by every earlier version of this rule.
    # The backtick is deliberately NOT in the value's own exclusion class: the
    # fourth example above has one inside the password and is still caught.
    # Cost of adding it, over the same corpus: +0 files and +2 occurrences.
    #
    # The shell-variable exclusion is bounded to ${...} and $UPPER_NAME for the
    # same reason. $ecurePass1 is a password and the unbounded form read it as a
    # variable.
    #
    # MEASURED BEFORE LANDING, over 119,837 third-party files: the old rule
    # fires in 430 of them, 0.359%, and this one in 477, 0.398%. This rule is a
    # strict superset of the old one, so that difference is exact: 47 files it
    # refuses that the old rule released, all of them benign code, sampled and
    # listed in the project's records.
    #
    # THE COST GOES THE OTHER WAY TOO, AND THE VECTOR FILE SAYS SO. Over
    # the test suite's secret probes, 38 of 38 real password shapes are caught
    # where the old rule caught 18, and 0 of 21 ordinary strings are refused by
    # either rule. Seven further strings are ordinary content that BOTH rules
    # refuse: a structural opener, a schema declaration, an empty value, an
    # already-redacted value, a whole-value dummy, a seven-digit number, a
    # strict-equality comparison. They are not a regression, they are what has
    # shipped all along, and they are pinned in that file's third group so a
    # change that starts or stops refusing one fails the suite. The loudest of
    # them: a file somebody redacted by hand is still refused.
    #
    # KNOW WHAT THAT CORPUS IS BEFORE YOU LEAN ON IT. 96% of those files are
    # published npm packages under node_modules, and 83% are .js or .ts library
    # code. Thirty-two of them are configuration files of the kind that actually
    # carries a password. So the corpus is strong evidence about false positives
    # on code, which is what a passport mostly contains, and weak evidence about
    # false negatives on secrets, because it is close to free of live secrets by
    # construction. The false-negative side was checked a different way: every
    # occurrence the old rule catches and this one does not was classified, and
    # the residue inspected string by string.
    #
    # The corpus, the classification and the command that rebuilds both, so the
    # numbers can be re-run rather than believed, are written up in the
    # project's own records; this file travels to strangers, so it does not cite
    # a path they cannot open.
    #
    # THREE CHANGES OF 2026-09-05. First: pwd's optional prefix no longer
    # needs to end in a separator, so `dbpwd`, `DBpwd` and their casings now
    # match like `password`/`passwd` always did; pass's glued-prefix class is
    # now [A-Za-z0-9] rather than lowercase-only, so `DBpass`/`DBPass`/`DBPASS`
    # now match. The bare `pass` form (no prefix at all) is deliberately still
    # unmatched: it is an ordinary English word and a test status, and
    # widening it needs its own corpus measurement first.
    #
    # Second: password/passwd/pwd now match on ANY prefix with NO value-side
    # exclusion, folding what used to be a separate bare-keyword-only arm into
    # this one. Closes a hole where a PREFIXED key (db_password, DB_PASSWORD)
    # followed by a bracket-leading value released the whole rule set, because
    # the bracket exclusion below only ever backstopped the bare keyword.
    # Giving this arm the weak arm's FULL guarded operator was tried and
    # reverted before landing: it broke every value starting with `~`, `=`,
    # `>` or `:` (`PWD=~gy...`), which the test suite's password-rule baseline
    # exists to catch. Fifteen must_not_fire fixtures moved to
    # known_false_positives as the accepted twin of an already-accepted bare
    # false positive; eleven of the same shapes also came out of
    # the test suite's false-positive corpus, which asserts a no-op and can no
    # longer assert one on them.
    #
    # Third: value reads to the end of the physical line on both arms,
    # `\S+(?:[^\S\n]+\S+)*`, not just the first word, so a space-separated
    # passphrase is not redacted one word deep.
    #
    # Same 120,248-file, four-cache corpus used elsewhere in this file: 477
    # files fired before this trio, 564 after, all explained by the second change's
    # twins reaching real files. Zero regressions ON THAT CORPUS, verified by
    # full file-level diff, not by occurrence count alone.
    #
    # The change of 2026-09-09. CREDENTIAL_ASSIGN carried the identical
    # `(?:[ \t]+\S+)*` shape (copied from this rule, the change of 2026-09-09) and a critic
    # found it leaked past any separator `\S` excludes that `[ \t]` does
    # not: NBSP (U+00A0), EN SPACE, IDEOGRAPHIC SPACE, VERTICAL TAB, FORM
    # FEED, LINE SEPARATOR (U+2028), a bare CR with no LF. Confirmed the
    # identical leak here, independent of that branch:
    # `password: <14 chars>\xa0battery\xa0staple\xa0horse` released the
    # tail past the NBSP exactly as it did for CREDENTIAL_ASSIGN. Fixed the
    # same way: `[ \t]` widened to `[^\S\n]`, "whitespace but not newline"
    # -- `\S` (the token class) already excluded every whitespace variant,
    # the separator was simply too narrow to cross the same characters.
    # Confirmed the newline boundary itself still holds (an actual `\n`
    # still stops the match, text on the next line survives).
    #
    # UNLIKE CREDENTIAL_ASSIGN, this rule's value has no character-class
    # gate before the tail -- CREDENTIAL_ASSIGN's `{20,}["']?` stops at a
    # closing quote before its own tail extension begins, which is why
    # widening ITS separator alone restored JSON-sibling safety.
    # PASSWORD_ASSIGN's `\S+` has no such gate and never did: it already
    # swallowed a JSON sibling on the far side of any space, on main,
    # before this fix (confirmed against the version before it) -- an accepted 2026-09-05
    # trade for this rule specifically, unrelated to and unchanged by this
    # fix. This fix closes the whitespace-separator leak; it does not
    # change, and was not meant to change, that pre-existing trade.
    #
    # A sweep of this file for the vulnerable `(?:[ \t]+\S+)*` shape, both
    # backslash-escaping styles this file uses (`r"..."` raw strings
    # elsewhere spell it with one backslash, this rule's plain `'...'`
    # strings spell it with two), found exactly these two occurrences and
    # nothing else: CREDENTIAL_ASSIGN (on the branch that introduced its
    # tail) and this rule's two arms. No third rule in this file carries
    # the shape.
    #
    # REORDERED within this same commit so the backstop (any-prefix
    # password/passwd/pwd, no value exclusion) is the FINAL alternation
    # branch, where the main_arm of the test suite's password-rule baseline
    # now freezes it: that is the arm this work over-guarded once already (the
    # `PWD=~gy...` regression above) before catching it, so it is the arm
    # worth a structural, corpus-independent tripwire against a future
    # re-narrowing, the same protection the old bare-keyword arm had at the
    # tail before the change of 2026-09-05 widened it. Verified behaviourally identical to the
    # unreordered form across the full fixture corpus, 8,000 generated
    # combinations, and all 120,248 real corpus files: zero differing matches.
    ("PASSWORD_ASSIGN", re.compile(
        # THIS RULE IS TWO RULES IN ONE, AND THE SECOND ARM IS NOT OPTIONAL.
        #
        # Everything from here to the first \S+ is the WEAK arm: `pass`, glued
        # or separated but never bare, gated by a digit-and-length lookahead,
        # then a FULLY guarded assignment operator and the full exclusion
        # chain below. `pass` alone is an ordinary English word and a test
        # status (`SHOULD_PASS`, `bypass`, `compass`), which is why it stays
        # behind every guard the arm after it no longer needs.
        #
        # After it is the STRONG (backstop) arm: `password`, `passwd` and
        # `pwd`, on any prefix at all -- glued, separated, or none -- with no
        # value-side exclusion whatsoever, reading to the end of the physical
        # line. It absorbs what used to be a separate bare-keyword-only arm,
        # and it is kept as the FINAL branch of this pattern for the same
        # reason that older arm was: the test suite's password-rule baseline
        # freezes this exact text as the tail of the shipped pattern
        # (main_arm), so an insertion into it -- an operator guard, a value
        # exclusion, anything -- fails the suite by string comparison alone,
        # independent of any corpus. An empty prefix is one case of "any
        # prefix", so the old bare-only arm is gone; this one subsumes it.
        #
        # Its operator keeps the quote handling the shared operator above has
        # -- `password": "value"` and `password\': \'value\'` still work --
        # but drops that operator\'s `(?![=>~:])` guard. Giving it the FULL
        # guarded operator was tried and reverted: values starting with `~`,
        # `=`, `>` or `:` stopped matching (`PWD=~gy...`), which
        # the test suite's password-rule baseline exists to catch, because every
        # value-side exclusion elsewhere in this file is safe only because
        # this arm backstops it unconditionally.
        '(?:'
        # Left boundary. Same reasoning as CREDENTIAL_ASSIGN below: without it
        # the leading [A-Za-z0-9_.\-]* restarts at every position of a long
        # identifier run and the rule goes quadratic on input carrying no
        # password at all.
        '(?<![A-Za-z0-9_.\\-])'
        '(?:'
        # Weak: pass, after a separator or a glued letter/digit (either case),
        # and only in front of a value with eight or more characters and a
        # digit somewhere in them. Never bare; see the note above this entry.
        '(?:[A-Za-z0-9_.\\-]*[_\\-.][Pp][Aa][Ssſ][Ssſ]|[A-Za-z0-9_.\\-]*[A-Za-z0-9][Pp][Aa][Ssſ][Ssſ])(?![A-Za-z])'
        '(?=[\\"\'`]?[ \\t]*(?:\\r?\\n[ \\t]*)*[:=](?![=>~:])[ \\t]*(?:\\r?\\n[ \\t]*)*[\\"\'`]?(?=[^\\s\\"\']{8})(?=[^\\s\\"\']{0,256}[0-9]))'
        # The assignment: [ \t] rather than \s, with one optional line break
        # spelled out, so "spans a newline" is a thing this rule says rather
        # than a thing \s does by accident. (?![=>~:]) keeps it off ===, =>,
        # := and the :: of a CSS selector -- safe here because `pass` is
        # already behind a digit gate and a full exclusion chain, unlike the
        # backstop arm's bare keyword below, which must stay wide open.
        '[\\"\'`]?[ \\t]*(?:\\r?\\n[ \\t]*)*[:=](?![=>~:])[ \\t]*(?:\\r?\\n[ \\t]*)*[\\"\'`]?'
        # The value must not itself start with a quote. Without this the engine
        # backtracks the optional quote above to nothing, takes the quote as the
        # first character of the value, and walks straight past every exclusion
        # below. That one lookahead is what makes the rest of them load bearing.
        '(?![\\"\'`])'
        '(?=[^\\s\\"\']{3})'
        '(?![\\[{(<>/\\]])'
        '(?!(?:[Tt]rue|TRUE|[Ff]alse|FALSE|[Nn]ull|NULL|[Nn]il|None|undefined|void)(?![A-Za-z0-9_]))'
        # THE DOTTED-IDENTIFIER EXCLUSION, AND THE THIRD TRADE IT MAKES.
        #
        # It is here to release `password: os.environ.get` and `pwd: config.db.pass`,
        # which are code references rather than values, and it does that well.
        #
        # It also releases any password that happens to LOOK like a dotted
        # identifier, and that is a real loss, not a theoretical one. Verified,
        # the old bare rule catches all three and this releases all three:
        #
        #     a password assignment whose value is `hunter2` dot `local`
        #     one whose value is three lowercase words joined by dots and ending
        #       in four digits
        #     one whose value is a single letter, a dot, and a single letter
        #
        # An env-var-style assignment whose value is two capitalised leetspeak
        # words joined by a dot is caught by NEITHER rule, which is the sharper
        # version: it is exactly the shape this rule was widened to catch, and a
        # single dot in the value is enough to put it back out of reach.
        #
        # The examples are described rather than written out because a literal
        # one trips this repository's own leak gate on the way in, which is the
        # rule working correctly on the comment that documents it.
        #
        # The escape hatch is narrow and worth knowing: the exclusion needs every
        # segment to start with a letter or underscore, so `password:
        # Correct.Horse.9` IS still caught, because `9` cannot open an identifier.
        #
        # Kept because a passport describing an agent carries far more dotted code
        # references than dotted passwords, and a gate that refuses
        # `os.environ.get` on every capture is a gate people route around. That is
        # a judgement about which error is cheaper, not a measurement, and it is
        # the third of this rule's three disclosed trades. The change of 2026-09-05
        # narrows its reach to the WEAK `pass` arm only; a prefixed
        # `password`/`passwd`/`pwd` no longer has any value-side exclusion at all.
        '(?!(?:[A-Za-z_][A-Za-z0-9_]*\\.)+[A-Za-z_][A-Za-z0-9_]*(?![A-Za-z0-9_.]))'
        '(?![A-Za-z_][A-Za-z0-9_]*[ \\t]*\\()'
        '(?!\\$\\{)'
        '(?!\\$[A-Z_][A-Z0-9_]*(?![A-Za-z0-9_]))'
        '(?!(?:[Yy][Oo][Uu][Rr]|[Mm][Yy]|[Ii][Nn][Ss][Ee][Rr][Tt]|[Rr][Ee][Pp][Ll][Aa][Cc][Ee]|[Ee][Xx][Aa][Mm][Pp][Ll][Ee]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Cc][Hh][Aa][Nn][Gg][Ee][Mm][Ee]|[Ss][Aa][Mm][Pp][Ll][Ee]|[Dd][Uu][Mm][Mm][Yy]|[Pp][Aa][Ss][Tt][Ee]|[Tt][Oo][Dd][Oo]|[Xx][Xx][Xx])[A-Za-z\\-]*(?![A-Za-z0-9_\\-+/=~.]))'
        # The change of 2026-09-05: weak arm only, same reason as the exclusion above.
        '(?![0-9]{1,7}(?![A-Za-z0-9_.\\-]))'
        # THE PLACEHOLDER VOCABULARY, AND THE TAIL THAT MADE IT WRONG.
        #
        # Inherited from CREDENTIAL_ASSIGN, where it is right: `your-api-key`
        # and `changeme` really are placeholders, and a token that starts with
        # one is documentation.
        #
        # The tail after the word is the whole argument. It used to be
        # [A-Za-z0-9_\-]*, which runs over digits, so ANY value whose first
        # syllable happened to be a placeholder word was released however real
        # the rest of it was. Somebody's dog's name and a birth year is a
        # placeholder by that reading. So is a capitalised English word that
        # starts with the letters of `todo`. So is a real password with `xxx`
        # written round it, which people do.
        #
        # The tail is [A-Za-z\-]* now: a placeholder word counts when the value
        # is WORDS. `your-password-here`, `changeme` and `dummy` are still
        # released, which is the case this guard exists for, and a value that
        # glues a placeholder word to entropy is not.
        #
        # This was a false-negative bug, not a trade. It was found by a critic
        # asked to refute the claim that the guards could not be separated, and
        # it had been written into the comment here as an accepted cost by the
        # same author who wrote the guard. An accepted cost that nobody tried to
        # remove is a defect with a note on it.
        #
        # Cost of the repair, measured over 119,837 third-party files: +4 files
        # and +4 occurrences, one distinct string, a dummy value in a fixture.
        # The change of 2026-09-05: weak arm only, same reason as the exclusion above.
        '(?![\\^~>=<]*[0-9]+\\.[0-9]+)'
        # Bounded to seven digits. Unbounded, this read every numeric password
        # as a port number: an eight-or-more-digit PIN is a password, and a
        # port, a timeout and a five-digit id are not. Same defect class as the
        # vocabulary tail above and found in the same pass. The change of 2026-09-05: weak arm
        # only; a prefixed `password: 1234567` is now the backstop arm's
        # business and its accepted cost, tracked in known_false_positives.
        #
        # The 2026-09-09 change, second pass (2026-09-10): a repetition cap ({0,20}) shipped
        # here and was reverted the same day. It does not touch the reachable
        # bug (a whitespace-free document dies in the UNCAPPED first \S+,
        # confirmed byte-identical with and without the cap), it barely helps
        # the degenerate-separator case (20 of 160 unrelated words survived a
        # dense-trigger CR-only document in testing), and it opens a leak that
        # does not exist on the unbounded tail: an ORDINARY document, real
        # `\n` on both sides, a genuine passphrase longer than the cap, prints
        # everything past word 21 in clear -- confirmed directly, a 30-word
        # real passphrase leaked words 22-30. Three further attempts at a
        # value-side gate (a length bound, a quote-excluding class with a
        # lookahead, a real matching-quote backreference gated on the key
        # also being quoted) were each built, tested, and refuted by a
        # critic: the length bound and the lookahead both leak password
        # punctuation HIGH_ENTROPY's alphabet does not cover; the
        # backreference design leaks well-formed YAML (its doubled-apostrophe
        # escaping collides with JSON/Python's backslash escaping in one
        # alternation) AND is exponentially slow on backslash-bearing content
        # with no closing quote on the line.
        # Left unbounded: over-destructive on the degenerate case, never
        # leaks the secret itself, which is the side of this file's own
        # false-positive/false-negative asymmetry it asks for. A safe
        # value-side gate needs a real per-format parser, not a regex, and
        # that is out of scope for this pass.
        #
        # The change of 2026-09-17: `[^\S\n]` shared CREDENTIAL_ASSIGN's line-model
        # disagreement with `text.split("\n")` on a CR/U+2028-only document
        # -- fixed the same way, naming the separator instead of defining it
        # by what `\S` excludes. See the full writeup beside CREDENTIAL_
        # ASSIGN's copy of this tail below rather than repeating it at both
        # arms; this arm's class is identical to that one.
        '\\S+(?:[\\t \\xa0\\u1680\\u2000-\\u200a\\u202f\\u205f\\u3000]+\\S+)*'
        # Strong/backstop: any prefix, then password / passwd / pwd, no
        # separator requirement anywhere, no value-side exclusion, value to
        # end of line. THIS is main_arm in the test suite's password-rule baseline
        # -- it must stay the exact, unbroken final branch of this pattern.
        '|'
        '[A-Za-z0-9_.\\-]*(?:[Pp][Aa][Ssſ][Ssſ][Ww][Oo][Rr][Dd]|[Pp][Aa][Ssſ][Ssſ][Ww][Dd]|[Pp][Ww][Dd])[Ssſ]?(?![A-Za-z])'
        # Quote handling, no (?![=>~:]) guard: see the note above this entry
        # for why the guard broke a value starting with ~, =, > or :.
        #
        # \s* ON BOTH SIDES, NOT [ \t]*(?:\r?\n[ \t]*)*, AND THIS IS NOT
        # COSMETIC. A critic caught this arm shipping with the WEAK arm's
        # explicit space/tab/CRLF-only spelling instead of the old bare arm's
        # bare `\s*`, which quietly dropped 25 codepoints this arm always
        # covered: NBSP, the other Unicode spaces (U+2000-200A, U+202F,
        # U+205F, U+1680, U+3000), U+2028/U+2029, bare CR, VT, FF and
        # U+001C-001F. `password:<NBSP>Tr0ub4dor&3` -- what you get pasting a
        # config line out of Word, Notion, Confluence or a rendered web page
        # -- was refused before this rule existed and passed straight through
        # while it shipped, in all three engines, because parity compares
        # regex SOURCE and both copies had made the identical mistake. Caught
        # by corpus fuzzing, not by the corpus itself: 120,248 real files are
        # npm tarballs and node_modules, which structurally cannot contain
        # these characters next to this keyword, so the corpus reported clean
        # while the rule was open. `\s*` restores exactly what the old
        # pre-union bare-keyword arm had, on the arm that inherited its job.
        '[\\"\'`]?\\s*[:=]\\s*[\\"\'`]?'
        # The change of 2026-09-05: reads to the end of the physical line rather
        # than stopping at the first space, so a space-separated passphrase is
        # not redacted one word deep, leaving the rest of it exposed. Same fix
        # as the weak arm's copy above.
        #
        # The change of 2026-09-09: the separator was `[ \t]`, deliberately not
        # bare `\s`, because `\s` would cross a real `\n` and merge two
        # separate lines' worth of text into one reported match -- that
        # reasoning is still correct, but `[ \t]` was narrower than it
        # needed to be to get it: it also excluded NBSP, EN SPACE, VERTICAL
        # TAB, FORM FEED, U+2028 and a bare CR, none of which end a line as
        # this codebase defines one (`text.split("\n")`), so a passphrase
        # separated by any of those leaked past this rule too. `[^\S\n]`
        # keeps the ONE exclusion that matters (`\n` itself) and drops the
        # rest: same protection against merging lines, none of the
        # incidental gaps. See CREDENTIAL_ASSIGN's copy of this same fix
        # for the fuller writeup and the JSON-safety property this rule
        # does not share with it (this value has no character-class gate
        # before the tail, so it already swallowed a same-line sibling
        # past any space, on main, before this fix -- unrelated,
        # unchanged, an accepted 2026-09-05 trade for this rule specifically).
        #
        # The 2026-09-09 change, second pass (2026-09-10): a repetition cap was tried and
        # reverted here too. See the weak arm's copy of this tail above for
        # the full writeup: it does not fix the reachable whitespace-free
        # case, barely helps the degenerate-separator case, and opens a new
        # leak on an ordinary long real passphrase that the unbounded tail
        # does not have. Left unbounded on purpose.
        #
        # The change of 2026-09-17: `[^\S\n]` turned out to be exactly as wrong
        # here as it was for CREDENTIAL_ASSIGN, for the identical reason --
        # it crosses CR and U+2028/U+2029, which a real document can use as
        # its own line ending, so a CR-only or U+2028-only document had
        # everything after the first `password:`/`pass:` line deleted
        # rather than redacted. Fixed the same way: named separator class,
        # not a `\S`-derived one. See CREDENTIAL_ASSIGN's copy of this tail
        # for the full writeup; this arm's class is identical to that one.
        '\\S+(?:[\\t \\xa0\\u1680\\u2000-\\u200a\\u202f\\u205f\\u3000]+\\S+)*'
        ')'
        # THERE IS DELIBERATELY NO EXCLUSION FOR A VALUE NAMED LIKE A PASSWORD,
        # and it was written and then taken out again rather than never tried.
        # An identifier ending in the trigger word is usually a reference rather
        # than a value: ADD_PASSWORD: "add_password", certPassword:
        # certificatePassword. Excluding those cost 46 files of the 119,708, but
        # it also refused correct-horse-password, correct_horse_password and
        # CorrectHorsePassword, which are passwords, and it silenced the
        # fixture's own second plant. A test that has to be edited to fit a new
        # rule is the test telling you about the rule.
        #
        # The change of 2026-09-05: reads to the end of the physical line rather
        # than stopping at the first space, so a space-separated passphrase is
        # not redacted one word deep, leaving the rest of it exposed. Both arms
        # carry this fix.
        ')'
    )),
    # SendGrid. Named rather than left to CREDENTIAL_ASSIGN because its value is
    # three dot-separated segments, which is the exact shape CREDENTIAL_ASSIGN
    # now refuses in order to stop matching ordinary code like
    # forge.random.getBytesSync. A vendor whose format collides with the generic
    # exclusion gets a named rule; that is what the named rules are for.
    ("SENDGRID_KEY", re.compile(r"(?<![A-Za-z0-9])SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}(?![A-Za-z0-9])")),
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
        r"[A-Za-z0-9_.\-]*(?:[Aa][Uu][Tt][Hh][Oo][Rr][Iiİı][Zz][Aa][Tt][Iiİı][Oo][Nn]"
        r"|[Tt][Oo][KkK][Ee][Nn]|[Ssſ][Ee][Cc][Rr][Ee][Tt]|[Aa][Uu][Tt][Hh]"
        r"|[Cc][Rr][Ee][Dd][Ee][Nn][Tt][Iiİı][Aa][Ll]|[Pp][Aa][Ssſ][Ssſ][Pp][Hh][Rr][Aa][Ssſ][Ee])[Ssſ]?"
        r"|[A-Za-z0-9_.\-]*[Aa][Pp][Iiİı][_\-]?[KkK][Ee][Yy][Ssſ]?"
        r"|[A-Za-z0-9_.\-]*[a-z0-9][KK]ey[Ssſ]?"
        r"|(?!(?:[Cc][Aa][Cc][Hh][Ee]|[Ss][Oo][Rr][Tt]|[Pp][Aa][Rr][Tt][Ii][Tt][Ii][Oo][Nn]"
        r"|[Ii][Dd][Ee][Mm][Pp][Oo][Tt][Ee][Nn][Cc][Yy]|[Ff][Oo][Rr][Ee][Ii][Gg][Nn])"
        r"[_\-.][KkK][Ee][Yy][Ssſ]?(?![A-Za-z0-9_.\-]))[A-Za-z0-9_.\-]*[_\-.][KkK][Ee][Yy][Ssſ]?"
        r")(?![A-Za-z])"
        r"[\"']?\s*[:=]\s*(?:Bearer\s+)?[\"']?"
        r"(?!(?![A-Za-z0-9_.]*?(?<![A-Za-z0-9_])(?=[A-Za-z0-9_]*[0-9])[A-Za-z0-9_]{16,})(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*(?![A-Za-z0-9_\-+/=~.]))"
        r"(?!(?:[Yy][Oo][Uu][Rr]|[Mm][Yy]|[Ii][Nn][Ss][Ee][Rr][Tt]|[Rr][Ee][Pp][Ll][Aa][Cc][Ee]"
        r"|[Ee][Xx][Aa][Mm][Pp][Ll][Ee]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]"
        r"|[Cc][Hh][Aa][Nn][Gg][Ee][Mm][Ee]|[Ss][Aa][Mm][Pp][Ll][Ee]|[Dd][Uu][Mm][Mm][Yy]"
        r"|[Pp][Aa][Ss][Tt][Ee]|[Tt][Oo][Dd][Oo]|[Xx][Xx][Xx])[A-Za-z0-9_\-]*(?![A-Za-z0-9_\-+/=~.]))"
        r"(?![A-Za-z0-9_\-+/=~.]{0,128}[_\-]?[Hh][Ee][Rr][Ee](?![A-Za-z0-9_\-+/=~.]))"
        r"(?![A-Za-z0-9_\-+/=~.]{0,128}/[A-Za-z0-9_\-+/=~.]{0,128}\.[A-Za-z]{2,5}(?![A-Za-z0-9_\-+/=~.]))"
        # The change of 2026-09-09. Everything above this line is the TRIGGER: the
        # keyword, the operator, and every exclusion lookahead that decides
        # WHETHER this rule fires, all unchanged from before this fix. What
        # changes is only how much gets swallowed once it has already fired.
        # The value still has to open with 20+ characters from the strict
        # charset -- that gate is what makes this rule fire on a
        # token-shaped value and not on an ordinary sentence following the
        # keyword, and it is unchanged.
        #
        # FIRST ATTEMPT, `(?:[ \t]+\S+)*`, copied the change of 2026-09-05's PASSWORD_ASSIGN
        # shape and a critic broke it in review before this landed: `\S`
        # excludes every Unicode whitespace character, not just [ \t\n], so
        # a separator of NBSP (U+00A0), EN SPACE (U+2002), IDEOGRAPHIC SPACE
        # (U+3000), VERTICAL TAB, FORM FEED, LINE SEPARATOR (U+2028), or a
        # bare CR with no LF all stopped the repetition dead, and everything
        # after the first such separator leaked in the clear:
        # `passphrase: A1b2C3d4E5f6G7h8I9j0\xa0battery\xa0staple\xa0horse`
        # scrubbed only the first token. scrub()'s own line splitting is
        # `text.split("\n")` (see scrub()'s caller below) -- the only
        # character that actually ends a "line" as this codebase defines
        # one is `\n` itself, so a separator class built from `\s`/`\S`
        # excludes far more than the caller does, and every one of those
        # exclusions was a gap an attacker could place a real secret behind.
        #
        # SECOND ATTEMPT, `[^\n]*`, matched scrub()'s own line boundary
        # exactly but went too far the other way: it swallows unconditionally
        # from the moment the gate fires to the next `\n`, no matter what is
        # there, so a one-line JSON blob like
        # `{"api_key": "abcdefghijklmnopqrst", "endpoint": "...", "region": "..."}`
        # lost its endpoint and region -- functional-spec content a recipient
        # needs -- where the first attempt's `(?:[ \t]+\S+)*` had correctly
        # stopped at the closing quote (no space precedes the comma, so the
        # repetition never fires). A critic caught this as a real regression
        # against the shipped commit, not a hypothetical.
        #
        # THIRD ATTEMPT AND WHAT SHIPPED: keep the token-repetition SHAPE
        # (separator, then a non-whitespace run, repeated), which is what
        # gives the JSON case its natural stopping point -- but widen the
        # SEPARATOR class from `[ \t]` to `[^\S\n]`, "whitespace but not
        # newline". `\S` already excludes every `\s` character, so token
        # boundaries (`\S+`) were never the problem; the separator was too
        # narrow to cross the same characters `\S` was already refusing to
        # swallow inside a token. `[^\S\n]` accepts every character Python's
        # `\s` calls whitespace except `\n` itself -- NBSP, EN SPACE,
        # IDEOGRAPHIC SPACE, VERTICAL TAB, FORM FEED, LINE SEPARATOR (U+2028)
        # and a bare CR all cross it now, closing the same leak the first
        # attempt had, while an ordinary space-then-non-whitespace boundary
        # (a comma right after a closing quote, with nothing separating them)
        # still ends the match exactly where it always did, restoring the
        # JSON case the second attempt broke. Only `\n` itself, scrub()'s own
        # line boundary (`text.split("\n")`, see scrub()'s caller below),
        # still stops the repetition outright. PASSWORD_ASSIGN's two arms
        # carried the identical vulnerable `(?:[ \t]+\S+)*` shape, independently
        # confirmed reproducible on main -- fixed alongside this rule on
        # A reconciliation on 2026-09-16, merging the homoglyph fix of
        # 2026-09-09 with the separator-leak fix of the same day,
        # rather than leaving PASSWORD_ASSIGN's copy
        # out of scope; see both arms' own tails below in this file for the
        # same separator widening.
        #
        # The 2026-09-09 change, second pass (2026-09-10): a repetition cap ({0,20}) shipped
        # here and was reverted the same day, same reasoning as
        # PASSWORD_ASSIGN's copy of this tail (scripts/scrub.py, weak arm): it
        # does not touch this rule's already-gated base value, barely helps
        # the degenerate-separator case, and opens a leak the unbounded tail
        # does not have -- an ordinary document, real newlines, a credential
        # value described across more words than the cap allows prints
        # everything past the cut in clear. Left unbounded on purpose.
        #
        # `[^\S\n]` IS ENGINE-RELATIVE, NOT ONE FIXED SET
        # (2026-09-16, reviewing this reconciliation). Measured directly, every
        # codepoint below U+3000: Python's `[^\S\n]` crosses 27 characters,
        # JS's crosses 22 -- Python additionally crosses 0x1c, 0x1d, 0x1e,
        # 0x1f (the C0 "information separator" controls) and U+0085 (NEL),
        # which JS's `\s` does not treat as whitespace. That divergence is
        # moot now: this rule no longer uses `[^\S\n]` (see FOURTH ATTEMPT
        # below), and the upload endpoint's validator's copy of this tail is unchanged
        # -- it only decides accept/refuse, never substitutes text, so an
        # engine difference there still has no observable effect. A future
        # JS-side redaction path reusing that pattern would need this same
        # fix applied on that side first, not assumed safe because the
        # source text used to match.
        #
        # FOURTH ATTEMPT AND WHAT SHIPS NOW (2026-09-17, the review's
        # ruling on the reconciliation's own regression): THIRD ATTEMPT's
        # `[^\S\n]` crossed six characters that are not `\n` but that a real
        # document can still use AS its own line ending -- CR, VERTICAL TAB,
        # FORM FEED, U+0085 NEL, LINE SEPARATOR (U+2028) and PARAGRAPH
        # SEPARATOR (U+2029). scrub()'s own line model is `text.split("\n")` alone
        # (see scrub()'s caller below), so a document written with, say,
        # bare CR as its line break has no `\n` anywhere in it: scrub()
        # treats the whole document as ONE line, and THIRD ATTEMPT's
        # widened tail then matched from the first credential straight
        # through every CR to the end of the document, deleting every field
        # after it rather than redacting only the credential.
        # A cap on the repetition was tried for the identical shape of bug
        # twice already in this file (see the weak arm's copy of this tail,
        # and the change of 2026-09-09 second pass above) and reverted both times because it
        # trades an unbounded leak for a bounded one on an ordinary long
        # value; the same trade would not fix this either, since the
        # destruction runs through the FIRST occurrence of the separator,
        # not through a long repetition count.
        #
        # Fixed by naming the separator, not by continuing to define it as
        # what `\S` excludes: literal space and tab, plus the Unicode
        # "space separator" (Zs) characters an owner's editor or paste
        # source might realistically produce in place of an ordinary space
        # -- NBSP, the EN/EM/THIN/HAIR spaces (U+2000-U+200A), FIGURE
        # SPACE, NARROW NO-BREAK SPACE, MEDIUM MATHEMATICAL SPACE, OGHAM
        # SPACE MARK, IDEOGRAPHIC SPACE. Five of the six characters THIRD
        # ATTEMPT crossed that behave as a line or paragraph break somewhere
        # are excluded again, and stay excluded in practice: `\n`, CR,
        # VERTICAL TAB, FORM FEED, U+2028, U+2029. None of the four original
        # 2026-09-17 probes (NBSP separator on this rule and on PASSWORD_ASSIGN,
        # plus the two keyword homoglyphs, which this tail does not touch)
        # use a character this excludes, so narrowing to this class does not
        # reopen any of them -- confirmed by the test suite EXTENT
        # block, OVER_REDACTION block and VENDOR_PROBES, not just asserted
        # here.
        #
        # It does reopen a narrower version of the leak THIRD ATTEMPT closed:
        # a passphrase that uses a bare CR, VERTICAL TAB, FORM FEED or
        # U+2028/U+2029 AS its own internal word separator (rather than as
        # the document's line ending) has its tail past that character left
        # unredacted again, the same gap `[ \t]` originally had for NBSP.
        # Accepted on purpose, per the ruling: those characters are far
        # more likely, in a real captured document, to be somebody's line
        # ending than a mid-passphrase space, and redacting through a real
        # line ending destroys content (product rule 3, the losses table,
        # among it) rather than merely leaking a value further than it
        # should. This is the "genuine conflict" the ruling asked to have
        # reported rather than patched around, and this is that report.
        #
        # THE SIXTH CHARACTER, U+0085 NEL, IS NOT ACTUALLY EXCLUDED, AND
        # SAYING SO WAS WRONG (two critics independently found this the same
        # way against the first version of this comment, round 1,
        # 2026-09-17). Excluding `U+0085` from this class is dead code:
        # `_normalise_with_map`, below, rewrites every NEL to an ordinary
        # space BEFORE this pattern ever runs (`out.append(" " if ch ==
        # "\u0085" else ch)`), and scrub() matches against that normalised
        # line, not only the raw one. So by the time the tail-extension
        # regex sees the text, there is no NEL left to exclude -- only the
        # ordinary space this class is required to cross for the NBSP/
        # multi-word-passphrase case the 2026-09-17 change exists to fix. A NEL-only
        # document therefore still has everything after its first credential
        # line deleted, the identical failure mode CR/U+2028/U+2029 had,
        # confirmed reproducible: `"\x85".join([...same seven fields as the
        # OVER_REDACTION test below...])` loses six of seven fields, 311
        # bytes in to 69 out.
        #
        # THIS IS THE SAME SHAPE OF ACCEPTED MISS preflight.py's INVISIBLE
        # comment already names for a different rule ("THE ACCEPTED MISS,
        # stated plainly. U+0085 is mapped to a space rather than removed...
        # That is deliberate"): fixing it here would mean changing what NEL
        # normalises to, or how the three-pass union picks the broadest
        # span, in `_normalise_with_map`/scrub()'s shared matching loop --
        # used by every rule in PATTERNS, not only these two, and exactly
        # the line-model-at-its-root change the ruling put out of this
        # task's scope. Filed as an open issue rather than patched around. No
        # credential leaves the machine either way; the failure is content
        # destruction in a document shape (bare-NEL line endings) that is
        # rarer in practice than the CR/U+2028 shapes this branch does fix.
        #
        # A NARROW FIX WAS TRIED, SAME DAY, AND REVERTED (round 2,
        # 2026-09-17). The review refused the disposition above on the grounds that
        # this branch introduces the NEL regression (confirmed: origin/main
        # handles a NEL-only document correctly) rather than inheriting a
        # pre-existing one, and asked whether NEL could join the excluded
        # class the way CR/VT/FF/U+2028/U+2029 did. It looked like it could:
        # `_normalise_with_map` left unchanged to leave NEL as NEL, instead of
        # rewriting it to a space, closed the over-redaction case and passed
        # the full test suite. Two critics, spawned in parallel per the
        # gate-code tier, independently found the same blocking defect this
        # fix introduced: PASSWORD_ASSIGN's short-`pass` arm gates its
        # operator on a LITERAL `[ \t]` class, not `\s`, in nine positions,
        # and PRIVATE_KEY_BLOCK/PGP_BLOCK's header match does the same with
        # `[A-Z ]`. Both tolerated a NEL only because it used to be rewritten
        # to an ordinary space; left as NEL, the rule stops FIRING, not just
        # over-redacting. `db_pass<NEL>=Tr0ubador99x` went from
        # `[SCRUBBED:PASSWORD_ASSIGN]` to publishing the password unredacted
        # with an EMPTY findings report -- a credential written into the
        # owner's own passport in the clear while the scrub report says the
        # line was clean, exactly the failure mode this file's own module
        # docstring names as the one to prevent, and worse than the
        # over-redaction bug the fix closed. The test suite and
        # the cross-engine parity harness both passed on the leaking tree, because
        # every existing check compares REGEX PATTERN TEXT or SEPARATOR-CLASS
        # behaviour, and this defect lives entirely in a NORMALISATION step
        # neither instrument reads. Reverted (revert commits on this branch);
        # `_normalise_with_map` still rewrites NEL to a space. This is now the
        # evidence the review asked for if a narrow fix did not exist: it does not.
        # Closing this needs `_normalise_with_map` or scrub()'s three-pass
        # span union reconciled PER RULE against every literal (non-`\s`)
        # whitespace class in PATTERNS, not a single shared substitution
        # target -- still that open issue, still not fixed here.
        r"[A-Za-z0-9_\-+/=~.]{20,}[\"']?(?:[\t \xa0\u1680\u2000-\u200a\u202f\u205f\u3000]+\S+)*"
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
    # FOLLOW-UP OF 2026-09-22: the trailing/leading exclusion of `_` on
    # these six rules used to be the whole reason "OPENAI_sk-proj-<key>" (an
    # underscore-glued credential) passed both gates. Once the OTHER nine
    # prefix rules dropped `_` from their boundary to close that
    # hole, these six were the only ones left excluding it, so a Notion or
    # Hugging Face token wrapped in underscores (markdown italics, or glued
    # to a preceding identifier) still passed. The ruling: allow `_` on
    # both sides here too, same as every other prefix rule. Measured on the
    # 165-capture corpus (the method of the 2026-09-21
    # measurement): 0 changed rows. Three
    # existing must_not_fire probes flip to firing (moved to must_fire,
    # below): an hf_ token wrapped in a snake_case identifier on either
    # side, and `client_secret_<32+ chars>`, which is exactly a real OAuth
    # client secret glued into a variable name. `AWS_SECRET_ACCESS_KEY` and
    # `my_secret_token_value` do NOT flip: they were never protected by this
    # boundary, they are protected by the class itself having no `_` in it,
    # since neither has 32+ contiguous alnum characters after `secret_`.
    ("NOTION_TOKEN",
     re.compile(r"(?<![A-Za-z0-9])ntn_[A-Za-z0-9]{40,}(?![A-Za-z0-9])")),
    ("NOTION_LEGACY_TOKEN",
     re.compile(r"(?<![A-Za-z0-9])secret_[A-Za-z0-9]{32,}(?![A-Za-z0-9])")),
    ("STRIPE_KEY",
     re.compile(r"(?<![A-Za-z0-9])(?:sk|rk)_live_[A-Za-z0-9]{20,}(?![A-Za-z0-9])")),
    ("SLACK_WEBHOOK",
     re.compile(r"[Hh][Oo][Oo][Kk][Ss]\.[Ss][Ll][Aa][Cc][Kk]\.[Cc][Oo][Mm](?::[0-9]*)?/[Ss][Ee][Rr][Vv][Ii][Cc][Ee][Ss]/[Tt][A-Za-z0-9]+/[Bb][A-Za-z0-9]+/[A-Za-z0-9]{20,}")),
    ("HUGGINGFACE_TOKEN",
     re.compile(r"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{32,}(?![A-Za-z0-9])")),
    ("LINEAR_KEY",
     re.compile(r"(?<![A-Za-z0-9])lin_api_[A-Za-z0-9]{36,}(?![A-Za-z0-9])")),
    ("AIRTABLE_TOKEN",
     re.compile(r"(?<![A-Za-z0-9])pat[A-Za-z0-9]{14}\.[0-9a-f]{64}(?![A-Za-z0-9])")),
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


# The change of 2026-09-24 widened two rules: DB_URL takes an empty username (redis://:pw@host) and
# TOKEN_URL takes an HTML-escaped ampersand before the parameter (&amp;key=). Widening a
# rule is safe for the gate, which only asks whether ANY match exists, and unsafe for
# this scrubber, which rewrites the line rule after rule: a wider match from an earlier
# rule can cut the head off a credential a later rule needs to see, and a match that runs
# past its own credential (DB_URL's host class [^\s/]+ runs through commas and
# semicolons to the next slash; a TOKEN_URL sig value runs through a "?" or a
# "postgres://user") leaves the tail of what it swallowed. Three critics found four
# different leaks of that one kind, in three rounds, each one a credential that the 2026-09-22 version's
# scrub.py removed and this one left, with the gate accepting the output.
#
# So the two new patterns are not allowed to touch the text the old ones saw. scrub()
# runs the pipeline as it stood on 2026-09-22 first (the two old patterns, derived from the
# live ones below so they cannot drift), and only then a second pass with the two new
# patterns, on text where every credential the old pipeline finds is already a marker.
# The second pass can therefore only remove MORE. Inside it the two new rules share one
# set of spans, unioned before anything is replaced, so neither can eat the head of the
# other; and DB_URL tries every start position, so a second URL that begins inside the
# first match's host run is still found. That rescan is affordable only because the
# rule is anchored on "://" (measured linear); a rescan on TOKEN_URL, whose tail is \S+,
# was 40 s on 262 KB of "&key=a" repeated, against 0.5 s.
#
# What this does not do: the 2026-09-22 pipeline still has its own version of the same
# hazard (a plain "&sig=AAAA...,postgres://u:p#w@h/db" leaves "#w@h/db"). That is old
# behaviour, kept on purpose so this change can be shown to remove nothing, and is a
# separate change.
_DB_URL_USER_NEW = r"://[^\s:/@]*:(?!<"
_DB_URL_USER_OLD = r"://[^\s:/@]+:(?!<"
_TOKEN_URL_OPENER_NEW = r"(?<=\S)(?:[?]|&(?:(?:[Aa][Mm][Pp]|#0*38|#[Xx]0*26);)*)"
_TOKEN_URL_OPENER_OLD = r"(?<=\S)[?&]"
_NEW_SHAPE_RULES = ("DB_URL", "TOKEN_URL")


def _before_ph529(rule_type, pattern):
    """The rule as it stood on 2026-09-22, derived from the live pattern."""
    if rule_type == "DB_URL":
        assert pattern.pattern.count(_DB_URL_USER_NEW) == 1, "DB_URL changed: update _DB_URL_USER_NEW"
        return re.compile(pattern.pattern.replace(_DB_URL_USER_NEW, _DB_URL_USER_OLD), pattern.flags)
    if rule_type == "TOKEN_URL":
        assert pattern.pattern.startswith(_TOKEN_URL_OPENER_NEW), "TOKEN_URL changed: update _TOKEN_URL_OPENER_NEW"
        return re.compile(_TOKEN_URL_OPENER_OLD + pattern.pattern[len(_TOKEN_URL_OPENER_NEW):], pattern.flags)
    return pattern


# Each group is redacted together: the spans of every rule in it are collected on the
# same text and unioned. The first len(PATTERNS) groups are one rule each, in the order
# and with the patterns of 2026-09-22, and behave exactly as the loop always did. The last
# group holds the two new patterns. The flag says whether to try every start position.
_GROUPS = [[(t, _before_ph529(t, p), False)] for t, p in PATTERNS] + [
    [(t, p, t == "DB_URL") for t, p in PATTERNS if t in _NEW_SHAPE_RULES]
]


def _spans(pattern, text, rescan):
    """(start, end) of every match finditer returns and, with rescan, of every match
    that starts inside an earlier one."""
    if not rescan:
        for m in pattern.finditer(text):
            yield m.start(), m.end()
        return
    pos = 0
    while pos <= len(text):
        m = pattern.search(text, pos)
        if m is None:
            return
        yield m.start(), m.end()
        pos = m.start() + 1


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
    for group in _GROUPS:
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
            #
            # A span is (start, end, rule_type). A group of one rule is the loop as
            # it always was; the last group holds two, and their spans are unioned.
            spans = []
            # The pre-2026-09-01 normalisation as its own pass. It strips only
            # U+FEFF, which makes it a THIRD normalisation rather than a subset of
            # the two around it, and it wins whenever a document needs U+FEFF gone
            # and another invisible kept. Without it this file stops redacting
            # credentials it used to redact.
            leg, leg_idx = _normalise_with_map(line, legacy=True)
            norm, idx = _normalise_with_map(line)
            for rule_type, pattern, rescan in group:
                for ms, me in _spans(pattern, line, rescan):
                    spans.append((ms, me, rule_type))
                for ms, me in _spans(pattern, leg, rescan):
                    s_ = leg_idx[ms]
                    e_ = leg_idx[me - 1] + 1 if me > ms else s_
                    spans.append((s_, e_, rule_type))
                for ms, me in _spans(pattern, norm, rescan):
                    start = idx[ms]
                    end = idx[me - 1] + 1 if me > ms else start
                    spans.append((start, end, rule_type))

            # Merge overlaps, then walk right to left so each edit lands entirely
            # to the right of every span still to be processed. A merged span is
            # named for the rule whose span starts first (ties: list order), and
            # reports one finding per rule that contributed to it.
            order = {t: n for n, (t, _p, _r) in enumerate(group)}
            merged = []
            for s, e, t in sorted(set(spans), key=lambda x: (x[0], order[x[2]], x[1])):
                if merged and s <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], e)
                    merged[-1][2].append(t)
                else:
                    merged.append([s, e, [t]])
            for start, end, types in reversed(merged):
                for t in dict.fromkeys(types):
                    findings.append({
                        "type": t,
                        "line": origin[i],
                        "match_prefix": _prefix(line[start:end]),
                    })
                line = line[:start] + "[SCRUBBED:" + types[0] + "]" + line[end:]
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

    # THIS RUNS ON THE OWNER'S OWN MACHINE, AND THE COST IS THEIR WALL CLOCK.
    #
    # The upload endpoint caps a body at MAX_BYTES (262,144) before it scans,
    # in its own validator. This file had no cap of any kind: it read
    # whatever it was handed and scanned all of it. That was survivable while
    # every rule was linear in the input, and it stopped being survivable when
    # the password rule gained lookaheads that scan to the end of a run.
    #
    # WHY IT IS STILL HERE AFTER THE RULE WAS FIXED, because the honest answer is
    # weaker than the one this comment first gave. The measurement that provoked
    # the cap was taken against the UNBOUNDED password rule: 313 ms at 16 KB
    # rising to 19.5 s at 128 KB, quadratic, projecting to roughly 21 minutes on
    # a 1 MB file. Bounding the rule in this same commit removed that: the same
    # shape now costs 0.13 s at 16 KB and 1.76 s at 256 KB, cleanly linear, and
    # nine adversarial shapes swept at 64, 128 and 256 KB found nothing
    # super-linear, worst 1.77 s.
    #
    # So this cap is defence in depth against a hazard that no longer exists on
    # any measured shape, not a fix for a live one. It is kept because this file
    # has no other bound of any kind, it runs on whatever the capture points at,
    # and the next rule added here does not have to be quadratic to be slow on a
    # megabyte. Stated this way so nobody reads the numbers above as current.
    #
    # The cap matches the endpoint's, because a file this tool cannot scrub in
    # reasonable time is also a file the endpoint would refuse to accept, and
    # two different limits would mean a passport that scrubs locally and is then
    # rejected on upload. Refusing here says so before the owner spends the time.
    #
    # MEASURED IN BYTES READ, NOT IN os.path.getsize. getsize returns 0 for any
    # non-seekable input, so a pipe or a FIFO walked straight past the earlier
    # version of this guard: `cat big.md | scrub.py /dev/stdin ...` scrubbed
    # 400,001 bytes and exited 0 with the cap in place. Reading the bytes and
    # measuring what came back cannot be fooled that way, and it also removes the
    # stat-then-read race on a file that grows in between. preflight.py's copy of
    # this check was written the second way and was correct; this one was not,
    # and the two are now the same shape.
    MAX_INPUT_BYTES = 262144

    try:
        raw = open(input_path, "rb").read()
    except (OSError, IOError) as e:
        print(f"Error reading {input_path}: {e}", file=sys.stderr)
        sys.exit(1)
    if len(raw) > MAX_INPUT_BYTES:
        print(f"Error reading {input_path}: {len(raw)} bytes, over the {MAX_INPUT_BYTES} limit.\n"
              "A passport describes an agent, it does not contain one. This is the same\n"
              "limit the upload endpoint applies, so a larger file would be refused there\n"
              "even if it were scrubbed here. Exclude it, or include the part that\n"
              "describes the agent rather than the whole file.",
              file=sys.stderr)
        sys.exit(1)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # A keystore, a .p12/.pfx/.jks, an image, or any latin-1 file. This
        # caught nothing before and produced a raw traceback, which is what the
        # model driving the capture would have seen: the one failure path in
        # this file that did not explain itself. It fails closed either way,
        # which is right; it now says why.
        #
        # THE SIZE GUARD ABOVE IS THE OTHER HALF OF THIS. See MAX_INPUT_BYTES.
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

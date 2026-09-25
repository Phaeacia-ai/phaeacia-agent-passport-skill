#!/usr/bin/env python3
"""validate.py — validate an agent passport Markdown file."""

import datetime
import json
import os
import re
import sys
import unicodedata


REQUIRED_KEYS = [
    "passport", "name", "title", "created",
    "capture_path", "source_stack", "owner_confirmed",
    "scrub", "envelope",
]

VALID_CAPABILITIES = {
    "web.fetch", "email.read", "calendar.read", "files.read",
    "schedule.run", "chat.notify", "memory.prefs", "email.send",
    "msg.send", "social.post", "ext.write",
}

# The declared-only half of the vocabulary: capabilities that write to the
# world. spec section 5 puts them outside the read-notify envelope and
# vocabulary.md lists exactly these. Check 16 refuses a passport that marks one
# of them installable.
#
# `money.` is a PREFIX and not an id, which is what vocabulary.md says it is and
# the reason it is held separately here. Enumerating the ways an agent could
# spend somebody's money before refusing to install one is the mistake the
# prefix exists to prevent, so nothing below ever compares a money id for
# equality.
DECLARED_ONLY = {"email.send", "msg.send", "social.post", "ext.write"}
DECLARED_ONLY_PREFIX = "money."


def fold_ascii(s):
    """Lower-case the ASCII capitals and nothing else.

    Not casefold() and not lower(): the two runtimes disagree on 154 codepoints
    under full Unicode folding and the record says not to build on their
    agreement. A-Z is the same table everywhere. This is enough for the job,
    which is that `Money.transfer` and `EMAIL.send` in a consent cell are the
    write ids they spell and not decoration the floor walks past."""
    return re.sub(r"[A-Z]", lambda m: m.group().lower(), s)


def is_declared_only(ref):
    """True when a capability id is outside the read-notify envelope.

    Folded on ASCII case. A critic put `MONEY.transfer` and `EMAIL.send` in
    an installable row and both gates accepted them, on main and on the
    branch that closed the lower-case prefix: one capital letter bought what
    declaring less used to buy. Ids are lower-case by vocabulary, so nothing
    honest spells one in capitals, and nothing honest is refused by reading
    the capitals as the id they are."""
    ref = fold_ascii(ref)
    return ref in DECLARED_ONLY or ref.startswith(DECLARED_ONLY_PREFIX)


# The five column names of the consent table, in order, so a FAIL 16 message
# can say which cell carried the id. Fixed strings from the header row, never
# a stranger's text. They are the names references/spec-schema.md section 2 gives
# the columns, shortened to what a person scans a table header for.
CONSENT_COLUMNS = ("Capability", "Why", "Required / Optional",
                   "If you skip it", "Installable in v0.1")


# A backticked `money.<ext>` in a consent cell is a filename, not an id. The
# cell is prose written for a person, and "Read the ledger file (`money.csv`)"
# is an honest row that this validator once refused as an offer to move money.
#
# THIS LIST IS THE WHOLE JUDGEMENT, so read it as one. Until 2026-09-04 the
# test for "filename, not id" was whether the passport declared the token as a
# capability_ref, and that resolved the ambiguity in favour of ACCEPT: an
# undeclared `money.transfer` in an installable row passed both gates and
# rendered Granted, because a lying passport declares nothing. The
# four fixed ids could not be evaded; the whole prefix could. So the test is
# now the shape of the token, and the presumption runs the other way: a
# `money.` token is an id unless it is exactly `money.<ext>` for an extension
# in this set. The cost is the honest author whose ledger is `money.xyz` or
# `money.ledger.csv`, who is refused with a message that says how to fix it;
# the alternative cost was a silent accept of a payment capability. Fail
# closed, cheap authoring fix.
#
# It is a list of what has been looked for, so it is a floor that gets raised
# and never a boundary that holds. Every entry is one exact string a passport
# can write in backticks and have skipped, so an entry that is a way of
# spending money (transfer, pay, wire) reopens the hole by exactly that word.
# Nothing structural separates an extension from a verb, so the test suite
# test 16 enforces it two ways: no entry may equal the suffix of any money id
# the repository itself names anywhere (vocabulary examples, fixture
# capability_refs, the probe tables that assert a token is an id), and no
# entry may be on a floor list of money verbs. The first grows with the corpus,
# the second is only the words somebody thought of. Each entry also has to be
# a name a ledger row would plausibly carry: archives and web pages were
# dropped for buying skip surface nobody would use.
# Every consumer of this decision must go through consent_token_is_write_id()
# below, in both languages, so the list is consulted in exactly one place.
FILENAME_EXTENSIONS = {
    "csv", "tsv", "txt", "md", "json", "yaml", "yml", "xml", "toml", "ini",
    "xlsx", "xls", "ods", "numbers", "parquet", "db", "sqlite", "sqlite3",
    "log", "dat", "pdf", "ofx", "qif", "xlsm", "gnucash",
}


def is_filename_token(token):
    """True when a `money.` token is exactly `money.<ext>`, nothing more.

    The WHOLE suffix after the prefix, not the last dot segment. The first
    spelling was rsplit(".", 1)[-1], and a critic put `money.transfer.csv`
    through it: the last segment is csv, the skip fired, and the token was
    never read as an id, so the evasion cost fell from "declare less" to
    "declare less and type four more characters". Read whole, the skip is a
    closed set of exact strings, one per extension, none of which is a
    plausible way to spend money. The honest cost is a two-segment ledger
    name like `money.ledger.csv`, which is refused and told how to fix it."""
    return fold_ascii(token[len(DECLARED_ONLY_PREFIX):]) in FILENAME_EXTENSIONS


def strip_blanks(token):
    """Strip ASCII space and tab, and only those.

    Not str.strip(): Python's isspace() and JavaScript's trim() disagree on
    U+001C to U+001F, U+0085 and U+FEFF, so `money.csv` followed by a BOM
    was stored by the site and refused here. Two languages, one definition."""
    return token.strip(" \t")


def is_ascii_control(token):
    """True when a token carries an ASCII control character or DEL.

    Unconditional, and separate from the lookalike test below. 0x00 to 0x1F
    and 0x7F are not text: they are what a passport carries when something
    went wrong upstream, and they are exactly the characters Python
    str.strip() and JavaScript trim() disagree about, so a token ending in one
    was stored by the site and refused by the owner loop. Nothing honest
    contains one."""
    return any(ord(c) < 0x20 or ord(c) == 0x7F for c in token)


def wildcard_matches(chars, target):
    """Whether chars matches target with every non-ASCII character a wildcard.

    Position by position, same length, and each position is either the same
    character or a non-ASCII one standing in for it. No regex, so there is
    nothing to backtrack and nothing to escape; no Unicode table, so the two
    runtimes cannot disagree about a codepoint.

    AND AT LEAST ONE POSITION MUST MATCH BY EQUALITY, which the first version
    of this function did not require and which made it refuse every language
    that is not written in ASCII. With wildcards alone, a slice of six
    non-ASCII characters matches "money." at every position, because every
    position takes the "or non-ASCII" branch. So `売上レポート`, an ordinary
    Japanese phrase, and `сообщение`, the Russian for message, and every
    other CJK or Cyrillic word of six characters or more, was refused inside
    a backticked span of an installable row. The change of 2026-09-05 exists to stop refusing
    a passport for the language it is written in, and it was doing exactly
    that to a wider set than the rule it replaced. Found by perf-168 while
    building a fixture, not by this file test table, whose honest cases all
    contained ASCII: the case was never in front of the check.

    A wildcard match with no anchor is not evidence. THE RESIDUAL IS AN OPEN
    HOLE, not a cost argued down. A token with no ASCII letter or digit in
    the compared region is not a lookalike, so `ⅿоոеу․transfer_acct_99`
    (Roman numeral m, Cyrillic o, Armenian n, Cyrillic e and u, one-dot
    leader) reads as money.transfer and passes, with the whole account suffix
    in plain ASCII because the prefix test reads only six characters. The
    first version of this docstring called the residual safe on the ground
    that fullwidth and CJK characters are visibly not the ASCII ones; that is
    true of `ｅｍａｉｌ．ｓｅｎｄ` and FALSE of U+217F, which is drawn as an
    ordinary lowercase m. Built and measured by a reviewer against
    this code.

    AND IT IS TRADED, NOT FREE. It is not a stated cost against nothing. Main
    as of 2026-09-05 refuses that attack token today, because the rule this one
    replaces refuses every token carrying any character outside printable
    ASCII, and it closes this route by accident while doing it. Measured by
    running main's own consent_token_is_opaque(): True for
    ⅿоոеу․transfer_acct_99, and True for Приложение.csv, 売上レポート and
    Zahlungsübersicht.csv alike. So this change closes a live nine-script
    false positive and opens one confusable route that was shut. An open issue
    holds the residual, and proposes a block-range direction that needs no
    Unicode table: what separates the critic's 93 honest tokens from these attacks is
    not how much ASCII they carry, since Приложение.csv carries none either,
    but that the honest ones draw their non-ASCII from ONE range and the
    attacks from four. The question for whoever reads this next is not
    whether the narrow rule is better reasoned, it is whether the trade is
    the one we want, and that is a decision rather than a bug."""
    if len(chars) != len(target):
        return False
    anchored = False
    for c, t in zip(chars, target):
        if c == t:
            # A LETTER OR DIGIT, not any equal character. The first anchored
            # version accepted the dot as evidence, and `메모장기록.csv`, an
            # ordinary Korean filename, still matched "money." on the strength
            # of one full stop in position 5. A dot is the commonest character
            # in a filename and it is worth nothing as evidence that a word is
            # a capability id.
            if c.isascii() and c.isalnum():
                anchored = True
        elif ord(c) <= 0x7F:
            return False
    return anchored


def token_is_id_lookalike(token):
    """True when a token containing non-ASCII is a write id in disguise.

    TWO READINGS, and the token is a lookalike if either one lands.

      (a) DELETE every non-ASCII character. A zero-width space inside the
          word, or a byte-order mark after it, vanishes and `money.transfer`
          is what is left.
      (b) REPLACE every non-ASCII character with a single-character wildcard.
          A Cyrillic o, a one-dot leader or a fullwidth stop then matches the
          position it was standing in.

    Neither is enough alone and that is the reason there are two: (a) cannot
    see a substitution, because deleting the impostor shortens the word past
    the id; (b) cannot see an insertion, because it changes the length.

    Either reading counts if it is a declared-only id or begins with the money
    prefix. The prefix is checked on the first six characters, which is what
    makes (b) enough on its own for a lookalike anywhere after `money.`.

    ITERATED BY CODEPOINT. In JavaScript that means Array.from() and not
    indexing, because a lookalike outside the Basic Multilingual Plane is one
    character to a reader and two UTF-16 units to a naive loop, which would
    make the two runtimes disagree on the length test in wildcard_matches().

    WHAT THIS REPLACED, and why the replacement is narrower on purpose. The
    rule used to be that an installable row may backtick only printable ASCII.
    That needs no Unicode table and closes every lookalike, and it also refused
    an honest German filename, a name with a diaeresis, a Japanese path and an
    en-dash in a date, in an installable row, telling the author to drop the
    backticks. 804 installable rows across three repositories carried zero such
    tokens, so nothing that existed was refused and a German-speaking author
    writing their first passport was. This rule never fires on a word that is
    not already shaped like a write id, so it costs no language anything, and
    that is what lets it run in all five cells instead of one (the two 2026-09-05
    changes together).

    The cost it does carry: a lookalike of a money FILENAME, `money.csv` with a
    Cyrillic o, is refused, because (a) and (b) test the prefix and do not
    consult the extension list. Nothing honest spells a filename with a
    Cyrillic o, and reading the extension list under wildcards too would buy
    nothing real."""
    chars = list(fold_ascii(token))
    if not any(ord(c) > 0x7F for c in chars):
        return False
    deleted = "".join(c for c in chars if ord(c) <= 0x7F)
    if is_declared_only(deleted):
        return True
    if any(wildcard_matches(chars, ref) for ref in DECLARED_ONLY):
        return True
    return wildcard_matches(chars[:len(DECLARED_ONLY_PREFIX)], DECLARED_ONLY_PREFIX)


def consent_token_is_opaque(token):
    """True when a backticked token in an installable row must be refused
    without being echoed.

    Two rules sharing one answer: an ASCII control character, which is never
    text, or a write id spelled with characters that are not the ones the id
    is spelled with. Both refuse without echoing the token, because in the
    second case the token is by construction indistinguishable from the id to
    a reader, and a regex written for the id would not match it."""
    return is_ascii_control(token) or token_is_id_lookalike(token)


def consent_cell_segments(cell):
    """Every segment of a Capability cell split on its backticks.

    Yields (segment, inner) where inner is True when the segment is bounded
    by a backtick on both sides. NOT the regex-paired spans. A critic put
    ``Charge the card`s `email.send` `` in an installable row: three
    backticks, and re.findall(r"`([^`]+)`") paired the first two, captured
    "s ", found no partner for the third, and never saw the id, which the
    page then rendered under a Granted stamp. `` `money.transfer` `` (the
    CommonMark way to show a literal backticked token) and ``x`` and
    `email.send` did the same with an even count. Pairing is a reading, and
    the validator's reading was not the reader's. Splitting on every
    backtick has no reading to get wrong: a write id between any two
    backticks, or standing alone as a whole segment, is found whatever the
    count.

    WHAT `inner` MEANS, AND WHAT IT DOES NOT. A segment is inner when a
    backtick stands on both sides of it. That is NOT the same as "inside a
    code span": the prose BETWEEN two code spans has a backtick on each side
    too, and this function cannot tell the two apart, because telling them
    apart is exactly the pairing it refuses to do. The conservative reading is
    deliberate and costs an honest author a real thing: in an installable row,
    "we read `inbox.csv` and the previous agent used email.send to mail
    `digest.html`" is refused, because email.send is a WORD of an inner
    segment. Moving the mention before the cell first backtick or after its
    last is what passes, and the refusal message says so. Making innerness
    depend on pairing would let ``a`run email.send now`b`` through, which is
    why the message changed and this did not.

    An earlier version of this paragraph said the opaque test runs on one-word
    inner segments only. The change of 2026-09-05 removed that carve-out; the sentence outlived
    the code by half a day."""
    parts = cell.split("`")
    last = len(parts) - 1
    for i, seg in enumerate(parts):
        yield seg, 0 < i < last


# The word boundary for the ID scan: anything that is not printable ASCII
# other than space. A vocabulary id is printable ASCII by definition, so every
# other character is a gap between words as far as this scan is concerned, and
# using the class rather than just space and tab closes a separator that is not
# a space: `` `email.send<NBSP>now` `` split on [ \t]+ is one word, is not
# equal to any fixed id, and reached a Granted stamp in four of five cells
# with the id itself in byte-identical ASCII. Found by this build critic.
#
# The OPACITY scan deliberately does NOT use this: it is looking for non-ASCII
# and cannot use non-ASCII as a boundary. Two scans, two boundaries, each the
# one its own question needs.
ID_WORD_SPLIT = re.compile(r"[^\x21-\x7e]+")


# A vocabulary id begins and ends with an ASCII letter or digit: files.read,
# email.send, money.transfer, money.transfer#1. Everything else on either end
# of a word is punctuation a sentence put there.
ID_TRIM = re.compile(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$")


def id_core(word):
    """A word with the sentence punctuation trimmed off both ends.

    A WHITELIST of what an id may end with rather than a list of punctuation
    marks, so it needs no Unicode table and no guess about which quote a
    stranger used: `` `use email.send, here` ``, `` `(email.send)` `` and
    `` `email.send.` `` name the id as plainly as `` `email.send` `` does, and
    the four fixed ids are compared by EQUALITY, so one trailing character was
    the whole evasion. Anchored at both ends and nowhere else, so `#` and `.`
    inside a word survive and `money.transfer#1` is untouched.

    THE ENDS ONLY. A word's interior is never touched, so a zero-width space
    or a Cyrillic o inside it survives to the opaque test, which is the test
    built for it. A lookalike ON an end is trimmed, which is a tightening:
    `money.transfe\u0433` with a Cyrillic r loses the r and is read as the
    money prefix it is.

    Never used on its own. consent_cell_write_id() tests a candidate as
    written AND as its core, so trimming can only add a refusal and never
    remove one: `` `money.` `` is a write id by the prefix test as written,
    and its core `money` is not, and the union keeps the refusal."""
    return ID_TRIM.sub("", word)


def consent_cell_write_id(cell, spec_refs):
    """The first write id a consent cell names, or None.

    TWO readings of the same cell, because a code span is not a token.

      - every SEGMENT between backticks, tested whole, which is what a
        one-token span is; and
      - every WORD of every INNER segment, tested on its own.

    The second is the other 2026-09-05 change's half. The one-word carve-out on the opaque rule
    exempts a multi-word inner segment, and this function's ancestor compared
    a fixed id to the whole segment, so `` `email.send now` ``,
    `` `run money.transfer now` `` and `` `use ext.write here` `` were read by
    nothing and rendered under a Granted stamp. `` `money.transfer daily` ``
    was refused the whole time, because the money test is a prefix and the
    fixed-id test is an equality; that asymmetry is what hid it.

    Words are read INSIDE BACKTICKS ONLY. A word of ordinary prose that
    happens to spell an id is the prose-to-id gap, open by design,
    and reading it here would refuse the honest sentence "the original used
    email.send to mail the digest" in a row that installs nothing but
    files.read."""
    for seg, inner in consent_cell_segments(cell):
        token = strip_blanks(seg)
        if not token:
            continue
        # WORDS FIRST, then the whole segment. Both orders reach the same
        # verdict, and the order decides which string the refusal names: with
        # the segment first, `money.transfer daily` is reported as the whole
        # four-word segment, because the money test is a prefix and the
        # segment starts with one. The word is the id, so the word is what
        # the author is told about.
        candidates = ID_WORD_SPLIT.split(token) + [token] if inner else [token]
        for cand in candidates:
            # AS WRITTEN AND AS ITS CORE, in that order, and the union of the
            # two is the point: trimming alone would have accepted
            # `` `money.` ``, which the prefix test refuses as written. A
            # union can only add refusals. The documented cost of keeping the
            # raw reading is `` `money.csv,` ``, an honest ledger filename
            # with the comma inside the backticks, refused because `csv,` is
            # not a listed extension. Moving the comma outside is the fix and
            # the message says so.
            for probe in (cand, id_core(cand)):
                if probe and consent_token_is_write_id(probe, spec_refs):
                    return probe
    # And the run reading. See consent_cell_code_runs(): the renderer pairs
    # backticks and this file does not, so an id written across two adjacent
    # spans is one word on the page and three segments here.
    for run in consent_cell_code_runs(cell):
        # strip_blanks() FIRST, exactly as the segment path does. Without it
        # the whole-run candidate for `` `money.csv ` `` is "money.csv " and
        # the suffix "csv " is not a listed extension, so an honest padded
        # filename that the segment path skips was refused by the run path.
        # Two readings of one cell only work if they read it the same way.
        run = strip_blanks(run)
        for cand in ID_WORD_SPLIT.split(run) + [run]:
            for probe in (cand, id_core(cand)):
                if probe and consent_token_is_write_id(probe, spec_refs):
                    return probe
    return None


CODE_SPAN = re.compile(r"`([^`]+)`")


def consent_cell_code_runs(cell):
    """Each maximal run of ADJACENT code spans, concatenated as a page shows it.

    THE SECOND READING OF A CELL, and it exists because the renderer has one
    the validator did not. inline() pairs backticks with `([^`]+)` and emits
    one <code> per pair, so `` `email.``send` `` becomes
    <code>email.</code><code>send</code>: two elements with NOTHING between
    them, which a reader sees as the single monospace string "email.send".
    Splitting on every backtick gives "email.", "" and "send", not one of
    which is an id, so a pure-ASCII write id reached a Granted stamp in four
    of the five cells. Measured across four fixed ids and three
    split points; the money prefix was the only one that survived, and only
    because it is a prefix test. Found by this build's critic.

    A run continues only across an EMPTY gap. One space between two spans and
    the reader sees two words, so " " ends the run: this models what the page
    shows and nothing more.

    This PAIRS, which is the reading consent_cell_segments() exists not to
    make. Both are kept and neither replaces the other: the split reading
    cannot be walked past by miscounting backticks, and the paired reading is
    what the reader actually sees. A candidate found by either is refused, so
    the pair can only add refusals."""
    run, prev_end = [], None
    for m in CODE_SPAN.finditer(cell):
        if prev_end is not None and m.start() != prev_end:
            yield "".join(run)
            run = []
        run.append(m.group(1))
        prev_end = m.end()
    if run:
        yield "".join(run)


def opaque_reading(word):
    """A word tested AS WRITTEN and AS ITS CORE, the first hit or None.

    The same union the id scan uses, and it was missing here. The id scan
    trims with id_core() and has no lookalike test; this scan had the
    lookalike test and no trim, so a lookalike with ordinary sentence
    punctuation on either end was read by neither. All four of these reached
    a Granted stamp through both gates, and all four were refused by the
    printable-ASCII rule this one replaced:

        `emаil.send.`      Cyrillic a, trailing full stop
        `emаil.send,`      trailing comma
        `(emаil.send)`     parenthesised
        `(mоney.transfer)` parenthesised, and the leading bracket is what
                           defeats the prefix reading, since position 0 is
                           then an ASCII "(" that does not match "m"

    Found by a reviewer. Two scans that each carried half of one
    reading is the shape: neither file was wrong on its own and the gap was
    between them."""
    for probe in (word, id_core(word)):
        if probe and consent_token_is_opaque(probe):
            return probe
    return None


def consent_cell_opaque_word(cell):
    """The first backticked word of a cell that must be refused unread, or None.

    WORDS OF INNER SEGMENTS, and the one-word carve-out is gone. That carve-out
    existed only because the old rule refused any character outside printable
    ASCII, so "Read `a.csv` und dann `b.csv`" was refused for a word standing
    between two code spans. Exempting every multi-word segment fixed that and
    opened a hole one space wide: a Cyrillic-o money id with a word beside it
    inside a single span was read by neither rule. The change of 2026-09-05 closed the id half
    of that with a word-wise scan; this closes the other half by making the
    rule narrow enough that nothing needs exempting.

    INNER SEGMENTS ONLY, exactly as the id scan, and see consent_cell_segments
    for what inner does and does not mean: prose between two code spans is
    inner and IS read, prose before the cell first backtick or after its last
    is not. That outer prose is the prose-to-id gap, open by design,
    and reading it here would refuse an honest German sentence in a Capability
    cell for the umlaut in it."""
    for seg, inner in consent_cell_segments(cell):
        if not inner:
            continue
        token = strip_blanks(seg)
        if not token:
            continue
        for word in re.split(r"[ \t]+", token):
            hit = opaque_reading(word)
            if hit is not None:
                return hit
    # And the run reading, so a lookalike split across two adjacent spans is
    # seen as the one word a reader sees. Space and tab only here, because
    # this test is looking FOR non-ASCII and must not use it as a boundary.
    for run in consent_cell_code_runs(cell):
        for word in re.split(r"[ \t]+", strip_blanks(run)):
            hit = opaque_reading(word)
            if hit is not None:
                return hit
    return None


def consent_token_is_write_id(token, spec_refs):
    """Whether a backticked consent-cell token must be read as a write id.

    The single place the money-guard decision is made. A declared token is an
    id whatever its shape, because the passport itself said so. An undeclared
    `money.` token is an id unless is_filename_token() says it is a file. The
    four fixed ids are ids always. Test 15 calls this function rather than
    re-implementing it, so a change here is a change the probes see."""
    token = fold_ascii(token)
    if not is_declared_only(token):
        return False
    if (token.startswith(DECLARED_ONLY_PREFIX) and token not in spec_refs
            and is_filename_token(token)):
        return False
    return True


# A refusal message quotes a consent cell so its author can find the row. The
# cell is a stranger's text, so what it may carry into the message is bounded
# in two ways and neither is optional.
#
# THE CAP. Nothing clipped these fields, and a passport may be 262144 bytes
# with most of it in one cell, so an endpoint error was as long as the
# attacker chose. 200 characters is enough to recognise a row by.
#
# THE BARE-TOKEN COLLAPSE. Both collapses below worked on BACKTICKED spans
# only, and an UNBACKTICKED money id in the same cell walked through untouched:
# a Cyrillic-o token in the Capability cell fires the opaque rule, and the
# Installable cell reading "yes, see money.transfer_acct_99_IBAN_CH93_..."
# carried that suffix into an endpoint error in both languages. Found by this
# build's critic, and it is the leak I had already fixed with the backticks
# left on, which is the shape of a fix that generalises one case too narrowly.
# The escape hatch for the four cells the 2026-09-05 change added to the scan, named in the
# message rather than left for the author to find. The Capability cell names
# what the row installs, so "the column reads no, declared only" is the whole
# truth there. The other four are prose ABOUT the row, and an author whose
# Why cell honestly names what some other agent did is being refused for a
# sentence rather than for a capability. Telling that author to mark the row
# declared-only is a lie about their agent, which is the thing this build
# split the cells to avoid one cell over.
#
# Every clause is measured rather than reasoned, against the live validator:
#   `email.send` in a Why cell                        REFUSED
#   email.send, the whole cell, no backticks          REFUSED
#   email.send `see docs`                             REFUSED  (segment = the id)
#   `see docs` email.send                             REFUSED  (segment = the id)
#   it used email.send `see docs`                     ACCEPTED
#   the original used email.send, this one does not   ACCEPTED
#   the original used money.transfer nightly          ACCEPTED
#   reads `a.csv`; the original used email.send       ACCEPTED
#   we read `a.csv` and it used email.send to mail `b.html`   REFUSED
#
# So "without backticks" ALONE is false, and so was the first correction of
# it. The last line is the critic case and it is the whole reason the
# sentence names a POSITION: consent_cell_segments calls any segment bounded
# by a backtick on both sides inner, and it cannot tell "inside a span" from
# "between two spans" without pairing, which it refuses to do because pairing
# can be shifted by a stray backtick. Making innerness depend on pairing
# would let ``a`run email.send now`b`` through, so the conservative reading
# stays and the MESSAGE is what changes.
PROSE_FIX = (
    "This column is prose about the row rather than the capability the row "
    "installs, so there is one more possibility: if the cell only names what "
    "some other agent did, write it in a sentence with no backticks, placed "
    "before the first backtick in the cell or after the last. A stretch of "
    "text that is nothing but the id is read wherever it stands, and so is "
    "every word of a stretch lying between two backticks, because this "
    "validator does not pair them."
)


# EVERY CHECK 16 REFUSAL IS PURE ASCII, and that is a rule for the messages
# below rather than an accident of how they are worded today. The echo
# invariant in the test suite asserts that no check-16 message contains a
# non-ASCII character, and it can assert that only because in this family a
# non-ASCII character could not have arrived any other way than by echo: the
# offending token is by definition a lookalike or an invisible. One message
# that legitimately spells a Cyrillic o destroys the invariant for all of
# them.
#
# So an example here is SPELLED OUT ("a Cyrillic o in place of the Latin
# one") and never pasted. The next author to write a message in this family
# will reach for the character, because it is the obvious way to show a
# lookalike, and the failing test will look like pedantry. It is not. Delete
# the character, not the assertion.
ECHO_CAP = 200


def collapse_bare_money(text):
    """Every money token collapsed to the prefix, backticked or not."""
    return re.sub(r"money\.\S*", "money.*", text, flags=re.I)


def clip_echo(text):
    """A cell echo, capped, so the length is ours and not the passport's."""
    text = text.strip()
    return text if len(text) <= ECHO_CAP else text[:ECHO_CAP] + "..."


def collapse_money_spans(text):
    """Every backticked span containing a money token collapsed to the prefix.

    vocabulary.md: "record `money.*` and not the id it arrived as". The suffix
    is a stranger's text of unbounded length and content, and the Installable
    cell is echoed into the refusal as the passport's own wording, so once the
    scan reads that cell the cell can hold a suffix. It did: a probe put
    `money.transfer_acct_99` in the Installable cell and the suffix reached
    the message through the column echo while the token echo was correctly
    labelled.

    A span CONTAINING a money token, not a span that starts with one, because
    the word scan finds `run money.transfer_acct_99 now`."""
    return clip_echo(collapse_bare_money(
        re.sub(r"`[^`]*money\.[^`]*`", "`money.*`", text, flags=re.I)))


def collapse_spans(text):
    """Everything from the FIRST backtick to the LAST, collapsed as one.

    For the opaque refusal, where the token is by definition a lookalike or a
    control character: no money regex would match a Cyrillic o, so nothing
    narrower is safe to echo.

    GREEDY AND UNPAIRED, and that is the whole point. A per-span collapse,
    `` `[^`]*` `` repeated, PAIRS the backticks, and pairing is the reading
    that this file was rewritten to stop making: in ``Move it ``x`` now`` the
    pairs are the two empty spans and the lookalike sits between them,
    untouched, so the collapse hands the message exactly the characters it
    exists to withhold. Caught by an existing assertion when this function was
    first written the narrow way."""
    return clip_echo(collapse_bare_money(re.sub(r"`.*`", "`...`", text)))


def safe_ref_label(ref):
    """Report a money capability as the prefix, never as the id it arrived as.

    vocabulary.md is explicit: "record `money.*` and not the id it arrived as".
    The suffix is a stranger's text of unbounded length and content, and the
    inference that a closed vocabulary means a bounded set of known strings is
    the one that put 71 characters of it into a store once already. This
    message only reaches a terminal, which is why the rule is easy to skip
    here; it is followed anyway so that the next thing to copy this function
    inherits the right habit."""
    return "money.*" if fold_ascii(ref).startswith(DECLARED_ONLY_PREFIX) else ref


# These mirror SKILL.md's deny list, which is the list the capture is told never
# to read. A passport naming one of them either quotes a file that should never
# have been opened or tells a recipient to open it.
#
# Substring matching does the work: `.env` catches `.env.local`, and the SSH key
# names catch a path that ends in one.
#
# These are the path-shaped entries, and that is a deliberate limit rather than
# an incomplete list. A deny-list entry that is a bare WORD rather than a
# filename fires on ordinary passport prose that discusses credentials, and a
# check that mangles legitimate text is a check somebody switches off. Matching
# those safely needs a rule that reads a token's POSITION rather than its
# substring, which is more than a list can do.
#
# assemble.py carries the same strings and the project's test suite compares the
# two, so widening one side and not the other fails the build.
FORBIDDEN_STRINGS = [
    "browser_profile", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    ".pem", ".key", ".env", "credentials/", "secrets/",
]

# Check 9 matched these as bare case-sensitive substrings, so `Credentials/`,
# `ID_RSA`, `id\_rsa` and a name broken across a line all passed while staying
# perfectly readable to whatever reads the passport next.
#
# THE OBVIOUS FIX IS WRONG. Reusing delta_phrase's normalisation, which
# collapses every run of non-alphanumerics to one space, turns "credentials/"
# into the ordinary English word "credentials" and "secrets/" into "secrets".
# The trailing slash is not punctuation here, it is the whole signal: these are
# DENIED PATHS (spec section 6), and a passport is expected to discuss
# credentials in prose. Under the collapsing rule all four of these are refused,
# and all four are things an honest passport says:
#
#   "you grant credentials yourself on your own platform"
#   "it never reads secrets from the environment"
#   "capture never opens your browser profile"
#   a sentence ending "done." above a line beginning "Pemberton"
#
# Those four are the evidence, and they are pinned as probes in
# the test suite test 13 so the claim stays checkable. An earlier version of
# this comment cited references/passport-template.md instead and was wrong: the
# template's only match is `no credentials, no paths` on line 7, inside the
# frontmatter, which check 9 did not read at the time. Corrected after a critic
# measured it rather than read it.
#
# So this deletes noise rather than collapsing structure. Three rules, each
# aimed at one evasion and none touching a path separator:
#
#   1. NFKC, which folds the compatibility characters that render as an ASCII
#      letter and are not one: the long s, the fullwidth solidus.
#   2. Characters that can be inserted between letters without changing what a
#      reader sees: backslash (`id\_rsa` in Markdown), backtick, the Markdown
#      emphasis pair `*` and `_`, and the zero-width and soft-hyphen family.
#   3. A line break that splits a word, joined back only when alphanumerics sit
#      on both sides.
#
# `.lower()`, NOT `.casefold()`, and that is a cross-implementation fix rather
# than a preference. The upload endpoint's validator has to reach the same verdict on the
# same file, and JavaScript has no casefold: `'CREDENTIALſ/'.casefold()` is
# 'credentials/' in Python while `.toLowerCase()` leaves the long s alone, so
# the two gates returned OPPOSITE answers on one passport. `.lower()` and
# `.toLowerCase()` agree, and NFKC does the folding both of them lack. The same
# trap sits behind casefold's ß to ss, which toLowerCase also does not do.
#
# Deleting `_` is safe even though two entries contain one, because the entries
# are normalised through this same function: "id_rsa" and "id\_rsa" and a
# Markdown-italicised "id_rsa" all reduce to "idrsa" on both sides of the
# comparison.
#
# `.pem` IS ANCHORED to a preceding word character, and NFKC is why it has to be.
# U+2026 HORIZONTAL ELLIPSIS folds to three ASCII dots, so "the run is done...
# Pemberton wrote it" became "done...pemberton" and matched `.pem`. That is the
# exact false positive rule 3 was shaped to avoid, walking back in through the
# fold, and a typographic ellipsis is what an editor autocorrects "..." into.
# `.pem` is the only entry beginning with punctuation and so the only one any of
# this can reach: 42 codepoints NFKC-fold to `.`, `/` or `_`, and none of them
# completes `credentials/` or `secrets/`. Requiring a word character before the
# dot keeps "cert.pem" and drops both ellipsis and "done.\nPemberton".
#
# KNOWN AND NOT FIXED: rule 3 cannot repair a break at a non-alphanumeric, so
# "cert.\npem" still evades `.pem`. Markdown bold, HTML entities and HTML
# comments inside a word all evade as well, as do an unbalanced backtick and a
# nested double-backtick span in a consent cell.
#
# This is a tripwire against accident, not a barrier. Secret VALUES are
# preflight.py's and scrub.py's, and nothing above is reachable by accident.
_FORBIDDEN_NOISE = re.compile(r"[\\`*_­​‌‍⁠﻿]")
_FORBIDDEN_SPLIT = re.compile(r"(?<=[a-z0-9])[ \t]*\n[ \t]*(?=[a-z0-9])")


def normalize_forbidden(text):
    """Fold away case and the noise a denied path can hide behind.

    Must stay verdict-identical to normalizeDenied in the upload endpoint's validator.
    The test suite test 13 pins this against scripts/assemble.py's copy."""
    folded = unicodedata.normalize("NFKC", text).lower()
    return _FORBIDDEN_SPLIT.sub("", _FORBIDDEN_NOISE.sub("", folded))

# Phrases that can only mean "compared against an earlier run". Check 13 refuses
# a verification check containing one of these unless the passport declares a
# state block.
#
# Phrases, never single words, and that is the whole design of this list. The
# cost of being wrong is asymmetric: a missed delta check produces a passport
# that is optimistic about persistence, while a false positive refuses a
# passport somebody has already finished and gives them no way to fix it except
# to declare a memory their agent does not have. So every entry needs at least
# two words. "previous" alone would catch "the previous section", "last" alone
# would catch "the last item in the list", and both are ordinary and correct.
#
# For the same reason there is no bare "since last". "items published since last
# week" is computable from the run time and needs no memory at all; only
# "since last run" and its relatives do.
#
# THE SAME REASONING EXCLUDES THREE PHRASES THAT LOOK LIKE THEY BELONG.
# "since yesterday",
# "previous day" and "previous week" are date windows, not comparisons: "every
# item is dated since yesterday" and "no item is older than the previous day"
# are judged against the run clock by a reader holding one output, which is
# exactly the kind of check spec section 4 asks capture to write. They were
# refused with a message telling the author to declare a memory their agent does
# not have, and there was no way to comply except to lie or to reword a correct
# check. What survives of yesterday here all carries a comparison verb: "vs",
# "compared to", "change since". The rule for adding an entry is that the phrase
# must be unusable without an earlier run, not merely mention an earlier day.
#
# Matching is on text with every run of non-alphanumeric characters collapsed to
# one space, so "period-over-period", "vs. prev" and "vs prev)" all reduce to
# the same thing and no entry needs a punctuation variant. Each entry is
# anchored at a word boundary on the left and open on the right, so "vs prev"
# also catches "vs previous" and "previous run" also catches "previous runs".
DELTA_PHRASES = [
    "vs prev", "versus prev", "against prev",
    "compared to prev", "compared with prev",
    "previous run", "previous period",
    "previous value", "previous figure", "previous number", "previous reading",
    "prior run", "prior period", "prior value",
    "last run", "earlier run", "preceding run",
    "since last run", "since the last run", "since last time",
    "since it last ran", "since the previous",
    "vs yesterday", "versus yesterday", "against yesterday",
    "compared to yesterday", "compared with yesterday",
    "yesterday s value", "yesterday s number", "yesterday s figure",
    "period over period", "day over day", "week over week",
    "month over month", "run over run",
    "change since the last", "change since the previous",
    "change since yesterday",
    # "delta since yesterday" and "difference since yesterday" are admitted by
    # the rule stated above, not as exceptions to it: both carry a comparison
    # noun that is unusable without an earlier run, exactly as "change since
    # yesterday" already did. The three deleted entries went the other way,
    # being date windows with no comparison in them, and nothing here reopens
    # that. Bare "since yesterday" stays out.
    "delta since yesterday", "difference since yesterday",
    "delta vs", "delta versus", "delta against", "delta from the previous",
]



# QUOTES. YAML says `access: credentialed`, `access: "credentialed"` and
# `access: 'credentialed'` are the same scalar. This validator reads YAML
# with regexes, so it sees three different strings, and it handled that
# inconsistently until 2026-09-03: `id:`, `binding:` and `fidelity:` stripped
# quotes, while `comparison_mode:`, `capability_ref:` and `access:` did not.
#
# The two directions of that inconsistency are NOT equally bad and it is
# worth being precise about which is which.
#
#   `comparison_mode: "structural"` and `capability_ref: "web.fetch"` were
#   REFUSED. Legal YAML, correct value, rejected with a message naming the
#   quoted string as though it were the problem. Loud, and it wastes an
#   author's afternoon.
#
#   `access: "credentialed"` was ACCEPTED AS NOT CREDENTIALED. That is the
#   dangerous one, and it is silent: the input skipped the binding
#   requirement entirely, so a passport could declare a source behind the
#   original owner's login and never ask the installer what plays that role.
#   The check that exists to stop a dead row shipped stopped seeing the row.
#
# A helper rather than a sixth `.strip("\"'")` at the call site, because the
# defect here was never that the strip is hard, it is that it is easy to
# forget and nothing notices when you do.
# ── THE WHITESPACE CLASSES, WRITTEN OUT INSTEAD OF `\s` ──────────────────────
#
# `\s` is not one class. Measured 2026-09-07 over every codepoint in both
# engines: Python also calls \x1c \x1d \x1e \x1f and \x85 whitespace, and
# JavaScript also calls \ufeff whitespace. Six characters, nothing else differs,
# and each one is a line that one gate reads as a declaration and the other does
# not. A critic built three of them. `\x1c- capability_ref: email.send`
# written at column 0 after a block scalar was refused by this file and ACCEPTED
# by the site; the \ufeff spelling was the same trade the other way round. Both
# put a write capability in front of a reader as an installable row on one of the
# two gates, and no fixture carried the shape because nobody types these.
#
# So neither engine's `\s` appears in a rule that decides what a passport
# declares. Two named classes do, and one sentence picks between them: WHERE THE
# TWO ENGINES DISAGREE ABOUT WHETHER A CHARACTER IS WHITESPACE, TAKE THE READING
# THAT MAKES THE GATE REFUSE.
#
#   WS_ANY   the UNION, everything either engine calls whitespace. Used wherever
#            whitespace is SKIPPED, so a declaration hidden behind an invisible
#            character is still read as the declaration it looks like.
#   WS_BOTH  the INTERSECTION, only what both engines agree on. Used NEGATED, as
#            the class of a value, so an id carrying an invisible character keeps
#            it, fails check 6 as an unknown capability, and is not quietly read
#            as the clean id it resembles.
#
# The two are opposite widths on purpose and both widths refuse more than `\s`
# did. Test 18 in the test suite compares each class against the live engines
# character by character and against its twin in the upload endpoint's validator, so this
# comment cannot go stale without something going red.
WS_ANY = "\t\n\x0b\x0c\r \x1c-\x1f\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
WS_BOTH = "\t\n\x0b\x0c\r \xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"

# The same set as a plain string of characters, for str.strip(), which takes
# characters rather than a class. DERIVED from WS_BOTH rather than written out a
# second time: two spellings of one set is the defect this whole block exists to
# remove, and writing the range \u2000-\u200a out by hand is how the second
# spelling would drift.
WS_BOTH_CHARS = "".join(c for c in map(chr, range(0x3001))
                        if re.match("[%s]" % WS_BOTH, c))


WS_ANY_CHARS = "".join(c for c in map(chr, range(0x10000))
                       if re.match("[%s]" % WS_ANY, c))


def yaml_trim(s):
    """Trim a line for a YAML CONTINUATION test, with WS_ANY.

    The opposite width from structural_trim(), and the rule is the same one:
    take the reading that refuses. Asking "does this line still belong to the
    open block" wants the WIDE class, because a line that is NOT read as a
    continuation ENDS the block, and everything after it stops being checked.

    A critic made `scripts/validate.py` return PASS on a passport whose functional
    spec reads `\ufeff- capability_ref: email.send` / `status: used`, because
    `str.isspace()` is False for U+FEFF and `str.strip()` does not remove it, so
    the capabilities block was declared over at that line and check 16a never
    saw the entry. That is the NORMATIVE gate accepting a write capability at
    `status: used`, which is the one thing the envelope floor exists to stop.
    Measured 2026-09-07 on `caps_bom.md`; identical on main, so it is a hole
    neither gate had closed rather than a regression."""
    return s.strip(WS_ANY_CHARS)


def structural_trim(s):
    """Trim a line for a STRUCTURAL comparison, with WS_BOTH and not str.strip().

    `str.strip()` uses Python's `\s` and `String.prototype.trim()` uses
    JavaScript's, and those are different sets (see WS_ANY above). A `## 3.
    Functional spec` heading with a trailing \x85 is the heading to this file and
    is not the heading to the upload endpoint's section parser, so one gate has a section 3 and
    the other has none. A critic measured that on 2026-09-07.

    WS_BOTH, the intersection, is the right width here for the same reason it is
    right for a value: a character only one engine calls whitespace is left in
    place, the line stops being the heading in BOTH gates, and check 4 refuses
    the passport for a missing heading rather than the two gates reading
    different documents."""
    return s.strip(WS_BOTH_CHARS)


# ── MARKDOWN STRUCTURE IS `[ \t]`, AND THAT IS A THIRD ALPHABET ─────────────
#
# WS_ANY and WS_BOTH above are about YAML. Everything that decides MARKDOWN
# structure, a heading, a fence, a table row, a table separator, takes the
# narrow class instead, for the same reason the fence does: recognising MORE
# lines as structure ENDS A SECTION EARLIER or breaks a table, so FEWER
# declarations are seen. That is fail-open, and a critic built it.
#
# `##\ufeffExtra` is a heading to JavaScript, whose `\s` matches U+FEFF, and is
# not a heading to Python. So section 3 ended in a different place in the two
# gates, the site never reached a `capability_ref: email.send` below that line,
# computed declaresWrite = false and ACCEPTED a passport with all six consent
# rows saying yes, while this file read on, saw the declaration and refused.
# Measured 2026-09-07 on `bom_heading.md`; identical on main, so it is not a
# regression, it is a hole neither of us had closed. `##\x1cExtra` and
# `##\x85Extra` are the same trade the other way.
#
# `[ \t]` is also what CommonMark says an ATX heading takes after its hashes,
# so this agrees with every renderer that will ever show the document, which
# `\s` did not.
WS_MD = " \t"


def yaml_field_re(key, value=True):
    """`^ -? key:` with WS_ANY, for the scans that feed checks 12 to 15.

    The same shape as the `^\\s*-?\\s*key:` these replace, and the same reason as
    everywhere else, arriving the other way round from the one you expect.
    Python's `\\s` does NOT cover U+FEFF, so a critic hid an `access:
    credentialed` line from check 12 by putting one in front of it, and shipped
    a login-gated input with no binding and no slot. `scripts/validate.py` said
    PASS. The Python-only characters do not evade, because widening Python's
    skip makes the scan match MORE lines, which is the fail-closed direction.
    These checks have no twin on the site, so this is a single-gate hole rather
    than a parity split, and it was open on main."""
    head = "^[%s]*-?[%s]*" % (WS_ANY, WS_ANY)
    tail = ":[%s]*([^%s]+)" % (WS_ANY, WS_BOTH) if value else ":[%s]*(?:#.*)?$" % WS_ANY
    return re.compile(head + re.escape(key) + tail)


SLOT_ID = yaml_field_re("id")
ACCESS = yaml_field_re("access")
ACCESS_DANGLING = yaml_field_re("access", value=False)
BINDING = yaml_field_re("binding")
FIDELITY = yaml_field_re("fidelity")
KEEPS = re.compile("^[%s]*keeps:" % WS_ANY)

# A YAML list item, WS_ANY on both sides, twin of LIST_ENTRY in
# the upload endpoint's validator. Where an entry STARTS decides which capability_ref is
# paired with which status, so the two gates must split a block in the same
# places or 16a compares different things.
LIST_ENTRY = re.compile("^[%s]*-[%s]" % (WS_ANY, WS_ANY))
SECTION_BOUNDARY_RE = re.compile(r"^#{1,2}[ \t]")
# What a heading and a table row LOOK like to the summary reader, twins of
# ANY_HEADING and TABLE_ROW_MD in the upload endpoint's section parser. `[ \t]` for the same
# reason as SECTION_BOUNDARY_RE: it is what CommonMark means, and a wider class
# would call more lines structure than any renderer does.
ANY_HEADING_RE = re.compile(r"^#{1,6}[ \t]")
TABLE_ROW_RE = re.compile(r"^[ \t]*\|")


# THE FENCE DELIMITER, and its alphabet is NARROW on purpose, which is the
# opposite width from WS_ANY above and for the same reason.
#
# A wider whitespace class here matches MORE lines as fences, which means more
# lines are treated as prose or as block-scalar content and FEWER declarations
# are seen. That is the fail-OPEN direction, so this class must be as narrow as
# the format allows rather than as wide as possible. Skipping whitespace before
# a key is the reverse: wider there means more declarations seen.
#
# `[ \t]` is also what a Markdown renderer means. Neither \ufeff``` nor \x1c```
# opens a code block in CommonMark, so a gate that called either one a fence
# would disagree with every renderer that will ever show this document, and a
# critic used exactly that on 2026-09-07: with the fence flag deciding which
# lines may open a block scalar, `\ufeff```` in the prose below section 3 made
# the site accept a passport carrying email.send at status: used with every
# consent row saying yes, while this file refused it. The \x1c spelling split
# them the other way.
FENCE_DELIM = re.compile(r"^[ \t]*(`{3,})")

# THE TRIPWIRE, and it is the same shape as the one on the consent table.
#
# Narrowing the fence class to `[ \t]` was right and it introduced a cost I had
# to be shown. A leading U+FEFF before a fence, which is what a Windows editor
# emits, stopped being a fence to BOTH gates, and the two then disagreed about
# the consequences: this file read on and PASSED, while the site refused with
# E_GOLDEN_COUNT, a message about golden examples that says nothing about a
# byte-order mark. On main both gates accepted it, so the narrowing introduced
# this and nothing else did.
#
# Refusing outright beats widening the class back, because a Markdown renderer
# will not open a code block there either: widening would put the gates back in
# disagreement with every reader of the same file. This way the author is told
# the actual problem, once, in the place it is.
FENCE_LOOSE = re.compile("^[%s]*(`{3,})" % WS_ANY)


def yaml_scalar_re(key, anchored=False):
    """A compiled `key: value` reader built from the classes above.

    `anchored` adds the line start and an optional list dash, which is what the
    section-wide capability_ref scan needs and what the block-scoped reads,
    which run over a line that has already been placed, do not."""
    head = "^[%s]*(?:-[%s]*)?" % (WS_ANY, WS_ANY) if anchored else ""
    return re.compile(head + re.escape(key) + ":[%s]*([^%s]+)" % (WS_ANY, WS_BOTH))


CAPABILITY_REF = yaml_scalar_re("capability_ref")
CAPABILITY_REF_LINE = yaml_scalar_re("capability_ref", anchored=True)
STATUS = yaml_scalar_re("status")
COMPARISON_MODE = yaml_scalar_re("comparison_mode")


def scalar(v):
    """A YAML scalar as written by our own regexes, minus ONE matched quote pair.

    A single matched pair, deliberately, and not `.strip("\"'")`. The loose form
    was the convention here before this helper existed and it is wrong about
    YAML in three ways, all of which make this validator MORE permissive than
    the upload endpoint, which is the direction that ends with a passport this
    tool called valid and the publish path refuses:

        input           .strip("\"'")   YAML actually means      one pair
        "\'x\'"          x              the string \'x\', quotes and all
                                                                 \'x\'
        "x              x              nothing, it is unbalanced  "x
        "               (empty)        nothing, it is unbalanced  "

    Only the third column is right, and only the fourth column agrees with the
    twin of this function in the upload endpoint's own validator. The two are
    the same gate at two different doors and they have to mean the same thing;
    a value this one accepts and that one refuses is a passport its owner
    cannot publish, for a reason no message they see will explain.
    """
    # Stripped with WS_BOTH rather than str.strip(), which uses Python's `\s`
    # and would remove a \x85 that the site's .trim() keeps. The value class
    # already excludes everything both engines call whitespace, so this only
    # ever has work to do when a caller hands over something it did not read.
    v = v.strip(WS_BOTH_CHARS)
    m = re.match(r'^(["\'])(.*)\1$', v, re.S)
    return m.group(2) if m else v

def _near_delimiter(line):
    """Describe a line that is `---` plus whitespace of either engine's width.

    Returns None when the line is not a near miss, so the caller falls back to
    the plain message. Used only to name what the owner has to delete."""
    core = line.strip(WS_ANY_CHARS)
    if core != "---" or line == "---":
        return None
    extra = [c for c in line if c != "-"]
    names = ", ".join(sorted({"U+%04X" % ord(c) for c in extra}))
    if line.startswith("---"):
        return "is followed by whitespace (%s)" % names
    if line.endswith("---"):
        return "is preceded by whitespace (%s)" % names
    return "is wrapped in whitespace (%s)" % names


def parse_frontmatter(text):
    """Parse frontmatter between --- delimiters. Returns (pairs_dict, error_msg)."""
    lines = text.split("\n")
    # EXACT comparison, no trim of any width, because that is what the site
    # does (`lines[0] !== '---'` in the endpoint's validator) and it is the reading that
    # refuses. The sentence this replaces said "WS_MD in all three places, and
    # the JS twin compares exactly, which is the same width", and it was
    # false: WS_MD is " \t", so `--- ` with one trailing space passed here and
    # was refused on upload with E_FRONTMATTER. A named class on a comparison
    # the other side does not trim at all is a divergence test 19 cannot see,
    # since it scans for BARE primitives and takes a class name as reviewed.
    # Earlier, a NON-BREAKING SPACE after the closing `---` was the same split
    # one class wider; NBSP is what a word processor emits, so a trailing space
    # or NBSP after `---` is the likeliest of these shapes to reach a real
    # owner, which is why the message names the line and the character
    # (2026-09-08).
    if not lines or lines[0] != "---":
        near = _near_delimiter(lines[0]) if lines else None
        if near:
            return None, f"line 1: the opening --- {near}; the site compares it exactly, so delete everything on that line except the three dashes"
        return None, "File does not start with ---"

    close_idx = None
    # 40, not 41. "Within the first 40 lines" means indices 1..39, which is
    # what the endpoint's validator scans (`i < Math.min(lines.length, 40)`). This
    # scanned one line further, so a passport whose closing --- sits on the
    # 41st line passed here and was refused on upload with E_FRONTMATTER.
    # Found by a critic; no Unicode involved, just the bound.
    for i in range(1, min(len(lines), 40)):
        if lines[i] == "---":
            close_idx = i
            break

    if close_idx is None:
        for i in range(1, min(len(lines), 40)):
            near = _near_delimiter(lines[i])
            if near:
                return None, f"line {i + 1}: the closing --- {near}; the site compares it exactly, so delete everything on that line except the three dashes"
        return None, "Second --- not found within the first 40 lines"

    fm_lines = lines[1:close_idx]
    pairs = {}
    for line in fm_lines:
        colon = line.find(":")
        if colon == -1:
            continue
        # WS_BOTH, not str.strip(): the twin in the upload endpoint's validator uses
        # .trim(), and a frontmatter value with a trailing \x85 was one value
        # here and a different one there. Neither side may remove what the
        # other keeps.
        key = line[:colon].strip(WS_BOTH_CHARS)
        val = line[colon + 1:].strip(WS_BOTH_CHARS)
        # Strip surrounding quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        pairs[key] = val

    return pairs, None


def get_body(text):
    """Return body text after the closing --- of frontmatter."""
    lines = text.split("\n")
    # Exact, the same reading as parse_frontmatter and the site. get_body runs
    # only after check 1 passed, so the two never disagree on a live document,
    # and keeping them spelled the same is what stops that being true only by
    # accident.
    for i in range(1, min(len(lines), 40)):
        if lines[i] == "---":
            return "\n".join(lines[i + 1:])
    return ""


def fence_flags(lines):
    """True for every line inside a fenced block, delimiters included.

    The CommonMark length rule: a fence closes only on a delimiter run at
    least as long as the one that opened it. FENCE_DELIM is the WS_MD reader,
    so an opener carrying an invisible character does not open a block here;
    check 8a refuses that file before anything calls this.

    Named rather than inlined because there are now four implementations of
    this walk across two languages: spec_lines() here, this, the copy in
    the page renderer (which imports nothing on purpose) and
    fenceMap() in the upload endpoint's validator. Test 17 runs all four over the same
    documents and requires the same answer line for line. Two implementations
    of one rule drift; four drift faster.
    """
    flags = [False] * len(lines)
    open_len = None
    for i, line in enumerate(lines):
        m = FENCE_DELIM.match(line)
        if m:
            if open_len is None:
                open_len = len(m.group(1))
            elif len(m.group(1)) >= open_len:
                open_len = None
            flags[i] = True
        else:
            flags[i] = open_len is not None
    return flags


def consent_window(body):
    """The lines of section 2: after its heading, before the next heading.

    This is section_lines() in the page renderer and sectionLines()
    in the upload endpoint's section parser, written a third time, and it is a separate
    function so that the test suite can hold the two Python spellings equal line
    for line over every fixture rather than trusting a comment that says they
    agree. The parity harness already holds the Python renderer and the JavaScript one
    equal, so the two tests together make all three agree.

    Returns None when there is no section 2, or when `## 3. Functional spec`
    is missing or precedes it: that is a shape failure the caller reports
    rather than a window it can slice.
    """
    lines_body = body.split("\n")
    body_fenced = fence_flags(lines_body)

    def heading_at(title):
        for i, line in enumerate(lines_body):
            if not body_fenced[i] and structural_trim(line) == title:
                return i
        return -1

    start_line = heading_at("## 2. What it needs from you")
    sec3_line = heading_at("## 3. Functional spec")
    if start_line == -1 or sec3_line == -1 or sec3_line < start_line:
        return None

    # END AT THE NEXT HEADING, NOT AT THE NEXT NUMBERED ONE.
    #
    # This ended the slice at the literal `## 3. Functional spec`. Both
    # renderers end a section at the next level-1 or level-2 heading outside a
    # fence, whatever it is, against SECTION_BOUNDARY. So a stray `## Notes`
    # between sections 2 and 3 put this window and theirs out of step, and this
    # one was LARGER: the gate validated a sixth consent row that neither
    # renderer publishes, and on a malformed stray line it refused the owner's
    # consent table by number while every row the owner could see had five
    # columns. Fail-closed, which is why it was filed rather than hotfixed.
    #
    # the page renderer section() already carried this exact correction in
    # its own docstring: found and fixed in one implementation, left in the
    # other. Requiring `## 3.` to exist and to follow `## 2.` is the SHAPE
    # check and stays; it no longer decides where the slice stops.
    end_line = sec3_line
    for i in range(start_line + 1, sec3_line):
        if not body_fenced[i] and SECTION_BOUNDARY_RE.match(lines_body[i]):
            end_line = i
            break
    return lines_body[start_line + 1:end_line]


def consent_rows(body):
    """Return the data rows of the section 2 consent table, as lists of cells.

    Returns None when there is no table there at all, which is its own failure
    rather than a table with no rows, and ("STRAY", line) when a line LOOKS like
    a row under the widest whitespace reading and is not one under WS_MD. See
    the note beside `strays`: that shape published a page with a consent row
    missing and no error on either gate."""
    # STRUCTURAL, not a substring search, and this is not a tidy-up.
    #
    # This was `body.find("## 2. What it needs from you")`. A raw substring
    # search finds the heading wherever it appears, including inside a code
    # fence, and until this function became fence-sensitive that was harmless:
    # the slice started early, the table was still in it, and the reader was
    # position-blind. Making it fence-aware turned that into a live defect,
    # because a slice starting mid-fence reads that block's CLOSING backticks
    # as an OPENER and Python's fence parity is inverted against the site's
    # for the whole of section 2, with no invisible character anywhere for
    # check 8a to catch.
    #
    # A critic built two documents. One is an honest passport the site accepts
    # and this refused. The other passes BOTH gates while each reads a
    # DIFFERENT consent table: Python stored "Read a web page" and the site
    # stored "Read your mail", zero errors on either side. That is the exact
    # shape this whole line of work exists to close, and the fence-skipping
    # commit created it. The page renderer's JavaScript never had it, because it slices with
    # sectionLines(), which is structural. So does this now, through the same
    # function the renderer's twin is held equal to.
    #
    # The window itself is consent_window() above, which is where the 2026-09-09
    # correction lives and where the heading-offset arithmetic that used to sit
    # here has gone: it computed character offsets to slice a string that was
    # split back into lines two statements later, and it made this function the
    # third place in the repo that decided where a section ends.
    raw = consent_window(body)
    if raw is None:
        return None

    # WS_MD, not str.strip(). A table row is Markdown structure, so it takes
    # the narrow class, and narrow is fail-closed here for the usual reason:
    # fewer lines read as rows makes the table SHORTER, and a short table is
    # refused by check 11 rather than published with a row missing.
    #
    # A critic put one \x85 in front of one row of the example passport. Python
    # stripped it, JavaScript did not, and BOTH GATES ACCEPTED the file while
    # the stored record carried five consent rows instead of six: "Read your
    # calendar" simply gone from the table the reader consents to, with no
    # error anywhere. That is not a gate split, it is a wrong page, and
    # the page renderer already names it as the one failure this
    # table exists to prevent.

    # FENCE AWARENESS, and both the row filter and the tripwire below get it.
    # A consent row is a table row; a line inside a code fence is not one
    # however much it looks like a pipe table. Copy a shell pipeline out of a
    # rendered web page into section 2 and its continuation lines start
    # `| jq -r ...`, which this function read as a row with two columns and
    # refused. That is an honest passport refused, it predates the tripwire,
    # and both gates did it, so nothing about parity would have found it.
    #
    # The tripwire made it worse rather than causing it. Web-pasted code
    # routinely carries U+00A0 where it was indented, so the fenced line hit
    # the loose test first and the refusal said: delete the character before
    # the pipe. It is inside a code block, it is content the owner pasted, and
    # deleting it does not fix the passport, because the ordinary-space
    # version fails too. A confusing refusal turned into a confident wrong
    # instruction, which is the worse of the two.
    #
    # FENCE_DELIM is the WS_MD reader on purpose. An opener carrying an
    # invisible character does not open a fence here, and check 8a refuses
    # that file before this function is reached, so the narrow reader cannot
    # be used to smuggle a row past the tripwire by hiding it in a block that
    # only one engine thinks is open.
    fenced = fence_flags(raw)
    raw = [l for i, l in enumerate(raw) if not fenced[i]]

    lines = [l.strip(WS_MD) for l in raw]
    table = [l for l in lines if l.startswith("|")]
    # A LINE THAT LOOKS LIKE A ROW TO ANY READER MUST BE ONE TO THIS READER.
    #
    # Converging the two gates on WS_MD made them agree about \x85| Read your
    # calendar |: neither reads it as a row. They then agree on a table with
    # five rows where the author wrote six, and the page renders the reader a
    # consent table with a capability missing and no error anywhere. Agreement
    # is not the goal; the goal is that a passport says what the agent does.
    #
    # So the loose reading is used as a TRIPWIRE rather than as the rule. If a
    # line starts with a pipe once every character either engine calls
    # whitespace is removed, and it did not survive the strict strip, the table
    # is malformed and the passport is refused with the line quoted.
    strays = [l for l in raw
              if l.strip(WS_ANY_CHARS).startswith("|")
              and not l.strip(WS_MD).startswith("|")]
    if strays:
        return "STRAY", strays[0]
    if len(table) < 3:          # header, divider, at least one row
        return None
    if not re.match(r"^\|?[ \t:|-]+\|?$", table[1]):
        return None

    def cells(row):
        r = row.strip(WS_MD)
        if r.startswith("|"):
            r = r[1:]
        if r.endswith("|"):
            r = r[:-1]
        return [c.strip(WS_MD) for c in r.split("|")]

    if len(cells(table[0])) != 5:
        return None
    return [cells(r) for r in table[2:] if any(cells(r))]


def spec_lines(text):
    """Return [(line_number, line, inside_fence)] for '## 3. Functional spec'.

    The third element is True for a line that is INSIDE the fenced YAML, and
    False for the fence delimiters themselves and for any Markdown prose in the
    section. It is returned rather than recomputed downstream because two
    machines walking the same lines with different fence rules is a defect
    class, not a detail: a critic desynchronised exactly that on 2026-09-07 by
    putting a three-backtick fence inside a four-backtick one. This function
    closes a fence only on a delimiter at least as long as the one that opened
    it, so the inner one is content; a second reader that toggled on every
    delimiter believed the opposite, and the disagreement put a declared
    `email.send` at `status: used` in front of a reader as an installable row.

    Line numbers are 1-based over the whole file, because that is what the
    person fixing the file sees in their editor.

    Fence-aware for the same reason check 8 is, and the two are the same walk:
    section 3 is itself one fenced YAML block, and a tacit note or a value
    quoting a '## ' heading must not end the section it sits inside. Scoping
    checks 12 and 13 to this slice is deliberate. Section 5 carries installer
    text that nobody here wrote, and a delta phrase in a branch appendix must
    never be read as a claim about this agent."""
    lines = text.split("\n")
    out, started, fence_len = [], False, None
    for i, line in enumerate(lines):
        match = FENCE_DELIM.match(line)
        if match:
            before = fence_len
            if fence_len is None:
                fence_len = len(match.group(1))
            elif len(match.group(1)) >= fence_len:
                fence_len = None
            if started:
                # A DELIMITER of the outer fence is not itself YAML; a SHORTER
                # fence inside a longer one is, because it did not close
                # anything. That is the length rule this function has always
                # had, and the third element exists so that nothing downstream
                # has to reimplement it. See strip_block_scalar_content().
                out.append((i + 1, line, before is not None and fence_len is not None))
            continue
        if fence_len is None:
            if not started:
                if structural_trim(line) == "## 3. Functional spec":
                    started = True
                continue
            if SECTION_BOUNDARY_RE.match(line):
                break
        if started:
            out.append((i + 1, line, fence_len is not None))
    return out


def yaml_block(entries, key):
    """Return the [(n, line)] of a top-level `key:` block from spec_lines().

    Top level means column 0 inside the fenced YAML, which is how every key in
    the schema is written. The block runs to the next non-blank line in column
    0, so the closing fence ends it like any other. A list written with its
    dashes in column 0 is legal YAML and continues the block.

    Deliberately not a YAML parse. This file has no dependencies and takes none
    for two checks, and a partially valid passport must still produce a useful
    message rather than a parser traceback."""
    # Accepts spec_lines()'s three-element entries and emits two-element ones:
    # every line of a YAML block is YAML, so the fence flag has done its work by
    # the time a block has been picked out and would only be noise downstream.
    out, inside = [], False
    for entry in entries:
        n, line = entry[0], entry[1]
        if re.match(r"^" + re.escape(key) + r":", line):
            inside = True
            out.append((n, line))
            continue
        if inside:
            # WS_ANY on both halves, not str.strip() and str.isspace(), which
            # are Python's `\s` and differ from the site's. See yaml_trim().
            stripped = yaml_trim(line)
            if stripped and line[:1] not in WS_ANY_CHARS and not stripped.startswith("-"):
                break
            out.append((n, line))
    return out


# A key whose value is a YAML block scalar: `note: |`, `what: >-`, `why: |+2`.
# Everything indented under one of these is TEXT, not fields.
#
# GROUP 1 IS EVERYTHING BEFORE THE KEY, dash and its spaces included, so its
# length is the COLUMN OF THE KEY. That is where YAML measures the block's
# content from, and measuring anywhere else is exploitable: the first version
# computed dash + 2 spaces, so `-   note: |` (three spaces) measured 4 while
# YAML measured 6, and two real sibling keys at column 6 were eaten as prose. A
# critic built that on 2026-09-07 against valid YAML, confirmed the declaration
# with PyYAML, and it flipped a passport declaring email.send at status: used
# from refused to accepted. Never assume the separator is one character wide.
#
# INDENTATION IS SPACES, and the leading class is `[ ]` rather than `\s`. YAML
# forbids a tab in indentation, and `\s` differs between the two runtimes: on
# the same line, Python's lstrip() eats \x1c, \x1e and \x85 while JavaScript's
# /^\s+/ does not, and JavaScript's eats U+FEFF while Python's does not. That
# is not a theoretical divergence: `\x1c- capability_ref: email.send` under a
# block scalar was eaten by this side and read by the other.
BLOCK_SCALAR_KEY = re.compile(r"^( *(?:-[ ]+)?)[A-Za-z_][A-Za-z0-9_.-]*: *[|>][-+]?[0-9]* *$")


def yaml_indent(line):
    """The line's YAML indentation: the count of leading SPACE characters.

    Not len(line) - len(line.lstrip()). Python's whitespace set and
    JavaScript's disagree on nine of thirty shapes measured, and a rule the two
    gates must agree on cannot be built on a set neither language pins. A tab
    or a control character in the indent position is not YAML indentation, so
    it counts as column 0 and closes any open block, which is the fail-closed
    direction: the line is READ as a field rather than skipped as prose."""
    return len(line) - len(line.lstrip(" "))


def strip_block_scalar_content(entries):
    """Drop the lines that are the CONTENT of a YAML block scalar.

    Returns [(n, line)] with the opening key kept and everything indented under
    it removed. `note: |` stays; the prose beneath it goes.

    ONE MECHANISM, TWO CALLERS, and that is the whole point of it existing.
    input_entries() carried this logic inline from 2026-09-03, when a passport
    whose `note: |` quoted the line `access: credentialed` was refused for a
    field it did not have. The identical defect sat untouched in check 16's
    wide `capability_ref` scan for four more days, because the repair was
    written into the function that had the bug rather than into a rule the
    other reader could share. An owner quoting `capability_ref: email.send` at
    the start of a line inside `tacit_notes` was refused as declaring it, with a message naming a declaration the file does not contain,
    whose implied remedy would have made the passport lie about the agent.

    Both prior repairs to that scan were narrowings: first anchoring the match
    to a line start, then this. A text scan over a region the spec DEFINES as
    free prose is not fixed by a narrower match, it is fixed by not reading the
    prose. `tacit_notes` is the owner's words "verbatim, quoted not
    paraphrased" and vocabulary.md rule 5 sends capture there when no id fits,
    so it is simultaneously the place most likely to name a capability in
    prose and the place we have promised not to reword.

    The rule is YAML's own: content is whatever is indented strictly deeper
    than the key that opened the block, and the block ends at the first line
    that is not. Blank lines inside a block are content. The dash of a list
    entry is stepped over so `- what: |` measures from `what` rather than from
    the dash, which is where YAML measures it too.

    KNOWN HOLE, the same one input_entries names and it is NOT closed here
    either: a multi-line QUOTED scalar (`note: "...` continued on the next
    line) is not a block scalar, so its continuation lines are still read as
    fields. Closing that means parsing YAML rather than matching it."""
    out = []
    block_indent = None
    for entry in entries:
        n, line = entry[0], entry[1]
        # THE CALLER SAYS WHICH LINES ARE YAML, and this function runs no fence
        # machine of its own. Two entries mean "all of it is YAML", which is
        # true of the block input_entries() is handed.
        in_yaml = entry[2] if len(entry) > 2 else True
        if block_indent is not None:
            # WS_ANY, not str.strip(), and the WIDE class here even though
            # "blank means still inside the block" reads like the hiding
            # direction. Three things settle it against my own rule of thumb,
            # and I had it the other way round until a critic pushed:
            #
            # 1. A blank line cannot extend a block past a DEDENT. The next
            #    non-blank line is still measured against the key column, so a
            #    wider blank hides nothing that a narrower one catches, except
            #    a line indented UNDER the block, which is block content by
            #    every reading anyway.
            # 2. PyYAML puts the ref INSIDE the scalar for a lone \x85 line:
            #    NEL is a line break to YAML, so the narrow reading refuses a
            #    document a real parser calls honest, with the exact 2026-09-07
            #    message that names a declaration the file does not contain.
            #    \x1c and \ufeff make the document invalid YAML outright, so
            #    the gate's behaviour on them is policy rather than correctness.
            # 3. The control that settles the security half: a passport with
            #    the declaration simply DELETED already passes, on main and
            #    here. Hiding one behind an invisible line buys an attacker
            #    nothing that deleting it does not buy more cheaply. That is
            #    hole 2 of spec section 7, which no validator closes.
            #
            # Narrow here converged the two gates too, so this is not a parity
            # choice; both widths agree. It is a choice about which converged
            # verdict is the honest one.
            if not line.strip(WS_ANY_CHARS):
                continue                                   # blank: still inside
            if yaml_indent(line) > block_indent:
                continue                                   # deeper: still inside
            block_indent = None                            # dedent: block closed
        out.append(entry)
        if not in_yaml:
            continue               # a delimiter, or Markdown prose: opens nothing
        m = BLOCK_SCALAR_KEY.match(line)
        if m:
            block_indent = len(m.group(1))   # the COLUMN OF THE KEY, see above
    return out


def input_entries(block):
    """Split an `inputs:` block into one list of lines per entry.

    Lines that are the CONTENT of a block scalar are dropped, because they are
    prose and not fields. Without this, a passport that says

        note: |
          an earlier draft wrote
          access: credentialed
          and we kept the sentence

    has that middle line read as a real `access` field by every check that
    walks these entries. It is legal YAML and the passport is correct, and it
    was refused. Verified against `main` on 2026-09-03: main refuses the
    `access: credentialed` form, so this is an existing defect being closed
    here rather than a new one, and the same line protects checks 12, 14 and
    15 alike.

    The rule is YAML's own: content is whatever is indented strictly deeper
    than the key that opened the block, and the block ends at the first line
    that is not. Blank lines inside a block are content. The dash of a list
    entry is stepped over so `- what: |` measures from `what` rather than from
    the dash, which is where YAML measures it too.

    KNOWN HOLE, named here because it is the same class and is NOT closed.
    Flow style puts a whole entry on one line:

        - {what: a wire service, access: credentialed, tag: wire}

    Every check that walks these entries reads one line at a time and looks for
    a key at the start of it, so a credentialed input written this way escapes
    the binding requirement. This validator and the hosted one both miss it.
    Raised by a critic on 2026-09-03 while confirming the dangling-key fix: the
    dangling hole is closed, the one-line-at-a-time assumption underneath it is
    not. Closing it means parsing YAML rather than matching it, which is a
    larger decision than this change."""
    entries, current = [], None
    for n, line in strip_block_scalar_content(block[1:]):
        if LIST_ENTRY.match(line):
            if current:
                entries.append(current)
            current = [(n, line)]
        elif current is not None:
            current.append((n, line))
    if current:
        entries.append(current)
    return entries


def delta_phrase(line):
    """Return the delta phrase this line contains, or None.

    Punctuation is collapsed before matching so "period-over-period" and
    "vs. prev" need no separate entries. Each phrase is anchored on the left at
    a word boundary and left open on the right, so "previous run" also catches
    "previous runs" without the list carrying every plural.

    A phrase that names something rather than claiming it does not count. "the
    section headed Week over week appears exactly once" is a structural check
    about a heading's text, judged from one output, and refusing it taught the
    author to rename their section rather than to declare a memory. So a match
    introduced by headed, titled, named, called, labelled or the word section or
    heading is read as a reference to the output's own furniture."""
    norm = re.sub(r"[^a-z0-9]+", " ", line.lower())
    for phrase in DELTA_PHRASES:
        for m in re.finditer(r"\b" + re.escape(phrase), norm):
            before = norm[:m.start()].rstrip().rsplit(" ", 2)
            if any(w in ("headed", "titled", "named", "called", "labelled",
                         "labeled", "section", "heading", "column")
                   for w in before[-2:]):
                continue        # naming a section, not claiming a comparison
            return phrase
    return None


# ---- Stage 3: untrusted content, checks 17 to 19 ----
#
# The upload endpoint's third stage, ported from the upload endpoint's validator, which is
# what the upload endpoint calls. Until 2026-09-21 this file had
# none of it, so a passport printed PASS here and was refused on
# upload for an HTML comment, a tag, an unfilled <placeholder> or a
# javascript: link, and at least one wrong report to Raffael came out of that.
#
# ONE DELIBERATE DIFFERENCE IN DIRECTION, RULED BY RAFFAEL. The tag scan and the
# comment scan both skip fenced lines here. The endpoint's tag scan always has
# ("fenced content is text, and is escaped on render"); its comment scan did
# not, and refused his own 2026-09-16 capture over a comment inside a fenced
# golden example, which is real agent output. He ruled on 2026-09-21 that the
# gates converge on the fenced reading (the change of 2026-09-21, direction A), and the endpoint's
# comment scan got the same guard the same day.
#
# The active-content scan mirrors the endpoint exactly as it is, with NO fence
# guard: it runs over the whole text, not line by line. That is out of scope
# for this change and stays so until someone shows it refuses a real capture.
#
# REGEX DIALECT. The patterns below are the endpoint's, spelled so Python gives
# JavaScript's answer. JS `\s` is not Python `\s`: JS includes U+FEFF and
# excludes U+001C..U+001F, Python the reverse, measured on 2026-09-21 over every
# BMP codepoint. So `\s` is written out as JS_S. And JS `/i` without the u flag
# folds ASCII only, while Python's re.I folds dotless i, long s and the Kelvin
# sign onto ASCII, so `javascrıpt:` would be refused here and accepted there;
# hence re.I | re.A.
JS_S = "\t\n\x0b\x0c\r \xa0  -     　﻿"
INSTALLER_PLACEHOLDER = "<!-- installer core and branches inserted on upload -->"
HTML_ELEMENTS = frozenset("""
a abbr address area article aside audio b base bdi bdo blockquote body br button
canvas caption cite code col colgroup data datalist dd del details dfn dialog div
dl dt em embed fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 head
header hgroup hr html i iframe img input ins kbd label legend li link main map
mark menu meta meter nav noscript object ol optgroup option output p param
picture pre progress q rp rt ruby s samp script search section select slot small
source span strong style sub summary sup svg table tbody td template textarea
tfoot th thead time title tr track u ul var video wbr
""".replace("\n", " ").split(" ")) - {""}
HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*([%s][^>]*)?>" % JS_S)
HTML_TAG_NAME = re.compile(r"[A-Za-z][A-Za-z0-9-]*")
JS_S_RE = re.compile("[%s]" % JS_S)
ACTIVE_URIS = ((re.compile(r"javascript:", re.I | re.A), "javascript: URI"),
               (re.compile(r"vbscript:", re.I | re.A), "vbscript: URI"),
               (re.compile(r"data:text/html", re.I | re.A), "data:text/html URI"))
# The link text is bounded at 256 for the endpoint's reason: unbounded, it is
# quadratic on a body of unmatched "[" (27.8 s against 107 ms at the size cap).
MD_LINK = re.compile(r"!?\[[^\]]{0,256}\]\([%s]*([^)%s]+)" % (JS_S, JS_S))
LINK_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
INSTALLER_HEADING = "## 5. Installer"
LOSSES_HEADING = "## 6. Losses"
INSTALLER_CORE_H1 = re.compile(r"^# Installer core v[0-9]")


def is_placeholder(raw):
    """Angle-bracketed prose a capture left behind, as opposed to a tag.

    The endpoint's isPlaceholder(). It only decides which of two refusals the
    owner reads, E_HTML or E_UNFILLED; the verdict is the same either way."""
    if raw.startswith("</"):
        return False
    inner = raw[1:-1]
    if inner.endswith("/"):
        inner = inner[:-1]
    name = HTML_TAG_NAME.match(inner).group(0).lower()
    if name not in HTML_ELEMENTS:
        return True
    return bool(JS_S_RE.search(inner)) and "=" not in inner


def assembled_installer_lines(lines, inside):
    """Line indices of an assembled installer, which stage 3 does not scan.

    The endpoint never sees this text. A passport is uploaded with the one
    INSTALLER_PLACEHOLDER line in section 5 and the site inserts the installer
    after validating. But scripts/assemble.py produces the other form, section
    5 replaced by references/installer-core.md and a branch, and the verification loop
    requires this file to PASS it. The installer is our own prose and carries
    unfenced <name>, <url> and <path> as instructions to the reader: 19 of them
    in the assembled example on 2026-09-21, every one of which the endpoint's
    rules would call unfilled.

    Recognised positively, not by position: section 5, bounded by its heading
    and the losses heading outside fences, is skipped only when it does NOT
    carry the placeholder and its first non-blank line is the installer core's
    own title. A section 5 of anything else is scanned like every other line.

    WHAT THIS GIVES AWAY, stated so nobody reads it as parity. A passport whose
    section 5 opens with "# Installer core v0.1" and then carries HTML is
    accepted here and refused by the endpoint. That is the direction that
    costs an owner a surprise refusal rather than a leak, it needs the
    installer's title typed by hand, and the endpoint still refuses it."""
    start = end = None
    for i, line in enumerate(lines):
        if inside[i]:
            continue
        t = structural_trim(line)
        if start is None and t == INSTALLER_HEADING:
            start = i
        elif start is not None and t == LOSSES_HEADING:
            end = i
            break
    if start is None or end is None:
        return set()
    region = range(start + 1, end)
    if any(INSTALLER_PLACEHOLDER in lines[i] for i in region):
        return set()
    first = next((lines[i] for i in region if lines[i].strip(WS_ANY_CHARS)), "")
    if not INSTALLER_CORE_H1.match(first):
        return set()
    return set(region)


def gate_reading(raw):
    """The file as the upload endpoint's transport() hands it to validate().

    transport() removes up to two leading BOMs, rewrites CRLF to LF, and does
    nothing else. The two BOMs are one each from TextDecoder, which drops a
    leading BOM while decoding unless told ignoreBOM, and from transport()'s
    own charCodeAt(0) === 0xFEFF test; a third survives. A lone CR survives
    too (the control-character class skips 0x0D). Python's default read
    turns a lone CR into a line break, so `Note.\\r```` became a fence line
    here and not there, and a tag after it was fenced here and refused
    there. A critic built exactly that: PASS here, E_HTML on upload.
    Round 1, 2026-09-21."""
    for _ in range(2):
        if raw.startswith("\ufeff"):
            raw = raw[1:]
    return raw.replace("\r\n", "\n")


def md_links(text):
    """The endpoint's LINK matches, in order, with its bound measured its way.

    JavaScript's {0,256} counts UTF-16 code units, so an astral character such
    as an emoji costs two, and Python's counts code points. A label of 129 to
    256 emoji was therefore a link to Python and not to the gate, and a
    critic got FAIL 19 here and ACCEPT there on `[` + 200 emoji + `](file:..)`.
    Python's bound is the looser one, so every gate match is also a match
    here; a match whose label is over 256 units is one the gate never made at
    that position, and the gate goes on to try the next character, which can
    find a shorter link inside the label. So does this."""
    pos = 0
    while True:
        m = MD_LINK.search(text, pos)
        if m is None:
            return
        label = m.group(0)[m.group(0).index("[") + 1:m.group(0).index("](")]
        if len(label.encode("utf-16-le")) // 2 <= 256:
            yield m
            pos = m.end()
        else:
            pos = m.start() + 1


def untrusted_content(text):
    """Checks 17 to 19: the endpoint's stage 3. Returns a list of FAIL lines."""
    lines = text.split("\n")
    inside = fence_flags(lines)
    skip = assembled_installer_lines(lines, inside)
    out = []

    tags, holes, comments = [], [], []
    for i, line in enumerate(lines):
        if i in skip or inside[i] or INSTALLER_PLACEHOLDER in line:
            continue
        for m in HTML_TAG.finditer(line):
            (holes if is_placeholder(m.group(0)) else tags).append(
                "line %d: %s" % (i + 1, m.group(0)))
        if "<!--" in line:
            comments.append("line %d: HTML comment" % (i + 1))
    if tags or comments:
        shown = tags[:20] + comments[:20]
        out.append(
            "FAIL 17: the passport contains HTML, which the upload endpoint "
            "refuses (E_HTML): " + "; ".join(shown) + ". A passport is "
            "Markdown only. Inside a fenced code block HTML is text and is "
            "allowed; outside one, remove it.")
    if holes:
        out.append(
            "FAIL 18: the capture did not finish, and the upload endpoint "
            "refuses it (E_UNFILLED): the template's own placeholders are "
            "still here: " + "; ".join(holes[:20]) + ". Replace each with the "
            "real thing. If they are the losses table in section 6, delete "
            "the placeholder row and leave the table empty.")

    scanned = "\n".join("" if i in skip else l for i, l in enumerate(lines))
    active = [what for rx, what in ACTIVE_URIS if rx.search(scanned)]
    for m in md_links(scanned):
        scheme = LINK_SCHEME.match(m.group(1))
        if scheme and scheme.group(1).lower() not in ("https", "http", "mailto"):
            active.append(scheme.group(1) + ": link target")
    if active:
        seen = list(dict.fromkeys(active))[:10]
        out.append(
            "FAIL 19: the passport contains a link or URI that can execute "
            "code, which the upload endpoint refuses (E_ACTIVE_CONTENT): "
            + ", ".join(seen) + ". This check reads fenced code too.")
    return out


def validate(text, gate_text=None):
    """Run every check. Return list of error strings.

    gate_text is the file as the upload endpoint reads it, for checks 17 to
    19 only; see gate_reading(). A caller that has only `text` gets stage 3
    over `text`, which is the old behaviour and differs only on a lone CR."""
    errors = []

    # Check 1: frontmatter delimiters
    pairs, fm_err = parse_frontmatter(text)
    if fm_err:
        errors.append(f"FAIL 1: {fm_err}")
        return errors

    # Check 2: required keys
    # PRESENT AND EMPTY IS MISSING, which is what the site has always said and
    # this file did not. `title: <U+FEFF>` and `title: <U+00A0>` are a title
    # whose whole value is one invisible character; after the WS_BOTH trim above
    # the value is the empty string. scripts/validate.py passed both, the upload
    # gate refused both with E_MISSING_KEY, and a passport that clears the
    # owner's own loop and is refused on publication is the failure the parity harness
    # exists to catch. Pre-existing on main; found by a critic on 2026-09-07.
    # WS_ANY for the EMPTINESS test only, not for the stored value: a value
    # made of nothing but characters EITHER engine calls whitespace is a
    # value the reader sees as blank, whichever engine is looking. `title:
    # <U+FEFF>` was non-empty to WS_BOTH and passed here while the site
    # refused it, so the narrow class was the wrong one for this question.
    missing = [k for k in REQUIRED_KEYS
               if not pairs.get(k, "").strip(WS_ANY_CHARS)]
    if missing:
        errors.append(f"FAIL 2: missing frontmatter keys: {', '.join(missing)}")

    # Check 3: value constraints
    if "passport" in pairs and pairs["passport"] != "0.1":
        errors.append(f"FAIL 3: passport must be 0.1, got '{pairs['passport']}'")

    if "capture_path" in pairs and pairs["capture_path"] not in ("file", "browser"):
        errors.append(f"FAIL 3: capture_path must be 'file' or 'browser', got '{pairs.get('capture_path')}'")

    if "owner_confirmed" in pairs and pairs["owner_confirmed"] not in ("true", "false"):
        errors.append(f"FAIL 3: owner_confirmed must be 'true' or 'false', got '{pairs.get('owner_confirmed')}'")

    if "envelope" in pairs and pairs["envelope"] != "read-notify":
        errors.append(f"FAIL 3: envelope must be 'read-notify', got '{pairs.get('envelope')}'")

    # Title length, which this gate did not check at all. A 250-character
    # title passed here and was refused on upload as E_BAD_VALUE, plain ASCII,
    # no whitespace question anywhere. Code points rather than UTF-16 units,
    # which is the reading the page renderer's JavaScript was moved to: a title of 12 emoji is 12
    # characters to a reader and to Python, and was 24 to JavaScript.
    title_val = pairs.get("title", "")
    if title_val and (len(title_val) > 200 or "\n" in title_val):
        errors.append("FAIL 3: title is %d characters, and it must be one line "
                      "of 1 to 200. It is never truncated, so shorten it "
                      "yourself." % len(title_val))

    name_val = pairs.get("name", "")
    if name_val and not re.match(r"^[a-z0-9][a-z0-9.\-]{0,63}$", name_val):
        errors.append(f"FAIL 3: name '{name_val}' does not match ^[a-z0-9][a-z0-9.\\-]{{0,63}}$")

    # Check 4: body headings
    body = get_body(text)
    expected_headings = [
        "## 1. What this agent is",
        "## 2. What it needs from you",
        "## 3. Functional spec",
        "## 4. Golden examples",
        "## 5. Installer",
        "## 6. Losses",
    ]
    # COUNT OVER THE FILE, AND SKIP FENCED LINES. Two gate splits close here,
    # pulling in opposite directions, which is why they are one edit.
    #
    # The change of 2026-09-09: this counted over get_body(), the text after the closing `---`,
    # so a line spelled exactly `## 1. What this agent is` placed INSIDE the
    # frontmatter block, with the real heading still below, was invisible here
    # and refused on upload as E_SECTIONS. The endpoint's validator 4.2 counts over the
    # whole file. An earlier change moved check 8a from the body to the file for exactly
    # this reason; this is the same asymmetry, one check over.
    #
    # The ticket proposed a second route: make parse_frontmatter refuse a
    # colonless non-blank line, "which is what the site's parseFrontmatter
    # does". It does not. The endpoint's validator skips a line whose structuralTrim
    # starts with `#` before it ever tests for a pair, so a heading in
    # frontmatter is skipped there exactly as it is here. Taking that route
    # would have opened a split rather than closed one. Checked, not assumed,
    # because the ticket itself said to check.
    #
    # The change of 2026-09-09: neither side skipped fenced lines, so a passport whose whole
    # body sits inside one unclosed ``` fence had all six headings counted and
    # was published by the site with a title, a summary and a consent table
    # read from inside a code block. The endpoint's validator 4.2 skips fenced lines in
    # the same commit, so both gates now refuse it.
    #
    # A heading that exists ONLY inside a fence gets its own message rather
    # than "missing", because "missing" sends the owner looking for a heading
    # they can see in their file. That case used to be handled for section 1
    # alone, below; it is all six now and the special case is gone.
    # TWO COUNTS, AND BOTH ARE LOAD-BEARING. Counting over the file alone is
    # FAIL-OPEN, which is how the first spelling of this fix broke product
    # rule 3.
    #
    # The reasoning that produced the bug, written down because it was
    # locally sound: the site counts over the whole file, so counting over the
    # body was the asymmetry, so count over the file. What that misses is WHY
    # the site can afford to. A heading line is a `#` line, and a `#` line is
    # the one non-blank thing YAML frontmatter admits without a colon: both
    # parsers skip it as a comment (the endpoint's validator tests
    # structuralTrim(line).startsWith('#') BEFORE it tests for a pair, and the
    # twin below does the same). So the frontmatter block is a place a heading
    # can sit and satisfy a file-wide count while being nowhere in the body.
    #
    # Move `## 6. Losses` out of the body and into the frontmatter and the
    # file-wide count is satisfied by the comment line. A critic built that
    # document; this gate PASSED a passport with no losses section, which main
    # refused, and the losses table always rendering is not negotiable. Six
    # more of the same shape, one per section, and one where both gates then
    # accepted and the page published `--- A minimal agent for testing.` as
    # the summary.
    #
    # So: DUPLICATES are counted over the file, because that is what the site
    # sees and it is the 2026-09-09 split. PRESENCE is required in the body,
    # because that is what a section actually is. Neither count alone is the
    # rule; the pair is.
    all_lines = text.split("\n")
    all_fenced = fence_flags(all_lines)
    # The body starts after the closing `---`. parse_frontmatter has already
    # run and any failure to find it has already been reported, so a missing
    # delimiter here means the file is refused on other grounds and every
    # occurrence counts as body: refusing twice for one defect helps nobody.
    fm_close = next((i for i, l in enumerate(all_lines[1:40], 1) if l == "---"), -1)
    fenced_only = []
    for h in expected_headings:
        at = [i for i, bl in enumerate(all_lines)
              if not all_fenced[i] and structural_trim(bl) == h]
        in_body = [i for i in at if i > fm_close]
        if len(at) > 1:
            errors.append(f"FAIL 4: heading '{h}' appears {len(at)} times (expected 1)")
        elif not in_body and any(all_fenced[i] and structural_trim(bl) == h
                                 for i, bl in enumerate(all_lines)):
            fenced_only.append(h)
        elif not in_body and at:
            errors.append("FAIL 4: heading '%s' is inside the frontmatter "
                          "block, above the closing ---, so it is a YAML "
                          "comment and not a section. Move it into the body."
                          % h)
        elif not in_body:
            errors.append(f"FAIL 4: missing heading '{h}'")
    if len(fenced_only) == 1:
        errors.append("FAIL 4: the heading '%s' is inside a code block, so "
                      "there is no section to read there. Close the fence "
                      "above it." % fenced_only[0])
    elif fenced_only:
        errors.append("FAIL 4: %d headings are inside a code block, so there "
                      "are no sections to read: %s. Close the fence above "
                      "them." % (len(fenced_only),
                                 ", ".join("'%s'" % h for h in fenced_only)))

    # Summary length, which this gate did not check either. The bound lives in
    # the upload endpoint's specification 6.2 and both renderers enforce it, so a
    # passport with a two-word section 1 passed here and was refused on upload
    # as E_DERIVE_SUMMARY. Code points, as for the title: a section 1 of 12
    # emoji is 12 characters here and in the page renderer, and was
    # 24 in JavaScript until the page renderer's JavaScript was moved to the same reading.
    body_lines_h = body.split("\n")
    body_fenced_h = fence_flags(body_lines_h)
    sec1_start = sec1_end = None
    for i, bl in enumerate(body_lines_h):
        if body_fenced_h[i]:
            continue
        if structural_trim(bl) == "## 1. What this agent is":
            sec1_start = i
        elif sec1_start is not None and SECTION_BOUNDARY_RE.match(bl):
            sec1_end = i
            break
    # The "section 1's heading is inside a fence" case used to be reported
    # here, alone among the six, because the heading COUNT above ignored
    # fences and this reader did not: the two silently agreed to check
    # nothing. The count is fence-aware now and reports all six, so this
    # branch would have double-reported section 1 and is gone. Built by
    # a reviewer on 2026-09-08; the fence-awareness and the structural_trim
    # comparison both survive in the loop above, and both matter: the first
    # spelling of that message was a substring test and printed "close the
    # fence above it" on a passport with no fence, whose heading had a
    # trailing colon (a second review, the same day).
    if sec1_start is not None and sec1_end is not None:
        # The SHAPE half, which this gate did not check until a reviewer
        # built four documents it passed and the site refused: the page renderer's JavaScript
        # refuses section 1 on any line that is a heading, a table row or a
        # fence, because the summary is three plain sentences and a page that
        # printed a sub-heading or a table as its one-line description would
        # be wrong in a way no length bound catches. The three patterns are
        # line-start rules, the same three the site tests, over the same
        # slice. A leading space before `## 2.` is one way to get here: it is
        # not a boundary to either gate, so section 1 runs on into the consent
        # table and the first row of that table is what refuses it.
        for j, sl in enumerate(body_lines_h[sec1_start + 1:sec1_end]):
            kind = ("a heading" if ANY_HEADING_RE.match(sl)
                    else "a table row" if TABLE_ROW_RE.match(sl)
                    else "a fence" if FENCE_DELIM.match(sl) else None)
            if kind:
                # File line number: the body starts after the closing ---,
                # which is the first exact `---` after line 1.
                fm_close = next(i for i, l in enumerate(text.split("\n")[1:40], 1) if l == "---")
                errors.append("FAIL 4: section 1 contains %s at line %d, and "
                              "the summary must be plain sentences only: no "
                              "headings, tables or code blocks. If that line "
                              "belongs to section 2, check that the `## 2.` "
                              "heading starts at the left margin."
                              % (kind, fm_close + 1 + sec1_start + 2 + j))
                break
        sec1 = " ".join(body_lines_h[sec1_start + 1:sec1_end])
        summary = re.sub("[%s]+" % WS_ANY, " ", sec1).strip(WS_ANY_CHARS)
        if not 20 <= len(summary) <= 2000:
            errors.append("FAIL 4: section 1 is %d characters once collapsed, and "
                          "the summary must be 20 to 2000. It is three plain "
                          "sentences: what the agent does, when, and what the "
                          "output is for." % len(summary))

    # Check heading order
    heading_indices = []
    for h in expected_headings:
        indices = [i for i, bl in enumerate(body.split("\n")) if structural_trim(bl) == h]
        if indices:
            heading_indices.append(indices[0])

    for i in range(len(heading_indices) - 1):
        if heading_indices[i] >= heading_indices[i + 1]:
            errors.append(f"FAIL 4: headings are out of order")
            break

    # Check 5: comparison_mode
    comp_matches = COMPARISON_MODE.findall(body)
    if len(comp_matches) == 0:
        errors.append("FAIL 5: no comparison_mode found")
    elif len(comp_matches) > 1:
        errors.append(f"FAIL 5: multiple comparison_mode lines ({len(comp_matches)})")
    elif scalar(comp_matches[0]) not in ("structural", "exact", "input_relative"):
        errors.append(f"FAIL 5: comparison_mode value '{comp_matches[0]}' is not valid")

    # Check 6: capability_ref values
    cap_matches = CAPABILITY_REF.findall(body)
    for raw in cap_matches:
        val = scalar(raw)
        if val in VALID_CAPABILITIES:
            continue
        if val.startswith("money."):
            continue
        errors.append(f"FAIL 6: invalid capability_ref '{raw}'")

    # Check 7: [SCRUBBED: implies scrub contains owner-reviewed
    if "[SCRUBBED:" in body:
        scrub_val = pairs.get("scrub", "")
        if "owner-reviewed" not in scrub_val:
            errors.append("FAIL 7: body contains [SCRUBBED: but scrub frontmatter lacks 'owner-reviewed'")

    # Check 8a: a line that opens a fence to a WIDER reader and not to this one.
    #
    # The tripwire described beside FENCE_LOOSE. Reported before check 8 counts
    # anything, because once a fence fails to open every count downstream is
    # about a different document than the author wrote.
    # THE WHOLE FILE, not the body. The endpoint's validator scans every line including
    # the frontmatter, and this scanned the body only, so a BOM before a fence
    # inside the frontmatter block passed here and was refused on upload. The
    # critic judged it unexploitable, because no line can both parse as a
    # frontmatter pair and trip this, and that is right; it is still a split,
    # and an invisible character before a fence is wrong wherever it sits.
    # Line numbers are counted over the whole file for the same reason: they
    # are what the author will look at.
    for i, line in enumerate(text.split("\n"), 1):
        if FENCE_LOOSE.match(line) and not FENCE_DELIM.match(line):
            errors.append(
                f"FAIL 8: line {i} carries an invisible character before its "
                f"code fence, so the fence never opens: {line!r}. A Markdown "
                f"renderer will not open a code block there either. Delete the "
                f"character before the backticks.")

    # Check 8: code blocks in golden examples section
    #
    # The section boundaries are found outside fences, not by substring search.
    # A golden example that quotes a literal "## 5. Installer" line ended
    # section 4 in the middle of the fence, so the fence never closed and this
    # check reported an open block about one the owner had closed properly.
    #
    # The section ends at the next level-1 or level-2 heading, not at a literal
    # match on "## 5. Installer". Matching the literal put any unnumbered
    # heading between the two sections inside section 4 for this counter and
    # outside it for section_lines(), and both directions of that disagreement
    # are reachable. A stray "## Appendix A, outputs" carrying the only fenced
    # block, or a stray "## Notes" carrying one, must land on the same side of
    # the boundary for every consumer of this format, or two of them will
    # disagree about how many golden examples a passport has. Anything that
    # slices a passport into sections must use this rule.
    golden_start, golden_end = -1, -1
    fence_len, offset = None, 0
    for line in body.split("\n"):
        match = FENCE_DELIM.match(line)
        if match:
            if fence_len is None:
                fence_len = len(match.group(1))
            elif len(match.group(1)) >= fence_len:
                fence_len = None
        elif fence_len is None:
            if golden_start == -1 and structural_trim(line) == "## 4. Golden examples":
                golden_start = offset
            elif (golden_start != -1 and golden_end == -1
                  and SECTION_BOUNDARY_RE.match(line)):
                golden_end = offset
        offset += len(line) + 1
    if golden_start != -1:
        # No section 5 outside a fence means either the passport has none,
        # which check 2 reports, or section 4 opened a fence and swallowed it.
        # Reading to the end of the file is what distinguishes the two: the
        # fence walk below then reports the open block, which is the truth.
        if golden_end == -1:
            golden_end = len(body)
        # Counting fence markers and halving them is wrong on legal Markdown: a
        # four-backtick example that quotes a three-backtick block has four
        # markers and is one block, and three such examples counted as six and
        # were refused. A fence closes on a run at least as long as the one
        # that opened it, and a shorter run inside is content. Anything that
        # counts golden blocks must count them this way, or two consumers of the
        # same passport will report different numbers.
        golden_body = body[golden_start:golden_end]
        block_count, open_len = 0, None
        for line in golden_body.split("\n"):
            match = FENCE_DELIM.match(line)
            if not match:
                continue
            if open_len is None:
                open_len = len(match.group(1))
                block_count += 1
            elif len(match.group(1)) >= open_len:
                open_len = None
        if open_len is not None:
            errors.append("FAIL 8: a fenced code block in golden examples is left open")
        elif block_count < 1 or block_count > 3:
            errors.append(f"FAIL 8: {block_count} code blocks in golden examples (expected 1-3)")

    # Check 9: forbidden strings, matched through normalize_forbidden so case,
    # an inserted backslash and a name split across a line cannot walk a denied
    # path past it. See the note on that function for the normalisation that
    # was tried and refused.
    #
    # OVER THE WHOLE FILE, not the body, and that is a fix rather than a
    # widening. This read `body`, which get_body() returns with everything above
    # the closing `---` removed, so `source_stack: credentials/prod-agent` in
    # the frontmatter passed here. The upload endpoint's validator has always scanned the
    # whole text, so the two implementations disagreed on that file: this one
    # accepted it and the site refused the upload. That is the same shape as the
    # divergence that produced checks 10 and 11, a capture passing its own
    # verification loop and being refused on upload, and the cross-engine parity harness
    # could not see it because no fixture carried a denied path in frontmatter.
    # There is one now.
    norm_text = normalize_forbidden(text)
    for forbidden in FORBIDDEN_STRINGS:
        needle = normalize_forbidden(forbidden)
        # An entry starting with punctuation needs a word character before it,
        # or NFKC's ellipsis folding turns ordinary prose into a match.
        pattern = (r"(?<=[a-z0-9])" if not needle[:1].isalnum() else "") + re.escape(needle)
        if re.search(pattern, norm_text):
            errors.append(f"FAIL 9: passport contains forbidden string '{forbidden}'")

    # Check 10: created is a real date and not in the future.
    #
    # Checking that the key is PRESENT is not checking that it is a date. A
    # passport carrying a malformed or future date satisfies the first and fails
    # anything that later has to parse it, which is every consumer of the
    # format. The check belongs wherever the format is checked.
    created = pairs.get("created", "")
    if created:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", created):
            errors.append(f"FAIL 10: created '{created}' is not a date as YYYY-MM-DD")
        else:
            try:
                when = datetime.date.fromisoformat(created)
            except ValueError:
                errors.append(f"FAIL 10: created '{created}' is not a real date")
            else:
                # One day of slack, because the capture machine's clock and
                # whatever reads it are not in the same timezone.
                if when > datetime.date.today() + datetime.timedelta(days=1):
                    errors.append(f"FAIL 10: created '{created}' is in the future")

    # Check 11: section 2 carries the consent table.
    #
    # The consent table is the part of a passport a person actually reads before
    # deciding, and references/spec-schema.md section 3 names its five columns.
    # A section 2 carrying one sentence of prose is a passport with nothing to
    # consent to. Accepting it would let a capture loop call such a passport
    # finished, which is the one thing the consent table exists to prevent.
    rows = consent_rows(body)
    if isinstance(rows, tuple) and rows and rows[0] == "STRAY":
        errors.append(
            "FAIL 11: this line in section 2 begins with a table pipe once "
            "invisible characters are removed, but carries one before the pipe, "
            "so it is not a table row and the row it describes would be dropped "
            "from the consent table with no other error: " + repr(rows[1]) +
            ". Delete the character before the pipe.")
        rows = None
    if rows is None:
        errors.append("FAIL 11: section 2 has no consent table with five columns "
                      "(Capability | Why | Required / Optional | If you skip it | Installable)")
    elif not rows:
        errors.append("FAIL 11: the consent table in section 2 has no rows")
    else:
        for row in rows:
            if len(row) != 5:
                errors.append(f"FAIL 11: a consent row has {len(row)} columns, expected 5")
                continue
            req = row[2].lower()
            if not (req.startswith("required") or req.startswith("optional")
                    or req.startswith("declared")):
                errors.append(f"FAIL 11: consent row '{row[0]}' has an unreadable "
                              f"Required column: '{row[2]}'")
            ins = row[4].lower()
            if not (ins.startswith("yes") or ins.startswith("no")):
                errors.append(f"FAIL 11: consent row '{row[0]}' has an unreadable "
                              f"Installable column: '{row[4]}'")

    spec = spec_lines(text)

    # Check 12: a credentialed input carries a binding.
    #
    # Anything behind the original owner's login is guaranteed not to be the
    # installer's, so an input that says `access: credentialed` and names no
    # slot is a demand with nobody to ask. That is not theoretical: an importer
    # with a perfectly good database of their own can be told most of the inputs
    # are lost, because the passport carried the original's sources as fixed
    # facts rather than as roles somebody else could fill.
    # The binding must name a slot that is actually there. A binding pointing at
    # nothing is the same demand with a nicer label on it, and `none` is the
    # likeliest way to write one, because `none` is exactly what the schema
    # teaches for a slot's `default`. Both were accepted until this check
    # existed.
    slot_ids = set()
    for _, line in yaml_block(spec, "personal_slots"):
        m = SLOT_ID.match(line)
        if m:
            slot_ids.add(scalar(m.group(1)))

    for entry in input_entries(yaml_block(spec, "inputs")):
        credentialed, bound, target, at = None, False, None, None
        for n, line in entry:
            # Dangling is tested FIRST, and the order is the whole point. A
            # trailing comment is still a dangling key: `access:  # open |
            # credentialed` is YAML null. When the value match ran first,
            # `(\S+)` grabbed the `#`, the dangling branch below could never
            # fire, and the author was told their access "reads as '#'", a
            # token they never wrote as a value. That shape is not exotic:
            # references/spec-schema.md writes the schema stub in exactly it, and
            # generates it onward into the skill's reference copy. Found by a
            # critic, 2026-09-03.
            if ACCESS_DANGLING.match(line):
                # `access:` with its value indented on the NEXT line is legal
                # YAML and means exactly `access: credentialed` when that is
                # the word beneath it. This validator reads a line at a time,
                # so the value match never fired, `credentialed` stayed None,
                # and BOTH checks went quiet: no FAIL 15 for an unrecognised
                # value, and no FAIL 12 for the missing binding. A login-gated
                # input shipped clean. Measured 2026-09-03.
                #
                # A trailing comment counts as dangling for the same reason:
                # `access:  # open | credentialed` is YAML null.
                #
                # The spec already requires `comparison_mode:` and
                # `capability_ref:` to carry their value on the same line, for
                # a related reason with the opposite mechanism: those are
                # searched over the whole text, where `\s*` DOES cross a
                # newline, so a dangling key swallows whatever token comes
                # next. Here a dangling key matches nothing at all. Same
                # silence, arrived at from the other side.
                #
                # Refusing is the conservative direction. This does not try to
                # read the next line: a validator that finds fields by regex
                # should say it cannot read the shape, not guess at it.
                errors.append(
                    f"FAIL 15: line {n}: access has no value on this line, "
                    f"only a comment or nothing at all. That is legal YAML, "
                    f"and its value may be the indented line beneath, but this "
                    f"validator reads one line at a time and cannot see it, so "
                    f"a credentialed input written this way would pass with no "
                    f"binding demanded. Put the value on this line: "
                    f"access: credentialed.")
            else:
                m = ACCESS.match(line)
                if m:
                    val = scalar(m.group(1))
                # NOTE for anyone relaxing the refusal below. `credentialed`
                # is set from `val`, so a form this branch does not recognise
                # attaches NO binding demand: `access: !!str credentialed` is
                # legal YAML meaning credentialed, and it is safe today only
                # because the next check refuses it outright. Accept a tagged
                # or folded form here without also feeding it through the
                # `credentialed` test above and the binding hole reopens in
                # silence. Raised by a critic, 2026-09-03.
                    # Case-folded ON PURPOSE, and this is deliberately more generous
                    # than check 14 next door, which pins `fidelity` case-sensitively.
                    # The two enums fail in opposite directions. An unrecognised
                    # `fidelity` is reported by check 14 and the row still renders; an
                    # unrecognised `access` used to mean the binding requirement did
                    # not apply, so `access: Credentialed` was a way to declare a
                    # login-gated source and be asked for nothing. Reading it as
                    # credentialed keeps the demand attached to the input. The
                    # spelling is still wrong and FAIL 15 below says so; this line
                    # decides only that you do not escape the binding by shouting.
                    if val.lower() == "credentialed":
                        credentialed = n
                    if val not in ("open", "credentialed"):
                        errors.append(
                            f"FAIL 15: line {n}: access reads as '{m.group(1)}', and "
                            f"the only two values are 'open' and 'credentialed'. "
                            f"Write one of them, unquoted or quoted, on this line. "
                            f"This validator folds case before testing for "
                            f"'credentialed', so it still demands the binding when "
                            f"you shout it, but nothing else here does: to a "
                            f"consumer that compares the string, an access it does "
                            f"not recognise is not credentialed, and the binding "
                            f"requirement that keeps a login-gated input from "
                            f"shipping as a dead row is gone.")
            m = BINDING.match(line)
            if m:
                bound, target, at = True, scalar(m.group(1)), n
        if bound and target.lower() in ("none", "null", "~", "[]"):
            errors.append(
                f"FAIL 12: line {at}: binding says '{target}', which names no slot. "
                f"A binding is the id of a question the installer will be asked, so "
                f"'none' leaves the input with nobody to ask. Name a personal_slots "
                f"id, and add that slot if it does not exist yet.")
        # No `and slot_ids` guard here. It was written as a hedge against a
        # personal_slots block this parser fails to read, and it inverted the
        # check exactly where it matters most: a passport with no slots at all
        # is the one where EVERY binding dangles, and it was the one case that
        # passed. An unreadable slot block now fails loudly and says which ids
        # it found, which is a better failure than silent acceptance.
        elif bound and target not in slot_ids:
            errors.append(
                f"FAIL 12: line {at}: binding names '{target}', and no slot in "
                f"personal_slots has that id. Known ids: "
                f"{', '.join(sorted(slot_ids)) or 'none'}.")
        if credentialed and not bound:
            errors.append(
                f"FAIL 12: line {credentialed}: this input says access: credentialed "
                f"and has no binding. Add a 'binding:' line naming a personal_slots "
                f"id, and a slot with that id asking the installer what supplies "
                f"this role on their side.")

    # Check 14: fidelity, when present, is one of the two words that mean
    # something. A closed enum nothing checks is a field that silently accepts
    # `fidelity: sortof` and reads as absent to every consumer, which is worse
    # than not having it: the losses table decides between `delivered` and
    # `delivered, unreliable` on this word.
    for entry in input_entries(yaml_block(spec, "inputs")):
        for n, line in entry:
            m = FIDELITY.match(line)
            if m and scalar(m.group(1)) not in ("exact", "lossy"):
                errors.append(
                    f"FAIL 14: line {n}: fidelity is '{m.group(1)}', and the only "
                    f"values are 'exact' (the original read the source's own data and "
                    f"would have errored rather than guessed) and 'lossy' (a model or "
                    f"a heuristic stood between the source and the number). Omit the "
                    f"field for inputs that are prose.")



    # Check 13: a check that compares runs needs a declared state block.
    #
    # The golden example that started this showed "83 (-142 vs prev)" and the
    # verification checks demanded the comparison, while the format had nowhere
    # to say the agent remembers yesterday. The installer was then caught
    # between honouring the check and not inventing features the spec does not
    # contain. Declaring the memory is one honest answer, rewriting the check so
    # one run can prove it is the other, and this check forces the choice
    # instead of leaving it to be made silently at install time.
    state = yaml_block(spec, "state")
    # `keeps:` present, not `keeps:` carrying a value on the same line. Written
    # as a YAML list, which is legal and means the same thing, the stricter
    # version refused the passport and told its author to add a state block they
    # had already written. That is the same "no way to comply" failure that got
    # three phrases deleted from DELTA_PHRASES, one layer down: a check whose
    # only remedy is to do the thing you already did teaches people the checker
    # is broken, and they are right.
    has_state = any(KEEPS.match(line) for _, line in state)
    if not has_state:
        for n, line in yaml_block(spec, "verification"):
            phrase = delta_phrase(line)
            if phrase:
                errors.append(
                    f"FAIL 13: line {n}: this verification check compares against an "
                    f"earlier run ('{phrase}') and the passport declares no state "
                    f"block. Either add a top-level 'state:' block with keeps, "
                    f"granularity, why and confidence, saying what is remembered "
                    f"between runs, or rewrite the check so it can be judged from a "
                    f"single run.")

    # Check 16: the envelope floor. A declared-only capability is never
    # installable.
    #
    # 16, not 14. It shipped as 14 on 2026-09-04 and that number already
    # belonged to the fidelity check above, so one FAIL line named two
    # unrelated rules and a finding in the record went half-true on the
    # strength of it. 15 is access. Renumbered the same day.
    #
    # Spec section 5 has always said this and said it only in prose, so a
    # passport declaring `envelope: read-notify` while marking email.send
    # "Installable: yes" passed here, passed preflight, and rendered to its
    # recipient as a granted write capability. The realistic failure is not a
    # malicious passport, which owns the whole body as injection surface
    # anyway; it is an honest capture shipping an installable write capability
    # that a consent page then shows a human as approved.
    #
    # THREE PARTS, because the format gives an id three different amounts of
    # context, and each part catches a probe the others miss. Removing any one
    # of them reopens a hole that was tested open:
    #
    #   16a  `status: used` on a declared-only id in the capabilities block.
    #   16b  a backticked declared-only id in a consent row marked installable.
    #   16c  a declared-only capability in section 3 with no `no` row in the
    #        consent table at all.
    #
    # 16b cannot carry this on its own and that is not an implementation
    # shortcut. The Capability column is prose written for a person, the ids
    # live in section 3, and NOTHING IN THE FORMAT LINKS A CONSENT ROW TO AN
    # ID unless the author happened to backtick one. The repository's own
    # example passport backticks nothing, so a check resting on 16b alone
    # would be vacuous on the flagship. 16c is the answer to that: it cannot
    # say which row is lying, only that a passport declaring a write
    # capability must show the reader at least one row it will not install.
    # The honest fix is a machine-readable id column in the consent table,
    # which is a format change and not a validator's to make.
    # Every capability_ref in section 3, wherever it sits. Two uses, and they
    # are deliberately wider than 16a's.
    #
    #   - 16b's money guard reads a declared money token as an id whatever
    #     its shape (see consent_token_is_write_id).
    #   - 16c asks "does this passport declare a write capability at all", and
    #     the answer must not depend on which block it was written in. Scoping
    #     that to `capabilities` left a bypass: moving `capability_ref:
    #     email.send` into `inputs` made 16a and 16c both blind, and with a
    #     plain consent row 16b too, so the whole floor was cleared by choosing
    #     a different block. That was 20 of the 30 evasions a differential fuzz
    #     found. 16a stays scoped to `capabilities` because it pairs a ref with
    #     a `status`, and an input has no status to pair with.
    # ANCHORED to a YAML key at line start, not a substring anywhere. An
    # unanchored match read prose as a declaration: `tacit_notes` is defined at
    # spec section 4 as the owner's words "verbatim, quoted not paraphrased",
    # and vocabulary.md sends capture there when no id fits, so it is both the
    # designated place to write about capabilities in prose and protected from
    # rewording. An owner sentence containing "capability_ref: email.send"
    # refused an honest passport, and the remedy the message implies, adding a
    # declared-only row, would have made that passport lie.
    # scalar(), not `.strip("\"'")`. Check 16 was written before scalar()
    # existed and kept the loose strip, which is MORE permissive than YAML: it
    # peels every quote, so `status: "'declared_only'"` (the YAML string
    # 'declared_only', quotes included, which is NOT declared_only) read as
    # honest here and the floor let a write capability through. The site's
    # envelope block peeled one pair and refused the same file, so the two
    # gates returned opposite verdicts on it and parity could not see it
    # because no fixture carried the shape. There is one now.
    # BLOCK-SCALAR CONTENT IS NOT READ. Anchoring to a line start was the first
    # repair and it was not enough: an owner quoting a config line at the START
    # of a line inside `tacit_notes` was read as declaring the capability and
    # the honest passport was refused. strip_block_scalar_content()
    # is the same rule input_entries() has had since 2026-09-03, now shared
    # rather than copied. The scan stays WIDE on purpose otherwise: every block
    # of section 3, not just `capabilities`, because moving a ref into `inputs`
    # was 20 of the 30 evasions a differential fuzz found.
    spec_refs = {scalar(m.group(1))
                 for _, line, _f in strip_block_scalar_content(spec)
                 for m in [CAPABILITY_REF_LINE.match(line)] if m}
    declares_write = any(is_declared_only(r) for r in spec_refs)

    cap_block = yaml_block(spec, "capabilities")
    declared_here = []
    for entry in input_entries(cap_block):
        ref = status = None
        for n, line in entry:
            m = CAPABILITY_REF.search(line)
            if m:
                ref = scalar(m.group(1))
            m = STATUS.search(line)
            if m:
                status = scalar(m.group(1))
        if ref is None or not is_declared_only(ref):
            continue
        declared_here.append(safe_ref_label(ref))
        # A MISSING status is a failure, not a pass, and reading it the other
        # way made 16a opt-out by omission: `- capability_ref: email.send` with
        # no status line fired nothing, and with one unrelated declared-only row
        # elsewhere in the consent table 16c was satisfied too, so the whole
        # floor was cleared by deleting a line. spec section 4 gives the
        # capabilities entry as {capability_ref, status}, so status is mandatory
        # by the schema and was optional here.
        if status is None:
            errors.append(
                f"FAIL 16: capability '{safe_ref_label(ref)}' writes to the "
                f"world and its entry carries no 'status'. Write "
                f"'status: declared_only'. An entry with no status is not an "
                f"entry this check can read as honest.")
        elif status != "declared_only":
            errors.append(
                f"FAIL 16: capability '{safe_ref_label(ref)}' writes to the world, so the "
                f"read-notify envelope puts it outside what v0.1 installs, but "
                f"its status is '{status}'. Set 'status: declared_only'. The "
                f"agent is still captured and still described; it is listed "
                f"rather than installed.")

    if rows:
        for row in rows:
            if len(row) != 5:
                continue                # already reported by check 11
            # EVERY backticked token, not the first. `re.search` took only the
            # first group, so "Read `files.read` and also `email.send`" was
            # checked on files.read and passed. A cell may legitimately carry
            # more than one.
            installable = not row[4].lower().startswith("no")
            if not installable:
                # A row marked no is never read, in any of its five cells.
                # It is the honest declared-only row the envelope asks for,
                # and refusing it for naming the id it declares would refuse
                # the shape the check exists to require.
                continue
            # ONE PASS OVER ALL FIVE CELLS, and each cell is read twice:
            # first for a token that must not be echoed, then for a write id.
            # The first hit refuses the row and stops, which is what
            # the page renderer's JavaScript always did and what keeps each invalid_ fixture
            # isolating exactly one part of check 16.
            #
            # PART ONE, the token that must not be echoed. This ran on the
            # Capability cell only, and on ONE-WORD segments only, because the
            # rule it enforced was "an installable row may backtick only
            # printable ASCII", which also refused an honest German filename,
            # a Japanese path and an en-dash in a date. The review scoped it to cell 0
            # for that reason and the one-word carve-out was there
            # for the same reason one level down. consent_token_is_opaque() is
            # now narrow enough to need neither: it fires only on a word
            # already shaped like a write id, so it costs no language anything
            # and reads every word of every cell. The two
            # restrictions came off together because each was paying for the
            # same over-wide rule.
            #
            # PART TWO, the write-id scan. The guard read the Capability cell
            # only, and the Installable cell travels verbatim as
            # `installable_label` through inline(), which renders backticks as
            # <code>, so `yes (via `money.transfer`)` put the id in front of
            # the reader beside a Granted stamp while both gates called the row
            # clean. The money guard itself lives in
            # consent_token_is_write_id(), with the list it consults and the
            # reasoning beside it.
            for idx, cell in enumerate(row):
                if consent_cell_opaque_word(cell) is not None:
                    # Every backticked span collapsed, in the echoed row AND in
                    # the echoed column: the word is by definition a lookalike
                    # or a control character, and no money regex would match a
                    # Cyrillic o, so nothing narrower is safe to echo.
                    errors.append(
                        f"FAIL 16: consent row '{collapse_spans(row[0])}' "
                        f"backticks a token in its {CONSENT_COLUMNS[idx]} "
                        f"column that this validator will not repeat back, "
                        f"because it is either an ASCII control character or a "
                        f"capability id spelled with a lookalike character, "
                        f"such as a Cyrillic o in place of the Latin one, or "
                        f"a zero-width space inside the word. Its Installable "
                        f"column says "
                        f"'{collapse_spans(row[4])}'. If the token is a "
                        f"capability that writes to the world, that column "
                        f"reads 'no, declared only'. If it is an honest "
                        f"filename, retype it: the characters that look wrong "
                        f"are not the ones you meant.")
                    break
                token = consent_cell_write_id(cell, spec_refs)
                if token is None:
                    continue
                # The CAPABILITY cell is echoed whichever cell offended, and
                # that is deliberate rather than lazy: cell 0 is what names
                # the row for its author, and echoing the offending cell
                # would carry a stranger's money suffix into the message that
                # safe_ref_label() exists to keep it out of. The column name
                # says where to look and is a fixed string from the header.
                #
                # Collapsed on any span CONTAINING a money token, not only a
                # span that starts with one: a word scan finds
                # `run money.transfer_acct_99 now`, and the old anchored
                # regex would have echoed that suffix whole.
                shown = collapse_money_spans(row[0])
                errors.append(
                    f"FAIL 16: consent row '{shown}' names "
                    f"'{safe_ref_label(token)}' in its "
                    f"{CONSENT_COLUMNS[idx]} column, "
                    f"which writes to the world, and its Installable column "
                    f"says '{collapse_money_spans(row[4])}'. "
                    + (f"Two fixes, and only one of them is true of your "
                       f"agent: if the backticked token is a filename, "
                       f"write it without backticks; if it is a capability "
                       f"that moves money, the column reads 'no, declared "
                       f"only'. Never write the second when the first is "
                       f"the truth."
                       # FOLDED. The token is echoed as the passport wrote
                       # it, so `MONEY.transfer` reached this test with a
                       # capital M, did not start with the prefix, and got
                       # the message for a fixed write id: correct verdict,
                       # wrong advice, since the money branch is the one that
                       # says a filename is also a possible reading.
                       if fold_ascii(token).startswith(DECLARED_ONLY_PREFIX) else
                       f"Two fixes, and only one of them is true of your "
                       f"agent: if this row installs that capability, its "
                       f"Installable column reads 'no, declared only'; if it "
                       f"does not, the cell should not name it as one.")
                    # See PROSE_FIX. Cell 0 names what the row installs and
                    # its message is complete; cells 1 to 4 are prose, and
                    # this is where the author is told how to keep the
                    # sentence they wrote.
                    + (" " + PROSE_FIX if idx != 0 else ""))
                break

        # `.startswith("no")` is well-founded only because check 11 has already
        # forced every Installable cell to start with "yes" or "no". Relaxing
        # check 11 silently breaks this one.
        if declares_write and not any(
                len(r) == 5 and r[4].lower().startswith("no") for r in rows):
            named = sorted({safe_ref_label(r) for r in spec_refs
                            if is_declared_only(r)})
            errors.append(
                f"FAIL 16: the functional spec declares "
                f"{', '.join(named)} as a capability "
                f"outside the read-notify envelope, and every row of the "
                f"consent table says it installs. Spec section 5 requires an "
                f"out-of-envelope capability to reach the reader as a "
                f"declared-only row, because the consent table is what they "
                f"actually read before deciding.")

    # Checks 17 to 19, the endpoint's stage 3. See untrusted_content().
    errors.extend(untrusted_content(text if gate_text is None else gate_text))

    return errors


def main():
    # --dump-scalar prints what scalar() does to each probe in
    # fixtures/scalar_probes.json, as JSON. The cross-language comparison
    # harness runs the same probes through the JavaScript twin of scalar() and
    # requires identical output. It takes no passport, which is why it is
    # handled before the argument count check below.
    if "--dump-scalar" in sys.argv[1:]:
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "fixtures", "scalar_probes.json"),
                  encoding="utf-8") as f:
            probes = json.load(f)["probes"]
        print(json.dumps([scalar(p) for p in probes]))
        return 0

    if len(sys.argv) != 2:
        print("Usage: validate.py PASSPORT.md", file=sys.stderr)
        sys.exit(1)

    try:
        with open(sys.argv[1], "r", encoding="utf-8", newline="") as f:
            raw = f.read()
    except (OSError, IOError) as e:
        print(f"Error reading {sys.argv[1]}: {e}", file=sys.stderr)
        sys.exit(1)

    # Checks 1 to 16 read the file as this script always has, with Python's
    # universal newlines (a lone CR becomes a line break), so none of their
    # verdicts moves. Checks 17 to 19 read it as the endpoint does.
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    errors = validate(text, gate_reading(raw))
    if errors:
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()

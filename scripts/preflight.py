#!/usr/bin/env python3
"""Will the site accept this passport? Run before telling anyone to upload.

Usage: preflight.py PASSPORT.md
Exit 0 and print OK, or exit 1 and say what the upload endpoint will refuse.

Why this exists, and why it is not part of validate.py. The authority is split
deliberately: validate.py is the reference implementation of the FORMAT rules,
and the upload endpoint is the sole authority for transport and untrusted
content. Honouring that split leaves a hole between them. A passport can satisfy
every format rule and still be refused on upload, and without this file the
first anyone hears of that is at the upload box, after the work is done, in an
error about markup they did not write. Predicting the refusal locally is the
whole job of this file.

So this file predicts the upload gate's answer and does nothing else. It does not duplicate
validate.py, and validate.py does not grow these checks. Two implementations of
one rule set are only safe while something compares them on every input, so if
you fork this file, compare it against whatever you forked it from.

Stdlib only, because it travels inside the distributable skill folder, where
the endpoint's own sources and runtime do not exist.
"""

import re
import sys

INSTALLER_PLACEHOLDER = "<!-- installer core and branches inserted on upload -->"

# Mirrors the endpoint's element list. A name missing from here is
# reported as an unfilled placeholder rather than as a tag; both are refused, so
# the cost of a gap is one wrong sentence, never a passport that slips through.
HTML_ELEMENTS = {
    "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base", "bdi",
    "bdo", "blockquote", "body", "br", "button", "canvas", "caption", "cite", "code",
    "col", "colgroup", "data", "datalist", "dd", "del", "details", "dfn", "dialog",
    "div", "dl", "dt", "em", "embed", "fieldset", "figcaption", "figure", "footer",
    "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr",
    "html", "i", "iframe", "img", "input", "ins", "kbd", "label", "legend", "li",
    "link", "main", "map", "mark", "menu", "meta", "meter", "nav", "noscript",
    "object", "ol", "optgroup", "option", "output", "p", "param", "picture", "pre",
    "progress", "q", "rp", "rt", "ruby", "s", "samp", "script", "search", "section",
    "select", "slot", "small", "source", "span", "strong", "style", "sub", "summary",
    "sup", "svg", "table", "tbody", "td", "template", "textarea", "tfoot", "th",
    "thead", "time", "title", "tr", "track", "u", "ul", "var", "video", "wbr",
}

TAG = re.compile(r"<\/?[A-Za-z][A-Za-z0-9-]*(\s[^>]*)?>")
FENCE = re.compile(r"^\s*(`{3,})")
# THE LINK TEXT IS BOUNDED, AND THAT BOUND IS LOAD-BEARING RATHER THAN TIDY.
# Unbounded, [^\]]* is quadratic on any body with unmatched "[": at every one of
# n start positions it runs to the end of the input looking for a "]" that is
# never there, then gives back one character at a time. On a 262,144-character
# body of "[" repeated the unbounded form costs about 27.8 seconds and this one
# about 107 milliseconds, and this gate has no input cap of its own, so the cost
# is the owner's own wall clock during a capture.
#
# THE TRADE, STATED: a markdown link whose TEXT exceeds 256 characters is no
# longer seen as active content. Held character for character in step with the
# upload endpoint's copy of the same rule.
LINK = re.compile(r"!?\[[^\]]{0,256}\]\(\s*([^)\s]+)")
SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")

# The two characters on which regex engines disagree about \s, and the only two
# that matter here. Enumerated rather than guessed, over all 0x110000 code
# points: U+0085 is whitespace to some engines and not others, and U+FEFF is the
# same the other way round. The other divergent code points are control
# characters and are refused outright before this rule is reached.
#
# Both are normalised away before the scan rather than left to two engines to
# disagree about.
#
# They are also exactly what survives a copy-paste out of a browser chat window,
# which is capture_path: browser. That path has no local scripts by
# construction, so normalising here is the only place it can happen.
#
# The remaining divergences all run the other way, making the upload gate
# STRICTER than this file rather than looser. This check exists to predict a
# refusal, so erring towards predicting one is the harmless direction.
# ---- Invisible-character evasion, closed 2026-09-01 ------------------------
#
# WHAT THIS BLOCK IS FOR, WHICH IS NOT WHAT THE ONE ABOVE IT IS FOR. Everything
# above concerns two engines disagreeing about \s. This concerns one engine
# being walked past. They share a function and they are different problems, and
# reading the older comment as covering both is how this stayed open.
#
# Measured on 2026-09-01: FOURTEEN invisible characters placed between the query
# delimiter and the parameter name defeat the URL rule, because that rule is
# anchored as [?&]name= and any character at all between the two breaks the
# adjacency it depends on. U+FEFF was the only one closed, and only because it
# was already being stripped for the unrelated reason above.
#
# WHY IT MATTERS MORE FOR SOME NAMES THAN OTHERS. token, secret, auth, apikey,
# api_key and access_token have a second rule behind them: CREDENTIAL_ASSIGN
# catches them at 20+ characters even when the URL rule is evaded. key, sig,
# signature and X-Amz-Signature have nothing behind them, because bare "key"
# cannot be added to CREDENTIAL_ASSIGN without re-opening the word "monkey"
# (the rule was narrowed in August 2026 after it refused the word "monkey")
# and the
# signature names were never there. For those four, this normalisation is the
# only thing standing between a live credential and a public page.
#
# WHY A LIST AND NOT A UNICODE CATEGORY. \p{Cf} would need the /u flag on the
# site's regexes, and adding /u changes \b and \d semantics across the whole
# table, which is a separate and much larger change. An explicit class
# means the same thing in both engines with no flag.
#
# THE CLASS IS GENERATED, NOT TYPED: every Cf code point in the BMP, plus the
# zero-advance marks and blank-rendering fillers (Mongolian FVS, Khmer inherent
# vowels, the Hangul fillers, Braille blank, the variation selectors). Seventy code points in twenty-one ranges. Zero false positives over
# 17,682 prose files.
#
# IT IS NOT COMPLETE AND THIS COMMENT DOES NOT CLAIM IT IS. The first version
# enumerated the fourteen characters somebody had thought to try, and a full sweep
# of all 1,112,064 code points found 153 more that defeat the rule and are refused
# by nothing. Most are now covered; the astral ones cannot be, see below. A list
# of invisible characters is a list of what has been looked for. Treat it as a
# floor that gets raised, never as a boundary that holds.
#
# COMBINING MARKS (Mn) ARE DELIBERATELY NOT IN IT. All 2,091 of them defeat the
# rule in this position, and they are excluded on threat model rather than on
# cost. This gate protects an owner from their own mistake; there is no adversary,
# because hiding a credential from the scrubber only hurts the person publishing
# it. The characters that matter are the ones that arrive by ACCIDENT, surviving a
# copy-paste out of a chat window, which is what the paragraph above this block is
# about. A combining acute between ? and a parameter name does not arrive by
# accident. It also renders as a visible mark on the ?, so it is not hidden.
#
# THE ASTRAL LIMIT, which is a real gap and is filed rather than accepted quietly.
# 120 Cf code points sit above the BMP, including the tag block U+E0000-U+E007F,
# which is invisible by design and a known hiding trick. They are NOT covered: a
# JS character class containing astral code points without /u is read as surrogate
# pairs, which is precisely the cross-engine defect the delimiter anchoring was
# introduced to fix. Closing them is part of the wider decision about whether
# this rule set adopts the unicode flag at all, which is not this rule's to take.
#
# THE ACCEPTED MISS, stated plainly. U+0085 is mapped to a space rather than
# removed, so ?<U+0085>key= still evades. That is deliberate: U+0085 is a line
# separator, and removing it would join two lines and could manufacture a match
# across a line boundary that exists in neither line. A URL split across a line
# break is already broken as a URL. The cost of the other choice is worse than
# the miss.
INVISIBLE = re.compile(
    "["
    # Generated from unicodedata, not typed: every Cf code point plus the
    # zero-advance marks and blank-rendering fillers. 437 code points in
    # 29 ranges, 8 of them above the BMP.
    "\u00ad\u034f\u0600-\u0605\u061c\u06dd\u070f\u0890-\u0891\u08e2\u115f-\u1160\u17b4-\u17b5\u180b-\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f\u2800\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff9-\ufffb\U000110bd\U000110cd\U00013430-\U0001343f\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0001\U000e0020-\U000e007f\U000e0100-\U000e01ef"
    "]")


def normalise_for_scan(text):
    """Make both engines see the same characters, and deny an invisible-character
    evasion. The upload gate normalises identically; a parity check compares the
    two on shared inputs."""
    return INVISIBLE.sub("", text).replace("\u0085", " ")


SECRETS = [
    ("an Anthropic key",            re.compile(r"\bsk-ant-[A-Za-z0-9\-]{10,}\b")),
    ("an OpenAI style key",         re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("an AWS access key id",        re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a GitHub token",              re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"
                                               r"|\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("a Google API key",            re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("a Slack token",               re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    ("a JWT",                       re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\."
                                               r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("a private key block",         re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    # Anchored at the query delimiter, not at the scheme. Tying the parameter to
    # https?:// needs a scan run between them, and every form of that run was
    # wrong: an upper bound inverts between engines (Python counts code points,
    # some engines count UTF-16 units) and cuts off any parameter past it, and no bound
    # is quadratic. [?&] anchoring has no length
    # axis and no backtracking site. (?<=\S) keeps "append ?key=value to the
    # URL" documentation clean; every match of the old scheme-tied form
    # contained a match of this one, so nothing it caught is lost.
    #
    # SIGNED-URL SIGNATURES, added 2026-09-01. The vocabulary was token, key,
    # secret, auth, apikey, api_key and access_token, and a presigned URL is
    # called none of those. Its entire security IS the signature parameter, so
    # the most credential-shaped URL in circulation published through both
    # gates. An AWS presigned URL was refused only incidentally, by the AKIA key
    # id sitting elsewhere in the same string; swap AKIA for ASIA, which is what
    # a temporary-credential presign carries, and nothing sees it at all.
    #
    # THE VENDOR PREFIX IS A BOUNDED ASCII CLASS AND NOT A LIST OF CLOUDS.
    # (?:[Xx]-[A-Za-z][A-Za-z0-9]{1,9}-)? covers X-Amz-, X-Goog-, X-Ms- and
    # whatever the next one is called, and a bound is safe here only because the
    # class it bounds cannot match an astral character: Python counts code
    # points and V8 counts UTF-16 units, so a bound over any class that CAN
    # match one puts the two engines on opposite sides of it. That is the defect
    # the delimiter anchoring above exists to have removed, and it is why this
    # sentence is checked rather than assumed.
    #
    # MEASURED BEFORE ADDING. 119,708 third-party prose and configuration files
    # from four package caches. Old rule fires on 171 files (0.143%), new rule
    # on 194 (0.162%). ZERO OLD-ONLY files, which is the containment claim:
    # nothing the narrower rule caught is lost. Zero per-file disagreements
    # between Python re and V8, both rules, all 119,708. Zero hits on any of the
    # 34 fixture passports, validator fixtures and golden examples.
    #
    # THE 23 NEW-ONLY FILES ARE THREE STRINGS, and none is a live credential:
    # "&sig=REDACTED" in 18 copies of one cached document, "?signature=${...}"
    # in 3, "&sig=${signature}" in 2. The last two are template interpolation
    # carrying a name and not a value, which is a PRE-EXISTING class the old
    # rule fired on too. The first is a redaction placeholder, and the database
    # URL rule below already excludes that whole vocabulary. Excluding it here
    # would remove 18 of the 23 and it is NOT smuggled into this change: it is a
    # separate judgement that gets its own measured round or does not happen.
    #
    # This change widens a vocabulary and nothing else. The normalisation
    # applied before scanning is unchanged by it, and a shape that survives that
    # normalisation survives this rule too. What is and is not normalised is
    # written up in the project's own records rather than here, for the reason
    # the vendor block below gives: a file that ships to strangers is not the
    # place to write out what still gets past it.
    # THE VALUE-LENGTH FLOOR, added 2026-09-01, AND WHY IT IS ON HALF THE RULE.
    #
    # The rule now has two arms. The seven original names keep \S+ and are
    # unchanged. sig, signature and X-*-Signature require sixteen value
    # characters, counted with [^\s&#] so the floor measures THE VALUE and not
    # the rest of the URL: with \S{16,}, ?signature=off&theme=darkmode clears the
    # floor on the strength of the parameters after it, which is the opposite of
    # the intent.
    #
    # WHY NOT ON ALL TEN, WHICH WAS THE FIRST ATTEMPT. A floor across the whole
    # rule broke four probes in the cross-engine parity harness: "a short URL
    # with a short
    # token", "a token as the second parameter", "a token behind an astral path"
    # and "a token past 512 characters of URL", all of which assert that
    # ?token=abc123 is caught. Those are the delimiter-anchoring regression tests
    # and they encode a decision already taken here: a short token is still a
    # token. Overturning it silently, to fix a false positive, is not a trade this
    # change is entitled to make. The suite refused it, which is the suite working.
    #
    # A SIGNATURE DIFFERS IN KIND, NOT IN LENGTH. sig and signature carry the
    # output of an HMAC or a hash. There is no such thing as a three-character
    # signature, so the floor costs nothing on that arm while buying the whole
    # settings-URL class: ?signature=off, ?signature=none, ?sig=1, ?sig=weekly.
    # Those are ordinary lines in a mail or reporting agent's passport.
    #
    # THE ACCEPTED MISS, stated plainly. A signature value under sixteen
    # characters no longer refuses here, and nothing else covers it:
    # CREDENTIAL_ASSIGN carries neither name, which is the same single-coverage
    # that made the invisible-character fix above load-bearing for these three.
    # Measured against 17,682 prose files, the value lengths this rule matches
    # fall into two groups with nothing between them: four at ten characters or
    # fewer, all non-credentials, and twenty-eight at twenty-three or more. The
    # floor sits inside a measured empty gap rather than at a number somebody
    # liked.
    #
    # ?key=off AND ?auth=none STILL REFUSE, and that is deliberate. They belong to
    # the seven-name arm, which keeps its old behaviour. Fixing them means putting
    # a floor on names whose short values the probes above require to be caught.
    # A pre-existing false positive is cheaper than a new hole, so it stays, and
    # it stays written down here rather than discovered again.
    #
    # THE PLACEHOLDER EXCLUSION IS A SHAPE TEST, NOT A WORD LIST, added 2026-09-01.
    #
    # WHY IT EXISTS. Product rule 1 says a passport names credential TYPES and
    # never values, so an owner doing exactly what the product asks writes
    # ?X-Amz-Signature=<signature>. This rule could not tell a type name from a
    # value, refused the name, and E_SECRET_FOUND has no override and tells the
    # owner to rotate a credential that never existed. A gate that refuses the
    # behaviour the product instructs is worse than the gap it was closing.
    #
    # WHY IT IS NOT A WORD LIST, WHICH IS WHAT IT WAS FIRST. Porting
    # CREDENTIAL_ASSIGN's YOUR/EXAMPLE/PLACEHOLDER/REDACTED vocabulary here
    # excludes on how a value STARTS, so any real credential beginning with one
    # of those words is released. Two that a word list lets through:
    # ?auth=XXXqwertyuiopasdfghjklz and ?key=YOURqwertyuiopasdfghjkl. Removing
    # one word at a time chases the symptom. A word list on a credential gate
    # trades a real leak for a cosmetic gain.
    #
    # A SIGIL TEST CANNOT RELEASE A CREDENTIAL. No credential begins with <, {,
    # $ or [. That covers <signature>, ${SECRET}, {{sig}} and [REDACTED], which
    # is the whole set of shapes an owner writes when deliberately NOT writing a
    # secret in a URL, and it cannot be widened by accident into something that
    # releases a value.
    #
    # WHAT IT GIVES UP, stated: ?token=PLACEHOLDER and ?sig=REDACTED still refuse.
    # Those are false positives. They are also what main already does for the
    # seven original names, so nothing regresses, and refusing a value that looks
    # like a credential slot is the safe direction at a public door. A false
    # positive costs one confusing message; releasing ?auth=XXXqwerty... costs
    # somebody their credential.
    ("a URL carrying a credential", re.compile(r"(?<=\S)[?&](?:(?:token|key|secret|auth|apikey|api_key|access_token)=(?!(?:\$\{[A-Za-z_][A-Za-z_]{0,64}\}|\{\{[A-Za-z_][A-Za-z _.-]{0,64}\}\}|<[A-Za-z_][A-Za-z _.-]{0,64}>|\[[A-Za-z_][A-Za-z _.-]{0,64}\])(?=[\s&#]|$))\S+|(?:[Ss][Ii][Gg]|(?:[Xx]-[A-Za-z][A-Za-z0-9]{1,9}-)?[Ss][Ii][Gg][Nn][Aa][Tt][Uu][Rr][Ee])=(?!(?:\$\{[A-Za-z_][A-Za-z_]{0,64}\}|\{\{[A-Za-z_][A-Za-z _.-]{0,64}\}\}|<[A-Za-z_][A-Za-z _.-]{0,64}>|\[[A-Za-z_][A-Za-z _.-]{0,64}\])(?=[\s&#]|$))[^\s&#]{16,})")),
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
    # AND THE LIST IS NOT THE PART THAT FAILED FIRST. The first version of this
    # rule named Slack, Discord, Teams and Zapier and still published a Discord
    # webhook on the versioned API path, a Slack URL with an uppercase host, and
    # the pre-webhook.office.com Office 365 connector form. Three vendors that
    # were on the list, reached by a path segment or a casing the pattern did
    # not cover. A vendor list makes the ceiling obvious and hides the fact that
    # the matching under it can be narrow too. Hosts are compared
    # case-insensitively now, because DNS is, and a host written in capitals is
    # a live credential rather than a near miss.
    #
    # SIX SHAPES WERE FOUND PUBLISHING, FIVE ARE CLOSED HERE, ONE IS NOT, and
    # the one is the honest limit rather than an oversight: a self-hosted
    # Mattermost at chat.example.com/hooks/<key>, and any private
    # /hooks/<key> like it, still publishes. There is no host to enumerate,
    # because the host is the customer's. Nothing short of a generic
    # "long opaque path segment" rule reaches it, and that rule would refuse
    # ordinary URLs by the thousand. Stated so that five closed does not read
    # as all found.
    #
    # ONE BRANCH RESTS ON AN UNVERIFIED VENDOR SHAPE. hooks.zapier.com/hooks/
    # standard/ was observed publishing and nobody here has confirmed against
    # Zapier that it is a live form rather than a plausible one. It is included
    # because the cost of a wrong guess is asymmetric: a branch for a shape that
    # does not exist is dead code measured at zero false positives, and a
    # missing branch for one that does is a credential. Marked so the next
    # person removes it on evidence rather than on tidiness.
    #
    # ONE ENTRY IS NOT A WEBHOOK AT ALL. api.telegram.org/bot<id>:<token> is a
    # bot API endpoint whose token sits in the path, so the same argument
    # applies and no other rule sees it. It gets its own branch because it is
    # self-terminating: the credential ends at the token and there is no long
    # opaque tail after it, so it cannot share the trailing run the others need.
    #
    # A Slack /services/ URL was ALREADY refused before this rule existed, by a
    # narrower Slack-specific rule below. What this adds for Slack is /triggers/
    # and /workflows/, and an uppercase host on both. Worth knowing so that four
    # vendor names here do not read as four doors that were standing open.
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
    ("a webhook URL carrying its own secret",
     re.compile(r"(?<![A-Za-z0-9_])[Hh][Tt][Tt][Pp][Ss]://(?:(?:[Hh][Oo][Oo][Kk][Ss]\.[Ss][Ll][Aa][Cc][Kk]\.[Cc][Oo][Mm]/(?:services|triggers|workflows)|(?:[Cc][Aa][Nn][Aa][Rr][Yy]\.|[Pp][Tt][Bb]\.)?[Dd][Ii][Ss][Cc][Oo][Rr][Dd](?:[Aa][Pp][Pp])?\.[Cc][Oo][Mm]/api/(?:v[0-9]{1,2}/)?webhooks|[A-Za-z0-9-]{1,63}\.[Ww][Ee][Bb][Hh][Oo][Oo][Kk]\.[Oo][Ff][Ff][Ii][Cc][Ee]\.[Cc][Oo][Mm]/webhookb2|[Oo][Uu][Tt][Ll][Oo][Oo][Kk]\.[Oo][Ff][Ff][Ii][Cc][Ee]\.[Cc][Oo][Mm]/webhook|[Hh][Oo][Oo][Kk][Ss]\.[Zz][Aa][Pp][Ii][Ee][Rr]\.[Cc][Oo][Mm]/hooks/(?:catch|standard))[/A-Za-z0-9_+=-]{0,4}/[A-Za-z0-9_/+=@.-]{16,}|[Aa][Pp][Ii]\.[Tt][Ee][Ll][Ee][Gg][Rr][Aa][Mm]\.[Oo][Rr][Gg]/bot[0-9]{6,}:[A-Za-z0-9_-]{20,})")),
    ("a password assignment",       re.compile(r"\b(password|passwd|pwd)\s*[:=]\s*\S+", re.I)),
    # A database URL carrying a password. Nothing else here sees this shape:
    # the EMAIL rule hits it by accident on the user:pass@host middle, and a
    # form with no @-shaped middle was caught nowhere.
    # Measured against a corpus of third-party markdown before adding it.
    # The negated classes all exclude \s, so THIS rule cannot span a line break.
    # The newline-spanning pin covers a credential assignment. A password
    # assignment spells its own line breaks rather than using \s, so it spans
    # too while a source-level check cannot see that; the suite asserts its
    # behaviour directly.
    #
    # The password is bounded because the unbounded form was quadratic. A bound
    # is a trade and this one is deliberate.
    ("a database URL carrying a password", re.compile(r"\b[a-z][a-z0-9+.\-]{0,31}://[^\s:/@]+:(?!<(?:[Rr][Ee][Dd][Aa][Cc][Tt][Ee][Dd]|[Ss][Cc][Rr][Uu][Bb][Bb][Ee][Dd]|[Rr][Ee][Mm][Oo][Vv][Ee][Dd]|[Hh][Ii][Dd][Dd][Ee][Nn]|[Mm][Aa][Ss][Kk][Ee][Dd]|[Ee][Ll][Ii][Dd][Ee][Dd]|[Oo][Mm][Ii][Tt][Tt][Ee][Dd]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Yy][Oo][Uu][Rr][-_]?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Xx]+|\*+)(?:[:_ -][A-Za-z]+)*[-_0-9]*>@|\[(?:[Rr][Ee][Dd][Aa][Cc][Tt][Ee][Dd]|[Ss][Cc][Rr][Uu][Bb][Bb][Ee][Dd]|[Rr][Ee][Mm][Oo][Vv][Ee][Dd]|[Hh][Ii][Dd][Dd][Ee][Nn]|[Mm][Aa][Ss][Kk][Ee][Dd]|[Ee][Ll][Ii][Dd][Ee][Dd]|[Oo][Mm][Ii][Tt][Tt][Ee][Dd]|[Pp][Ll][Aa][Cc][Ee][Hh][Oo][Ll][Dd][Ee][Rr]|[Yy][Oo][Uu][Rr][-_]?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Xx]+|\*+)(?:[:_ -][A-Za-z]+)*[-_0-9]*\]@|\*+@|\$\{[A-Za-z_][A-Za-z0-9_]*\}@|\$[A-Za-z_][A-Za-z0-9_]*@)[^\s:/@]{3,}@[^\s/]+")),
    # SendGrid. Named because its value is three dot-separated segments, the
    # exact shape the credential rule below now refuses so that it stops
    # matching ordinary code like forge.random.getBytesSync.
    ("a SendGrid key",              re.compile(r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b")),
    # Context-anchored, so that this file is a second line of defence behind the
    # scrubber rather than a weaker copy of it.
    #
    # Every rule above knows one vendor's key shape. None of them can see a
    # 64-character lowercase hex token, because nothing about the string says
    # credential rather than sha256.
    #
    # Kept deliberately in step with the scrubber's CREDENTIAL_ASSIGN. If you
    # change one, change the other: they are two copies of one judgement, and a
    # duplicated rule with nothing comparing it is a rule that drifts. Compare
    # them by behaviour rather than by name; a rule compared only by name is not
    # compared.
    #
    # Tightened against a large corpus of third-party markdown. A wider form
    # matches far more than it should, so each exclusion below is narrow and
    # deliberate; the reasoning for each sits beside the scrubber's copy of this
    # rule. This file travels inside the distributable skill, so it names no
    # file outside it.
    ("a credential assignment",     re.compile(
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
        r"[A-Za-z0-9_\-+/=~.]{20,}[\"']?")),
    # ── Vendor prefixes, added 2026-08-31 ────────────────────────────────────
    #
    # Eight credential shapes over the seven rules below. Every one of them
    # passed BOTH gates before this block existed, bare in prose. In KEY=value
    # form the credential-assignment rule above already caught most of them;
    # prose is the shape that actually leaked, because a passport's tacit_notes
    # is prose and an owner's instruction line quoted into it is prose.
    #
    # WHY THE BOUNDS ARE LOWER BOUNDS AND NOT THE DOCUMENTED LENGTHS. The token
    # this block was written for is a Notion integration token with 47
    # alphanumerics after ntn_. Notion documents 46. The obvious rule,
    # ntn_[A-Za-z0-9]{46} with a trailing boundary, does not match it, and the
    # mechanism is worth stating exactly because it is easy to misfix: the rule
    # consumes 46 characters and then needs a non-word character, and the 47th
    # character is alphanumeric, so the boundary fails. Changing 46 to 47 fixes
    # this token and breaks on the next one of a different length. An open lower
    # bound is the only form that does not encode a guess about the vendor.
    #
    # So: measure the bound against a real token, never take it from the vendor's
    # documentation. A rule with a wrong bound passes every false-positive test
    # anybody would think to write and never fires on the thing it exists for.
    #
    # WHY (?<![A-Za-z0-9_]) AND NOT \b. Python's \b is Unicode-aware and V8's,
    # without /u, is not, so \bntn_... matches "éntn_TOKEN" at the endpoint
    # and not here. Measured, not assumed. A parity harness that compares regex
    # SOURCE rather than behaviour cannot see that divergence at all, because
    # these two sources are identical while the two engines disagree on the
    # string. An explicit ASCII class means the same thing in both
    # engines, and it is also strictly more sensitive than Python's \b. Every
    # rule below uses it, so this block adds nothing to that pile.
    #
    # The trailing (?![A-Za-z0-9_]) excludes the underscore deliberately. It is
    # what keeps an ordinary snake_case identifier such as
    # hf_<32 chars>_cache from matching, and on the legacy Notion rule it is
    # load bearing: the underscore in the lookbehind is why client_secret_...,
    # AWS_SECRET_ACCESS_KEY and my_secret_token_value cannot match at all, rather
    # than merely being unlikely to. secret_ reads as a weak prefix in English
    # and behaves as a strong one here, because the two properties that make it
    # common in prose, a leading underscore run and an underscore-broken tail,
    # are the two the pattern excludes.
    #
    # MEASURED BEFORE ADDING. Zero false positives for all seven over a corpus
    # of 18,911 third-party prose and configuration files. Zero on all 34
    # fixture passports, validator fixtures and golden examples. A hit on one
    # of those disqualifies a rule outright: they are the documents this gate
    # exists to pass, so a rule that refuses one is wrong no matter how good it
    # looks elsewhere. That is an assertion in the test suite rather than a
    # convention. Over this project's own source the seven
    # fire six times, and all six are planted test credentials.
    #
    # All eight verified behaviourally identical between Python re and V8, first
    # over 30 hand-written vectors held in one file that both test suites read,
    # so a vector added there is checked in both engines or in neither, and then
    # over 6,628 generated vectors with non-ASCII context, at zero divergences.
    #
    # DELIBERATELY AND PERMANENTLY EXCLUDED, so that nobody re-proposes them:
    # raw 40-character AWS-style secrets and generic 40-character lowercase hex.
    # On that same corpus they fire on 4.06% and 5.15% of files, hitting git
    # SHAs and checksums in ordinary READMEs, and both fire on this project's
    # own scrubber test input. At a public front door that refuses
    # about one honest document in twenty and tells its author to rotate a
    # commit hash.
    #
    # The corpus roots, the per-source counts and the six planted literals are
    # written up in the project's own records; this file travels to strangers,
    # so it does not cite a path they cannot open, and naming one would put a
    # single machine's directory layout into a file that ships inside the skill.
    #
    # THE ACCEPTED COST, named because it is real and was found by attacking
    # this block rather than by defending it. A DOCUMENTATION PLACEHOLDER of the
    # right shape is refused: "put ntn_xxxxxxxx... in your .env" and
    # "SK00000000000000000000000000000000" are refused exactly as a live token
    # would be. These rules carry none of the placeholder exclusions the
    # credential-assignment rule above carries, and a passport whose whole job is
    # to name credential TYPES is a document that invites writing shapes.
    #
    # It is accepted rather than overlooked, for two reasons. It is not a new
    # behaviour: every one of the seven pre-existing vendor rules does the same
    # thing, verified rather than assumed, so sk-xxxxxxxx, AKIAXXXXXXXXXXXXXXXX,
    # AIzaXXX..., xoxb-000..., ghp_xxx... and sk-ant-xxx... are all already
    # refused today. Extending eight more vendors to the same rule is uniform
    # where an exclusion on only these eight would not be. And the class did not
    # appear once in 18,911 third-party documentation files, which is where it
    # would show up if it were common.
    #
    # If it turns out to bite a real uploader, the fix is a shared placeholder
    # exclusion applied to all twenty rules at once, not a special case
    # bolted onto these eight.
    #
    # WHAT IS STILL UNCAUGHT, named so that the presence of seven rules is not
    # read as coverage. Found by attacking this block rather than by writing it:
    #
    #   - Slack WORKFLOW trigger URLs, hooks.slack.com/triggers/T.../<digits>/...
    #     A live credential. The rule below is anchored on /services/T.../B.../
    #     and cannot see a different path with a numeric second segment. This is
    #     the one most worth adding next.
    #   - Stripe whsec_ webhook signing secrets.
    #   - Linear lin_oauth_ tokens.
    #   - Figma figd_, Resend re_, Telegram bot tokens.
    #   - Both Twilio values that are actually secret; see the absence note above.
    #
    # Each is a deliberate gap rather than an oversight now that it is written
    # down, and none was measured, so none should be added without the same
    # false-positive work the seven above got.
    #
    # THESE RULES ARE A BACKSTOP AND NOT A SOLUTION, and the difference is the
    # thing to carry away from this block rather than the seven patterns in it.
    # A capture model can quote an owner's own text back into the passport after
    # its own review has already passed, and no pattern here sees that: the
    # rules run over what was written, and the failure is in what got written
    # after they ran. Any credential shape travels that path, including the ones
    # this block cannot match. The remedy is a completeness check late in the
    # capture, comparing the finished document against what the scrub reported,
    # and not another rule here.
    ("a Notion integration token",
     re.compile(r"(?<![A-Za-z0-9_])ntn_[A-Za-z0-9]{40,}(?![A-Za-z0-9_])")),
    # Notion's legacy format. The bound is a judgement, not a measurement: the
    # canonical length is documented as 43 and nobody here has verified that
    # against Notion. It is written open and BELOW the documented length on
    # purpose, so that a real token shorter than the document claims still fires.
    # Measured identical at zero false positives at every bound from {20,} to
    # {43}, so unlike ntn_ there is no cliff to fall off here.
    ("a legacy Notion integration token",
     re.compile(r"(?<![A-Za-z0-9_])secret_[A-Za-z0-9]{32,}(?![A-Za-z0-9_])")),
    # Live and restricted only. sk_test_ and rk_test_ are deliberately absent:
    # they are not secrets, and matching them would refuse ordinary Stripe
    # documentation. Note this is NOT caught by the OpenAI-style rule above,
    # which requires sk- with a hyphen.
    ("a Stripe secret key",
     re.compile(r"(?<![A-Za-z0-9_])(?:sk|rk)_live_[A-Za-z0-9]{20,}(?![A-Za-z0-9_])")),
    # Anchored on the literal host, so it needs no boundary rule of its own and
    # has no length axis before the final segment. Every quantifier is followed
    # by a character outside its own class, so there is no backtracking site.
    ("a Slack webhook URL",
     re.compile(r"hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]{20,}")),
    ("a Hugging Face token",
     re.compile(r"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{32,}(?![A-Za-z0-9_])")),
    ("a Linear API key",
     re.compile(r"(?<![A-Za-z0-9_])lin_api_[A-Za-z0-9]{36,}(?![A-Za-z0-9_])")),
    # TWILIO IS DELIBERATELY ABSENT, and this comment is here so that the next
    # person to notice the absence does not close it.
    #
    # SK + 32 hex was added on 2026-08-31 and removed the same day. It is an API
    # key SID, and a SID is an IDENTIFIER: it is the basic-auth username and it
    # stays visible in the console. The two Twilio values that are actually
    # secret are the API key Secret, 32 mixed-case alphanumerics, and the Auth
    # Token, 32 lowercase hex. NEITHER carries a prefix, so both are
    # shape-identical to the two generic classes excluded permanently above, and
    # no rule in this table can ever catch them without paying that
    # false-positive rate.
    #
    # So a Twilio rule of this shape refuses the public half and misses both
    # secret halves. It is the same reasoning that keeps the AC account SID out.
    # Twilio is not covered here, cannot be covered by a prefix rule, and the
    # honest place for it is the owner-facing scrub review.
    ("an Airtable personal access token",
     re.compile(r"(?<![A-Za-z0-9_])pat[A-Za-z0-9]{14}\.[0-9a-f]{64}(?![A-Za-z0-9_])")),
]


def is_placeholder(raw):
    """Angle-bracketed prose a capture left behind, as opposed to a tag.

    Mirrors the endpoint's placeholder test. Two ways to tell, because
    the first alone was not enough: the template writes
    "<a declared-only capability>", whose first word is the anchor element, and
    calling that HTML sends the owner looking for markup they never wrote.
    """
    if raw.startswith("</"):
        return False
    inner = raw[1:-1].rstrip("/")
    name = re.match(r"[A-Za-z][A-Za-z0-9-]*", inner).group(0).lower()
    if name not in HTML_ELEMENTS:
        return True
    return bool(re.search(r"\s", inner)) and "=" not in inner


def fenced(lines):
    """Which lines are inside a fenced block. Fenced content is text and is
    escaped on render, so a tag in a golden example is not a tag. Length-aware,
    the same rule as everywhere else in this repo: a fence closes on a run at
    least as long as the one that opened it."""
    inside, open_len = [False] * len(lines), None
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if m:
            inside[i] = True
            if open_len is None:
                open_len = len(m.group(1))
            elif len(m.group(1)) >= open_len:
                open_len = None
            continue
        inside[i] = open_len is not None
    return inside


def check(text):
    """Everything the upload gate refuses on sight. Returns a list of (code, [detail])."""
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    inside = fenced(lines)
    out = []

    tags, holes = [], []
    for i, line in enumerate(lines):
        if inside[i] or INSTALLER_PLACEHOLDER in line:
            continue
        for m in TAG.finditer(line):
            target = holes if is_placeholder(m.group(0)) else tags
            target.append("line %d: %s" % (i + 1, m.group(0)))
    if tags:
        out.append(("E_HTML", tags[:20]))
    if holes:
        out.append(("E_UNFILLED", holes[:20]))

    comments = ["line %d: HTML comment" % (i + 1)
                for i, line in enumerate(lines)
                if "<!--" in line and INSTALLER_PLACEHOLDER not in line]
    if comments:
        out.append(("E_HTML", comments[:20]))

    active = []
    for pattern, what in ((r"javascript:", "javascript: URI"),
                          (r"vbscript:", "vbscript: URI"),
                          (r"data:text/html", "data:text/html URI")):
        if re.search(pattern, text, re.I):
            active.append(what)
    for m in LINK.finditer(text):
        scheme = SCHEME.match(m.group(1))
        if scheme and scheme.group(1).lower() not in ("https", "http", "mailto"):
            active.append(scheme.group(1) + ": link target")
    if active:
        out.append(("E_ACTIVE_CONTENT", sorted(set(active))[:10]))

    # BOTH the text as written AND the normalised copy, unioned.
    #
    # Normalising is not free in one direction. The URL rule is anchored
    # (?<=\S)[?&], which distinguishes a parameter sitting mid-run in a leaked
    # URL from documentation showing ?token= after a space. An invisible
    # character sitting BEFORE the ? satisfies that lookbehind, because it is
    # not whitespace. Strip it and the character before the ? becomes the space
    # again, so the rule stops matching and a credential this file caught before
    # the normalisation was added now publishes.
    #
    # Removal is required for the opposite position: an invisible BETWEEN the
    # delimiter and the parameter name breaks the adjacency the rule needs, and
    # only removal restores it. One substitution cannot serve both, because the
    # two positions want opposite things from the same character.
    #
    # So scan both forms and refuse if either fires. That is strictly a superset
    # of the pre-normalisation behaviour: it cannot lose a credential that was
    # caught before, which a single normalised pass demonstrably could.
    # Reproduced over nine cases across seven invisible characters, all of them
    # in the leak direction.
    scan = normalise_for_scan(text)
    # THE THIRD PASS IS THE ORIGINAL NORMALISATION, and it is why "superset" is
    # a theorem here rather than a measurement. Before this rule set widened,
    # the gate stripped exactly U+FEFF and mapped U+0085 to a space. That single pass
    # is not a subset of either of the two above: it beats both on a document that
    # needs U+FEFF removed and some OTHER invisible kept, because the other one is
    # \S and satisfies the lookbehind. Put U+FEFF inside a parameter name and a
    # soft hyphen before the delimiter and the old gate refuses while both new
    # passes miss. Running the old normalisation as its own pass makes the set of
    # things this gate refuses a strict superset of what it refused before, by
    # construction, for every input rather than for the inputs somebody tested.
    legacy = text.replace("\ufeff", "").replace("\u0085", " ")
    kinds = [kind for kind, pattern in SECRETS
             if pattern.search(scan) or pattern.search(text)
             or pattern.search(legacy)]
    if kinds:
        out.append(("E_SECRET_FOUND", kinds))

    return out


ADVICE = {
    "E_UNFILLED": "The capture did not finish. Replace each placeholder with the\n"
                  "  real thing. If they are the losses table in section 6, delete the\n"
                  "  placeholder row and leave that table empty: the install fills it in.",
    "E_HTML": "Passports are Markdown only. Remove the HTML and try again.",
    "E_ACTIVE_CONTENT": "A link or URI here can execute code. Remove it.",
    "E_SECRET_FOUND": "This was not stored. Re-run the scrub step, then treat that\n"
                      "  credential as exposed and rotate it.",
}


def main():
    # --codes prints one error code per line and nothing else. A parity check
    # uses it to diff this file against the other implementation on
    # every fixture; a person gets the prose form.
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    codes_only = "--codes" in sys.argv[1:]
    # --list-secret-rules prints THIS FILE's secret-rule labels, one per line,
    # and takes no passport. --dump-secret-rules prints each label with its
    # pattern source and flags as JSON.
    #
    # Both describe this file and nothing else. They exist so that a test can
    # compare this predictor against whatever it is meant to predict, on every
    # rule rather than only on the ones a fixture happens to exercise, and so
    # that the comparison is by PATTERN and not by label: two implementations
    # can hold the same rule name over different regexes and report agreement.
    # A name is not a rule.
    #
    # Read the output as a description of what this script will warn you about.
    # It is not a statement about what any other system accepts or refuses.
    if "--dump-secret-rules" in sys.argv[1:]:
        import json
        # Every flag, not just IGNORECASE. VERBOSE alone silently changes what a
        # pattern matches while leaving its source byte-identical.
        print(json.dumps({n: {"source": p.pattern,
                              "i": bool(p.flags & re.I), "s": bool(p.flags & re.S),
                              "m": bool(p.flags & re.M), "x": bool(p.flags & re.X),
                              # re.ASCII is reported because it leaves the pattern
                              # SOURCE byte-identical while changing what \\w, \\b,
                              # \\s and \\d match. Comparing sources alone would
                              # call two different rules the same rule.
                              "a": bool(p.flags & re.A)}
                          for n, p in SECRETS}))
        sys.exit(0)
    if "--list-secret-rules" in sys.argv[1:]:
        for label, _ in SECRETS:
            print(label)
        sys.exit(0)
    if len(args) != 1:
        print("Usage: preflight.py [--codes] PASSPORT.md", file=sys.stderr)
        sys.exit(2)
    # THE SIZE LIMIT IS PART OF THE QUESTION THIS TOOL ANSWERS.
    #
    # The endpoint refuses a body over MAX_BYTES before it looks at the content
    # at all, with E_TOO_LARGE. This file knew nothing about that,
    # so on a 300,000-byte passport it scanned the content, found no secret, and
    # printed "the upload endpoint will accept this passport's content" — which
    # is false, and false about the single question this tool exists to answer.
    #
    # A clean scan is not an acceptance. Checked FIRST, and in bytes rather than
    # characters, because MAX_BYTES is a byte cap and a passport full of
    # non-ASCII is longer on the wire than on the screen.
    MAX_BYTES = 262144

    raw = open(args[0], "rb").read()
    if len(raw) > MAX_BYTES:
        if codes_only:
            print("E_TOO_LARGE")
            sys.exit(1)
        print("The upload endpoint will refuse this passport:", file=sys.stderr)
        print("\nE_TOO_LARGE", file=sys.stderr)
        print("   %d bytes, over the %d limit. A passport describes an agent, it does\n"
              "   not contain one. Trim the golden examples and try again." % (len(raw), MAX_BYTES),
              file=sys.stderr)
        sys.exit(1)

    found = check(raw.decode("utf-8"))
    if codes_only:
        for code in sorted({c for c, _ in found}):
            print(code)
        sys.exit(1 if found else 0)
    if not found:
        print("OK: the upload endpoint will accept this passport's content.")
        sys.exit(0)
    print("The upload endpoint will refuse this passport:", file=sys.stderr)
    for code, details in found:
        print("\n%s" % code, file=sys.stderr)
        for d in details[:8]:
            print("  %s" % d, file=sys.stderr)
        if len(details) > 8:
            print("  ... and %d more" % (len(details) - 8), file=sys.stderr)
        print("  %s" % ADVICE.get(code, ""), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""validate.py — validate an agent passport Markdown file."""

import datetime
import re
import sys


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
    "delta vs", "delta versus", "delta against", "delta from the previous",
]


def parse_frontmatter(text):
    """Parse frontmatter between --- delimiters. Returns (pairs_dict, error_msg)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, "File does not start with ---"

    close_idx = None
    for i in range(1, min(len(lines), 41)):
        if lines[i].strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        return None, "Second --- not found within the first 40 lines"

    fm_lines = lines[1:close_idx]
    pairs = {}
    for line in fm_lines:
        colon = line.find(":")
        if colon == -1:
            continue
        key = line[:colon].strip()
        val = line[colon + 1:].strip()
        # Strip surrounding quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        pairs[key] = val

    return pairs, None


def get_body(text):
    """Return body text after the closing --- of frontmatter."""
    lines = text.split("\n")
    for i in range(1, min(len(lines), 41)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
    return ""


def consent_rows(body):
    """Return the data rows of the section 2 consent table, as lists of cells.

    Returns None when there is no table there at all, which is its own failure
    rather than a table with no rows."""
    start = body.find("## 2. What it needs from you")
    end = body.find("## 3. Functional spec")
    if start == -1 or end == -1 or end < start:
        return None

    lines = [l.strip() for l in body[start:end].split("\n")]
    table = [l for l in lines if l.startswith("|")]
    if len(table) < 3:          # header, divider, at least one row
        return None
    if not re.match(r"^\|?[\s:|-]+\|?$", table[1]):
        return None

    def cells(row):
        r = row.strip()
        if r.startswith("|"):
            r = r[1:]
        if r.endswith("|"):
            r = r[:-1]
        return [c.strip() for c in r.split("|")]

    if len(cells(table[0])) != 5:
        return None
    return [cells(r) for r in table[2:] if any(cells(r))]


def spec_lines(text):
    """Return [(line_number, line)] for the body of '## 3. Functional spec'.

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
        match = re.match(r"^\s*(`{3,})", line)
        if match:
            if fence_len is None:
                fence_len = len(match.group(1))
            elif len(match.group(1)) >= fence_len:
                fence_len = None
            if started:
                out.append((i + 1, line))
            continue
        if fence_len is None:
            if not started:
                if line.strip() == "## 3. Functional spec":
                    started = True
                continue
            if re.match(r"^#{1,2}\s", line):
                break
        if started:
            out.append((i + 1, line))
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
    out, inside = [], False
    for n, line in entries:
        if re.match(r"^" + re.escape(key) + r":", line):
            inside = True
            out.append((n, line))
            continue
        if inside:
            stripped = line.strip()
            if stripped and not line[:1].isspace() and not stripped.startswith("-"):
                break
            out.append((n, line))
    return out


def input_entries(block):
    """Split an `inputs:` block into one list of lines per entry."""
    entries, current = [], None
    for n, line in block[1:]:
        if re.match(r"^\s*-\s", line):
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


def validate(text):
    """Run all 14 checks. Return list of error strings."""
    errors = []

    # Check 1: frontmatter delimiters
    pairs, fm_err = parse_frontmatter(text)
    if fm_err:
        errors.append(f"FAIL 1: {fm_err}")
        return errors

    # Check 2: required keys
    missing = [k for k in REQUIRED_KEYS if k not in pairs]
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
    for h in expected_headings:
        count = sum(1 for bl in body.split("\n") if bl.strip() == h)
        if count == 0:
            errors.append(f"FAIL 4: missing heading '{h}'")
        elif count > 1:
            errors.append(f"FAIL 4: heading '{h}' appears {count} times (expected 1)")

    # Check heading order
    heading_indices = []
    for h in expected_headings:
        indices = [i for i, bl in enumerate(body.split("\n")) if bl.strip() == h]
        if indices:
            heading_indices.append(indices[0])

    for i in range(len(heading_indices) - 1):
        if heading_indices[i] >= heading_indices[i + 1]:
            errors.append(f"FAIL 4: headings are out of order")
            break

    # Check 5: comparison_mode
    comp_matches = re.findall(r"comparison_mode:\s*(\S+)", body)
    if len(comp_matches) == 0:
        errors.append("FAIL 5: no comparison_mode found")
    elif len(comp_matches) > 1:
        errors.append(f"FAIL 5: multiple comparison_mode lines ({len(comp_matches)})")
    elif comp_matches[0] not in ("structural", "exact", "input_relative"):
        errors.append(f"FAIL 5: comparison_mode value '{comp_matches[0]}' is not valid")

    # Check 6: capability_ref values
    cap_matches = re.findall(r"capability_ref:\s*(\S+)", body)
    for val in cap_matches:
        if val in VALID_CAPABILITIES:
            continue
        if val.startswith("money."):
            continue
        errors.append(f"FAIL 6: invalid capability_ref '{val}'")

    # Check 7: [SCRUBBED: implies scrub contains owner-reviewed
    if "[SCRUBBED:" in body:
        scrub_val = pairs.get("scrub", "")
        if "owner-reviewed" not in scrub_val:
            errors.append("FAIL 7: body contains [SCRUBBED: but scrub frontmatter lacks 'owner-reviewed'")

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
        match = re.match(r"^\s*(`{3,})", line)
        if match:
            if fence_len is None:
                fence_len = len(match.group(1))
            elif len(match.group(1)) >= fence_len:
                fence_len = None
        elif fence_len is None:
            if golden_start == -1 and line.strip() == "## 4. Golden examples":
                golden_start = offset
            elif (golden_start != -1 and golden_end == -1
                  and re.match(r"^#{1,2}\s", line)):
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
            match = re.match(r"^\s*(`{3,})", line)
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

    # Check 9: forbidden strings
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in body:
            errors.append(f"FAIL 9: body contains forbidden string '{forbidden}'")

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
        m = re.match(r"^\s*-?\s*id:\s*(\S+)", line)
        if m:
            slot_ids.add(m.group(1).strip("\"'"))

    for entry in input_entries(yaml_block(spec, "inputs")):
        credentialed, bound, target, at = None, False, None, None
        for n, line in entry:
            if re.match(r"^\s*-?\s*access:\s*credentialed\b", line):
                credentialed = n
            m = re.match(r"^\s*-?\s*binding:\s*(\S+)", line)
            if m:
                bound, target, at = True, m.group(1).strip("\"'"), n
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
            m = re.match(r"^\s*-?\s*fidelity:\s*(\S+)", line)
            if m and m.group(1).strip("\"'") not in ("exact", "lossy"):
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
    has_state = any(re.match(r"^\s*keeps:", line) for _, line in state)
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

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: validate.py PASSPORT.md", file=sys.stderr)
        sys.exit(1)

    try:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, IOError) as e:
        print(f"Error reading {sys.argv[1]}: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(text)
    if errors:
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()

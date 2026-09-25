#!/usr/bin/env python3
"""Insert the installer core and branch appendices into a passport's section 5.

Usage: assemble.py PASSPORT.md [OUT.md] [--branch=NAME]

Capture emits a passport whose section 5 is the placeholder line

    <!-- installer core and branches inserted on upload -->

because the installer text is product-owned and versioned separately from the
agent description. This script performs that insertion. The site's upload
endpoint does the same thing; keep the two in step.

Stdlib only. Exit 0 on success, 1 on any problem, including the two integration
hazards that only show up in the assembled file:

  - a line matching `comparison_mode:` inside installer text, which would break
    validate.py check 5, since it counts that pattern across the whole body
  - any denied-path string from validate.py check 9 appearing in installer text
"""

import os
import re
import unicodedata
import sys

PLACEHOLDER = "<!-- installer core and branches inserted on upload -->"
BRANCH_ORDER = ["chatgpt.md", "claude-ai.md", "claude-code.md", "generic.md"]
# MUST match validate.py's FORBIDDEN_STRINGS exactly. This list held five
# entries while that one held ten, so `.env`, `.key`, `id_ed25519`, `id_ecdsa`
# and `id_dsa` passed here and were then refused in the assembled file, which is
# the precise integration hazard this script's docstring says it exists to
# prevent. The guard failed open on the five most common modern cases.
#
# The lists are duplicated rather than imported because both files ship
# standalone and neither may import the other. They are compared by the
# project's own test suite, so a widening on one side and not the other fails
# the build instead of failing an owner at the upload box.
FORBIDDEN = [
    "browser_profile", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    ".pem", ".key", ".env", "credentials/", "secrets/",
]

# A SECOND COPY of validate.py's FORBIDDEN_STRINGS and its normalisation, and it
# has to be a copy. In the built skill both files are siblings in
# the skill's scripts/ folder and an import would work; in this repository
# they are scripts/ and tools/ and it would not. Neither file takes a
# dependency or edits sys.path to paper over that.
#
# What makes the copy safe is the test suite, which pins the two lists and
# the two normalisations to identical behaviour. This check exists only to say
# "validate.py check 9 will refuse the passport you are about to assemble", so
# the moment the two disagree it is worse than useless: it either passes text
# that will be refused later, or refuses text that would have been fine.
#
# The reasoning behind deleting noise rather than collapsing every non-alphanumeric
# run is written out in full at validate.py's normalize_forbidden. Short version:
# collapsing turns "credentials/" into the ordinary word "credentials" and refuses
# references/passport-template.md, which every capture starts from.
_FORBIDDEN_NOISE = re.compile(r"[\\`*_­​‌‍⁠﻿]")
_FORBIDDEN_SPLIT = re.compile(r"(?<=[a-z0-9])[ \t]*\n[ \t]*(?=[a-z0-9])")


def normalize_forbidden(text):
    """Fold away case and the noise a denied path can hide behind.

    Must stay byte-for-byte equivalent to validate.py's function of the same
    name. The test suite fails if it does not."""
    folded = unicodedata.normalize("NFKC", text).lower()
    return _FORBIDDEN_SPLIT.sub("", _FORBIDDEN_NOISE.sub("", folded))

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Each key lists the places its file can sit; resolve() returns the first that
# exists, so this script runs unchanged wherever it is installed.
LAYOUTS = {
    "core": ["references/installer-core.md", "references/installer-core.md"],
    "branch_dir": ["references/installer-branches", "references/installer-branches"],
    "judge": ["references/judge-prompt.md", "references/judge-prompt.md"],
}


def resolve(key):
    for rel in LAYOUTS[key]:
        path = os.path.join(root, rel)
        if os.path.exists(path):
            return path
    return None


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def judge_prompt():
    """The judge prompt only, without its operator preamble.

    The judge prompt is written for two audiences: documentation for a reader
    about why the judge is weak, and the prompt itself in one fenced block. Only
    the block belongs in a passport.
    """
    path = resolve("judge")
    if path is None:
        print("warning: no judge prompt, section 5 will have no verification step",
              file=sys.stderr)
        return None
    lines = read(path).split("\n")
    fences = [i for i, line in enumerate(lines) if line.startswith("````")]
    if len(fences) < 2:
        print("warning: judge prompt has no four-backtick fenced block, skipping",
              file=sys.stderr)
        return None
    body = "\n".join(lines[fences[0] + 1:fences[-1]]).strip()
    return "## Appendix: the verification judge\n\n" \
           "Run this at step 7, against the first real run.\n\n" + body


def installer_text(only=None):
    core = resolve("core")
    if core is None:
        print("FAIL: no installer core found under %s" % root, file=sys.stderr)
        sys.exit(1)
    parts = [read(core).rstrip()]
    judge = judge_prompt()
    if judge:
        parts.append(judge)
    branch_dir = resolve("branch_dir") or ""
    wanted = BRANCH_ORDER if only is None else [only]
    for name in wanted:
        path = os.path.join(branch_dir, name)
        if not os.path.exists(path):
            print("warning: missing branch %s" % name, file=sys.stderr)
            continue
        parts.append(read(path).rstrip())
    return "\n\n".join(parts) + "\n"


def check(text):
    """Return a list of problems the insertion would introduce."""
    problems = []
    for i, line in enumerate(text.split("\n"), 1):
        if re.search(r"comparison_mode:\s*\S", line):
            problems.append(
                "installer text line %d contains a `comparison_mode:` assignment, "
                "which makes the assembled passport fail validate.py check 5. "
                "Write it as prose or without the colon: %s" % (i, line.strip()[:70])
            )
    norm_text = normalize_forbidden(text)
    for word in FORBIDDEN:
        needle = normalize_forbidden(word)
        # Anchored when the entry starts with punctuation: NFKC folds an
        # ellipsis to three dots and "done...Pemberton" then matches `.pem`.
        # Must stay identical to validate.py check 9.
        pattern = (r"(?<=[a-z0-9])" if not needle[:1].isalnum() else "") + re.escape(needle)
        if re.search(pattern, norm_text):
            problems.append(
                "installer text contains the denied-path string %r, which fails "
                "validate.py check 9 in the assembled passport" % word
            )
    return problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    branch = None
    for a in sys.argv[1:]:
        if a.startswith("--branch="):
            key = a.split("=", 1)[1]
            match = [f for f in BRANCH_ORDER if f[:-3] == key]
            if not match:
                print("FAIL: unknown branch %r, expected one of %s"
                      % (key, ", ".join(f[:-3] for f in BRANCH_ORDER)), file=sys.stderr)
                sys.exit(1)
            branch = match[0]

    if len(args) not in (1, 2):
        print("Usage: assemble.py PASSPORT.md [OUT.md] [--branch=%s]"
              % "|".join(f[:-3] for f in BRANCH_ORDER), file=sys.stderr)
        sys.exit(1)

    src = args[0]
    passport = read(src)

    if PLACEHOLDER not in passport:
        print("FAIL: no installer placeholder found in %s" % src, file=sys.stderr)
        print("      expected the line: %s" % PLACEHOLDER, file=sys.stderr)
        sys.exit(1)

    text = installer_text(branch)
    problems = check(text)
    if problems:
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        sys.exit(1)

    out_text = passport.replace(PLACEHOLDER, text)
    dest = args[1] if len(args) == 2 else None
    if dest:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(out_text)
        print("wrote %s (%d bytes)" % (dest, len(out_text.encode("utf-8"))))
    else:
        sys.stdout.write(out_text)


if __name__ == "__main__":
    main()

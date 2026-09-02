#!/usr/bin/env python3
"""Publish a passport to the Agent Passport site and hand back its link.

Usage: publish.py PASSPORT.md [--endpoint URL] [--unconfirmed] [--json]

On success this prints the public URL as the last line of stdout and exits 0.
The capture skill's final step calls exactly that and opens the line it gets
back, so the contract (exit 0, absolute URL last, nothing after it) is load
bearing: whatever calls this script reads the last line and nothing else.

Why this exists: the skill used to end by writing an HTML file next to the
passport and opening it from disk. That was correct while there was nowhere to
put a passport, and wrong once app.phaeacia.ai existed. A file on disk carries
installer text frozen on the day it was made, cannot be withdrawn once it has
been mailed to somebody, and has no expiry. A published passport renders from
current installer text, dies by itself after thirty days, and can be deleted on
demand. So the skill publishes, and this is the step that does it.

What it does NOT do, deliberately:

  It does not decide to publish. Publishing puts a page on the public internet
  and the owner is the only one who can authorise that. The skill asks on the
  check-in; this script assumes the answer was yes and does not ask again.

  It does not paraphrase a refusal. A failure string is rendered as it arrives.
  A second copy of those messages here would drift from the first, and then two
  parts of one product would explain the same refusal differently.

  It does not retry past the owner-review gate unless told to. A passport whose
  frontmatter says owner_confirmed: false is refused once, with a one-shot ticket
  for the retry. The gate cannot verify that a human read anything and does not
  claim to; what it enforces is that the exchange happened. A script that spent
  the ticket automatically would turn the exchange into a formality, so the
  default is to stop and say what is missing. --unconfirmed spends it, and the
  published page still prints that nobody confirmed the description.

The delete token comes back exactly once, in the upload response, and the site
cannot reissue it. Losing it means a page that cannot be withdrawn before it
expires. So it is written to a file next to the passport rather than printed
into a conversation that scrolls, and that file is created 0600.
"""

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://app.phaeacia.ai/api/upload"
TIMEOUT_SECONDS = 30

EXIT_OK = 0
EXIT_USAGE = 1        # a local problem: bad arguments, unreadable file
EXIT_REFUSED = 2      # the endpoint answered and said no. Nothing was published.
EXIT_UNREACHABLE = 3  # no answer at all: offline, DNS, TLS, timeout
# Published, but the response could not be used. This is NOT a refusal and the
# caller must not treat it as one: a page is live and public, and the token that
# would take it down may be gone. The capture skill reads a non-zero exit as "the
# passport is finished without the page", which is the right thing to say for 1,
# 2 and 3 and a dangerous thing to say for this one, so it gets its own code.
EXIT_PUBLISHED_UNUSABLE = 4


def die(message, code):
    print(message, file=sys.stderr)
    sys.exit(code)


def link_path_for(passport_path):
    """<name>-passport.md becomes <name>-passport.link.md, beside it."""
    base = passport_path[:-3] if passport_path.endswith(".md") else passport_path
    return base + ".link.md"


def post(endpoint, body, ack=None):
    """One request. Returns (status, parsed_json_or_None, raw_text)."""
    headers = {
        "content-type": "text/markdown; charset=utf-8",
        "accept": "application/json",
        "user-agent": "agent-passport-capture/0.1",
    }
    if ack:
        headers["x-passport-owner-ack"] = ack

    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", "replace")
            return response.status, safe_json(raw), raw
    except urllib.error.HTTPError as exc:
        # A refusal is a normal answer here, not an exception. Every 4xx from
        # this endpoint carries a JSON body with the reason in it.
        raw = exc.read().decode("utf-8", "replace")
        return exc.code, safe_json(raw), raw
    except urllib.error.URLError as exc:
        die(
            "Could not reach the passport site (%s). The passport file is finished and "
            "valid; publishing is the only thing that did not happen. Try again when you "
            "are online, or upload the file yourself at https://app.phaeacia.ai/upload."
            % exc.reason,
            EXIT_UNREACHABLE,
        )
    except (ssl.SSLError, TimeoutError, OSError) as exc:
        die(
            "The connection to the passport site failed (%s). The passport file is "
            "finished and valid; publishing is the only thing that did not happen." % exc,
            EXIT_UNREACHABLE,
        )


def safe_json(raw):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def refusal_text(payload, status, raw):
    """The endpoint's own words, never ours. Falls back only when there are none."""
    if isinstance(payload, dict) and payload.get("message"):
        text = payload["message"]
        details = payload.get("details")
        if isinstance(details, list) and details:
            text += "\n" + "\n".join("  " + str(d) for d in details)
        return text
    return (
        "The passport site refused the upload with status %s and no readable reason. "
        "The passport file is unchanged.\n%s" % (status, raw[:400])
    )


def write_link_file(path, result, passport_path):
    lines = [
        "# Where this passport lives",
        "",
        "Published from `%s`." % os.path.basename(passport_path),
        "",
        "**Send this link** to whoever should have the agent. Their own assistant",
        "reads the page and takes it from there.",
        "",
        "    %s" % result["url"],
        "",
        "The page is public to anyone holding that link, and it deletes itself on",
        "%s. Renewing or deleting it early is done from the management page below."
        % result.get("expires_at", "its expiry date"),
        "",
        "## Management link, keep this one private",
        "",
        "    %s" % result["manage_url"],
        "",
        "It carries the delete token below in its address, which is what lets it",
        "withdraw or renew the passport without an account.",
        "",
        "## Delete token",
        "",
        "    %s" % result["delete_token"],
        "",
        "This is the only copy. The site does not store it in a form it can read",
        "back, so it cannot be sent to you again. Without it the page stays up",
        "until it expires by itself.",
    ]
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w",
              encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Publish a passport and print its public URL.",
        allow_abbrev=False,  # --unconf must not silently mean --unconfirmed
    )
    parser.add_argument("passport", help="path to the passport .md file")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("PHAEACIA_UPLOAD_ENDPOINT", DEFAULT_ENDPOINT),
        help="upload endpoint, for testing against a local dev server",
    )
    parser.add_argument(
        "--unconfirmed",
        action="store_true",
        help="publish a passport the owner never reviewed; the page says so",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the full response as JSON first"
    )
    args = parser.parse_args()

    try:
        with open(args.passport, "rb") as handle:
            body = handle.read()
    except OSError as exc:
        die("Cannot read %s: %s" % (args.passport, exc), EXIT_USAGE)

    if not body.strip():
        die("%s is empty. Nothing was published." % args.passport, EXIT_USAGE)

    status, payload, raw = post(args.endpoint, body)

    if status == 409 and isinstance(payload, dict) and payload.get("code") == "E_OWNER_UNCONFIRMED":
        if not args.unconfirmed:
            die(
                "This passport says the owner never reviewed it, so the site refused it "
                "once.\n\n%s\n\nRun the check-in with the owner and publish the "
                "reviewed passport, or re-run with --unconfirmed to publish it as it is. "
                "A passport published that way prints \"did not confirm this description\" "
                "on its own page, where the recipient will read it."
                % refusal_text(payload, status, raw),
                EXIT_REFUSED,
            )
        ticket = payload.get("ack")
        if not ticket:
            die(
                "The site refused this passport for owner review but issued no retry "
                "ticket, so it cannot be published this way.",
                EXIT_REFUSED,
            )
        status, payload, raw = post(args.endpoint, body, ack=ticket)

    if status != 200 or not isinstance(payload, dict) or not payload.get("ok"):
        die(refusal_text(payload, status, raw), EXIT_REFUSED)

    for key in ("url", "manage_url", "delete_token"):
        if not payload.get(key):
            die(
                "THE PASSPORT WAS PUBLISHED, and the response is missing %s, so it "
                "cannot be handed over safely. A public page may exist that this run "
                "cannot give you the link to or take down. Do not publish again: check "
                "https://app.phaeacia.ai/upload first. Everything the response did return:\n%s"
                % (key, json.dumps({k: v for k, v in payload.items()
                                    if k != "delete_token"}, indent=2)),
                EXIT_PUBLISHED_UNUSABLE,
            )

    link_file = link_path_for(args.passport)
    try:
        write_link_file(link_file, payload, args.passport)
    except OSError as exc:
        # The passport is published either way. Losing the token is the harm, so
        # this is the one place the token is printed rather than lost.
        print(
            "PUBLISHED, but the link file could not be written (%s).\n"
            "This is now the only copy of both. Save them before this scrolls away, "
            "they cannot be reissued:\n"
            "  manage: %s\n  delete token: %s"
            % (exc, payload["manage_url"], payload["delete_token"]),
            file=sys.stderr,
        )
        link_file = None

    if args.json:
        redacted = dict(payload)
        redacted["delete_token"] = "<written to the link file>"
        print(json.dumps(redacted, indent=2))

    if link_file:
        print("Link and delete token written to %s" % os.path.abspath(link_file))
    print("Expires %s" % payload.get("expires_at", "in 30 days"))
    print(payload["url"])   # last line, by contract
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

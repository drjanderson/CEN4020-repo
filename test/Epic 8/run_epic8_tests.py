"""Epic #8 (Messaging Part 1: Send Message) test generator, runner and packager.

Usage (from the repo root):
    python3 "test/Epic 8/run_epic8_tests.py" [--binary PATH]

For every test case below this script:
  1. writes Epic8-StoryN-Test-Input/<case>/ (seed data files, InCollege-Input-K.txt
     per program run, expected.json),
  2. runs InCollege once per input file in a fresh working directory (data files
     carry over between runs of the same case, to test persistence),
  3. saves the actual results to Epic8-StoryN-Test-Output/<case>/run-K/
     (console.txt, InCollege-Output.txt, stderr.txt, data files, result.txt),
  4. zips both folders as Epic8-StoryN-Test-Input.zip / -Output.zip,
  5. writes Epic8-Test-Summary.txt with PASS/FAIL per case.

Checks applied to every run: exit code 0, empty stderr, console output identical
to InCollege-Output.txt, plus each case's require / forbid / order / messages checks.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PASSWORD = "Test123!"
USERS = ["alice", "bob", "carol", "dave", "erin", "frank"]

# alice <-> bob    ACCEPTED (alice sent the request)
# carol <-> alice  ACCEPTED (carol sent the request)
# alice  -> dave   PENDING
# erin   -> alice  REJECTED
# frank            no relationship with anyone
REQUESTS = [
    ("alice", "bob", "ACCEPTED"),
    ("carol", "alice", "ACCEPTED"),
    ("alice", "dave", "PENDING"),
    ("erin", "alice", "REJECTED"),
]

STORIES = {
    1: "As a logged-in user, I want to send a private message to a user I am connected with.",
    2: "As a user sending a message, I want to select the recipient by their username.",
    3: "As a user sending a message, I want to enter free-form text as the message content.",
    4: "As a user, I want to be informed if I try to send a message to someone I am not connected with.",
    5: "As a user, I want my sent messages to be saved persistently for the recipient to view later.",
    6: "As a user, I want the main menu to have a 'Messages' option, which includes 'Send a New Message'.",
    7: "As a tester, I want the program to read all user inputs for sending messages from a file so I can automate testing.",
    8: "As a tester, I want the program to write all screen output related to sending messages to a file so I can easily verify results.",
}

NOT_CONNECTED = "You can only message users you are connected with."
CONTENT_PROMPT = "Enter your message (max 200 chars):"
RECIPIENT_PROMPT = "Enter recipient's username (must be a connection):"
UNDER_CONSTRUCTION = "View My Messages is under construction."
TOO_LONG = "Message must be 200 characters or fewer."
EMPTY = "Message cannot be empty."
INVALID = "Invalid choice, please try again."
MAIN_MENU = [
    "1. Create/Edit My Profile", "2. View My Profile", "3. Search for a job",
    "4. Find someone you know", "5. Learn a New Skill", "6. Logout",
    "7. View pending requests", "8. View connections", "9. Messages",
    "Enter your choice:",
]
MSG_MENU = [
    "--- Messages Menu ---", "1. Send a New Message", "2. View My Messages",
    "3. Back to Main Menu", "Enter your choice:",
]

TEXT_200 = ("InCollege 200-char boundary test. " * 6)[:196] + "END."
TEXT_201 = TEXT_200 + "!"
TEXT_300 = "L" * 300
SYMBOLS = "Hey Bob! Meet @ 3:30pm, room #204 -- bring notes; ok? (50% done) & 'single' \"double\" [x] {y} <z> ~^*_=+|/\\"


def sent(name):
    return f"Message sent to {name} successfully!"


def run(user, lines, logout=True, **checks):
    """One program execution: log in as `user`, feed `lines`, then log out."""
    tail = ["3", "6"] if logout else []
    return {"input": ["1", user, PASSWORD, *lines, *tail], **checks}


def case(cid, story, kind, title, runs, seed_messages=None):
    return {"id": cid, "story": story, "type": kind, "title": title,
            "seed_messages": seed_messages or [], "runs": runs}


CASES = [
    # Story 1 - send to a connected user
    case("E8-01", 1, "positive", "Send a message to a connection whose request I sent (alice -> bob)", [
        run("alice", ["9", "1", "bob", "Hi Bob, want to study for CEN4020 together?"],
            require=[re.escape(sent("bob"))],
            order=[*MSG_MENU, "1", RECIPIENT_PROMPT, "bob", CONTENT_PROMPT,
                   "Hi Bob, want to study for CEN4020 together?", sent("bob"), *MSG_MENU],
            messages=[["alice", "bob", "Hi Bob, want to study for CEN4020 together?"]]),
    ]),
    case("E8-02", 1, "positive", "Send a message to a connection whose request I accepted (alice -> carol)", [
        run("alice", ["9", "1", "carol", "Thanks for connecting, Carol!"],
            require=[re.escape(sent("carol"))],
            messages=[["alice", "carol", "Thanks for connecting, Carol!"]]),
    ]),
    case("E8-03", 1, "positive", "The other side of a connection can message back (bob -> alice)", [
        run("bob", ["9", "1", "alice", "Sure Alice, see you at the library."],
            require=[re.escape(sent("alice"))],
            messages=[["bob", "alice", "Sure Alice, see you at the library."]]),
    ]),
    case("E8-04", 1, "positive", "Send several messages to different connections in one session", [
        run("alice", ["9", "1", "bob", "First message to Bob", "1", "carol", "First message to Carol",
                      "1", "bob", "Second message to Bob"],
            order=[sent("bob"), *MSG_MENU, sent("carol"), *MSG_MENU, sent("bob"), *MSG_MENU],
            messages=[["alice", "bob", "First message to Bob"],
                      ["alice", "carol", "First message to Carol"],
                      ["alice", "bob", "Second message to Bob"]]),
    ]),

    # Story 2 - recipient selection by username
    case("E8-05", 2, "positive", "Recipient prompt comes first and the confirmation names the chosen recipient", [
        run("alice", ["9", "1", "carol", "Picked by username"],
            order=[RECIPIENT_PROMPT, "carol", CONTENT_PROMPT, "Picked by username", sent("carol")],
            forbid=[re.escape(sent("bob"))],
            messages=[["alice", "carol", "Picked by username"]]),
    ]),
    case("E8-06", 2, "edge", "Recipient typed with surrounding spaces is accepted and stored as the clean username", [
        run("alice", ["9", "1", "   bob   ", "Padded recipient"],
            require=[re.escape(sent("bob"))],
            messages=[["alice", "bob", "Padded recipient"]]),
    ]),
    case("E8-07", 2, "negative", "Recipient username in the wrong case (BOB) is not treated as a connection", [
        run("alice", ["9", "1", "BOB"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)],
            order=[RECIPIENT_PROMPT, "BOB", NOT_CONNECTED, *MSG_MENU], messages=[]),
    ]),
    case("E8-08", 2, "negative", "Blank recipient username is rejected", [
        run("alice", ["9", "1", ""],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)], messages=[]),
    ]),

    # Story 3 - free-form content
    case("E8-09", 3, "positive", "Free-form content with punctuation, digits and symbols is stored verbatim", [
        run("alice", ["9", "1", "bob", SYMBOLS],
            require=[re.escape(sent("bob"))], order=[CONTENT_PROMPT, SYMBOLS, sent("bob")],
            messages=[["alice", "bob", SYMBOLS]]),
    ]),
    case("E8-10", 3, "edge", "Message of exactly 200 characters is accepted and stored in full", [
        run("alice", ["9", "1", "bob", TEXT_200],
            require=[re.escape(sent("bob"))], forbid=[re.escape(TOO_LONG)],
            messages=[["alice", "bob", TEXT_200]]),
    ]),
    case("E8-11", 3, "negative", "Message of 201 characters is rejected and not saved", [
        run("alice", ["9", "1", "bob", TEXT_201],
            require=[re.escape(TOO_LONG)], forbid=[re.escape(sent("bob"))],
            order=[CONTENT_PROMPT, TOO_LONG, *MSG_MENU], messages=[]),
    ]),
    case("E8-12", 3, "negative", "Very long message (300 chars, longer than the input buffer) is rejected and the next input line is still read correctly", [
        run("alice", ["9", "1", "bob", TEXT_300, "2"],
            require=[re.escape(TOO_LONG), re.escape(UNDER_CONSTRUCTION)],
            forbid=[re.escape(sent("bob"))],
            order=[TOO_LONG, *MSG_MENU, "2", UNDER_CONSTRUCTION, *MSG_MENU, "3", *MAIN_MENU],
            messages=[]),
    ]),
    case("E8-13", 3, "edge", "Empty message content is not sent", [
        run("alice", ["9", "1", "bob", ""],
            require=[re.escape(EMPTY)], forbid=[re.escape(sent("bob"))],
            order=[CONTENT_PROMPT, "", EMPTY, *MSG_MENU], messages=[]),
    ]),

    # Story 4 - not connected
    case("E8-14", 4, "negative", "Recipient does not exist (ghost)", [
        run("alice", ["9", "1", "ghost"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)],
            order=[RECIPIENT_PROMPT, "ghost", NOT_CONNECTED, *MSG_MENU], messages=[]),
    ]),
    case("E8-15", 4, "negative", "Recipient exists but has no connection with the sender (frank)", [
        run("alice", ["9", "1", "frank"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)], messages=[]),
    ]),
    case("E8-16", 4, "negative", "Recipient has a PENDING request from the sender (alice -> dave)", [
        run("alice", ["9", "1", "dave"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)], messages=[]),
    ]),
    case("E8-17", 4, "negative", "Receiver of a PENDING request tries to message the requester (dave -> alice)", [
        run("dave", ["9", "1", "alice"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)], messages=[]),
    ]),
    case("E8-18", 4, "negative", "Recipient whose request was REJECTED (erin -> alice)", [
        run("erin", ["9", "1", "alice"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)], messages=[]),
    ]),
    case("E8-19", 4, "negative", "User tries to message themselves (alice -> alice)", [
        run("alice", ["9", "1", "alice"],
            require=[re.escape(NOT_CONNECTED)], forbid=[re.escape(CONTENT_PROMPT)], messages=[]),
    ]),
    case("E8-20", 4, "negative", "After a rejected recipient the user can still message a real connection; only that one is saved", [
        run("alice", ["9", "1", "frank", "1", "dave", "1", "bob", "Second try worked"],
            order=[NOT_CONNECTED, *MSG_MENU, NOT_CONNECTED, *MSG_MENU, CONTENT_PROMPT, sent("bob")],
            forbid=[re.escape(sent("frank")), re.escape(sent("dave"))],
            messages=[["alice", "bob", "Second try worked"]]),
    ]),

    # Story 5 - persistence
    case("E8-21", 5, "positive", "Messages survive a restart and new messages are appended, not overwritten", [
        run("alice", ["9", "1", "bob", "Saved before restart"],
            messages=[["alice", "bob", "Saved before restart"]]),
        run("bob", ["9", "1", "alice", "Sent after restart"],
            messages=[["alice", "bob", "Saved before restart"],
                      ["bob", "alice", "Sent after restart"]]),
    ]),
    case("E8-22", 5, "positive", "A pre-existing InCollege-Messages.txt is kept and the new message is appended", [
        run("carol", ["9", "1", "alice", "New message from Carol"],
            messages=[["bob", "alice", "Old message already on disk"],
                      ["carol", "alice", "New message from Carol"]]),
    ], seed_messages=[["bob", "alice", "2026110112000000+0000", "Old message already on disk"]]),
    case("E8-23", 5, "positive", "Accepting a pending request allows messaging immediately and after a restart", [
        run("dave", ["7", "1", "9", "1", "alice", "Thanks for the request, Alice!"],
            require=[r"Connection request from alice accepted!", re.escape(sent("alice"))],
            messages=[["dave", "alice", "Thanks for the request, Alice!"]]),
        run("alice", ["9", "1", "dave", "Welcome to my network, Dave"],
            require=[re.escape(sent("dave"))],
            messages=[["dave", "alice", "Thanks for the request, Alice!"],
                      ["alice", "dave", "Welcome to my network, Dave"]]),
    ]),

    # Story 6 - Messages menu
    case("E8-24", 6, "positive", "Main menu has 'Messages'; submenu shows Send / View / Back; View is under construction; Back returns to main menu", [
        run("alice", ["9", "2"],
            order=[*MAIN_MENU, "9", *MSG_MENU, "2", UNDER_CONSTRUCTION, *MSG_MENU, "3", *MAIN_MENU, "6"],
            messages=[]),
    ]),
    case("E8-25", 6, "negative", "Invalid choices in the Messages menu are rejected and the menu is shown again", [
        run("alice", ["9", "4", "0", "abc", ""],
            order=[*MSG_MENU, "4", INVALID, *MSG_MENU, "0", INVALID, *MSG_MENU, "abc", INVALID,
                   *MSG_MENU, "", INVALID, *MSG_MENU, "3", *MAIN_MENU],
            messages=[]),
    ]),
    case("E8-26", 6, "positive", "Messages menu can be entered and left repeatedly in one session", [
        run("alice", ["9", "3", "9", "2", "3", "9", "1", "bob", "Third visit"],
            order=[*MSG_MENU, "3", *MAIN_MENU, "9", *MSG_MENU, "2", UNDER_CONSTRUCTION, *MSG_MENU, "3",
                   *MAIN_MENU, "9", *MSG_MENU, "1", RECIPIENT_PROMPT],
            messages=[["alice", "bob", "Third visit"]]),
    ]),
    case("E8-27", 6, "positive", "Regression: View connections still works after sending a message", [
        run("alice", ["9", "1", "bob", "Before checking my network", "3", "8", "2"], logout=False,
            require=[re.escape(sent("bob")), r"--- Your Network ---", r"Username: bob\b", r"Username: carol\b"],
            forbid=[r"Username: dave\b", r"Username: erin\b"],
            messages=[["alice", "bob", "Before checking my network"]]),
    ]),

    # Story 7 - input read from file (incl. end-of-file handling)
    case("E8-28", 7, "positive", "Complete send flow driven only by InCollege-Input.txt (matches the epic's sample run)", [
        run("alice", ["9", "1", "bob", "Hello from the input file", "2"],
            order=["Welcome to InCollege!", "Enter your choice:", "1", "Please enter your username:", "alice",
                   "Please enter your password:", PASSWORD, "You have successfully logged in.",
                   "Welcome, alice!", *MAIN_MENU, "9", *MSG_MENU, "1", RECIPIENT_PROMPT, "bob",
                   CONTENT_PROMPT, "Hello from the input file", sent("bob"), *MSG_MENU, "2",
                   UNDER_CONSTRUCTION, *MSG_MENU, "3", *MAIN_MENU, "6"],
            messages=[["alice", "bob", "Hello from the input file"]]),
    ]),
    case("E8-29", 7, "edge", "Input file ends right after choosing Messages: program exits cleanly", [
        run("alice", ["9"], logout=False, order=[*MSG_MENU], messages=[]),
    ]),
    case("E8-30", 7, "edge", "Input file ends at the recipient prompt: program exits cleanly, nothing saved", [
        run("alice", ["9", "1"], logout=False, order=[RECIPIENT_PROMPT],
            forbid=[re.escape(NOT_CONNECTED)], messages=[]),
    ]),
    case("E8-31", 7, "edge", "Input file ends at the message prompt: program exits cleanly, nothing saved", [
        run("alice", ["9", "1", "bob"], logout=False, order=[CONTENT_PROMPT],
            forbid=[re.escape(sent("bob"))], messages=[]),
    ]),

    # Story 8 - output written to file, identical to console
    case("E8-32", 8, "positive", "Console and InCollege-Output.txt are identical for a session mixing sends, errors and long input", [
        run("alice", ["9", "x", "1", "ghost", "1", "dave", "1", "bob", TEXT_201, "1", "bob", SYMBOLS,
                      "1", "carol", TEXT_200, "2"],
            require=[re.escape(NOT_CONNECTED), re.escape(TOO_LONG), re.escape(sent("bob")),
                     re.escape(sent("carol")), re.escape(UNDER_CONSTRUCTION)],
            messages=[["alice", "bob", SYMBOLS], ["alice", "carol", TEXT_200]]),
    ]),
]


def fixed(value, width):
    return f"{value:<{width}}"[:width]


def build_binary(dest):
    subprocess.run(["make", f"TARGET={dest}"], cwd=ROOT, check=True, capture_output=True, text=True)


def write_inputs(c, case_dir):
    case_dir.mkdir(parents=True)
    (case_dir / "InCollege-Accounts.txt").write_text(
        "".join(f"{fixed(u, 20)}{fixed(PASSWORD, 12)}\n" for u in USERS))
    (case_dir / "InCollege-Requests.txt").write_text(
        "".join(f"{fixed(s, 20)}{fixed(r, 20)}{st}\n" for s, r, st in REQUESTS))
    if c["seed_messages"]:
        (case_dir / "InCollege-Messages.txt").write_text("".join(
            f"{fixed(s, 20)}{fixed(r, 20)}{fixed(ts, 21)}{text}\n" for s, r, ts, text in c["seed_messages"]))
    for k, r in enumerate(c["runs"], 1):
        (case_dir / f"InCollege-Input-{k}.txt").write_text("\n".join(r["input"]) + "\n")
    expected = {k: v for k, v in c.items() if k != "seed_messages"}
    expected["user_story"] = STORIES[c["story"]]
    expected["always_checked"] = ["exit code 0", "stderr empty",
                                  "console output identical to InCollege-Output.txt"]
    (case_dir / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")


def check_messages(path, expected):
    """Each record: sender X(20), recipient X(20), timestamp X(21), content X(200)."""
    lines = path.read_text().splitlines() if path.exists() else []
    if len(lines) != len(expected):
        return [f"InCollege-Messages.txt has {len(lines)} record(s), expected {len(expected)}"]
    problems = []
    for n, (line, (s, r, text)) in enumerate(zip(lines, expected), 1):
        if line[0:20] != fixed(s, 20):
            problems.append(f"record {n}: sender field {line[0:20]!r}, expected {fixed(s, 20)!r}")
        if line[20:40] != fixed(r, 20):
            problems.append(f"record {n}: recipient field {line[20:40]!r}, expected {fixed(r, 20)!r}")
        if not re.fullmatch(r"\d{16}[+-]\d{4}",line[40:61]):
            problems.append(f"record {n}: timestamp field {line[40:61]!r} is not a date-time")
        if line[61:].rstrip() != text:
            problems.append(f"record {n}: content {line[61:].rstrip()!r}, expected {text!r}")
    return problems


def check_order(lines, wanted):
    pos = 0
    for item in wanted:
        try:
            pos = lines.index(item, pos) + 1
        except ValueError:
            return [f"expected line not found in order: {item!r} (after output line {pos})"]
    return []


def run_case(c, binary, in_dir, out_dir):
    failures = []
    with tempfile.TemporaryDirectory(prefix="epic8-") as tmp:
        work = Path(tmp)
        for f in in_dir.glob("InCollege-*.txt"):
            if not f.name.startswith("InCollege-Input"):
                shutil.copy(f, work / f.name)
        for k, r in enumerate(c["runs"], 1):
            shutil.copy(in_dir / f"InCollege-Input-{k}.txt", work / "InCollege-Input.txt")
            (work / "InCollege-Output.txt").unlink(missing_ok=True)
            proc = subprocess.run([str(binary)], cwd=work, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=10)
            output_file = (work / "InCollege-Output.txt").read_text() \
                if (work / "InCollege-Output.txt").exists() else ""
            lines = proc.stdout.splitlines()
            problems = []
            if proc.returncode != 0:
                problems.append(f"exit code {proc.returncode}")
            if proc.stderr:
                problems.append("stderr is not empty")
            if proc.stdout != output_file:
                problems.append("console output differs from InCollege-Output.txt")
            for pattern in r.get("require", []):
                if not re.search(pattern, proc.stdout, re.M):
                    problems.append(f"required output missing: /{pattern}/")
            for pattern in r.get("forbid", []):
                if re.search(pattern, proc.stdout, re.M):
                    problems.append(f"forbidden output present: /{pattern}/")
            problems += check_order(lines, r.get("order", []))
            if "messages" in r:
                problems += check_messages(work / "InCollege-Messages.txt", r["messages"])

            run_dir = out_dir / f"run-{k}"
            run_dir.mkdir(parents=True)
            (run_dir / "console.txt").write_text(proc.stdout)
            (run_dir / "stderr.txt").write_text(proc.stderr)
            for f in work.glob("InCollege-*.txt"):
                shutil.copy(f, run_dir / f.name)
            (run_dir / "result.txt").write_text(
                ("PASS\n" if not problems else "FAIL\n") + "".join(f"- {p}\n" for p in problems))
            failures += [f"run-{k}: {p}" for p in problems]
    return failures


def zip_folder(folder):
    with zipfile.ZipFile(folder.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            z.write(path, path.relative_to(folder.parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--binary", help="prebuilt InCollege executable (default: build with make)")
    args = parser.parse_args()

    for old in list(HERE.glob("Epic8-Story*-Test-*")):
        shutil.rmtree(old) if old.is_dir() else old.unlink()

    with tempfile.TemporaryDirectory(prefix="epic8-build-") as build:
        binary = Path(args.binary).resolve() if args.binary else Path(build) / "InCollege"
        if not args.binary:
            build_binary(binary)

        summary, failed = [], 0
        for c in CASES:
            prefix = f"Epic8-Story{c['story']}-Test"
            in_dir = HERE / f"{prefix}-Input" / c["id"]
            out_dir = HERE / f"{prefix}-Output" / c["id"]
            write_inputs(c, in_dir)
            failures = run_case(c, binary, in_dir, out_dir)
            failed += bool(failures)
            summary.append(f"[{'PASS' if not failures else 'FAIL'}] {c['id']} (Story {c['story']}, "
                           f"{c['type']}) {c['title']}")
            summary += [f"         {f}" for f in failures]

    for story in sorted({c["story"] for c in CASES}):
        for side in ("Input", "Output"):
            zip_folder(HERE / f"Epic8-Story{story}-Test-{side}")

    summary.append(f"\n{len(CASES) - failed}/{len(CASES)} test cases passed.")
    (HERE / "Epic8-Test-Summary.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()

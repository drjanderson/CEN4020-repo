"""Epic #9 (Messaging Part 2: View Messages) test generator, runner and packager.

Usage (from the repo root):
    python3 "test/Epic 9/run_epic9_tests.py" [--binary PATH]

For every test case below this script:
  1. writes Epic9-StoryN-Test-Input/<case>/ (seed data files, InCollege-Input-K.txt
     per program run, expected.json),
  2. runs InCollege once per input file in a fresh working directory (data files
     carry over between runs of the same case, to test persistence across restarts),
  3. saves the actual results to Epic9-StoryN-Test-Output/<case>/run-K/
     (console.txt, InCollege-Output.txt, stderr.txt, data files, result.txt),
  4. zips both folders as Epic9-StoryN-Test-Input.zip / -Output.zip,
  5. writes Epic9-Test-Summary.txt with PASS/FAIL per case.

Checks applied to every run: exit code 0, empty stderr, console output identical
to InCollege-Output.txt, plus each case's require / forbid / order / block /
count / messages checks.
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
# bob   <-> carol  ACCEPTED (bob sent the request)
# alice  -> dave   PENDING
# erin   -> alice  REJECTED
# frank            no relationship with anyone
REQUESTS = [
    ("alice", "bob", "ACCEPTED"),
    ("carol", "alice", "ACCEPTED"),
    ("bob", "carol", "ACCEPTED"),
    ("alice", "dave", "PENDING"),
    ("erin", "alice", "REJECTED"),
]

STORIES = {
    1: "As a logged-in user, I want to view all messages I have received.",
    2: "As a user viewing messages, I want to clearly see who sent each message and its content.",
    3: "As a user, I want to be informed if I have no messages to display.",
    4: "As a user, I want the 'Messages' menu to allow me to 'View My Messages'.",
    5: "As a tester, I want the program to read all user inputs for viewing messages from a file so I can automate testing.",
    6: "As a tester, I want the program to write all screen output related to viewing messages to a file so I can easily verify results.",
}

VIEW_HEADER = "--- Your Messages ---"
VIEW_FOOTER = "---------------------"
SEPARATOR = "---"
NO_MESSAGES = "You have no messages at this time."
UNDER_CONSTRUCTION = "View My Messages is under construction."
RECIPIENT_PROMPT = "Enter recipient's username (must be a connection):"
CONTENT_PROMPT = "Enter your message (max 200 chars):"
INVALID = "Invalid choice, please try again."
SENT_NOW = {"regex": r"Sent: \d{4}-\d{2}-\d{2} \d{2}:\d{2}"}  # timestamp of a message sent during the test
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

TEXT_200 = ("Long message display test for InCollege inbox. " * 5)[:196] + "END."
SYMBOLS = "Meet @ 3:30pm, room #204 -- bring notes; ok? (50% done) & 'single' \"double\" [x] {y} <z> ~^*_=+|/\\"

# Seed records written before the first run (sender, recipient, raw CURRENT-DATE timestamp, content).
# These stand in for messages sent in Week 8, before the program was restarted.
TS1, SHOWN1 = "2026110110300000+0000", "Sent: 2026-11-01 10:30"
TS2, SHOWN2 = "2026110209150000+0000", "Sent: 2026-11-02 09:15"
TS3, SHOWN3 = "2026110318450000+0000", "Sent: 2026-11-03 18:45"
TS4, SHOWN4 = "2026110407050000+0000", "Sent: 2026-11-04 07:05"


def shown(sender, text, sent_line):
    """The three lines the program prints for one message."""
    return [f"From: {sender}", f"Message: {text}", sent_line]


def inbox(*messages):
    """Full expected inbox output: header, messages separated by '---', footer."""
    lines = [VIEW_HEADER]
    for n, m in enumerate(messages):
        if n:
            lines.append(SEPARATOR)
        lines += m
    return lines + [VIEW_FOOTER]


EMPTY_INBOX = [VIEW_HEADER, NO_MESSAGES, VIEW_FOOTER]


def run(user, lines, logout=True, **checks):
    """One program execution: log in as `user`, feed `lines`, then go back and log out."""
    tail = ["3", "6"] if logout else []
    return {"input": ["1", user, PASSWORD, *lines, *tail], **checks}


def case(cid, story, kind, title, runs, seed_messages=None):
    return {"id": cid, "story": story, "type": kind, "title": title,
            "seed_messages": seed_messages or [], "runs": runs}


# 15 messages to alice, alternating bob / carol, one per day 2026-11-01 .. 2026-11-15 at 08:00.
MANY = [(["bob", "carol"][n % 2], "alice", f"202611{n + 1:02d}08000000+0000",
         f"Inbox message number {n + 1:02d}") for n in range(15)]
MANY_SHOWN = [shown(s, text, f"Sent: 2026-11-{n + 1:02d} 08:00") for n, (s, _, _, text) in enumerate(MANY)]

CASES = [
    # Story 1 - view all received messages (incl. persistence across restarts)
    case("E9-01", 1, "positive", "User with exactly one received message sees it", [
        run("alice", ["9", "2"],
            block=[[*MSG_MENU, "2", *inbox(shown("bob", "Hi Alice, glad we connected!", SHOWN1)), *MSG_MENU]],
            count={"From: ": 1},
            messages=[["bob", "alice", "Hi Alice, glad we connected!"]]),
    ], seed_messages=[["bob", "alice", TS1, "Hi Alice, glad we connected!"]]),
    case("E9-02", 1, "positive", "Multiple messages from different senders are all shown, oldest first", [
        run("alice", ["9", "2"],
            block=[inbox(shown("bob", "Hi Alice, glad we connected!", SHOWN1),
                         shown("carol", "Check out this job posting I found!", SHOWN2))],
            count={"From: ": 2}),
    ], seed_messages=[["bob", "alice", TS1, "Hi Alice, glad we connected!"],
                      ["carol", "alice", TS2, "Check out this job posting I found!"]]),
    case("E9-03", 1, "positive", "Multiple messages from the same sender are all shown", [
        run("alice", ["9", "2"],
            block=[inbox(shown("bob", "First note", SHOWN1), shown("bob", "Second note", SHOWN2),
                         shown("bob", "Third note", SHOWN3))],
            count={"From: bob": 3}),
    ], seed_messages=[["bob", "alice", TS1, "First note"], ["bob", "alice", TS2, "Second note"],
                      ["bob", "alice", TS3, "Third note"]]),
    case("E9-04", 1, "positive", "Only messages addressed to the logged-in user are shown (not other users' or my own sent ones)", [
        run("alice", ["9", "2"],
            block=[inbox(shown("bob", "For Alice from Bob", SHOWN2),
                         shown("carol", "For Alice from Carol", SHOWN4))],
            forbid=[r"For Bob", r"For Carol", r"Alice to Bob"], count={"From: ": 2}),
    ], seed_messages=[["alice", "bob", TS1, "Alice to Bob (sent by me)"],
                      ["bob", "alice", TS2, "For Alice from Bob"],
                      ["carol", "bob", TS3, "For Bob from Carol"],
                      ["carol", "alice", TS4, "For Alice from Carol"],
                      ["bob", "carol", TS4, "For Carol from Bob"]]),
    case("E9-05", 1, "positive", "Persistence: messages sent in earlier program runs are retrieved after restart", [
        run("bob", ["9", "1", "alice", "Sent by Bob in run 1"],
            messages=[["bob", "alice", "Sent by Bob in run 1"]]),
        run("carol", ["9", "1", "alice", "Sent by Carol in run 2"],
            messages=[["bob", "alice", "Sent by Bob in run 1"], ["carol", "alice", "Sent by Carol in run 2"]]),
        run("alice", ["9", "2"],
            block=[[VIEW_HEADER, "From: bob", "Message: Sent by Bob in run 1", SENT_NOW, SEPARATOR,
                    "From: carol", "Message: Sent by Carol in run 2", SENT_NOW, VIEW_FOOTER]],
            count={"From: ": 2}),
    ]),
    case("E9-06", 1, "positive", "Persistence: viewing does not delete or change messages; a second run shows the same inbox", [
        run("alice", ["9", "2"],
            block=[inbox(shown("bob", "Week 8 message from Bob", SHOWN1),
                         shown("carol", "Week 8 message from Carol", SHOWN2))],
            messages=[["bob", "alice", "Week 8 message from Bob"], ["carol", "alice", "Week 8 message from Carol"]]),
        run("alice", ["9", "2"],
            block=[inbox(shown("bob", "Week 8 message from Bob", SHOWN1),
                         shown("carol", "Week 8 message from Carol", SHOWN2))],
            messages=[["bob", "alice", "Week 8 message from Bob"], ["carol", "alice", "Week 8 message from Carol"]]),
    ], seed_messages=[["bob", "alice", TS1, "Week 8 message from Bob"],
                      ["carol", "alice", TS2, "Week 8 message from Carol"]]),
    case("E9-07", 1, "edge", "Many messages (15) are all shown in order with a separator between each", [
        run("alice", ["9", "2"],
            block=[inbox(*MANY_SHOWN)], count={"From: ": 15, r"---$": 14}),
    ], seed_messages=[list(m) for m in MANY]),

    # Story 2 - see who sent each message and its content
    case("E9-08", 2, "positive", "Each message shows From, Message and Sent lines, in that order", [
        run("bob", ["9", "2"],
            block=[[VIEW_HEADER, "From: alice", "Message: Lunch at noon?", SHOWN3, SEPARATOR,
                    "From: carol", "Message: Sure, I will join.", SHOWN4, VIEW_FOOTER]]),
    ], seed_messages=[["alice", "bob", TS3, "Lunch at noon?"], ["carol", "bob", TS4, "Sure, I will join."]]),
    case("E9-09", 2, "edge", "A 200-character message is displayed in full, not truncated", [
        run("alice", ["9", "1", "bob", TEXT_200], messages=[["alice", "bob", TEXT_200]]),
        run("bob", ["9", "2"],
            block=[[VIEW_HEADER, "From: alice", f"Message: {TEXT_200}", SENT_NOW, VIEW_FOOTER]]),
    ]),
    case("E9-10", 2, "edge", "Punctuation, digits and symbols in content are displayed verbatim", [
        run("alice", ["9", "1", "carol", SYMBOLS], messages=[["alice", "carol", SYMBOLS]]),
        run("carol", ["9", "2"],
            block=[[VIEW_HEADER, "From: alice", f"Message: {SYMBOLS}", SENT_NOW, VIEW_FOOTER]]),
    ]),
    case("E9-11", 2, "positive", "End to end: message sent through the app shows the right sender, content and today's timestamp", [
        run("bob", ["9", "1", "carol", "Group meeting moved to Friday"],
            messages=[["bob", "carol", "Group meeting moved to Friday"]]),
        run("carol", ["9", "2"],
            block=[[VIEW_HEADER, "From: bob", "Message: Group meeting moved to Friday", SENT_NOW, VIEW_FOOTER]],
            forbid=[r"^From: carol$"]),
    ]),

    # Story 3 - no messages
    case("E9-12", 3, "negative", "No InCollege-Messages.txt file exists: 'no messages' notice is shown", [
        run("alice", ["9", "2"], block=[[*MSG_MENU, "2", *EMPTY_INBOX, *MSG_MENU]],
            forbid=[r"^From: "]),
    ]),
    case("E9-13", 3, "negative", "Messages exist but none are for this user: 'no messages' notice is shown", [
        run("dave", ["9", "2"], block=[EMPTY_INBOX], forbid=[r"^From: ", r"For Bob", r"For Alice"]),
    ], seed_messages=[["bob", "alice", TS1, "For Alice"], ["alice", "bob", TS2, "For Bob"]]),
    case("E9-14", 3, "negative", "User who has only sent messages (none received) gets the 'no messages' notice", [
        run("carol", ["9", "1", "alice", "Outgoing only", "2"],
            block=[EMPTY_INBOX], forbid=[r"^From: ", r"Message: Outgoing only"],
            messages=[["carol", "alice", "Outgoing only"]]),
    ]),
    case("E9-15", 3, "negative", "Empty (0-byte) InCollege-Messages.txt: 'no messages' notice is shown", [
        run("alice", ["9", "2"], block=[EMPTY_INBOX], forbid=[r"^From: "], messages=[]),
    ], seed_messages="EMPTY"),
    case("E9-16", 3, "negative", "User with no connections (frank) has no messages", [
        run("frank", ["9", "2"], block=[EMPTY_INBOX], forbid=[r"^From: "]),
    ], seed_messages=[["bob", "alice", TS1, "Not for Frank"]]),

    # Story 4 - Messages menu offers View My Messages
    case("E9-17", 4, "positive", "Option 2 'View My Messages' opens the inbox (no longer under construction) and the menu returns", [
        run("alice", ["9", "2"],
            order=[*MAIN_MENU, "9", *MSG_MENU, "2", VIEW_HEADER, VIEW_FOOTER, *MSG_MENU, "3", *MAIN_MENU, "6"],
            forbid=[re.escape(UNDER_CONSTRUCTION)]),
    ], seed_messages=[["bob", "alice", TS1, "Menu test"]]),
    case("E9-18", 4, "positive", "After viewing, '3. Back to Main Menu' returns to the main menu and other features still work", [
        run("alice", ["9", "2", "3", "8", "2"], logout=False,
            order=[VIEW_FOOTER, *MSG_MENU, "3", *MAIN_MENU, "8", "--- Your Network ---"],
            require=[r"Username: bob\b", r"Username: carol\b"]),
    ], seed_messages=[["bob", "alice", TS1, "Regression test"]]),
    case("E9-19", 4, "positive", "View, send, view again in one session: inbox is re-read and excludes my own sent message", [
        run("bob", ["9", "2", "1", "alice", "Reply from Bob", "2"],
            block=[[*MSG_MENU, "2", *inbox(shown("carol", "Hello Bob", SHOWN1)), *MSG_MENU, "1"],
                   [*MSG_MENU, "2", *inbox(shown("carol", "Hello Bob", SHOWN1)), *MSG_MENU, "3"]],
            forbid=[r"^Message: Reply from Bob$"], count={"From: ": 2},
            messages=[["carol", "bob", "Hello Bob"], ["bob", "alice", "Reply from Bob"]]),
    ], seed_messages=[["carol", "bob", TS1, "Hello Bob"]]),
    case("E9-20", 4, "negative", "Invalid Messages-menu choices are rejected, then View My Messages still works", [
        run("alice", ["9", "4", "0", "abc", "", "2"],
            order=[*MSG_MENU, "4", INVALID, *MSG_MENU, "0", INVALID, *MSG_MENU, "abc", INVALID,
                   *MSG_MENU, "", INVALID, *MSG_MENU, "2", VIEW_HEADER, "From: bob", VIEW_FOOTER],
            count={"From: ": 1}),
    ], seed_messages=[["bob", "alice", TS1, "Still works"]]),

    # Story 5 - inputs read from file (incl. end-of-file handling)
    case("E9-21", 5, "positive", "Full view flow driven only by InCollege-Input.txt (matches the epic's sample run)", [
        run("alice", ["9", "2"],
            block=[["Welcome to InCollege!", "Log In", "Create New Account", "Enter your choice:", "1",
                    "Please enter your username:", "alice", "Please enter your password:", PASSWORD,
                    "You have successfully logged in.", "Welcome, alice!", *MAIN_MENU, "9", *MSG_MENU, "2",
                    *inbox(shown("bob", "Hi there! Glad we connected on InCollege.", SHOWN1),
                           shown("carol", "Check out this interesting job posting I found!", SHOWN2)),
                    *MSG_MENU, "3", *MAIN_MENU, "6"]]),
    ], seed_messages=[["bob", "alice", TS1, "Hi there! Glad we connected on InCollege."],
                      ["carol", "alice", TS2, "Check out this interesting job posting I found!"]]),
    case("E9-22", 5, "edge", "Input file ends right after choosing View: inbox is shown and the program exits cleanly", [
        run("alice", ["9", "2"], logout=False,
            block=[["2", *inbox(shown("bob", "Last input test", SHOWN1)), *MSG_MENU]]),
    ], seed_messages=[["bob", "alice", TS1, "Last input test"]]),
    case("E9-23", 5, "edge", "Input file ends right after choosing Messages: no inbox, program exits cleanly", [
        run("alice", ["9"], logout=False, order=[*MSG_MENU], forbid=[re.escape(VIEW_HEADER)]),
    ], seed_messages=[["bob", "alice", TS1, "Never displayed"]]),
    case("E9-24", 5, "edge", "Menu choice with surrounding spaces ('  2  ') still opens View My Messages", [
        run("alice", ["9", "  2  "],
            order=[*MSG_MENU, "2", VIEW_HEADER, "From: bob", "Message: Spaces test", VIEW_FOOTER],
            forbid=[re.escape(INVALID)]),
    ], seed_messages=[["bob", "alice", TS1, "Spaces test"]]),

    # Story 6 - output written to file, identical to console
    case("E9-25", 6, "positive", "Console and InCollege-Output.txt are identical for a long session (invalid input, 15-message inbox, send, re-view)", [
        run("alice", ["9", "x", "2", "1", "bob", SYMBOLS, "2", "1", "carol", TEXT_200, "2"],
            count={"From: ": 45, re.escape(VIEW_HEADER) + "$": 3}, require=[re.escape(INVALID)],
            messages=[*[[s, r, t] for s, r, _, t in MANY], ["alice", "bob", SYMBOLS],
                      ["alice", "carol", TEXT_200]]),
    ], seed_messages=[list(m) for m in MANY]),
    case("E9-26", 6, "negative", "Console and InCollege-Output.txt are identical for a 'no messages' session", [
        run("frank", ["9", "2", "2"], count={re.escape(NO_MESSAGES): 2}),
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
    if c["seed_messages"] == "EMPTY":
        (case_dir / "InCollege-Messages.txt").write_text("")
    elif c["seed_messages"]:
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
        if not re.fullmatch(r"\d{16}[+-]\d{4}", line[40:61]):
            problems.append(f"record {n}: timestamp field {line[40:61]!r} is not a date-time")
        if line[61:].rstrip() != text:
            problems.append(f"record {n}: content {line[61:].rstrip()!r}, expected {text!r}")
    return problems


def line_matches(line, item):
    if isinstance(item, dict):
        return re.fullmatch(item["regex"], line) is not None
    return line == item


def check_order(lines, wanted):
    """Lines appear in this order (other lines may come in between)."""
    pos = 0
    for item in wanted:
        while pos < len(lines) and not line_matches(lines[pos], item):
            pos += 1
        if pos == len(lines):
            return [f"expected line not found in order: {item!r}"]
        pos += 1
    return []


def check_block(lines, block):
    """Lines appear consecutively, exactly as given (nothing extra in between)."""
    for start in range(len(lines) - len(block) + 1):
        if all(line_matches(lines[start + i], item) for i, item in enumerate(block)):
            return []
    return [f"expected consecutive block not found (starting {block[0]!r}, {len(block)} lines)"]


def check_count(stdout, pattern, wanted):
    """Number of output lines matching `pattern` (always anchored at line start)."""
    got = len(re.findall("^" + pattern.lstrip("^"), stdout, re.M))
    return [] if got == wanted else [f"/{pattern}/ matched {got} line(s), expected {wanted}"]


def run_case(c, binary, in_dir, out_dir):
    failures = []
    with tempfile.TemporaryDirectory(prefix="epic9-") as tmp:
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
            for block in r.get("block", []):
                problems += check_block(lines, block)
            for pattern, wanted in r.get("count", {}).items():
                problems += check_count(proc.stdout, pattern, wanted)
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

    for old in list(HERE.glob("Epic9-Story*-Test-*")):
        shutil.rmtree(old) if old.is_dir() else old.unlink()

    with tempfile.TemporaryDirectory(prefix="epic9-build-") as build:
        binary = Path(args.binary).resolve() if args.binary else Path(build) / "InCollege"
        if not args.binary:
            build_binary(binary)

        summary, failed = [], 0
        for c in CASES:
            prefix = f"Epic9-Story{c['story']}-Test"
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
            zip_folder(HERE / f"Epic9-Story{story}-Test-{side}")

    summary.append(f"\n{len(CASES) - failed}/{len(CASES)} test cases passed.")
    (HERE / "Epic9-Test-Summary.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()

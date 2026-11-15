# CEN4020-repo

COBOL project environment for Software Engineering (CEN4020).

## Setup: open in a dev container

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. In VS Code, install the **Dev Containers** extension (`ms-vscode-remote.remote-containers`).
3. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux) and run **Dev Containers: Reopen in Container**.

The first build takes about 3–5 minutes: VS Code pulls an Ubuntu 22.04 image, installs GnuCOBOL and build tools, and sets up the COBOL extensions. Reopening later takes seconds.

You'll know it worked when the bottom-left corner of VS Code shows **Dev Container: Software Engineering - COBOL Project Environment**. Verify the compiler with:

```sh
cobc --version
```

To return to your local machine: `Cmd+Shift+P` → **Dev Containers: Reopen Folder Locally**.

## Compile and run

### Option 1: the ▷ Run button

Open a `.cbl` file (e.g. `HelloWorld.cbl`) and click the **▷ Run Code** button in the editor's top-right corner. The Code Runner extension (installed automatically by the dev container) compiles the file with GnuCOBOL and runs the executable in the terminal.

### Option 2: the terminal

In the dev container terminal (`` Ctrl+` ``):

```sh
cobc -x -o HelloWorld HelloWorld.cbl
./HelloWorld
```

Expected output (either way):

```
Hello, World!
```

The `-x` flag produces an executable. Without it, `cobc` builds a shared module (`.so`) that cannot be run directly.

## InCollege (Epic #1: Log In, Part 1)

The InCollege console application handles account registration, login, and post-login
navigation (profiles, skills, and more — see Epic #2 below). All input is read from a file and
every line shown on screen is also written to an output file, so the two are always identical.

### Module layout

The program is split into a main program, copybooks (`.cpy`, shared data layouts included via
`COPY`), and CALL-based subprogram modules (`.cob`, one or more `PROGRAM-ID`s each), so no single
file is a monolith:

| File | Contains |
|---|---|
| `InCollege.cob` | Main program: top-level and post-login menu orchestration only. |
| `InCollege-IO.cob` | `WRITE-LINE` / `READ-LINE` — shared screen+file echo I/O (plus 250-char `WRITE-LONG-LINE` / `READ-LONG-LINE`). |
| `InCollege-Account.cob` | `ACCOUNT-LOAD` / `ACCOUNT-CREATE` / `ACCOUNT-LOGIN`. |
| `InCollege-Profile.cob` | `PROFILE-LOAD` / `PROFILE-SAVE` / `PROFILE-EDIT`. |
| `InCollege-ProfileEntries.cob` | `PROFILE-EXPERIENCE` / `PROFILE-EDUCATION` (repeatable entries). |
| `InCollege-ProfileView.cob` | `PROFILE-VIEW`. |
| `InCollege-UserSearch.cob` | `USER-SEARCH` — exact full-name lookup across saved profiles. |
| `InCollege-Skills.cob` | `SKILL-MENU`. |
| `InCollege-Jobs.cob` | `JOB-MENU` — job/internship menu, loading the job list, and posting a job. |
| `InCollege-ApplyJob.cob` | `BROWSE-JOBS` — list all jobs, show one job's full details, and apply for it. |
| `InCollege-ViewApplications.cob` | `VIEW-APPLICATIONS` — the Job Application Summary Report for the logged-in user. |
| `InCollege-SavedJobs.cob` | `SAVED-JOBS-MENU` — save, list, and unsave jobs. |
| `InCollege-Messages.cob` | `MESSAGE-MENU` / `SEND-MESSAGE` — connection-only private message sending. |
| `InCollege-*.cpy` | Shared record layouts and `EXTERNAL` session/table data, included via `COPY` where more than one program needs the same shape. |

### Compile

```sh
make
```

This compiles all the `.cob` modules above together into the `InCollege` executable (see
`Makefile`). `make run` builds and runs it in one step; `make clean` removes the built binary.

Because the program now spans multiple files, the single-file "▷ Run Code" button / Code Runner
mapping only compiles whichever file is open and will not produce a working build — use `make` /
`make run` instead. (Code Runner is still fine for standalone single-file programs like
`HelloWorld.cbl`.)

### Prepare the input file

Create `InCollege-Input.txt` in the same directory as the executable, with one input value per
line, in the exact order the program will ask for it (menu choices, usernames, passwords). A
sample walkthrough is committed at [`InCollege-Input.txt`](InCollege-Input.txt) — it creates an
account, fails a login once, logs in successfully, visits every post-login menu option, and logs
out.

Menu choices are entered as numbers (`1`/`2` at the top level, `1`-`7` after logging in, `1`-`5`
plus `6` for "Go Back" in the skills menu). Passwords must be 8-12 characters with at least one
uppercase letter, one digit, and one special character.

### Run

```sh
./InCollege
```

(or `make run` to build and run in one step)

This reads `InCollege-Input.txt`, prints every prompt/message to the screen, and writes the same
lines to `InCollege-Output.txt` (created/overwritten in the current directory). A sample expected
output for the committed input file is at [`InCollege-Output.txt`](InCollege-Output.txt).

### Account persistence

Created accounts are saved to `InCollege-Accounts.txt` (also in the current directory) and are
loaded back in on the next run, so registered users can log in across separate executions without
re-registering. Delete this file to reset to zero accounts.

## InCollege (Epic #2: User Profile Creation, Part 1)

Logged-in users can now create and view a personal profile from the post-login menu:

```
1. Create/Edit My Profile
2. View My Profile
3. Search for a job
4. Find someone you know
5. Learn a New Skill
6. Logout
7. View pending requests
```

### Preparing input for profile creation

Choosing **1** walks through the profile prompts, one input line per prompt, in this order:
First Name, Last Name, University/College Attended, Major, Graduation Year, About Me (optional —
send a blank line to skip). Graduation Year must be a 4-digit number greater than 2025 and less
than 2034; any required field left blank aborts the save with an error message and returns to the
post-login menu without writing anything.

After About Me, the program prompts for up to 3 work experience entries and then up to 3
education entries. For each, it shows an "Add ... (Enter 'DONE' to finish)" prompt — supply the
line `DONE` to stop adding entries for that section, or any other line to add one more (that line
itself is just the "continue" signal and is not used as data). Each experience entry then reads
Title, Company/Organization, Dates, and an optional Description (blank to skip); each education
entry reads Degree, University/College, and Years Attended. All four/three fields in an entry
(other than Description) are required once you've chosen to add that entry.

Choosing **2** displays the current user's saved profile, or a message that no profile has been
created yet.

[`InCollege-Input.txt`](InCollege-Input.txt) extends the Epic #1 walkthrough with a full profile
creation and a profile view; the matching expected output is in
[`InCollege-Output.txt`](InCollege-Output.txt).

### Profile persistence

Profiles are saved to `InCollege-Profiles.txt` (created/overwritten in the current directory),
one record per profile keyed by username, and reloaded on the next run so a profile persists
across restarts just like accounts do.

### Finding another user

Choose **4** after logging in and enter the person's full name as `First Last`. The search
uses an exact, case-sensitive comparison against other users' saved profile names and reports
whether that person is part of the InCollege system.


## InCollege (Epic #6: Job/Internship Postings)

Choosing **3** ("Search for a job") after logging in opens the job menu:

```
--- Job Search/Internship Menu ---
1. Post a Job/Internship
2. Browse Jobs/Internships
3. View My Applications
4. Saved Jobs
5. Back to Main Menu
```

**2** and **3** are the Epic #7 features described below, and **5** returns to the post-login
menu.

### Preparing input for posting a job

After **1**, supply one line per prompt, in this order:

| Prompt | Rules |
|---|---|
| Job Title | Required, max 50 characters |
| Description | Required, max 200 characters |
| Employer Name | Required, max 50 characters |
| Location | Required, max 50 characters |
| Salary | Optional, free text up to 20 characters (e.g. `$50,000/year`). `NONE` or a blank line means no salary. |

A blank required field or an over-long value stops the post with a message naming the field
(e.g. `Job Title is required. Job not posted.`) and returns to the job menu. That post reads
nothing after the failing field, so any lines you prepared for the remaining prompts are read as
job menu choices. On success the program prints `Job posted successfully!` followed by a
`----------------------------------` separator.

Example (log in, post a job, go back to the main menu, log out):

```text
1
jstudent
Passw0rd!
3
1
Marketing Intern
Help plan social media campaigns
InCollege Media
Orlando, FL
$25/hour
5
6
```

### Saving jobs

**4** opens the saved-jobs menu (`1. Save a Job`, `2. View My Saved Jobs`, `3. Unsave a Job`,
`4. Back to Job Menu`):

- **Save a Job** lists every posted job as `ID. Title - Employer (Location)`, then reads one line:
  the job ID to save. Unknown or non-numeric IDs print `Invalid job ID.`; saving the same job twice
  prints `You have already saved this job.`
- **View My Saved Jobs** lists the logged-in user's saved jobs in the same format, or
  `You have no saved jobs.`
- **Unsave a Job** lists your saved jobs, then reads the ID to remove. If you have no saved jobs it
  prints the message and does not read an ID.

Example input after logging in: `3`, `4`, `1`, `2` (save job 2), `2` (view), `4`, `5`, `6`.

### Job persistence and output

- `InCollege-JobList.txt` holds one fixed-width line per job: a 3-digit sequential ID, the
  poster's username (20 chars), then Title (50), Description (200), Employer (50), Location (50),
  and Salary (20). Jobs are read back in on every visit to the job menu, so they survive restarts.
  The file holds up to 20 jobs. Delete it to start with no jobs.
- `InCollege-SavedJobs.txt` holds one line per saved job: username (20 chars) + job ID (3 digits).
  Each user only sees their own saved jobs, and the list is still there at the next login.
- As with every feature, prompts, echoed input, and results appear on screen and identically in
  `InCollege-Output.txt`.

## InCollege (Epic #8: Private Messaging, Part 1)

Choose **9** ("Messages") after logging in. The messaging menu provides **1. Send a New
Message**, **2. View My Messages**, and **3. Back to Main Menu**. Viewing messages is reserved
for the next epic and currently displays an under-construction message.

To send, provide the recipient's username followed by one line of free-form message content (up
to 200 characters; an empty line is rejected with `Message cannot be empty.`). Surrounding spaces in
the recipient's username are ignored. The recipient must be connected to the logged-in user through an accepted
connection request; non-existent, pending, rejected, and otherwise unconnected users all produce
`You can only message users you are connected with.` without reading a message-content line.

Sent messages are appended to `InCollege-Messages.txt`. Each fixed-width record contains the
sender username, recipient username, a 21-character COBOL `CURRENT-DATE` timestamp, and the
200-character content. Inputs continue to come from `InCollege-Input.txt`, while prompts, echoed
input, and results are identically displayed and written to `InCollege-Output.txt`.

## File-based connection request testing

All connection-request inputs use the same `InCollege-Input.txt` stream as login and the
main menus. Put one response per line: choose **4** to search, enter the recipient's exact
full name, then choose **1** to send a connection request or **2** to return to the main
menu. Invalid choices (including blank lines) consume one line and prompt again. End of
file exits cleanly, including at the search and connection-choice prompts; it never sends
a request without reading a valid **1** choice.

For example, with an existing `alice` account whose password is `Test123!` and another
account with a saved profile named `Bob Tester`, use:

```text
1
alice
Test123!
4
Bob Tester
1
6
```

Run `make run`. Prompts, input echoes, and results appear in `InCollege-Output.txt` and
on screen. A successful request is saved in `InCollege-Requests.txt` with `PENDING`
status. On a later run, the recipient can log in and choose **7** to see it. Sending the
same request again reports a duplicate. Account, profile, and request files persist
between runs, so use a fresh working directory for independent scenarios.

### Automated regression tests

With GnuCOBOL, Make, and Python 3 installed, run:

```sh
make test
```

The tests build a fresh executable and create accounts, profiles, and input files in
temporary directories, leaving the repository's sample data and executable untouched.
Standard input is closed and each run has a timeout, so keyboard input or an EOF loop
fails the test. Coverage includes sending and reloading pending requests, going back,
invalid/blank choices, duplicate and incoming requests, repeated searches, and EOF at
each connection prompt. Every run also checks that screen output matches the output file.

## InCollege (Epic #7: Browse, Apply, and Application Report)

After logging in, choose **3** ("Search for a job") to open the job menu (see Epic #6 above),
then:

- **2. Browse Jobs/Internships** lists every posted job, one per line, as
  `N. Title at Employer (Location)`, where `N` is the job number. It then reads one line: a job
  number to view, or `0` to go back to the job menu. An unknown or non-numeric number prints
  `Invalid job number.` and shows the list again. With no jobs posted it prints
  `There are no jobs available.` and returns to the job menu without reading a line.
- **Job details** show Title, Description, Employer, Location, and Salary (left out when the job
  has none), then `1. Apply for this Job` / `2. Back to Job List`. Both choices return to the job
  list. Applying prints `Your application for <Title> at <Employer> has been submitted.`;
  applying again for the same job prints `You have already applied for this job.`
- **3. View My Applications** prints the Job Application Summary Report for the logged-in user,
  then returns to the job menu:

```
--- Your Job Applications ---
Application Summary for jstudent
------------------------------
Job ID: 1
Job Title: Software Engineering Intern
Employer: Google
Location: Remote
---
Job ID: 2
Job Title: Data Analyst Intern
Employer: Amazon
Location: Tampa, FL
------------------------------
Total Applications: 2
------------------------------
```

With no applications, the report prints `You have not applied for any jobs yet.` in place of the
entries and `Total Applications: 0`.

### Preparing input for browsing, applying, and the report

Put one line per prompt. For example, after the three login lines (`1`, username, password):

| Line | Meaning |
|---|---|
| `3` | Post-login menu: Search for a job |
| `2` | Job menu: Browse Jobs/Internships |
| `1` | Job list: view job number 1 |
| `1` | Job details: Apply for this Job (back at the job list afterwards) |
| `0` | Job list: back to the job menu |
| `3` | Job menu: View My Applications (the report) |
| `5` | Job menu: Back to Main Menu |
| `6` | Post-login menu: Logout |

End of file at any prompt ends the program cleanly. It never records an application unless
the program has read a `1` at the job details prompt.

### Application persistence and output

- `InCollege-Applications.txt` holds one line per application: username (20 chars) + job ID
  (3 digits). New applications are appended, so they persist across restarts. The report lists
  only the logged-in user's applications, skipping any job that is no longer in
  `InCollege-JobList.txt`. Delete the file to start with no applications.
- The job list, job details, confirmations, and the report are written to the screen and,
  identically, to `InCollege-Output.txt`.

The committed [`InCollege-Input.txt`](InCollege-Input.txt) logs in as `jstudent`, views the
(empty) report, applies for jobs 1 and 2, opens job 3 without applying, and views the report
again. The matching output is in [`InCollege-Output.txt`](InCollege-Output.txt), produced by
running it with the committed data files and no `InCollege-Applications.txt`. A second run shows
`You have already applied for this job.` instead, so delete `InCollege-Applications.txt`
to reproduce the committed output.

`make test` covers the job menu, browsing empty, single, and multi-job lists, full details with
and without a salary, applying and duplicate protection across restarts, invalid job numbers
and choices, EOF at each prompt, and the report with zero, one, and several applications
(showing only the logged-in user's).

"""
===============================================================================
Memact SSoC26 Automation Engine
-------------------------------------------------------------------------------

Single automation engine replacing:

- assign_eager_contributors.py
- label_and_align_prs.py
- warn_stale_assignments.py
- check_unassign_comments.py

Author:
Memact

===============================================================================
"""

import json
import subprocess
import re
import os
import sys
import tempfile
import shutil
import datetime
import time
from collections import defaultdict

# =============================================================================
# CONFIGURATION
# =============================================================================

ORG_NAME = "Memact"

EXCLUDED_REPOSITORIES = {
    "Website",
    "oldWebsite"
}

CORE_REPOSITORIES = [
    "Context",
    "Access",
    "Memory",
    "Contracts",
    "SDK",
    "Notebook",
    "Fitent",
    ".github"
]

BOT_USERS = {
    "keepsloading",
    "github-actions",
    "memact"
}

LABEL_COLORS = {
    "SSoC26": "ededed",
    "Easy": "008672",
    "Medium": "d1b100",
    "Hard": "e11d21",
    "Quality: Needs Polish": "d93f0b"
}

DIFFICULTIES = (
    "Easy",
    "Medium",
    "Hard"
)

LABEL_NORMALIZATION = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "ssoc26": "SSoC26"
}

NEGATIVE_KEYWORDS = [

    "unassign",
    "un-assign",
    "remove me",
    "wrong issue",
    "withdraw",
    "not interested",
    "please un",
    "don't assign",
    "do not assign",
    "stepping away",
    "stepping down",
    "no longer",
    "not familiar",
    "picked the wrong"
]

ASSIGN_PATTERNS = [

    r"^/assign",
    r"^assign",
    r"assign me",
    r"assign to me",
    r"claim",
    r"take this",
    r"take it",
    r"contribute",
    r"i.?d like to work",
    r"want to work",
    r"can i work",
    r"happy to work",
    r"let me work",
]

QUALITY_PATTERNS = {

    "debug": re.compile(
        r"(console\.log|console\.error|debugger)",
        re.IGNORECASE
    ),

    "todo": re.compile(
        r"(TODO|FIXME|XXX)",
        re.IGNORECASE
    ),

    "secret": re.compile(
        r"(api_key|secret|password|passwd|bearer|private_key)",
        re.IGNORECASE
    )
}

STALE_AFTER_DAYS = 3

DEFAULT_ASSIGNMENT_LIMIT = 10

GREYLIST_LIMIT = 1

FORMER_GREYLIST = {

    "codesparks45",
    "codesparks",
    "prasiddhi-105",
    "prasiddhi",
    "prassidhi"
}

EXEMPT_FROM_STALE = {

    "yachna-jpg"
}

# =============================================================================
# GLOBAL CACHE
# =============================================================================

CACHE = {

    "repositories": [],

    "issues": {},

    "prs": {},

    "merged_prs": {},

    "comments": {},

    "assignment_count": defaultdict(int),

    "latest_intent": defaultdict(dict),

    "current_user": "",

    "stats": defaultdict(int)
}

# =============================================================================
# LOGGING
# =============================================================================

def info(msg):
    print(f"[INFO] {msg}")

def success(msg):
    print(f"[SUCCESS] {msg}")

def warning(msg):
    print(f"[WARNING] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")

# =============================================================================
# GITHUB WRAPPER
# =============================================================================

def gh(command):

    result = subprocess.run(

        command,

        shell=True,

        capture_output=True,

        text=True,

        encoding="utf-8"
    )

    return result

def gh_json(command):

    result = gh(command)

    if result.returncode != 0:

        return None

    if not result.stdout.strip():

        return None

    return json.loads(result.stdout)

def gh_success(command):

    return gh(command).returncode == 0

# =============================================================================
# UTILITIES
# =============================================================================

def normalize_label(label):

    return LABEL_NORMALIZATION.get(

        label.lower(),

        label
    )

def contains_negative_intent(text):

    text = text.lower()

    return any(

        keyword in text

        for keyword in NEGATIVE_KEYWORDS

    )

def contains_assignment_request(text):

    text = text.lower()

    return any(

        re.search(pattern, text)

        for pattern in ASSIGN_PATTERNS

    )

def current_utc():

    return datetime.datetime.now(

        datetime.timezone.utc
    )

def temp_markdown(content):

    handle = tempfile.NamedTemporaryFile(

        delete=False,

        suffix=".md",

        mode="w",

        encoding="utf-8"
    )

    handle.write(content)

    handle.close()

    return handle.name

# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():

    info("Initializing automation engine...")

    if sys.platform.startswith("win"):

        try:

            sys.stdout.reconfigure(

                encoding="utf-8"
            )

            sys.stderr.reconfigure(

                encoding="utf-8"
            )

        except Exception:

            pass

    result = gh(

        "gh api user --jq .login"
    )

    if result.returncode == 0:

        CACHE["current_user"] = result.stdout.strip().lower()

        BOT_USERS.add(

            CACHE["current_user"]
        )

    success("Initialization complete.")

    # =============================================================================
# REPOSITORY DISCOVERY
# =============================================================================

def fetch_repositories():

    info("Discovering repositories...")

    repos = gh_json(
        f'gh repo list {ORG_NAME} --limit 100 --json name'
    )

    if not repos:
        error("Could not fetch repositories.")
        return

    CACHE["repositories"] = sorted([
        r["name"]
        for r in repos
        if r["name"] not in EXCLUDED_REPOSITORIES
    ])

    success(
        f"Loaded {len(CACHE['repositories'])} repositories."
    )


# =============================================================================
# FETCH ALL ISSUES
# =============================================================================

def fetch_all_issues():

    info("Fetching issues...")

    CACHE["issues"].clear()

    for repo in CACHE["repositories"]:

        data = gh_json(

            f'gh issue list '
            f'-R {ORG_NAME}/{repo} '
            f'--state open '
            f'--limit 100 '
            f'--json '
            f'number,title,body,url,'
            f'author,labels,assignees,'
            f'comments,createdAt'

        )

        if data is None:
            warning(f"{repo}: issue fetch failed.")
            continue

        CACHE["issues"][repo] = data

        CACHE["stats"]["issues"] += len(data)

    success(
        f"Fetched {CACHE['stats']['issues']} open issues."
    )


# =============================================================================
# FETCH ALL PRS
# =============================================================================

def fetch_all_pull_requests():

    info("Fetching pull requests...")

    CACHE["prs"].clear()
    CACHE["merged_prs"].clear()

    for repo in CACHE["repositories"]:

        prs = gh_json(

            f'gh pr list '
            f'-R {ORG_NAME}/{repo} '
            f'--state all '
            f'--limit 150 '
            f'--json '
            f'number,title,body,state,'
            f'author,labels'

        )

        if prs is None:
            warning(f"{repo}: PR fetch failed.")
            continue

        CACHE["prs"][repo] = prs

        CACHE["merged_prs"][repo] = [

            pr

            for pr in prs

            if str(pr.get("state", "")).lower() == "merged"

        ]

        CACHE["stats"]["prs"] += len(prs)

    success(
        f"Fetched {CACHE['stats']['prs']} pull requests."
    )


# =============================================================================
# BUILD ACTIVE ASSIGNMENT INDEX
# =============================================================================

def build_assignment_index():

    info("Counting active assignments...")

    CACHE["assignment_count"].clear()

    for repo, issues in CACHE["issues"].items():

        for issue in issues:

            for assignee in issue.get("assignees", []):

                login = assignee["login"].lower()

                CACHE["assignment_count"][login] += 1

    success(
        f"Indexed {len(CACHE['assignment_count'])} contributors."
    )


# =============================================================================
# BUILD LATEST INTENT STATE
# =============================================================================

#
# This replaces the old assignment logic.
#
# Every contributor on every issue has ONE latest intent.
#
# ASSIGN
# UNASSIGN
# NONE
#
# Only the newest intent matters.
#

def build_intent_index():

    info("Building contributor intent graph...")

    CACHE["latest_intent"].clear()

    for repo, issues in CACHE["issues"].items():

        for issue in issues:

            issue_id = issue["number"]

            creator = issue.get("author", {})

            creator_login = ""

            if creator:
                creator_login = creator.get("login", "").lower()

            #
            # Creator implicitly wants assignment.
            #

            if creator_login and creator_login not in BOT_USERS:

                CACHE["latest_intent"][repo].setdefault(
                    issue_id,
                    {}
                )

                CACHE["latest_intent"][repo][issue_id][creator_login] = {

                    "intent": "ASSIGN",
                    "timestamp": issue.get("createdAt", "")
                }

            comments = sorted(

                issue.get("comments", []),

                key=lambda x: x.get("createdAt", "")

            )

            for comment in comments:

                author = comment.get("author", {}).get("login", "")

                if not author:
                    continue

                author = author.lower()

                if author in BOT_USERS:
                    continue

                body = comment.get("body", "")

                CACHE["latest_intent"][repo].setdefault(

                    issue_id,

                    {}

                )

                #
                # Withdrawal overrides previous assignment request.
                #

                if contains_negative_intent(body):

                    CACHE["latest_intent"][repo][issue_id][author] = {

                        "intent": "UNASSIGN",

                        "timestamp": comment["createdAt"]

                    }

                    continue

                #
                # Fresh assignment request.
                #

                if contains_assignment_request(body):

                    CACHE["latest_intent"][repo][issue_id][author] = {

                        "intent": "ASSIGN",

                        "timestamp": comment["createdAt"]

                    }

    success("Intent graph built.")


# =============================================================================
# SUMMARY
# =============================================================================

def print_summary():

    print()

    print("=" * 70)

    info("Automation cache summary")

    print("=" * 70)

    print(f"Repositories : {len(CACHE['repositories'])}")
    print(f"Issues       : {CACHE['stats']['issues']}")
    print(f"PRs          : {CACHE['stats']['prs']}")
    print(f"Contributors : {len(CACHE['assignment_count'])}")

    print("=" * 70)

    print()


# =============================================================================
# MAIN
# =============================================================================

def main():

    start = time.time()

    initialize()

    fetch_repositories()

    fetch_all_issues()

    fetch_all_pull_requests()

    build_assignment_index()

    build_intent_index()

    #
    # Engines begin here
    #

    # label_issue_engine()

    # difficulty_engine()

    # assignment_engine()

    # unassignment_engine()

    # stale_assignment_engine()

    # pr_label_engine()

    # dummy_pr_engine()

    # quality_engine()

    # autoclose_engine()

    print_summary()

    success(
        f"Completed in {round(time.time()-start,2)} seconds."
    )


if __name__ == "__main__":

    main()
# =============================================================================
# ASSIGNMENT ENGINE
# =============================================================================

def assignment_limit(username):

    username = username.lower()

    if username in FORMER_GREYLIST:
        return GREYLIST_LIMIT

    return DEFAULT_ASSIGNMENT_LIMIT


def already_assigned(issue, username):

    username = username.lower()

    for assignee in issue.get("assignees", []):

        if assignee["login"].lower() == username:
            return True

    return False


def comment_already_exists(issue, username):

    bot_users = BOT_USERS.copy()

    for c in issue.get("comments", []):

        author = c.get("author", {}).get("login", "").lower()

        if author not in bot_users:
            continue

        body = c.get("body", "").lower()

        if (
            username.lower() in body
            and "active assignment" in body
            and "limit" in body
        ):
            return True

    return False


def assign_user(repo, issue_number, username):

    result = gh(

        f'gh api repos/{ORG_NAME}/{repo}/issues/{issue_number} '
        f'-X PATCH '
        f'-F "assignees[]={username}"'

    )

    return result.returncode == 0


def assignment_engine():

    info("Running assignment engine...")

    assigned = 0

    skipped = 0

    for repo in CACHE["repositories"]:

        repo_state = CACHE["latest_intent"].get(repo, {})

        repo_issues = CACHE["issues"].get(repo, [])

        issue_lookup = {

            i["number"]: i

            for i in repo_issues

        }

        #
        # Iterate issue by issue
        #

        for issue_number, users in repo_state.items():

            issue = issue_lookup.get(issue_number)

            if issue is None:
                continue

            #
            # Someone already owns the issue.
            #

            if issue.get("assignees"):

                continue

            #
            # Build candidate list
            #

            candidates = []

            for username, state in users.items():

                if state["intent"] != "ASSIGN":
                    continue

                candidates.append({

                    "user": username,

                    "timestamp": state["timestamp"]

                })

            if not candidates:
                continue

            #
            # First request wins
            #

            candidates.sort(

                key=lambda x: x["timestamp"]

            )

            winner = candidates[0]["user"]

            #
            # Assignment limit
            #

            active = CACHE["assignment_count"].get(

                winner,

                0

            )

            limit = assignment_limit(winner)

            if active >= limit:

                skipped += 1

                if not comment_already_exists(

                    issue,

                    winner

                ):

                    body = (

                        f"Hi @{winner} 👋\n\n"

                        f"You currently have **{active} active assignment(s)** "

                        f"(limit: **{limit}**).\n\n"

                        "Please finish one of your existing issues "

                        "before requesting another."

                    )

                    file = temp_markdown(body)

                    gh(

                        f'gh issue comment {issue_number} '

                        f'-R {ORG_NAME}/{repo} '

                        f'-F "{file}"'

                    )

                    os.remove(file)

                continue

            #
            # Assign
            #

            ok = assign_user(

                repo,

                issue_number,

                winner

            )

            if not ok:

                warning(

                    f"Assignment failed "

                    f"{repo}#{issue_number}"

                )

                continue

            CACHE["assignment_count"][winner] += 1

            assigned += 1

            #
            # Success comment
            #

            body = (

                f"Hey @{winner} 👋\n\n"

                "You have been assigned this issue "

                "for **SSoC26**.\n\n"

                "Good luck! 🚀"

            )

            #
            # Former greylist notice
            #

            if winner in FORMER_GREYLIST:

                body += (

                    "\n\n"

                    "⚠️ Please pay extra attention "

                    "to code quality, testing, "

                    "and project conventions."

                )

            file = temp_markdown(body)

            gh(

                f'gh issue comment {issue_number} '

                f'-R {ORG_NAME}/{repo} '

                f'-F "{file}"'

            )

            os.remove(file)

            success(

                f"Assigned "

                f"{repo}#{issue_number}"

                f" -> @{winner}"

            )

    CACHE["stats"]["assigned"] = assigned

    CACHE["stats"]["assignment_skipped"] = skipped

    success(

        f"Assignment engine complete."

        f" Assigned={assigned}"

        f" Skipped={skipped}"

    )
  # =============================================================================
# LABEL ENGINE
# =============================================================================

def detect_difficulty(title, body):

    text = f"{title}\n{body}".lower()

    if re.search(r"\beasy\b", text):
        return "Easy"

    if re.search(r"\bmedium\b", text):
        return "Medium"

    if re.search(r"\bhard\b", text):
        return "Hard"

    return None


def ensure_label(repo, label):

    color = LABEL_COLORS.get(label, "ededed")

    gh(
        f'gh label create "{label}" '
        f'-R {ORG_NAME}/{repo} '
        f'--color "{color}"'
    )


def add_labels(repo, issue_number, labels):

    if not labels:
        return

    label_string = ",".join(labels)

    gh(
        f'gh issue edit {issue_number} '
        f'-R {ORG_NAME}/{repo} '
        f'--add-label "{label_string}"'
    )


def remove_label(repo, issue_number, label):

    gh(
        f'gh issue edit {issue_number} '
        f'-R {ORG_NAME}/{repo} '
        f'--remove-label "{label}"'
    )


def normalize_labels(repo, issue_number, current_labels):

    normalized = []

    for label in current_labels:

        fixed = normalize_label(label)

        if fixed != label:

            remove_label(
                repo,
                issue_number,
                label
            )

            ensure_label(
                repo,
                fixed
            )

            normalized.append(fixed)

            success(
                f"{repo}#{issue_number}: "
                f"{label} -> {fixed}"
            )

    if normalized:

        add_labels(
            repo,
            issue_number,
            normalized
        )


def label_issue_engine():

    info("Running issue label engine...")

    labeled = 0

    for repo in CACHE["repositories"]:

        issues = CACHE["issues"].get(repo, [])

        for issue in issues:

            issue_number = issue["number"]

            title = issue["title"]

            body = issue.get("body", "")

            current_labels = [

                l["name"]

                for l in issue.get("labels", [])

            ]

            #
            # Fix label casing first
            #

            normalize_labels(

                repo,

                issue_number,

                current_labels

            )

            #
            # Reload normalized labels
            #

            current_labels = [

                normalize_label(l)

                for l in current_labels

            ]

            labels_to_add = []

            #
            # Always ensure SSoC26 exists
            #

            if "SSoC26" not in current_labels:

                ensure_label(

                    repo,

                    "SSoC26"

                )

                labels_to_add.append(

                    "SSoC26"

                )

            #
            # Difficulty detection
            #

            difficulty = detect_difficulty(

                title,

                body

            )

            if (

                difficulty

                and

                difficulty not in current_labels

            ):

                ensure_label(

                    repo,

                    difficulty

                )

                labels_to_add.append(

                    difficulty

                )

            #
            # Apply labels
            #

            if labels_to_add:

                add_labels(

                    repo,

                    issue_number,

                    labels_to_add

                )

                labeled += 1

                success(

                    f"{repo}#{issue_number} "

                    f"+ {labels_to_add}"

                )

    CACHE["stats"]["issue_labels"] = labeled

    success(

        f"Issue labeling complete "

        f"({labeled} issues updated)."

    )
  # =============================================================================
# PR LABEL ENGINE
# =============================================================================

ISSUE_REFERENCE_REGEX = re.compile(
    r"(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)?\s*#(\d+)",
    re.IGNORECASE,
)


def get_issue_labels(repo, issue_number):

    #
    # Prefer cache first.
    #

    issues = CACHE["issues"].get(repo, [])

    for issue in issues:

        if issue["number"] == issue_number:

            return [

                normalize_label(label["name"])

                for label in issue.get("labels", [])

            ]

    #
    # Closed issue.
    #

    result = gh_json(

        f'gh issue view {issue_number} '
        f'-R {ORG_NAME}/{repo} '
        f'--json labels'

    )

    if not result:

        return []

    return [

        normalize_label(label["name"])

        for label in result["labels"]

    ]


def extract_issue_numbers(pr):

    combined = (

        pr.get("title", "")

        + "\n"

        + (pr.get("body") or "")

    )

    return sorted({

        int(match)

        for match

        in ISSUE_REFERENCE_REGEX.findall(

            combined

        )

    })


def label_pull_request(

    repo,

    pr_number,

    labels

):

    if not labels:

        return

    for label in labels:

        ensure_label(

            repo,

            label

        )

    gh(

        f'gh pr edit {pr_number} '

        f'-R {ORG_NAME}/{repo} '

        f'--add-label "{",".join(labels)}"'

    )


def pr_label_engine():

    info("Running PR label engine...")

    updated = 0

    for repo in CACHE["repositories"]:

        prs = CACHE["prs"].get(

            repo,

            []

        )

        for pr in prs:

            #
            # Ignore abandoned PRs.
            #

            if (

                pr.get("state", "")

                .lower()

                == "closed"

            ):

                continue

            pr_number = pr["number"]

            current_labels = {

                normalize_label(

                    label["name"]

                )

                for label

                in pr.get(

                    "labels",

                    []

                )

            }

            issue_refs = extract_issue_numbers(

                pr

            )

            labels_to_apply = set()

            #
            # Copy issue labels.
            #

            for issue_number in issue_refs:

                issue_labels = get_issue_labels(

                    repo,

                    issue_number

                )

                for label in issue_labels:

                    if (

                        label == "SSoC26"

                        or

                        label in DIFFICULTIES

                    ):

                        labels_to_apply.add(

                            label

                        )

            #
            # Title fallback.
            #

            if (

                "ssoc"

                in pr["title"].lower()

            ):

                labels_to_apply.add(

                    "SSoC26"

                )

            #
            # Remove labels already present.
            #

            labels_to_apply = [

                label

                for label

                in labels_to_apply

                if label not in current_labels

            ]

            if not labels_to_apply:

                continue

            label_pull_request(

                repo,

                pr_number,

                labels_to_apply

            )

            updated += 1

            success(

                f"{repo} PR #{pr_number}"

                f" + {labels_to_apply}"

            )

            #
            # Nice engagement comment.
            #

            body = (

                "**SSoC26 Automation**\n\n"

                "This pull request has been "

                "automatically linked to the "

                "labels of its corresponding "

                "issue."

            )

            file = temp_markdown(

                body

            )

            gh(

                f'gh pr comment {pr_number} '

                f'-R {ORG_NAME}/{repo} '

                f'-F "{file}"'

            )

            os.remove(file)

    CACHE["stats"]["pr_labels"] = updated

    success(

        f"Updated "

        f"{updated} PRs."

    )
  # =============================================================================
# DUMMY PR ENGINE
# =============================================================================

def find_dummy_pr(author, repo, pr_number, linked_issues):

    context_prs = CACHE["prs"].get("Context", [])

    repo = repo.lower()

    for pr in context_prs:

        pr_author = pr.get("author", {}).get("login", "").lower()

        if pr_author != author.lower():
            continue

        combined = (

            pr.get("title", "")

            + "\n"

            + (pr.get("body") or "")

        ).lower()

        #
        # Direct reference
        #

        if f"{repo}#{pr_number}" in combined:
            return pr

        #
        # Github URL
        #

        if f"github.com/memact/{repo}/pull/{pr_number}" in combined:
            return pr

        #
        # Issue references
        #

        for issue in linked_issues:

            if f"{repo}#{issue}" in combined:
                return pr

            if f"issue {issue}" in combined:
                return pr

            if f"#{issue}" in combined and repo in combined:
                return pr

    return None


def comment_exists(pr_number, repo, prefix):

    result = gh_json(

        f'gh pr view {pr_number} '
        f'-R {ORG_NAME}/{repo} '
        f'--json comments'

    )

    if not result:

        return False

    for comment in result.get("comments", []):

        if prefix in comment.get("body", ""):
            return True

    return False


def dummy_pr_engine():

    info("Running dummy PR engine...")

    found = 0

    warned = 0

    for repo in CACHE["repositories"]:

        #
        # Context never needs dummy PRs.
        #

        if repo in ["Context", ".github"]:

            continue

        prs = CACHE["prs"].get(

            repo,

            []

        )

        for pr in prs:

            state = pr.get(

                "state",

                ""

            ).lower()

            if state == "closed":

                continue

            pr_number = pr["number"]

            author = pr["author"]["login"]

            linked_issues = extract_issue_numbers(

                pr

            )

            dummy = find_dummy_pr(

                author,

                repo,

                pr_number,

                linked_issues

            )

            #
            # SUCCESS
            #

            if dummy:

                dummy_number = dummy["number"]

                found += 1

                #
                # Copy labels.
                #

                labels = [

                    normalize_label(

                        label["name"]

                    )

                    for label

                    in pr.get(

                        "labels",

                        []

                    )

                    if normalize_label(

                        label["name"]

                    )

                    in DIFFICULTIES

                    or

                    normalize_label(

                        label["name"]

                    )

                    == "SSoC26"

                ]

                if labels:

                    label_pull_request(

                        "Context",

                        dummy_number,

                        labels

                    )

                prefix = "**SSoC26 Success:**"

                if not comment_exists(

                    pr_number,

                    repo,

                    prefix

                ):

                    body = (

                        "**SSoC26 Success:**\n\n"

                        "Dummy PR detected in "

                        f"Context (#{dummy_number}).\n\n"

                        "Contribution tracking "

                        "has been verified."

                    )

                    file = temp_markdown(

                        body

                    )

                    gh(

                        f'gh pr comment '

                        f'{pr_number} '

                        f'-R {ORG_NAME}/{repo} '

                        f'-F "{file}"'

                    )

                    os.remove(file)

                continue

            #
            # WARNING
            #

            warned += 1

            prefix = "**SSoC26 Warning:**"

            if comment_exists(

                pr_number,

                repo,

                prefix

            ):

                continue

            body = (

                "**SSoC26 Warning:**\n\n"

                "No corresponding dummy PR "

                "was found in "

                "**Memact/Context**.\n\n"

                "Please create one referencing "

                f"`Memact/{repo}#{pr_number}` "

                "so your contribution can "

                "be tracked."

            )

            file = temp_markdown(

                body

            )

            gh(

                f'gh pr comment '

                f'{pr_number} '

                f'-R {ORG_NAME}/{repo} '

                f'-F "{file}"'

            )

            os.remove(file)

    CACHE["stats"]["dummy_found"] = found

    CACHE["stats"]["dummy_warned"] = warned

    success(

        f"Dummy PR engine complete "

        f"(found={found}, warned={warned})"

    )
  # =============================================================================
# CODE QUALITY ENGINE
# =============================================================================

QUALITY_RULES = [

    {
        "name": "Debug Statements",
        "label": "Quality: Needs Polish",
        "pattern": re.compile(
            r"(console\.log|console\.error|debugger)",
            re.IGNORECASE
        ),
        "message": "Remove debugging statements."
    },

    {
        "name": "TODO Marker",
        "label": "Quality: Needs Polish",
        "pattern": re.compile(
            r"\b(TODO|FIXME|XXX)\b",
            re.IGNORECASE
        ),
        "message": "Resolve TODO/FIXME markers."
    },

    {
        "name": "Possible Secret",
        "label": "Quality: Needs Polish",
        "pattern": re.compile(
            r"(api[_-]?key|secret|password|passwd|bearer|private[_-]?key)",
            re.IGNORECASE
        ),
        "message": "Possible hardcoded credential detected."
    }

]


def fetch_pr_diff(repo, number):

    result = gh(

        f'gh pr diff {number} '

        f'-R {ORG_NAME}/{repo}'

    )

    if result.returncode != 0:

        return ""

    return result.stdout


def analyze_diff(diff):

    findings = []

    for line in diff.splitlines():

        #
        # Only inspect added lines.
        #

        if not line.startswith("+"):

            continue

        #
        # Ignore file headers.
        #

        if line.startswith("+++"):

            continue

        code = line[1:]

        for rule in QUALITY_RULES:

            if rule["pattern"].search(code):

                findings.append({

                    "rule": rule,

                    "line": code.strip()

                })

    return findings


def quality_comment(findings):

    lines = [

        "**SSoC26 Code Quality Warning**",

        "",

        "The automation detected some issues "

        "that should be fixed before review.",

        ""

    ]

    for finding in findings:

        lines.append(

            f"- **{finding['rule']['name']}**"

        )

        lines.append(

            f"  `{finding['line']}`"

        )

        lines.append(

            f"  {finding['rule']['message']}"

        )

        lines.append("")

    lines.append(

        "After fixing these issues the "

        "warning label will be removed "

        "automatically."

    )

    return "\n".join(lines)


def code_quality_engine():

    info("Running code quality engine...")

    flagged = 0

    cleaned = 0

    for repo in CACHE["repositories"]:

        prs = CACHE["prs"].get(

            repo,

            []

        )

        for pr in prs:

            if (

                pr.get("state", "")

                .lower()

                != "open"

            ):

                continue

            pr_number = pr["number"]

            diff = fetch_pr_diff(

                repo,

                pr_number

            )

            findings = analyze_diff(

                diff

            )

            labels = {

                normalize_label(

                    l["name"]

                )

                for l

                in pr.get(

                    "labels",

                    []

                )

            }

            #
            # Everything looks good.
            #

            if not findings:

                if (

                    "Quality: Needs Polish"

                    in labels

                ):

                    gh(

                        f'gh pr edit '

                        f'{pr_number} '

                        f'-R {ORG_NAME}/{repo} '

                        f'--remove-label '

                        f'"Quality: Needs Polish"'

                    )

                    cleaned += 1

                continue

            #
            # Needs review.
            #

            ensure_label(

                repo,

                "Quality: Needs Polish"

            )

            gh(

                f'gh pr edit '

                f'{pr_number} '

                f'-R {ORG_NAME}/{repo} '

                f'--add-label '

                f'"Quality: Needs Polish"'

            )

            if not comment_exists(

                pr_number,

                repo,

                "**SSoC26 Code Quality Warning**"

            ):

                body = quality_comment(

                    findings

                )

                file = temp_markdown(

                    body

                )

                gh(

                    f'gh pr comment '

                    f'{pr_number} '

                    f'-R {ORG_NAME}/{repo} '

                    f'-F "{file}"'

                )

                os.remove(file)

            flagged += 1

            success(

                f"{repo} PR #{pr_number} "

                f"flagged "

                f"({len(findings)} findings)"

            )

    CACHE["stats"]["quality_flagged"] = flagged

    CACHE["stats"]["quality_cleaned"] = cleaned

    success(

        f"Quality engine complete "

        f"(flagged={flagged}, cleaned={cleaned})"

    )
  # =============================================================================
# UNASSIGNMENT ENGINE
# =============================================================================

def remove_assignee(repo, issue_number, username):

    result = gh(

        f'gh issue edit {issue_number} '
        f'-R {ORG_NAME}/{repo} '
        f'--remove-assignee {username}'

    )

    return result.returncode == 0


def latest_assignee_comment(issue, username):

    comments = [

        c

        for c in issue.get("comments", [])

        if c.get("author", {}).get("login", "").lower()

        == username.lower()

    ]

    if not comments:

        return None

    comments.sort(

        key=lambda x: x.get("createdAt", ""),

        reverse=True

    )

    return comments[0]


def unassignment_engine():

    info("Running unassignment engine...")

    removed = 0

    for repo in CACHE["repositories"]:

        issues = CACHE["issues"].get(

            repo,

            []

        )

        for issue in issues:

            issue_number = issue["number"]

            assignees = list(

                issue.get(

                    "assignees",

                    []

                )

            )

            if not assignees:

                continue

            for assignee in assignees:

                username = assignee["login"].lower()

                latest = latest_assignee_comment(

                    issue,

                    username

                )

                if latest is None:

                    continue

                body = latest.get(

                    "body",

                    ""

                )

                #
                # Latest intent is still assignment.
                #

                if not contains_negative_intent(body):

                    continue

                #
                # Remove assignment.
                #

                ok = remove_assignee(

                    repo,

                    issue_number,

                    username

                )

                if not ok:

                    warning(

                        f"Could not unassign "

                        f"{username}"

                    )

                    continue

                #
                # Update cache immediately.
                #

                CACHE["assignment_count"][

                    username

                ] = max(

                    0,

                    CACHE["assignment_count"][

                        username

                    ] - 1

                )

                CACHE["latest_intent"][

                    repo

                ][

                    issue_number

                ][

                    username

                ] = {

                    "intent": "UNASSIGN",

                    "timestamp": latest["createdAt"]

                }

                body = (

                    f"Okay @{username} 👋\n\n"

                    "You have been "

                    "unassigned from this "

                    "issue.\n\n"

                    "If you ever want to "

                    "work on it again, simply "

                    "comment:\n\n"

                    "`/assign`\n\n"

                    "and the automation will "

                    "consider you again."

                )

                file = temp_markdown(

                    body

                )

                gh(

                    f'gh issue comment '

                    f'{issue_number} '

                    f'-R {ORG_NAME}/{repo} '

                    f'-F "{file}"'

                )

                os.remove(file)

                removed += 1

                success(

                    f"Unassigned "

                    f"@{username} "

                    f"from "

                    f"{repo}#{issue_number}"

                )

    CACHE["stats"]["unassigned"] = removed

    success(

        f"Unassignment engine complete "

        f"({removed} removed)."

    )
  # =============================================================================
# STALE ASSIGNMENT ENGINE
# =============================================================================

def assignment_age(repo, issue_number, username):

    result = gh_json(

        f'gh api repos/{ORG_NAME}/{repo}/issues/{issue_number}/timeline'

    )

    if not result:

        return None

    latest = None

    for event in result:

        if event.get("event") != "assigned":
            continue

        assignee = event.get(

            "assignee",

            {}

        ).get(

            "login",

            ""

        ).lower()

        if assignee != username.lower():
            continue

        latest = datetime.datetime.fromisoformat(

            event["created_at"].replace(

                "Z",

                "+00:00"

            )

        )

    return latest


def contributor_has_open_pr(

    repo,

    username,

    issue_number

):

    #
    # Search current repo.
    #

    repositories = [

        repo,

        "Context"

    ]

    pattern = re.compile(

        rf"(#{issue_number}|issue\s*{issue_number})",

        re.IGNORECASE

    )

    for r in repositories:

        for pr in CACHE["prs"].get(

            r,

            []

        ):

            if (

                pr.get(

                    "state",

                    ""

                ).lower()

                != "open"

            ):

                continue

            author = pr.get(

                "author",

                {}

            ).get(

                "login",

                ""

            ).lower()

            if author != username.lower():

                continue

            text = (

                pr.get(

                    "title",

                    ""

                )

                +

                "\n"

                +

                (

                    pr.get(

                        "body"

                    )

                    or ""

                )

            )

            if pattern.search(text):

                return True

    return False


def stale_comment_exists(

    issue,

    username

):

    for c in issue.get(

        "comments",

        []

    ):

        body = c.get(

            "body",

            ""

        ).lower()

        if (

            username.lower()

            in body

            and

            "just checking in"

            in body

        ):

            return True

    return False


def stale_assignment_engine():

    info(

        "Running stale assignment engine..."

    )

    warned = 0

    threshold = datetime.timedelta(

        days=STALE_AFTER_DAYS

    )

    now = current_utc()

    for repo in CACHE["repositories"]:

        issues = CACHE["issues"].get(

            repo,

            []

        )

        for issue in issues:

            issue_number = issue["number"]

            assignees = issue.get(

                "assignees",

                []

            )

            if not assignees:

                continue

            for assignee in assignees:

                username = assignee["login"]

                #
                # Exempt contributors.
                #

                if (

                    username.lower()

                    in EXEMPT_FROM_STALE

                ):

                    continue

                assigned_at = assignment_age(

                    repo,

                    issue_number,

                    username

                )

                if assigned_at is None:

                    continue

                if (

                    now - assigned_at

                    <= threshold

                ):

                    continue

                #
                # Already opened a PR.
                #

                if contributor_has_open_pr(

                    repo,

                    username,

                    issue_number

                ):

                    continue

                #
                # Already warned.
                #

                if stale_comment_exists(

                    issue,

                    username

                ):

                    continue

                body = (

                    f"Hi @{username} 👋\n\n"

                    "Just checking in!\n\n"

                    f"This issue has been "

                    f"assigned to you for "

                    f"more than "

                    f"**{STALE_AFTER_DAYS} days**.\n\n"

                    "If you are still "

                    "working on it, "

                    "that is completely fine.\n\n"

                    "Otherwise please let "

                    "us know so we can "

                    "keep the backlog "

                    "moving.\n\n"

                    "Thank you ❤️"

                )

                file = temp_markdown(

                    body

                )

                gh(

                    f'gh issue comment '

                    f'{issue_number} '

                    f'-R {ORG_NAME}/{repo} '

                    f'-F "{file}"'

                )

                os.remove(file)

                warned += 1

                success(

                    f"Stale reminder "

                    f"{repo}#{issue_number}"

                )

    CACHE["stats"]["stale_warnings"] = warned

    success(

        f"Stale engine complete "

        f"({warned} reminders)"

    )
  # =============================================================================
# AUTO CLOSE ENGINE
# =============================================================================

def merged_prs():

    merged = []

    for repo in CACHE["repositories"]:

        merged.extend(

            CACHE["merged_prs"].get(

                repo,

                []

            )

        )

    return merged


def issue_resolved_by_pr(

    repo,

    issue_number

):

    pattern = re.compile(

        rf"(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)?\s*(?:Memact/{repo})?#?{issue_number}\b",

        re.IGNORECASE

    )

    for pr in merged_prs():

        text = (

            pr.get("title", "")

            +

            "\n"

            +

            (

                pr.get("body")

                or ""

            )

        )

        if pattern.search(text):

            return pr

    return None


def close_issue(

    repo,

    issue_number,

    pr_number

):

    return gh(

        f'gh issue close '

        f'{issue_number} '

        f'-R {ORG_NAME}/{repo} '

        f'-c '

        f'"Automatically closed because '

        f'PR #{pr_number} '

        f'has been merged."'

    ).returncode == 0


def autoclose_engine():

    info(

        "Running auto-close engine..."

    )

    closed = 0

    for repo in CACHE["repositories"]:

        issues = CACHE["issues"].get(

            repo,

            []

        )

        for issue in issues:

            issue_number = issue["number"]

            merged = issue_resolved_by_pr(

                repo,

                issue_number

            )

            if merged is None:

                continue

            if close_issue(

                repo,

                issue_number,

                merged["number"]

            ):

                closed += 1

                success(

                    f"Closed "

                    f"{repo}#{issue_number}"

                )

    CACHE["stats"]["issues_closed"] = closed

    success(

        f"Auto-close complete "

        f"({closed} issues closed)"
    )


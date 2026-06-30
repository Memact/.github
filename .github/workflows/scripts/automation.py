"""
Memact SSoC26 automation engine.

Replaces the old split scripts for issue labeling, assignment/unassignment,
stale reminders, PR label sync, dummy PR checks, quality checks, and
auto-closing resolved issues.
"""

from __future__ import annotations

import datetime as dt
import base64
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, TypedDict

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = None
    Field = None


ORG_NAME = os.environ.get("ORG_NAME", "Memact")
REPO_LIMIT = int(os.environ.get("REPO_LIMIT", "1000"))
ISSUE_LIMIT = int(os.environ.get("ISSUE_LIMIT", "1000"))
PR_LIMIT = int(os.environ.get("PR_LIMIT", "1000"))
AI_ENABLED = os.environ.get("AI_ENABLED", "true").lower() == "true"
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
AI_MODEL = os.environ.get("AI_MODEL", "gemini-2.5-flash-lite").strip()
AI_FALLBACK_MODELS = [
    model.strip()
    for model in os.environ.get("AI_FALLBACK_MODELS", "gemini-2.5-flash").split(",")
    if model.strip()
]
AI_MIN_CONFIDENCE = int(os.environ.get("AI_MIN_CONFIDENCE", "90"))
AI_AUTO_MERGE = os.environ.get("AI_AUTO_MERGE", "false").lower() == "true"
AI_MERGE_METHOD = os.environ.get("AI_MERGE_METHOD", "squash").strip().lower()
AI_REVIEW_DRAFT_PRS = os.environ.get("AI_REVIEW_DRAFT_PRS", "false").lower() == "true"
AI_REVIEW_ON_SCHEDULE = os.environ.get("AI_REVIEW_ON_SCHEDULE", "false").lower() == "true"
AI_MAX_DIFF_CHARS = int(os.environ.get("AI_MAX_DIFF_CHARS", "20000"))
AI_RETRY_COUNT = int(os.environ.get("AI_RETRY_COUNT", "2"))
AI_RETRY_BASE_SECONDS = float(os.environ.get("AI_RETRY_BASE_SECONDS", "2"))
AI_RETRY_MAX_SECONDS = float(os.environ.get("AI_RETRY_MAX_SECONDS", "20"))
AI_RETRY_JITTER_SECONDS = float(os.environ.get("AI_RETRY_JITTER_SECONDS", "1.5"))
AI_REQUEST_COOLDOWN_SECONDS = float(os.environ.get("AI_REQUEST_COOLDOWN_SECONDS", "10"))
AUTOCLOSE_ENABLED = os.environ.get("AUTOCLOSE_ENABLED", "false").lower() == "true"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

EXCLUDED_REPOSITORIES = {"Website", "oldWebsite"}
CONTEXT_REPO = "Context"

BOT_USERS = {
    "keepsloading",
    "github-actions",
    "github-actions[bot]",
    "memact",
}

LABEL_COLORS = {
    "SSoC26": "ededed",
    "Easy": "008672",
    "Medium": "d1b100",
    "Hard": "e11d21",
    "Quality: Needs Polish": "d93f0b",
}

LABEL_NORMALIZATION = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "ssoc26": "SSoC26",
}

DIFFICULTIES = {"Easy", "Medium", "Hard"}

ASSIGN_PATTERNS = [
    re.compile(r"^\s*/assign\s*$", re.IGNORECASE),
    re.compile(r"\bassign me\b", re.IGNORECASE),
    re.compile(r"\bplease assign (?:me|this to me)\b", re.IGNORECASE),
    re.compile(r"\bi would like to work on this\b", re.IGNORECASE),
    re.compile(r"\bi'd like to work on this\b", re.IGNORECASE),
    re.compile(r"\bi want to work on this\b", re.IGNORECASE),
    re.compile(r"\bcan i work on this\b", re.IGNORECASE),
]

NEGATIVE_PATTERNS = [
    re.compile(r"^\s*/unassign\s*$", re.IGNORECASE),
    re.compile(r"\bplease unassign me\b", re.IGNORECASE),
    re.compile(r"\bunassign me\b", re.IGNORECASE),
    re.compile(r"\bremove me\b", re.IGNORECASE),
    re.compile(r"\bi withdraw\b", re.IGNORECASE),
    re.compile(r"\bi am no longer working on this\b", re.IGNORECASE),
    re.compile(r"\bi'm no longer working on this\b", re.IGNORECASE),
]

DEFAULT_ASSIGNMENT_LIMIT = 10
GREYLIST_LIMIT = 1
FORMER_GREYLIST = {
    "codesparks45",
    "codesparks",
    "prasiddhi-105",
    "prasiddhi",
    "prassidhi",
}

EXEMPT_FROM_STALE = {"yachna-jpg"}
STALE_AFTER_DAYS = 3

MARKERS = {
    "assignment_limit": "<!-- ssoc26-assignment-limit -->",
    "assignment_success": "<!-- ssoc26-assignment-success -->",
    "unassign": "<!-- ssoc26-unassign-confirmation -->",
    "stale": "<!-- ssoc26-stale-reminder -->",
    "pr_label": "<!-- ssoc26-pr-label-sync -->",
    "dummy_success": "<!-- ssoc26-dummy-pr-success -->",
    "dummy_warning": "<!-- ssoc26-dummy-pr-warning -->",
    "quality": "<!-- ssoc26-quality-warning -->",
    "ai_review": "<!-- ssoc26-ai-review -->",
    "ai_merge": "<!-- ssoc26-ai-merge-advice -->",
}

AI_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "confidence": {"type": "integer"},
        "recommendation": {
            "type": "string",
            "enum": ["PASS", "PASS_WITH_COMMENTS", "NEEDS_CHANGES"],
        },
        "blocking": {"type": "array", "items": {"type": "string"}},
        "architecture": {"type": "array", "items": {"type": "string"}},
        "security": {"type": "array", "items": {"type": "string"}},
        "performance": {"type": "array", "items": {"type": "string"}},
        "maintainability": {"type": "array", "items": {"type": "string"}},
        "style": {"type": "array", "items": {"type": "string"}},
        "testing": {"type": "array", "items": {"type": "string"}},
        "documentation": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "confidence",
        "recommendation",
        "blocking",
        "architecture",
        "security",
        "performance",
        "maintainability",
        "style",
        "testing",
        "documentation",
        "suggestions",
    ],
}


class AIReviewResponse(TypedDict):
    summary: str
    confidence: int
    recommendation: str
    blocking: list[str]
    architecture: list[str]
    security: list[str]
    performance: list[str]
    maintainability: list[str]
    style: list[str]
    testing: list[str]
    documentation: list[str]
    suggestions: list[str]


if BaseModel is not None:
    class AIReviewModel(BaseModel):
        summary: str = ""
        confidence: int = Field(ge=0, le=100)
        recommendation: str
        blocking: list[str] = Field(default_factory=list)
        architecture: list[str] = Field(default_factory=list)
        security: list[str] = Field(default_factory=list)
        performance: list[str] = Field(default_factory=list)
        maintainability: list[str] = Field(default_factory=list)
        style: list[str] = Field(default_factory=list)
        testing: list[str] = Field(default_factory=list)
        documentation: list[str] = Field(default_factory=list)
        suggestions: list[str] = Field(default_factory=list)
else:
    AIReviewModel = None

MEMACT_AI_REVIEW_CONTEXT = """
You are reviewing Memact pull requests.

Memact is an open protocol and reference implementation for portable,
user-owned context. Its doctrine is: activity is not identity, identity belongs
to users, apps contribute observations, users approve identity, context is
portable and permissioned, identity evolves, and freshness, confidence,
relevance, provenance, explainability, and simplicity matter.

Core evidence flow: Raw Activity -> Evidence -> Claim -> Approval ->
Approved Claim -> Memory -> Retrieval. Apps may contribute observations and
request approved context, but apps must never create identity. Users approve,
rectify, archive, and delete identity claims.

Repository boundaries:
- Access owns permissions, consent, authentication, authorization, revocation,
  sharing scopes, transparency, and auditability. Access must not own memory,
  claim semantics, or business identity.
- Context owns categorization, ranking, relevance, freshness, confidence,
  contradiction resolution, reinforcement, provenance, explainability, and
  retrieval preparation. Context must not bypass consent or persist canonical
  user history.
- Memory owns persistence capabilities, journals, replay, indexing, history,
  and retrieval support. It must stay implementation-independent at the
  protocol level.
- Contracts owns shared schemas, validators, and protocol contracts. Contracts
  must contain zero business logic.
- SDK is the reference implementation and developer experience layer for CAP,
  CCP, CRP wrappers, auth helpers, and diagnostics. It must not own product
  policy or protocol semantics.
- Notebook is the presentation-first user experience for approvals,
  rectification, search, timelines, trust/freshness visualization, undo,
  history, connected apps, and profile management.

Protocols:
- CAP is for applications requesting approved context with consent and least
  context.
- CCP is for applications contributing observations/evidence.
- CRP is for retrieval of approved, permissioned context.
Prefer extending CAP, CCP, or CRP over inventing new protocols.

Review priorities: protect user ownership, consent, least-context access,
repository boundaries, protocol compatibility, simple architecture, stable
public APIs, maintainability, tests, and clear documentation. Block changes
that let apps create identity, bypass approval, mix repository responsibilities,
add speculative infrastructure, leak secrets, weaken authorization, or make
protocol contracts unstable.
""".strip()

SKIP_DIFF_PREFIXES = ("docs/", "examples/", "test/", "tests/", ".github/")
SKIP_DIFF_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "npm-shrinkwrap.json",
}

QUALITY_RULES = [
    (
        "Debug Statements",
        re.compile(r"\b(console\.log|console\.error|debugger)\b", re.IGNORECASE),
        "Remove debugging statements before review.",
        False,
    ),
    (
        "TODO Marker",
        re.compile(r"\b(TODO|FIXME|XXX)\b", re.IGNORECASE),
        "Resolve placeholder markers before review.",
        False,
    ),
    (
        "Possible Secret",
        re.compile(
            r"\b(api[_-]?key|secret|password|passwd|bearer|private[_-]?key)\b\s*[:=]",
            re.IGNORECASE,
        ),
        "Review this file for possible hardcoded credentials.",
        True,
    ),
]

CACHE: dict[str, Any] = {
    "repositories": [],
    "issues": {},
    "prs": {},
    "merged_prs": {},
    "issue_comments": {},
    "pr_comments": {},
    "timelines": {},
    "mutation_keys": set(),
    "assignment_count": defaultdict(int),
    "latest_intent": defaultdict(dict),
    "current_user": "",
    "stats": defaultdict(int),
}


def info(message: str) -> None:
    print(f"[INFO] {message}")


def success(message: str) -> None:
    print(f"[SUCCESS] {message}")


def warning(message: str) -> None:
    print(f"[WARNING] {message}", file=sys.stderr)


def error(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)


def action(message: str) -> None:
    print(f"[ACTION] {message}")


def claim_mutation(key: str) -> bool:
    if key in CACHE["mutation_keys"]:
        CACHE["stats"]["mutations_suppressed_in_run"] += 1
        return False
    CACHE["mutation_keys"].add(key)
    return True


def retry_delay(attempt: int) -> float:
    base = min(AI_RETRY_MAX_SECONDS, AI_RETRY_BASE_SECONDS * (2 ** attempt))
    jitter = random.uniform(0, AI_RETRY_JITTER_SECONDS) if AI_RETRY_JITTER_SECONDS > 0 else 0
    return base + jitter


def is_transient_ai_error(exc: Exception) -> bool:
    message = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return (
        status in {500, 502, 503, 504}
        or any(
            token in message
            for token in (
                "503",
                "service unavailable",
                "servererror",
                "server error",
                "overload",
                "overloaded",
                "unavailable",
                "deadline",
                "timeout",
            )
        )
    )


def is_ai_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return (
        status == 429
        or any(
            token in message
            for token in (
                "429",
                "quota",
                "rate limit",
                "resource_exhausted",
                "daily limit",
                "rpd",
            )
        )
    )


def gh(args: list[str], *, log_failure: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if log_failure and result.returncode != 0:
        error("Command failed: gh " + " ".join(args))
        if result.stderr.strip():
            error(result.stderr.strip())
    return result


def gh_json(args: list[str]) -> Any | None:
    result = gh(args)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        error("Invalid JSON from: gh " + " ".join(args))
        error(str(exc))
        error(result.stdout[:1000])
        return None


@contextmanager
def temp_markdown(content: str):
    path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".md",
            mode="w",
            encoding="utf-8",
        ) as handle:
            handle.write(content)
            path = handle.name
        yield path
    finally:
        if path:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


def normalize_label(label: str) -> str:
    return LABEL_NORMALIZATION.get(label.lower(), label)


def label_names(item: dict[str, Any]) -> set[str]:
    return {normalize_label(label.get("name", "")) for label in item.get("labels", [])}


def author_login(item: dict[str, Any]) -> str:
    return item.get("author", {}).get("login", "").lower()


def is_bot(username: str) -> bool:
    return username.lower() in BOT_USERS


def current_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_github_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        warning(f"Invalid GitHub timestamp: {value}")
        return None


def contains_assignment_request(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in ASSIGN_PATTERNS)


def contains_negative_intent(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in NEGATIVE_PATTERNS)


def issue_reference_pattern(repo: str, number: int, *, closing_keyword: bool = False) -> re.Pattern[str]:
    org = re.escape(ORG_NAME)
    repository = re.escape(repo)
    issue = re.escape(str(number))
    ref = (
        rf"(?:"
        rf"#{issue}\b|"
        rf"{org}/{repository}#{issue}\b|"
        rf"{repository}#{issue}\b|"
        rf"github\.com/{org}/{repository}/issues/{issue}\b|"
        rf"issue\s+{issue}\b"
        rf")"
    )
    if closing_keyword:
        return re.compile(
            rf"\b(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+{ref}",
            re.IGNORECASE,
        )
    return re.compile(ref, re.IGNORECASE)


def pr_reference_pattern(repo: str, number: int) -> re.Pattern[str]:
    org = re.escape(ORG_NAME)
    repository = re.escape(repo)
    pr_number = re.escape(str(number))
    return re.compile(
        rf"(?:"
        rf"{org}/{repository}#{pr_number}\b|"
        rf"{repository}#{pr_number}\b|"
        rf"github\.com/{org}/{repository}/pull/{pr_number}\b|"
        rf"{repository}\s+(?:pr|pull)\s*#?{pr_number}\b"
        rf")",
        re.IGNORECASE,
    )


def load_event() -> dict[str, Any] | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        with open(event_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        warning(f"Could not read event payload: {exc}")
        return None


def event_repo_only() -> str | None:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name in {"issue_comment", "issues", "pull_request"}:
        event = load_event()
        full_name = (event or {}).get("repository", {}).get("full_name", "")
        owner, _, repo = full_name.partition("/")
        if owner.lower() == ORG_NAME.lower() and repo:
            return repo
    return None


def initialize() -> None:
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    result = gh(["api", "user", "--jq", ".login"])
    if result.returncode != 0:
        error("GitHub authentication failed.")
        sys.exit(1)
    CACHE["current_user"] = result.stdout.strip().lower()
    if CACHE["current_user"]:
        BOT_USERS.add(CACHE["current_user"])


def fetch_repositories() -> None:
    repo_filter = event_repo_only()
    if repo_filter:
        CACHE["repositories"] = [] if repo_filter in EXCLUDED_REPOSITORIES else [repo_filter]
        success(f"Loaded event repository: {repo_filter}")
        return

    repos = gh_json(["repo", "list", ORG_NAME, "--limit", str(REPO_LIMIT), "--json", "name"])
    if repos is None:
        error("Could not fetch repositories.")
        sys.exit(1)

    CACHE["repositories"] = sorted(
        repo["name"] for repo in repos if repo.get("name") not in EXCLUDED_REPOSITORIES
    )
    success(f"Loaded {len(CACHE['repositories'])} repositories.")


def fetch_issue_comments(repo: str, issue_number: int, *, refresh: bool = False) -> list[dict[str, Any]]:
    key = (repo, issue_number)
    if not refresh and key in CACHE["issue_comments"]:
        return CACHE["issue_comments"][key]
    data = gh_json(["issue", "view", str(issue_number), "-R", f"{ORG_NAME}/{repo}", "--json", "comments"])
    comments = (data or {}).get("comments", [])
    CACHE["issue_comments"][key] = comments
    return comments


def fetch_pr_comments(repo: str, pr_number: int, *, refresh: bool = False) -> list[dict[str, Any]]:
    key = (repo, pr_number)
    if not refresh and key in CACHE["pr_comments"]:
        return CACHE["pr_comments"][key]
    data = gh_json(["pr", "view", str(pr_number), "-R", f"{ORG_NAME}/{repo}", "--json", "comments"])
    comments = (data or {}).get("comments", [])
    CACHE["pr_comments"][key] = comments
    return comments


def fetch_all_issues() -> None:
    info("Fetching open issues...")
    CACHE["issues"].clear()
    CACHE["stats"]["issues"] = 0

    for repo in CACHE["repositories"]:
        issues = gh_json(
            [
                "issue",
                "list",
                "-R",
                f"{ORG_NAME}/{repo}",
                "--state",
                "open",
                "--limit",
                str(ISSUE_LIMIT),
                "--json",
                "number,title,body,url,author,labels,assignees,createdAt",
            ]
        )
        if issues is None:
            warning(f"{repo}: issue fetch failed.")
            continue
        for issue in issues:
            issue["comments"] = fetch_issue_comments(repo, issue["number"])
        CACHE["issues"][repo] = issues
        CACHE["stats"]["issues"] += len(issues)


def fetch_all_pull_requests() -> None:
    info("Fetching pull requests...")
    CACHE["prs"].clear()
    CACHE["merged_prs"].clear()
    CACHE["stats"]["prs"] = 0

    repos = set(CACHE["repositories"])
    repos.add(CONTEXT_REPO)
    for repo in sorted(repos):
        prs = gh_json(
            [
                "pr",
                "list",
                "-R",
                f"{ORG_NAME}/{repo}",
                "--state",
                "all",
                "--limit",
                str(PR_LIMIT),
                "--json",
                "number,title,body,state,author,labels,url,headRefOid,isDraft,files,reviewDecision,mergeStateStatus,mergeable,statusCheckRollup",
            ]
        )
        if prs is None:
            warning(f"{repo}: PR fetch failed.")
            continue
        CACHE["prs"][repo] = prs
        CACHE["merged_prs"][repo] = [pr for pr in prs if pr.get("state", "").lower() == "merged"]
        if repo in CACHE["repositories"]:
            CACHE["stats"]["prs"] += len(prs)


def build_assignment_index() -> None:
    CACHE["assignment_count"].clear()
    for issues in CACHE["issues"].values():
        for issue in issues:
            for assignee in issue.get("assignees", []):
                CACHE["assignment_count"][assignee.get("login", "").lower()] += 1


def build_intent_index() -> None:
    CACHE["latest_intent"].clear()
    for repo, issues in CACHE["issues"].items():
        for issue in issues:
            issue_number = issue["number"]
            comments = sorted(issue.get("comments", []), key=lambda item: item.get("createdAt", ""))
            for comment in comments:
                username = comment.get("author", {}).get("login", "").lower()
                if not username or is_bot(username):
                    continue
                body = comment.get("body", "")
                if contains_negative_intent(body):
                    intent = "UNASSIGN"
                elif contains_assignment_request(body):
                    intent = "ASSIGN"
                else:
                    continue
                CACHE["latest_intent"][repo].setdefault(issue_number, {})[username] = {
                    "intent": intent,
                    "timestamp": comment.get("createdAt", ""),
                }


def bot_comment_exists(comments: list[dict[str, Any]], marker: str) -> bool:
    for comment in comments:
        username = comment.get("author", {}).get("login", "").lower()
        if is_bot(username) and marker in (comment.get("body") or ""):
            return True
    return False


def post_comment_once(kind: str, repo: str, number: int, marker: str, body: str) -> bool:
    mutation_key = f"comment:{kind}:{repo}:{number}:{marker}"
    if not claim_mutation(mutation_key):
        return False
    comments = (
        fetch_issue_comments(repo, number, refresh=True)
        if kind == "issue"
        else fetch_pr_comments(repo, number, refresh=True)
    )
    if bot_comment_exists(comments, marker):
        CACHE["stats"]["comments_suppressed_existing"] += 1
        return False

    full_body = f"{marker}\n{body}"
    command = "issue" if kind == "issue" else "pr"
    with temp_markdown(full_body) as path:
        result = gh([command, "comment", str(number), "-R", f"{ORG_NAME}/{repo}", "-F", path])
    if result.returncode == 0:
        if kind == "issue":
            fetch_issue_comments(repo, number, refresh=True)
        else:
            fetch_pr_comments(repo, number, refresh=True)
        return True
    return False


def ensure_label(repo: str, label: str) -> bool:
    color = LABEL_COLORS.get(label, "ededed")
    result = gh(
        ["label", "create", label, "-R", f"{ORG_NAME}/{repo}", "--color", color, "--force"],
        log_failure=False,
    )
    if result.returncode != 0:
        warning(f"{repo}: could not ensure label {label}: {result.stderr.strip()}")
        return False
    return True


def fetch_current_labels(kind: str, repo: str, number: int) -> set[str]:
    command = "issue" if kind == "issue" else "pr"
    result = gh(
        [command, "view", str(number), "-R", f"{ORG_NAME}/{repo}", "--json", "labels"],
        log_failure=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return set()
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return set()
    return {normalize_label(label.get("name", "")) for label in data.get("labels", [])}


def edit_labels(kind: str, repo: str, number: int, *, add: list[str] | None = None, remove: list[str] | None = None) -> bool:
    ok = True
    command = "issue" if kind == "issue" else "pr"
    current_labels = fetch_current_labels(kind, repo, number)
    for label in add or []:
        normalized = normalize_label(label)
        if normalized in current_labels:
            CACHE["stats"]["labels_suppressed_existing"] += 1
            continue
        mutation_key = f"label:add:{kind}:{repo}:{number}:{normalized}"
        if not claim_mutation(mutation_key):
            continue
        if not ensure_label(repo, label):
            ok = False
            continue
        result = gh([command, "edit", str(number), "-R", f"{ORG_NAME}/{repo}", "--add-label", label])
        if result.returncode == 0:
            current_labels.add(normalized)
        ok = ok and result.returncode == 0
    for label in remove or []:
        normalized = normalize_label(label)
        if normalized not in current_labels:
            CACHE["stats"]["labels_suppressed_absent"] += 1
            continue
        mutation_key = f"label:remove:{kind}:{repo}:{number}:{normalized}"
        if not claim_mutation(mutation_key):
            continue
        result = gh(
            [command, "edit", str(number), "-R", f"{ORG_NAME}/{repo}", "--remove-label", label],
            log_failure=False,
        )
        if result.returncode != 0 and "not found" not in result.stderr.lower():
            warning(f"{repo}#{number}: could not remove label {label}: {result.stderr.strip()}")
            ok = False
        elif result.returncode == 0:
            current_labels.discard(normalized)
    return ok


def sync_normalized_labels(kind: str, repo: str, number: int, labels: set[str]) -> set[str]:
    updated = set(labels)
    for label in list(labels):
        fixed = normalize_label(label)
        if fixed == label:
            continue
        if edit_labels(kind, repo, number, add=[fixed], remove=[label]):
            updated.discard(label)
            updated.add(fixed)
    return updated


def detect_difficulty(title: str, body: str | None) -> str | None:
    text = f"{title}\n{body or ''}".lower()
    if re.search(r"\beasy\b", text):
        return "Easy"
    if re.search(r"\bmedium\b", text):
        return "Medium"
    if re.search(r"\bhard\b", text):
        return "Hard"
    return None


def label_issue_engine() -> None:
    added = 0
    for repo, issues in CACHE["issues"].items():
        for issue in issues:
            labels = sync_normalized_labels("issue", repo, issue["number"], label_names(issue))
            to_add = []
            if "SSoC26" not in labels:
                to_add.append("SSoC26")
            difficulty = detect_difficulty(issue.get("title", ""), issue.get("body"))
            if difficulty and difficulty not in labels:
                to_add.append(difficulty)
            if edit_labels("issue", repo, issue["number"], add=to_add):
                added += len(to_add)
                if to_add:
                    action(f"issue_labels_added repo={repo} issue=#{issue['number']} labels={','.join(to_add)}")
    CACHE["stats"]["issue_labels_added"] = added


def assignment_limit(username: str) -> int:
    return GREYLIST_LIMIT if username.lower() in FORMER_GREYLIST else DEFAULT_ASSIGNMENT_LIMIT


def fetch_issue(repo: str, issue_number: int) -> dict[str, Any] | None:
    return gh_json(
        [
            "issue",
            "view",
            str(issue_number),
            "-R",
            f"{ORG_NAME}/{repo}",
            "--json",
            "number,assignees,labels,author,createdAt",
        ]
    )


def fetch_active_assignment_count(username: str) -> int:
    username = username.lower()
    count = 0
    for repo in CACHE["repositories"]:
        data = gh_json(
            [
                "issue",
                "list",
                "-R",
                f"{ORG_NAME}/{repo}",
                "--state",
                "open",
                "--assignee",
                username,
                "--limit",
                str(ISSUE_LIMIT),
                "--json",
                "number",
            ]
        )
        if data is not None:
            count += len(data)
    CACHE["assignment_count"][username] = count
    return count


def assign_user(repo: str, issue_number: int, username: str) -> bool:
    if not claim_mutation(f"assign:{repo}:{issue_number}:{username.lower()}"):
        return False
    result = gh(
        [
            "issue",
            "edit",
            str(issue_number),
            "-R",
            f"{ORG_NAME}/{repo}",
            "--add-assignee",
            username,
        ]
    )
    return result.returncode == 0


def assignment_engine() -> None:
    assigned = 0
    skipped_already_assigned = 0
    skipped_limit = 0
    skipped_race = 0
    for repo, issue_states in CACHE["latest_intent"].items():
        for issue_number, users in issue_states.items():
            fresh_issue = fetch_issue(repo, issue_number)
            if not fresh_issue:
                continue
            if fresh_issue.get("assignees"):
                skipped_already_assigned += 1
                continue

            candidates = [
                {"user": username, "timestamp": state["timestamp"]}
                for username, state in users.items()
                if state.get("intent") == "ASSIGN"
            ]
            if not candidates:
                continue

            candidates.sort(key=lambda item: item["timestamp"])
            winner = candidates[0]["user"]
            active = fetch_active_assignment_count(winner)
            limit = assignment_limit(winner)

            if active >= limit:
                skipped_limit += 1
                post_comment_once(
                    "issue",
                    repo,
                    issue_number,
                    MARKERS["assignment_limit"],
                    (
                        f"Hi @{winner},\n\n"
                        f"You currently have {active} active assignment(s), and the limit is {limit}. "
                        "Please finish an existing assignment or request unassignment before taking another issue."
                    ),
                )
                continue

            fresh_issue = fetch_issue(repo, issue_number)
            if not fresh_issue or fresh_issue.get("assignees"):
                skipped_race += 1
                continue
            if not assign_user(repo, issue_number, winner):
                continue

            CACHE["assignment_count"][winner] += 1
            assigned += 1
            action(f"assigned repo={repo} issue=#{issue_number} user=@{winner}")
            body = (
                f"Hey @{winner},\n\n"
                "You have been assigned this issue for SSoC26. Looking forward to your PR."
            )
            if winner in FORMER_GREYLIST:
                body += (
                    "\n\nPlease pay extra attention to code quality, testing, and project conventions."
                )
            post_comment_once("issue", repo, issue_number, MARKERS["assignment_success"], body)
    CACHE["stats"]["assigned"] = assigned
    CACHE["stats"]["assignment_skipped_already_assigned"] = skipped_already_assigned
    CACHE["stats"]["assignment_skipped_limit"] = skipped_limit
    CACHE["stats"]["assignment_skipped_race"] = skipped_race


def remove_assignee(repo: str, issue_number: int, username: str) -> bool:
    if not claim_mutation(f"unassign:{repo}:{issue_number}:{username.lower()}"):
        return False
    result = gh(
        [
            "issue",
            "edit",
            str(issue_number),
            "-R",
            f"{ORG_NAME}/{repo}",
            "--remove-assignee",
            username,
        ]
    )
    return result.returncode == 0


def latest_comment_by(issue: dict[str, Any], username: str) -> dict[str, Any] | None:
    comments = [
        comment
        for comment in issue.get("comments", [])
        if comment.get("author", {}).get("login", "").lower() == username.lower()
    ]
    if not comments:
        return None
    return sorted(comments, key=lambda item: item.get("createdAt", ""), reverse=True)[0]


def unassignment_engine() -> None:
    removed = 0
    for repo, issues in CACHE["issues"].items():
        for issue in issues:
            for assignee in issue.get("assignees", []):
                username = assignee.get("login", "").lower()
                latest = latest_comment_by(issue, username)
                if not latest or not contains_negative_intent(latest.get("body", "")):
                    continue
                if remove_assignee(repo, issue["number"], username):
                    CACHE["assignment_count"][username] = max(0, CACHE["assignment_count"][username] - 1)
                    removed += 1
                    action(f"unassigned repo={repo} issue=#{issue['number']} user=@{username}")
                    post_comment_once(
                        "issue",
                        repo,
                        issue["number"],
                        MARKERS["unassign"],
                        (
                            f"Okay @{username}, you have been unassigned from this issue.\n\n"
                            "If you want to work on it later, comment `/assign`."
                        ),
                    )
    CACHE["stats"]["unassigned"] = removed


def get_issue_timeline(repo: str, issue_number: int) -> list[dict[str, Any]]:
    key = (repo, issue_number)
    if key not in CACHE["timelines"]:
        CACHE["timelines"][key] = gh_json(
            ["api", f"repos/{ORG_NAME}/{repo}/issues/{issue_number}/timeline"]
        ) or []
    return CACHE["timelines"][key]


def assignment_time(repo: str, issue_number: int, username: str) -> dt.datetime | None:
    latest = None
    for event in get_issue_timeline(repo, issue_number):
        if event.get("event") != "assigned":
            continue
        assignee = event.get("assignee", {}).get("login", "").lower()
        if assignee != username.lower():
            continue
        event_time = parse_github_time(event.get("created_at"))
        if event_time and (latest is None or event_time > latest):
            latest = event_time
    return latest


def contributor_has_open_pr(repo: str, username: str, issue_number: int) -> bool:
    pattern = issue_reference_pattern(repo, issue_number)
    for candidate_repo in {repo, CONTEXT_REPO}:
        for pr in CACHE["prs"].get(candidate_repo, []):
            if pr.get("state", "").lower() != "open":
                continue
            if author_login(pr) != username.lower():
                continue
            text = f"{pr.get('title', '')}\n{pr.get('body') or ''}"
            if pattern.search(text):
                return True
    return False


def stale_assignment_engine() -> None:
    stale_detected = 0
    warned = 0
    threshold = dt.timedelta(days=STALE_AFTER_DAYS)
    now = current_utc()

    for repo, issues in CACHE["issues"].items():
        for issue in issues:
            created_at = parse_github_time(issue.get("createdAt"))
            if created_at and now - created_at <= threshold:
                continue
            for assignee in issue.get("assignees", []):
                username = assignee.get("login", "")
                if username.lower() in EXEMPT_FROM_STALE:
                    continue
                assigned_at = assignment_time(repo, issue["number"], username)
                if assigned_at is None or now - assigned_at <= threshold:
                    continue
                if contributor_has_open_pr(repo, username, issue["number"]):
                    continue
                stale_detected += 1
                if post_comment_once(
                    "issue",
                    repo,
                    issue["number"],
                    MARKERS["stale"],
                    (
                        f"Hi @{username},\n\n"
                        f"Just checking in. This issue has been assigned to you for more than "
                        f"{STALE_AFTER_DAYS} days. If you are still working on it, no problem. "
                        "Otherwise, please let us know so we can keep the backlog moving."
                    ),
                ):
                    warned += 1
                    action(f"stale_warning_posted repo={repo} issue=#{issue['number']} user=@{username}")
    CACHE["stats"]["stale_detected"] = stale_detected
    CACHE["stats"]["stale_warnings_posted"] = warned


def referenced_issues(repo: str, text: str) -> set[int]:
    refs: set[int] = set()
    for match in re.finditer(r"#(\d+)\b", text):
        refs.add(int(match.group(1)))
    org = re.escape(ORG_NAME)
    repository = re.escape(repo)
    for match in re.finditer(rf"{org}/{repository}#(\d+)\b", text, re.IGNORECASE):
        refs.add(int(match.group(1)))
    for match in re.finditer(rf"github\.com/{org}/{repository}/issues/(\d+)\b", text, re.IGNORECASE):
        refs.add(int(match.group(1)))
    return refs


def fetch_issue_labels(repo: str, issue_number: int) -> set[str]:
    for issue in CACHE["issues"].get(repo, []):
        if issue["number"] == issue_number:
            return label_names(issue)
    data = gh_json(["issue", "view", str(issue_number), "-R", f"{ORG_NAME}/{repo}", "--json", "labels"])
    return {normalize_label(label.get("name", "")) for label in (data or {}).get("labels", [])}


def pr_label_engine() -> None:
    updated = 0
    for repo, prs in CACHE["prs"].items():
        if repo not in CACHE["repositories"]:
            continue
        for pr in prs:
            if pr.get("state", "").lower() != "open":
                continue
            pr_number = pr["number"]
            pr_labels = sync_normalized_labels("pr", repo, pr_number, label_names(pr))
            text = f"{pr.get('title', '')}\n{pr.get('body') or ''}"
            labels_to_add: set[str] = set()
            for issue_number in referenced_issues(repo, text):
                for label in fetch_issue_labels(repo, issue_number):
                    if label == "SSoC26" or label in DIFFICULTIES:
                        labels_to_add.add(label)
            if "ssoc" in pr.get("title", "").lower():
                labels_to_add.add("SSoC26")
            labels_to_add -= pr_labels
            if labels_to_add and edit_labels("pr", repo, pr_number, add=sorted(labels_to_add)):
                updated += 1
                action(f"pr_labels_added repo={repo} pr=#{pr_number} labels={','.join(sorted(labels_to_add))}")
                if post_comment_once(
                    "pr",
                    repo,
                    pr_number,
                    MARKERS["pr_label"],
                    "SSoC26 labels were synchronized from the linked issue.",
                ):
                    CACHE["stats"]["pr_label_comments_posted"] += 1
    CACHE["stats"]["prs_labeled"] = updated


def find_dummy_pr(repo: str, pr: dict[str, Any]) -> dict[str, Any] | None:
    username = author_login(pr)
    pr_number = pr["number"]
    text = f"{pr.get('title', '')}\n{pr.get('body') or ''}"
    issue_refs = referenced_issues(repo, text)
    pr_pattern = pr_reference_pattern(repo, pr_number)
    issue_patterns = [issue_reference_pattern(repo, issue_number) for issue_number in issue_refs]

    for context_pr in CACHE["prs"].get(CONTEXT_REPO, []):
        if username and author_login(context_pr) != username:
            continue
        context_text = f"{context_pr.get('title', '')}\n{context_pr.get('body') or ''}"
        if pr_pattern.search(context_text) or any(pattern.search(context_text) for pattern in issue_patterns):
            return context_pr
    return None


def dummy_pr_engine() -> None:
    found = 0
    missing = 0
    success_comments = 0
    warning_comments = 0
    for repo, prs in CACHE["prs"].items():
        if repo in {CONTEXT_REPO, ".github"} or repo not in CACHE["repositories"]:
            continue
        for pr in prs:
            if pr.get("state", "").lower() not in {"open", "merged"}:
                continue
            dummy_pr = find_dummy_pr(repo, pr)
            if dummy_pr:
                found += 1
                source_labels = {label for label in label_names(pr) if label == "SSoC26" or label in DIFFICULTIES}
                if not source_labels:
                    source_labels.add("SSoC26")
                dummy_labels = label_names(dummy_pr)
                edit_labels(
                    "pr",
                    CONTEXT_REPO,
                    dummy_pr["number"],
                    add=sorted(source_labels - dummy_labels),
                )
                action(f"dummy_pr_found repo={repo} pr=#{pr['number']} context_pr=#{dummy_pr['number']}")
                if post_comment_once(
                    "pr",
                    repo,
                    pr["number"],
                    MARKERS["dummy_success"],
                    f"Dummy PR detected in Memact/{CONTEXT_REPO} (#{dummy_pr['number']}).",
                ):
                    success_comments += 1
            else:
                missing += 1
                if post_comment_once(
                    "pr",
                    repo,
                    pr["number"],
                    MARKERS["dummy_warning"],
                    (
                        f"No corresponding dummy PR was found in Memact/{CONTEXT_REPO}. "
                        f"Please create one referencing `Memact/{repo}#{pr['number']}` so this contribution can be tracked."
                    ),
                ):
                    warning_comments += 1
                    action(f"dummy_warning_posted repo={repo} pr=#{pr['number']}")
    CACHE["stats"]["dummy_found"] = found
    CACHE["stats"]["dummy_missing"] = missing
    CACHE["stats"]["dummy_success_comments_posted"] = success_comments
    CACHE["stats"]["dummy_warning_comments_posted"] = warning_comments


def should_skip_diff_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    name = normalized.rsplit("/", 1)[-1]
    return name in SKIP_DIFF_FILES or normalized.startswith(SKIP_DIFF_PREFIXES)


def fetch_pr_diff(repo: str, pr_number: int) -> str:
    result = gh(["pr", "diff", str(pr_number), "-R", f"{ORG_NAME}/{repo}"], log_failure=False)
    return result.stdout if result.returncode == 0 else ""


def analyze_diff(diff: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    current_file = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current_file and should_skip_diff_path(current_file):
            continue
        code = line[1:].strip()
        if not code or code.startswith(("//", "#", "*")):
            continue
        for name, pattern, message, redact in QUALITY_RULES:
            if pattern.search(code):
                finding = {"rule": name, "file": current_file or "unknown", "message": message}
                if not redact:
                    finding["line"] = code[:180]
                findings.append(finding)
                break
    return findings


def quality_comment(findings: list[dict[str, str]]) -> str:
    lines = [
        "SSoC26 code quality check found items to clean up before review.",
        "",
    ]
    for finding in findings[:20]:
        detail = f"- {finding['rule']} in `{finding['file']}`: {finding['message']}"
        if finding.get("line"):
            detail += f" `{finding['line']}`"
        lines.append(detail)
    if len(findings) > 20:
        lines.append(f"- {len(findings) - 20} additional finding(s) omitted.")
    return "\n".join(lines)


def update_or_post_pr_comment(repo: str, pr_number: int, marker: str, body: str) -> bool:
    comments = fetch_pr_comments(repo, pr_number, refresh=True)
    if bot_comment_exists(comments, marker):
        bot_comments = [
            comment
            for comment in comments
            if is_bot(comment.get("author", {}).get("login", "").lower())
        ]
        bot_comments.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
        if bot_comments and marker in (bot_comments[0].get("body") or ""):
            with temp_markdown(f"{marker}\n{body}") as path:
                result = gh(
                    [
                        "pr",
                        "comment",
                        str(pr_number),
                        "-R",
                        f"{ORG_NAME}/{repo}",
                        "--edit-last",
                        "-F",
                        path,
                    ]
                )
            return result.returncode == 0
        return False
    return post_comment_once("pr", repo, pr_number, marker, body)


def pr_head_sha(pr: dict[str, Any]) -> str:
    return (pr.get("headRefOid") or "").strip()


def pr_file_paths(pr: dict[str, Any]) -> list[str]:
    paths = []
    for item in pr.get("files") or []:
        path = item.get("path") or item.get("filename") or ""
        if path:
            paths.append(path)
    return paths


def is_low_value_ai_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    filename = normalized.rsplit("/", 1)[-1]
    if filename in {"license", "license.md", "readme.md"}:
        return True
    if normalized.startswith(("docs/", ".github/")):
        return True
    if normalized.endswith((".md", ".markdown", ".mdx", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".pdf")):
        return True
    return False


def should_review_files_with_ai(paths: list[str]) -> bool:
    if not paths:
        return True
    return any(not is_low_value_ai_path(path) for path in paths)


def should_run_ai_review_for_event() -> bool:
    if not AI_ENABLED:
        return False
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name in {"schedule", "workflow_dispatch"}:
        return AI_REVIEW_ON_SCHEDULE
    if event_name != "pull_request":
        return False
    event = load_event() or {}
    return event.get("action") in {"opened", "synchronize", "ready_for_review"}


def ai_review_exists_for_sha(comments: list[dict[str, Any]], sha: str) -> bool:
    if not sha:
        return False
    marker = MARKERS["ai_review"]
    sha_line = f"Reviewed commit: `{sha}`"
    for comment in comments:
        username = comment.get("author", {}).get("login", "").lower()
        body = comment.get("body") or ""
        if is_bot(username) and marker in body and sha_line in body:
            return True
    return False


def post_ai_review_comment(repo: str, pr_number: int, sha: str, body: str) -> bool:
    if not claim_mutation(f"ai-review:{repo}:{pr_number}:{sha}"):
        return False
    comments = fetch_pr_comments(repo, pr_number, refresh=True)
    if ai_review_exists_for_sha(comments, sha):
        CACHE["stats"]["ai_reviews_suppressed_existing_sha"] += 1
        return False
    with temp_markdown(f"{MARKERS['ai_review']}\n{body}") as path:
        result = gh(["pr", "comment", str(pr_number), "-R", f"{ORG_NAME}/{repo}", "-F", path])
    if result.returncode == 0:
        fetch_pr_comments(repo, pr_number, refresh=True)
        return True
    return False


def fetch_text_file(repo: str, path: str, *, max_chars: int = 4000) -> str:
    result = gh(
        [
            "api",
            f"repos/{ORG_NAME}/{repo}/contents/{path}",
            "-H",
            "Accept: application/vnd.github+json",
        ],
        log_failure=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ""
    if not data or data.get("type") != "file" or not data.get("content"):
        return ""
    try:
        decoded = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""
    return decoded[:max_chars]


def linked_issue_context(repo: str, pr: dict[str, Any]) -> str:
    text = f"{pr.get('title', '')}\n{pr.get('body') or ''}"
    blocks = []
    for issue_number in sorted(referenced_issues(repo, text))[:3]:
        data = gh_json(
            [
                "issue",
                "view",
                str(issue_number),
                "-R",
                f"{ORG_NAME}/{repo}",
                "--json",
                "title,body,labels",
            ]
        )
        if not data:
            continue
        blocks.append(
            f"Issue #{issue_number}: {data.get('title', '')}\n"
            f"Labels: {', '.join(sorted(label.get('name', '') for label in data.get('labels', [])))}\n"
            f"{(data.get('body') or '')[:3000]}"
        )
    return "\n\n".join(blocks)


def repository_context(repo: str) -> str:
    sections = [
        ("README.md", fetch_text_file(repo, "README.md")),
        ("MEMACT.md", fetch_text_file(repo, "MEMACT.md")),
        ("CONTRIBUTING.md", fetch_text_file(repo, "CONTRIBUTING.md")),
    ]
    return "\n\n".join(
        f"## {name}\n{content}"
        for name, content in sections
        if content.strip()
    )


def sanitize_prompt_text(text: str) -> str:
    secret_words = ("token", "secret", "password", "api_key", "apikey", "authorization")
    lines = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if any(word in lowered for word in secret_words) and ("=" in line or ":" in line):
            lines.append("[redacted potential secret line]")
        else:
            lines.append(line)
    return "\n".join(lines)


class AIProvider:
    def review(self, prompt: str) -> dict[str, Any] | None:
        raise NotImplementedError


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.client = None

    def available(self) -> bool:
        if not self.api_key:
            return False
        if genai is None or genai_types is None:
            warning("google-genai is not installed; skipping AI review.")
            return False
        if self.client is None:
            self.client = genai.Client(api_key=self.api_key)
        return True

    def review(self, prompt: str) -> dict[str, Any] | None:
        if not self.available():
            return None
        models = []
        for model in [self.model, *AI_FALLBACK_MODELS]:
            if model and model not in models:
                models.append(model)

        for model in models:
            model_quota_exhausted = False
            for use_schema in (True, False):
                if model_quota_exhausted:
                    break
                for attempt in range(AI_RETRY_COUNT + 1):
                    try:
                        config_args = {
                            "temperature": 0.2,
                            "response_mime_type": "application/json",
                        }
                        if use_schema:
                            config_args["response_schema"] = AIReviewModel or AI_REVIEW_SCHEMA
                        response = self.client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=genai_types.GenerateContentConfig(**config_args),
                        )
                        parsed = getattr(response, "parsed", None)
                        if parsed is not None and hasattr(parsed, "model_dump"):
                            parsed_review = parse_ai_review_data(parsed.model_dump())
                            if parsed_review:
                                return parsed_review
                        parsed_review = parse_ai_review_response(response.text or "")
                        if parsed_review:
                            return parsed_review
                    except Exception as exc:
                        if is_ai_quota_error(exc):
                            info(
                                "AI provider quota or rate limit reached for model; trying next model "
                                f"(model={model}, schema={use_schema}, error={exc.__class__.__name__})."
                            )
                            model_quota_exhausted = True
                            break
                        transient = is_transient_ai_error(exc)
                        if not transient:
                            info(
                                "AI review provider attempt failed without retry "
                                f"(model={model}, schema={use_schema}, error={exc.__class__.__name__})."
                            )
                            break
                        if attempt >= AI_RETRY_COUNT:
                            info(
                                "AI review provider attempt failed "
                                f"(model={model}, schema={use_schema}, transient={transient}, "
                                f"error={exc.__class__.__name__})."
                            )
                            break
                        delay = retry_delay(attempt)
                        info(
                            "AI provider transient failure; retrying "
                            f"(model={model}, schema={use_schema}, attempt={attempt + 1}, "
                            f"delay={round(delay, 1)}s)."
                        )
                        time.sleep(delay)
        info("AI review skipped because all provider fallback attempts failed.")
        return None


def get_ai_provider() -> AIProvider | None:
    if not AI_ENABLED:
        return None
    if AI_PROVIDER != "gemini":
        warning(f"Unsupported AI provider '{AI_PROVIDER}'; skipping AI review.")
        return None
    return GeminiProvider(GEMINI_API_KEY, AI_MODEL)


def parse_ai_review_response(text: str) -> dict[str, Any] | None:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        warning("AI review returned malformed JSON; skipping AI comment.")
        return None
    return parse_ai_review_data(data)


def parse_ai_review_data(data: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        warning("AI review returned non-object JSON; skipping AI comment.")
        return None

    recommendation = data.get("recommendation")
    confidence = data.get("confidence")
    if recommendation not in {"PASS", "PASS_WITH_COMMENTS", "NEEDS_CHANGES"}:
        warning("AI review returned invalid recommendation; skipping AI comment.")
        return None
    if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
        warning("AI review returned invalid confidence; skipping AI comment.")
        return None
    for key in (
        "blocking",
        "architecture",
        "security",
        "performance",
        "maintainability",
        "style",
        "testing",
        "documentation",
        "suggestions",
    ):
        if not isinstance(data.get(key), list):
            data[key] = []
    data["summary"] = str(data.get("summary", "")).strip()
    return data


def ai_review_prompt(repo: str, pr: dict[str, Any], diff: str) -> str:
    labels = ", ".join(sorted(label_names(pr))) or "none"
    changed_files = "\n".join(f"- {path}" for path in pr_file_paths(pr)) or "unknown"
    diff_size = len(diff)
    diff_for_review = diff[:AI_MAX_DIFF_CHARS]
    truncated_diff = sanitize_prompt_text(diff_for_review)
    truncation_note = (
        f"Diff size: {diff_size} characters. Full diff included."
        if diff_size <= AI_MAX_DIFF_CHARS
        else (
            f"Diff size: {diff_size} characters. Included the first {AI_MAX_DIFF_CHARS} "
            "characters for quota and reliability control; review may miss omitted changes."
        )
    )

    return f"""
{MEMACT_AI_REVIEW_CONTEXT}

Return only JSON matching this schema:
{json.dumps(AI_REVIEW_SCHEMA, indent=2)}

Review this PR as a Memact engineering assistant. Do not provide generic advice
unless it is tied to the PR. Check whether the PR solves linked issues and
whether code belongs in this repository.

Repository: Memact/{repo}
PR: #{pr.get("number")}
Title: {pr.get("title", "")}
Author: {pr.get("author", {}).get("login", "")}
Labels: {labels}
Head commit: {pr_head_sha(pr)}

PR description:
{sanitize_prompt_text(pr.get("body") or "")}

Linked issue context:
{sanitize_prompt_text(linked_issue_context(repo, pr))}

Changed files:
{changed_files}

Repository-specific context:
{sanitize_prompt_text(repository_context(repo))}

Unified diff:
```diff
{truncated_diff}
```

{truncation_note}
""".strip()


def format_ai_review_comment(review: dict[str, Any], sha: str) -> str:
    def section(title: str, values: list[str]) -> list[str]:
        if not values:
            return []
        return [f"## {title}", *[f"- {item}" for item in values], ""]

    recommendation_labels = {
        "PASS": "Pass",
        "PASS_WITH_COMMENTS": "Pass with comments",
        "NEEDS_CHANGES": "Needs changes",
    }
    recommendation = review["recommendation"]

    lines = [
        "# AI Review",
        "",
        f"Reviewed commit: `{sha}`",
        "",
        "## Summary",
        review.get("summary") or "No summary returned.",
        "",
        f"## Confidence",
        f"{review.get('confidence')}%",
        "",
    ]
    lines.extend(section("Blocking", review["blocking"]))
    lines.extend(section("Architecture", review["architecture"]))
    lines.extend(section("Security", review["security"]))
    lines.extend(section("Performance", review["performance"]))
    lines.extend(section("Maintainability", review["maintainability"]))
    lines.extend(section("Style", review["style"]))
    lines.extend(section("Testing", review["testing"]))
    lines.extend(section("Documentation", review["documentation"]))
    lines.extend(section("Suggestions", review["suggestions"]))
    lines.extend(
        [
            "## Recommendation",
            f"{recommendation_labels.get(recommendation, recommendation)} (`{recommendation}`)",
            "",
            (
                "_AI review is advisory and may be inaccurate. Maintainers and GitHub "
                "protections remain authoritative. If this review looks wrong, please "
                "reply here and explain what should be reconsidered._"
            ),
        ]
    )
    return "\n".join(lines)


def ai_review_engine() -> None:
    CACHE.setdefault("ai_reviews", {})
    CACHE["stats"]["ai_reviewed"] = 0
    CACHE["stats"]["ai_skipped"] = 0
    if not should_run_ai_review_for_event():
        return

    provider = get_ai_provider()
    if provider is None:
        return

    ai_calls_attempted = 0
    for repo, prs in CACHE["prs"].items():
        if repo not in CACHE["repositories"]:
            continue
        for pr in prs:
            if pr.get("state", "").lower() != "open":
                continue
            if repo == CONTEXT_REPO and "dummy" in f"{pr.get('title', '')}\n{pr.get('body') or ''}".lower():
                CACHE["stats"]["ai_skipped"] += 1
                action(f"ai_review_skipped_dummy_tracking_pr repo={repo} pr=#{pr.get('number')}")
                continue
            if pr.get("isDraft") and not AI_REVIEW_DRAFT_PRS:
                CACHE["stats"]["ai_skipped"] += 1
                continue
            paths = pr_file_paths(pr)
            if not should_review_files_with_ai(paths):
                CACHE["stats"]["ai_skipped"] += 1
                continue
            sha = pr_head_sha(pr)
            if not sha:
                CACHE["stats"]["ai_skipped"] += 1
                continue
            pr_number = pr["number"]
            comments = fetch_pr_comments(repo, pr_number, refresh=True)
            if ai_review_exists_for_sha(comments, sha):
                CACHE["stats"]["ai_skipped"] += 1
                continue
            diff = fetch_pr_diff(repo, pr_number)
            if not diff.strip():
                CACHE["stats"]["ai_skipped"] += 1
                continue
            if ai_calls_attempted and AI_REQUEST_COOLDOWN_SECONDS > 0:
                info(f"Cooling down before next AI request ({AI_REQUEST_COOLDOWN_SECONDS}s).")
                time.sleep(AI_REQUEST_COOLDOWN_SECONDS)
            ai_calls_attempted += 1
            review = provider.review(ai_review_prompt(repo, pr, diff))
            if review is None:
                CACHE["stats"]["ai_skipped"] += 1
                continue
            CACHE["ai_reviews"][(repo, pr_number, sha)] = review
            if post_ai_review_comment(repo, pr_number, sha, format_ai_review_comment(review, sha)):
                CACHE["stats"]["ai_reviewed"] += 1
                action(f"ai_review_posted repo={repo} pr=#{pr_number} sha={sha[:12]}")


def ci_successful(pr: dict[str, Any]) -> bool:
    rollup = pr.get("statusCheckRollup")
    if not rollup:
        return False
    contexts = rollup if isinstance(rollup, list) else rollup.get("contexts", [])
    if not contexts:
        return False
    for context in contexts:
        state = str(context.get("state") or context.get("conclusion") or "").upper()
        if state not in {"SUCCESS", "SUCCESSFUL", "COMPLETED", "NEUTRAL", "SKIPPED"}:
            return False
    return True


def merge_requirements_met(pr: dict[str, Any], review: dict[str, Any] | None) -> tuple[bool, list[str]]:
    reasons = []
    if review is None:
        reasons.append("No AI review result for current commit.")
    else:
        if review.get("recommendation") != "PASS":
            reasons.append("AI recommendation is not PASS.")
        if int(review.get("confidence", 0)) < AI_MIN_CONFIDENCE:
            reasons.append("AI confidence is below threshold.")
        if review.get("blocking"):
            reasons.append("AI reported blocking issues.")
    if not ci_successful(pr):
        reasons.append("CI checks are not successful.")
    if pr.get("reviewDecision") not in {"APPROVED", ""}:
        reasons.append("Required review decision is not approved.")
    if str(pr.get("mergeable", "")).upper() not in {"MERGEABLE", "UNKNOWN"}:
        reasons.append("PR is not mergeable.")
    if str(pr.get("mergeStateStatus", "")).upper() not in {"CLEAN", "HAS_HOOKS", "UNKNOWN"}:
        reasons.append("Branch protection or repository rules are not satisfied.")
    return not reasons, reasons


def merge_pr(repo: str, pr_number: int) -> bool:
    method_flag = {
        "squash": "--squash",
        "merge": "--merge",
        "rebase": "--rebase",
    }.get(AI_MERGE_METHOD, "--squash")
    result = gh(["pr", "merge", str(pr_number), "-R", f"{ORG_NAME}/{repo}", method_flag, "--auto"], log_failure=False)
    if result.returncode != 0:
        warning("Automatic merge could not be enabled; GitHub protections remain authoritative.")
        return False
    return True


def ai_merge_engine() -> None:
    CACHE["stats"]["ai_merge_ready"] = 0
    CACHE["stats"]["ai_merge_blocked"] = 0
    CACHE["stats"]["ai_auto_merge_enabled"] = 0
    if not AI_ENABLED:
        return
    if not AI_AUTO_MERGE and not CACHE.get("ai_reviews"):
        return
    for repo, prs in CACHE["prs"].items():
        if repo not in CACHE["repositories"]:
            continue
        for pr in prs:
            if pr.get("state", "").lower() != "open":
                continue
            sha = pr_head_sha(pr)
            review = CACHE.get("ai_reviews", {}).get((repo, pr["number"], sha))
            ready, reasons = merge_requirements_met(pr, review)
            if ready:
                CACHE["stats"]["ai_merge_ready"] += 1
                if AI_AUTO_MERGE and merge_pr(repo, pr["number"]):
                    CACHE["stats"]["ai_auto_merge_enabled"] += 1
            else:
                CACHE["stats"]["ai_merge_blocked"] += 1


def code_quality_engine() -> None:
    flagged = 0
    cleaned = 0
    for repo, prs in CACHE["prs"].items():
        if repo not in CACHE["repositories"]:
            continue
        for pr in prs:
            if pr.get("state", "").lower() != "open":
                continue
            labels = label_names(pr)
            pr_number = pr["number"]
            findings = analyze_diff(fetch_pr_diff(repo, pr_number))
            if not findings:
                if "Quality: Needs Polish" in labels:
                    edit_labels("pr", repo, pr_number, remove=["Quality: Needs Polish"])
                    cleaned += 1
                continue
            edit_labels("pr", repo, pr_number, add=["Quality: Needs Polish"])
            update_or_post_pr_comment(repo, pr_number, MARKERS["quality"], quality_comment(findings))
            flagged += 1
    CACHE["stats"]["quality_flagged"] = flagged
    CACHE["stats"]["quality_cleaned"] = cleaned


def issue_resolved_by_pr(repo: str, issue_number: int) -> dict[str, Any] | None:
    pattern = issue_reference_pattern(repo, issue_number, closing_keyword=True)
    for pr in CACHE["merged_prs"].get(repo, []):
        text = f"{pr.get('title', '')}\n{pr.get('body') or ''}"
        if pattern.search(text):
            return pr
    return None


def autoclose_engine() -> None:
    closed = 0
    if not AUTOCLOSE_ENABLED:
        CACHE["stats"]["issues_closed"] = closed
        return
    for repo, issues in CACHE["issues"].items():
        for issue in issues:
            merged = issue_resolved_by_pr(repo, issue["number"])
            if not merged:
                continue
            result = gh(
                [
                    "issue",
                    "close",
                    str(issue["number"]),
                    "-R",
                    f"{ORG_NAME}/{repo}",
                    "-c",
                    f"Automatically closed because PR #{merged['number']} has been merged.",
                ]
            )
            if result.returncode == 0:
                closed += 1
    CACHE["stats"]["issues_closed"] = closed


def print_summary() -> None:
    print()
    print("=" * 70)
    info("Automation summary")
    print("=" * 70)
    for key in [
        "issues",
        "prs",
        "issue_labels_added",
        "assigned",
        "assignment_skipped_already_assigned",
        "assignment_skipped_limit",
        "assignment_skipped_race",
        "unassigned",
        "stale_detected",
        "stale_warnings_posted",
        "prs_labeled",
        "pr_label_comments_posted",
        "dummy_found",
        "dummy_missing",
        "dummy_success_comments_posted",
        "dummy_warning_comments_posted",
        "quality_flagged",
        "quality_cleaned",
        "ai_reviewed",
        "ai_skipped",
        "ai_merge_ready",
        "ai_merge_blocked",
        "ai_auto_merge_enabled",
        "comments_suppressed_existing",
        "labels_suppressed_existing",
        "labels_suppressed_absent",
        "mutations_suppressed_in_run",
        "ai_reviews_suppressed_existing_sha",
        "issues_closed",
    ]:
        print(f"{key:24}: {CACHE['stats'].get(key, 0)}")
    print("=" * 70)


def main() -> None:
    start = time.time()
    initialize()
    fetch_repositories()
    if not CACHE["repositories"]:
        warning("No repositories selected for automation.")
        return

    fetch_all_issues()
    fetch_all_pull_requests()
    build_assignment_index()
    build_intent_index()

    label_issue_engine()
    unassignment_engine()
    assignment_engine()
    stale_assignment_engine()
    pr_label_engine()
    dummy_pr_engine()
    code_quality_engine()
    ai_review_engine()
    ai_merge_engine()
    autoclose_engine()

    print_summary()
    success(f"Completed in {round(time.time() - start, 2)} seconds.")


if __name__ == "__main__":
    main()

import json
import subprocess
import re
import os
import sys

# Reconfigure stdout/stderr to use UTF-8 encoding to prevent UnicodeEncodeError on emojis
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Fallback print wrapper to avoid any UnicodeEncodeError in case output redirection limits encoding
_orig_print = print
def print(*args, **kwargs):
    encoding = sys.stdout.encoding or 'utf-8'
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg.encode(encoding, errors='replace').decode(encoding))
        else:
            new_args.append(arg)
    _orig_print(*new_args, **kwargs)

# Fetch current authenticated user name
current_user = ""
try:
    res_user = subprocess.run("gh api user --jq .login", shell=True, capture_output=True, text=True, encoding='utf-8')
    if res_user.returncode == 0 and res_user.stdout:
        current_user = res_user.stdout.strip().lower()
except Exception:
    pass

# 1. Fetch all repositories
cmd_repos = 'gh repo list Memact --limit 100 --json name'
res_repos = subprocess.run(cmd_repos, shell=True, capture_output=True, text=True, encoding='utf-8')
repos = []
if res_repos.returncode == 0 and res_repos.stdout:
    repos_data = json.loads(res_repos.stdout)
    # Exclude Website and oldWebsite from automation per guidelines
    repos = [r["name"] for r in repos_data if r["name"] not in ["Website", "oldWebsite"]]

# Pre-scan repositories to count current active open assignments per user
active_assignments = {}
print("Pre-scanning repositories to count active open assignments per contributor...")
for repo in repos:
    try:
        cmd_issues = f'gh issue list -R Memact/{repo} --state open --limit 100 --json assignees'
        res_issues = subprocess.run(cmd_issues, shell=True, capture_output=True, text=True, encoding='utf-8')
        if res_issues.returncode == 0 and res_issues.stdout:
            issues_data = json.loads(res_issues.stdout)
            for issue in issues_data:
                for a in issue.get("assignees", []):
                    login_lower = a["login"].lower()
                    active_assignments[login_lower] = active_assignments.get(login_lower, 0) + 1
        else:
            print(f"Error: Pre-scan of Memact/{repo} failed with returncode {res_issues.returncode}: {res_issues.stderr.strip() if res_issues.stderr else ''}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error during pre-scan of Memact/{repo}: {e}")

print(f"Current active assignments: {active_assignments}")


print(f"Scanning {len(repos)} repositories for issue workflow automation...")

temp_body_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_update_body.md")
requests_to_process = []

for repo in repos:
    try:
        # Fetch open issues with author, assignees, creation time, and comments
        cmd = f'gh issue list -R Memact/{repo} --state open --limit 100 --json number,title,url,assignees,author,body,labels,createdAt,comments'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        if res.returncode != 0 or not res.stdout:
            continue
            
        issues = json.loads(res.stdout)
        for issue in issues:
            num = issue["number"]
            title = issue["title"]
            body = issue.get("body", "")
            assignees = [a["login"] for a in issue["assignees"]]
            creator = issue["author"]["login"] if issue.get("author") else ""
            labels = [l["name"] for l in issue.get("labels", [])]
            
            print(f"\nProcessing Memact/{repo}#{num}: '{title}'")
            
            # --- 1. Labeling Automation (Interpret difficulty and assign labels) ---
            title_lower = title.lower()
            body_lower = body.lower() if body else ""
            
            # Parse difficulty
            difficulty = None
            if re.search(r'\b[\[\(]?easy[\]\)]?\b', title_lower) or re.search(r'\b[\[\(]?easy[\]\)]?\b', body_lower):
                difficulty = "Easy"
            elif re.search(r'\b[\[\(]?medium[\]\)]?\b', title_lower) or re.search(r'\b[\[\(]?medium[\]\)]?\b', body_lower):
                difficulty = "Medium"
            elif re.search(r'\b[\[\(]?hard[\]\)]?\b', title_lower) or re.search(r'\b[\[\(]?hard[\]\)]?\b', body_lower):
                difficulty = "Hard"
                
            labels_to_add = []
            if "SSoC26" not in labels:
                labels_to_add.append("SSoC26")
            if difficulty and difficulty not in labels:
                labels_to_add.append(difficulty)
                
            if labels_to_add:
                label_str = ",".join(labels_to_add)
                cmd_label = f'gh issue edit {num} -R Memact/{repo} --add-label "{label_str}"'
                res_label = subprocess.run(cmd_label, shell=True, capture_output=True, text=True, encoding='utf-8')
                if res_label.returncode != 0:
                    # If labeling failed, try creating the labels on this repo and retry
                    label_colors = {"SSoC26": "ededed", "Easy": "008672", "Medium": "d1b100", "Hard": "e11d21"}
                    for lbl in labels_to_add:
                        col = label_colors.get(lbl, "ededed")
                        res_create = subprocess.run(f'gh label create "{lbl}" -R Memact/{repo} --color "{col}"', shell=True, capture_output=True, text=True, encoding='utf-8')
                        if res_create.returncode != 0 and "already exists" not in res_create.stderr.lower():
                            print(f"    -> Warning: Failed to create label '{lbl}': {res_create.stderr.strip()}")
                    # Retry edit
                    res_label = subprocess.run(cmd_label, shell=True, capture_output=True, text=True, encoding='utf-8')
                
                if res_label.returncode == 0:
                    print(f"  -> Added labels: {label_str}")
                else:
                    print(f"  -> Failed to add labels: {res_label.stderr.strip()}")
            
            # --- 2. Non-Context Repo Notice Automation (Dummy PR check & inject) ---
            if repo.lower() != "context":
                if "dummy pr" not in body_lower or "memact/context" not in body_lower:
                    notice = f"\n\n---\n**SSoC26 Contributor Notice:**\n\nSince this repository (`Memact/{repo}`) is outside the main `Context` repository, and the registered project for tracking contributions is specifically **Context** (`Memact/Context`), please make sure to **create a dummy PR in the Context repository** linking to your actual PR or commits in this repository. This is required for your contribution to be correctly tracked and counted.\n\nIf you have already created a dummy PR in `Memact/Context` linking to your work here, please ignore this message!"
                    new_body = (body or "") + notice
                    try:
                        with open(temp_body_path, "w", encoding="utf-8") as f_body:
                            f_body.write(new_body)
                        cmd_update_body = f'gh issue edit {num} -R Memact/{repo} -F "{temp_body_path}"'
                        res_body = subprocess.run(cmd_update_body, shell=True, capture_output=True, text=True, encoding='utf-8')
                        if res_body.returncode == 0:
                            print(f"  -> Successfully injected dummy PR notice into issue body.")
                            # Update local reference to prevent double checks
                            body = new_body
                            body_lower = new_body.lower()
                        else:
                            print(f"  -> Failed to inject dummy PR notice: {res_body.stderr.strip()}")
                    except Exception as ex:
                        print(f"  -> Error updating body: {ex}")
            
            # --- 2.5 Unassignment Automation ---
            if assignees:
                res_comment_data = issue.get("comments", [])
                if res_comment_data:
                    res_comment_data.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
                    
                    negative_keywords = [
                        "un-assign", "unassign", "remove me", "wrong issue",
                        "not familiar", "picked the wrong", "can you un",
                        "please un", "don't assign", "do not assign",
                        "not interested", "withdraw", "stepping down",
                        "stepping away", "no longer"
                    ]
                    
                    for assignee in list(assignees):
                        assignee_comments = [c for c in res_comment_data if c.get("author", {}).get("login", "") == assignee]
                        if assignee_comments:
                            latest_comment = assignee_comments[0].get("body", "").lower()
                            if any(nk in latest_comment for nk in negative_keywords):
                                print(f"  -> Assignee @{assignee} requested unassignment.")
                                cmd_unassign = f'gh issue edit {num} -R Memact/{repo} --remove-assignee {assignee}'
                                res_unassign = subprocess.run(cmd_unassign, shell=True, capture_output=True, text=True, encoding='utf-8')
                                if res_unassign.returncode == 0:
                                    body_msg = f"Okay @{assignee}, I have unassigned you from this issue."
                                    cmd_msg = f'gh issue comment {num} -R Memact/{repo} -b "{body_msg}"'
                                    subprocess.run(cmd_msg, shell=True)
                                    assignees.remove(assignee)
                                    if assignee.lower() in active_assignments:
                                        active_assignments[assignee.lower()] = max(0, active_assignments[assignee.lower()] - 1)

            # --- 3. Assignment Automation (Collect requests chronologically) ---
            if not assignees:
                res_comment_data = issue.get("comments", [])

                # Rule 1: If created by a community contributor, creator request is at issue creation time
                if creator and creator.lower() not in ["keepsloading", "github-actions", "memact"]:
                    requests_to_process.append({
                        "timestamp": issue.get("createdAt", ""),
                        "repo": repo,
                        "num": num,
                        "user": creator,
                        "is_creator": True,
                        "comment_body": "Issue creation",
                        "comments_list": res_comment_data
                    })
                    print(f"  -> Collected creator request from @{creator} (timestamp: {issue.get('createdAt', '')})")
                else:
                    # Rule 2: If created by keepsloading, check comments chronologically for requests
                    if res_comment_data:
                        for c in res_comment_data:
                            author = c.get("author", {}).get("login", "")
                            body_comment = c.get("body", "")
                            if not author or author.lower() in ["keepsloading", "github-actions", "memact"]:
                                continue
                                
                            body_comment_lower = body_comment.lower()

                            # Skip comments that express intent to withdraw or unassign
                            negative_keywords = [
                                "un-assign", "unassign", "remove me", "wrong issue",
                                "not familiar", "picked the wrong", "can you un",
                                "please un", "don't assign", "do not assign",
                                "not interested", "withdraw", "stepping down",
                                "stepping away", "no longer"
                            ]
                            if any(nk in body_comment_lower for nk in negative_keywords):
                                continue

                            # Only match comments that clearly express intent to work on the issue
                            def is_request(body):
                                # 1. Direct commands
                                if body.startswith("/assign") or body.startswith("assign"):
                                    return True
                                # 2. "assign" and "me" or "to me"
                                if "assign" in body and ("me" in body or "to me" in body):
                                    return True
                                # 3. "work" and common intent verbs/phrases
                                if "work" in body and any(w in body for w in ["like to", "want to", "d like", "let me", "can i", "interested", "happy to", "take"]):
                                    return True
                                # 4. "claim" or "take" action phrases
                                if "claim" in body or ("take" in body and any(t in body for t in ["up", "this", "it"])):
                                    return True
                                # 5. "contribute"
                                if "contribute" in body:
                                    return True
                                return False

                            if is_request(body_comment_lower):
                                requests_to_process.append({
                                    "timestamp": c.get("createdAt", ""),
                                    "repo": repo,
                                    "num": num,
                                    "user": author,
                                    "is_creator": False,
                                    "comment_body": body_comment,
                                    "comments_list": res_comment_data
                                })
                                print(f"  -> Collected commenter request from @{author} (timestamp: {c.get('createdAt', '')})")

    except Exception as e:
        print(f"Error processing Memact/{repo}: {e}")

# --- 4. Global Chronological Assignment ---
print(f"\nProcessing {len(requests_to_process)} collected requests globally by timestamp...")
requests_to_process.sort(key=lambda x: x["timestamp"])

assigned_issues = set()
skeptical_list = ["prasiddhi-105", "codesparks45", "prassidhi", "prasiddhi", "codesparks"]

for req in requests_to_process:
    repo = req["repo"]
    num = req["num"]
    user = req["user"]
    is_creator = req["is_creator"]
    timestamp = req["timestamp"]
    comments_list = req["comments_list"]
    
    issue_key = f"{repo}#{num}"
    if issue_key in assigned_issues:
        continue
        
    limit = 1 if user.lower() in skeptical_list else 2
    active_count = active_assignments.get(user.lower(), 0)
    
    def already_notified(user_login, res_comment_data):
        bot_logins = ["keepsloading", "github-actions", "memact"]
        if current_user:
            bot_logins.append(current_user)
        for c in res_comment_data:
            author_login = c.get("author", {}).get("login", "").lower()
            body_c = c.get("body", "")
            if (author_login in bot_logins and 
                    f"@{user_login.lower()}" in body_c.lower() and 
                    "active assignment" in body_c.lower() and
                    "limit" in body_c.lower()):
                return True
        return False

    if active_count >= limit:
        print(f"Skipping assignment of {issue_key} to @{user} (already has {active_count} active assignments, limit is {limit}).")
        if not already_notified(user, comments_list):
            if is_creator:
                body_msg = (
                    f"Hi @{user} 👋 You created this issue and are eligible for automatic assignment. "
                    f"However, you currently have {active_count} active assignment(s) (limit is {limit}). "
                    "Please finish your open assignments and submit PRs or request unassignment "
                    "before requesting a new task. Thank you!"
                )
            else:
                body_msg = (
                    f"Hi @{user} 👋 You requested to be assigned to this issue. "
                    f"However, you currently have {active_count} active assignment(s) (limit is {limit}). "
                    "Please finish your open assignments and submit PRs or request unassignment "
                    "before requesting a new task. Thank you!"
                )
            cmd_msg = f'gh issue comment {num} -R Memact/{repo} -b "{body_msg}"'
            subprocess.run(cmd_msg, shell=True, capture_output=True, text=True, encoding='utf-8')
            print(f"  -> Posted active limit comment for @{user} on {issue_key}.")
            # Add a mock comment to comments_list locally to prevent duplicate notices on the same run if they commented multiple times
            comments_list.append({
                "author": {"login": current_user or "keepsloading"},
                "body": body_msg
            })
    else:
        # Assign using PATCH API
        cmd_assign = f'gh api repos/Memact/{repo}/issues/{num} -X PATCH -F "assignees[]={user}"'
        res_assign = subprocess.run(cmd_assign, shell=True, capture_output=True, text=True, encoding='utf-8')
        if res_assign.returncode == 0:
            print(f"[SUCCESS] Assigned {issue_key} to @{user} (requested at {timestamp})")
            active_assignments[user.lower()] = active_count + 1
            assigned_issues.add(issue_key)
            # Comment on the issue notifying them
            if is_creator:
                body_msg = f"Hey @{user} 👋 Since you created this issue, you've been auto-assigned to it as part of SSoC26! Looking forward to your PR. Feel free to ask questions if you get stuck. Good luck!"
            else:
                body_msg = f"Hey @{user} 👋 You've been assigned this issue as part of SSoC26! Looking forward to your PR. Feel free to ask questions if you get stuck. Good luck!"
            cmd_msg = f'gh issue comment {num} -R Memact/{repo} -b "{body_msg}"'
            subprocess.run(cmd_msg, shell=True, capture_output=True, text=True, encoding='utf-8')
        else:
            print(f"[FAILED] Could not assign {issue_key} to @{user}: {res_assign.stderr.strip()}")

# Clean up temp file
if os.path.exists(temp_body_path):
    try:
        os.remove(temp_body_path)
    except Exception:
        pass

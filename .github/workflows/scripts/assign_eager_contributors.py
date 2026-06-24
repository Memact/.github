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

# 1. Fetch all repositories
cmd_repos = 'gh repo list Memact --limit 100 --json name'
res_repos = subprocess.run(cmd_repos, shell=True, capture_output=True, text=True, encoding='utf-8')
repos = []
if res_repos.returncode == 0 and res_repos.stdout:
    repos_data = json.loads(res_repos.stdout)
    repos = [r["name"] for r in repos_data]

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
    except Exception as e:
        print(f"Error during pre-scan of Memact/{repo}: {e}")

print(f"Current active assignments: {active_assignments}")


print(f"Scanning {len(repos)} repositories for issue workflow automation...")

temp_body_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_update_body.md")

for repo in repos:
    try:
        # Fetch open issues with author and assignees
        cmd = f'gh issue list -R Memact/{repo} --state open --limit 100 --json number,title,url,assignees,author,body,labels'
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
            
            # --- 3. Assignment Automation (Chronological checking & assignment) ---
            if not assignees:
                target_assignee = None
                
                # Rule 1: If created by a community contributor, assign it to them
                if creator and creator.lower() not in ["keepsloading", "github-actions", "memact"]:
                    if creator.lower() in ["prasiddhi-105", "archita-29"]:
                        print(f"  -> Skipping creator assignment to @{creator} (prasiddhi/archita blocklist).")
                    elif active_assignments.get(creator.lower(), 0) >= 2:
                        print(f"  -> Skipping creator assignment to @{creator} (already has {active_assignments[creator.lower()]} active assignments).")
                    else:
                        target_assignee = creator
                        print(f"  -> Created by contributor. Target assignee: @{target_assignee}")
                else:
                    # Rule 2: If created by keepsloading, check comments chronologically for requests
                    cmd_comments = f'gh issue view {num} -R Memact/{repo} --json comments'
                    res_comments = subprocess.run(cmd_comments, shell=True, capture_output=True, text=True, encoding='utf-8')
                    if res_comments.returncode == 0 and res_comments.stdout:
                        res_comment_data = json.loads(res_comments.stdout).get("comments", [])
                    else:
                        res_comment_data = []
                    
                    if res_comment_data:
                        # Sort comments by creation time to find the first requester
                        res_comment_data.sort(key=lambda x: x.get("createdAt", ""))
                        for c in res_comment_data:
                            author = c.get("author", {}).get("login", "")
                            body_comment = c.get("body", "")
                            if not author or author.lower() in ["keepsloading", "github-actions", "memact"]:
                                continue
                                
                            body_comment_lower = body_comment.lower()
                            request_keywords = ["assign", "work on", "claim", "take this up", "contribution", "have a crack"]
                            if any(kw in body_comment_lower for kw in request_keywords):
                                if author.lower() in ["prasiddhi-105", "archita-29"]:
                                    print(f"  -> Skipping commenter @{author} (prasiddhi/archita blocklist).")
                                    continue
                                if active_assignments.get(author.lower(), 0) >= 2:
                                    print(f"  -> Skipping commenter @{author} (already has {active_assignments[author.lower()]} active assignments).")
                                    continue
                                target_assignee = author
                                print(f"  -> First requester in comments: @{target_assignee}")
                                print(f"     Comment: \"{body_comment.strip()[:100]}...\"")
                                break
                                
                if target_assignee:
                    # Apply assignment using the working PATCH API
                    cmd_assign = f'gh api repos/Memact/{repo}/issues/{num} -X PATCH -F "assignees[]={target_assignee}"'
                    res_assign = subprocess.run(cmd_assign, shell=True, capture_output=True, text=True, encoding='utf-8')
                    if res_assign.returncode == 0:
                        print(f"  [SUCCESS] Assigned Memact/{repo}#{num} to @{target_assignee}")
                        active_assignments[target_assignee.lower()] = active_assignments.get(target_assignee.lower(), 0) + 1
                        # Comment on the issue notifying them
                        body_msg = f"Hey @{target_assignee} 👋 You've been assigned this issue as part of SSoC26! Looking forward to your PR. Feel free to ask questions if you get stuck. Good luck!"
                        cmd_msg = f'gh issue comment {num} -R Memact/{repo} -b "{body_msg}"'
                        subprocess.run(cmd_msg, shell=True, capture_output=True, text=True, encoding='utf-8')
                    else:
                        print(f"  [FAILED] Could not assign to @{target_assignee}: {res_assign.stderr.strip()}")
            
    except Exception as e:
        print(f"Error processing Memact/{repo}: {e}")

# Clean up temp file
if os.path.exists(temp_body_path):
    try:
        os.remove(temp_body_path)
    except Exception:
        pass

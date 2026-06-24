import json
import subprocess
import re
import sys
import os

# Reconfigure stdout/stderr for UTF-8
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Core active repositories in the spine
repos = ["Context", "Website", "Access", "Memory", "Contracts", "SDK", "Notebook", "Fitent", ".github"]

# Exact allowed case-sensitive labels
ALLOWED_DIFFICULTIES = ["Easy", "Medium", "Hard"]
CORRECT_LABELS = {
    "easy": "Easy", "medium": "Medium", "hard": "Hard",
    "ssoc26": "SSoC26"
}
LABEL_COLORS = {
    "SSoC26": "ededed",
    "Easy": "008672",
    "Medium": "d1b100",
    "Hard": "e11d21"
}

print("=== STARTING PR AND ISSUE LABEL ALIGNMENT ROUTINE ===")

def fix_label_typos(repo, item_num, current_labels, item_type="issue"):
    """
    Checks for typos (wrong casing) in current labels, removes incorrect ones, 
    and applies correct title-cased labels.
    """
    labels_to_remove = []
    labels_to_add = []
    
    for lbl in current_labels:
        lbl_lower = lbl.lower()
        if lbl_lower in CORRECT_LABELS:
            correct_name = CORRECT_LABELS[lbl_lower]
            if lbl != correct_name:
                labels_to_remove.append(lbl)
                labels_to_add.append(correct_name)
    
    # Remove wrong labels
    for lbl in labels_to_remove:
        print(f"  -> Typos detected in {item_type} #{item_num}: '{lbl}' should be '{CORRECT_LABELS[lbl.lower()]}'")
        cmd_remove = f'gh {item_type} edit {item_num} -R Memact/{repo} --remove-label "{lbl}"'
        subprocess.run(cmd_remove, shell=True, capture_output=True)
        
    # Add corrected labels
    if labels_to_add:
        # Preemptively create correct labels if they don't exist
        for lbl in labels_to_add:
            col = LABEL_COLORS.get(lbl, "ededed")
            subprocess.run(f'gh label create "{lbl}" -R Memact/{repo} --color "{col}"', shell=True, capture_output=True)
            
        label_str = ",".join(labels_to_add)
        cmd_add = f'gh {item_type} edit {item_num} -R Memact/{repo} --add-label "{label_str}"'
        res_add = subprocess.run(cmd_add, shell=True, capture_output=True, text=True, encoding='utf-8')
        if res_add.returncode == 0:
            print(f"  -> Typo labels corrected on {item_type} #{item_num}: {label_str}")
        else:
            print(f"  -> Failed to correct labels: {res_add.stderr.strip()}")

def post_github_comment(repo, pr_num, body_msg):
    """
    Safely post a comment to a PR/issue using a temporary file to avoid shell truncation issues on Windows.
    """
    try:
        temp_comment_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_comment_{repo}_{pr_num}.md")
        with open(temp_comment_path, "w", encoding="utf-8") as f:
            f.write(body_msg)
            
        cmd_comment = f'gh pr comment {pr_num} -R Memact/{repo} -F "{temp_comment_path}"'
        subprocess.run(cmd_comment, shell=True, capture_output=True)
        
        # Clean up
        if os.path.exists(temp_comment_path):
            os.remove(temp_comment_path)
    except Exception as e:
        print(f"Error posting comment to PR #{pr_num}: {e}")


# Fetch all Context PRs (open and closed) to match dummy PRs
context_prs = []
print("Fetching all PRs from Memact/Context to match dummy PRs...")
cmd_context_prs = 'gh pr list -R Memact/Context --state all --limit 150 --json number,title,body,author,labels,url'
res_context_prs = subprocess.run(cmd_context_prs, shell=True, capture_output=True, text=True, encoding='utf-8')
if res_context_prs.returncode == 0 and res_context_prs.stdout:
    context_prs = json.loads(res_context_prs.stdout)
    print(f"Loaded {len(context_prs)} Context PRs for dummy PR matching.")
else:
    print(f"Warning: Failed to fetch Context PRs: {res_context_prs.stderr}")

for repo in repos:
    try:
        print(f"\nProcessing Memact/{repo}...")
        
        # 1. Fetch all open issues in the repo
        cmd_issues = f'gh issue list -R Memact/{repo} --state open --limit 100 --json number,title,labels'
        res_issues = subprocess.run(cmd_issues, shell=True, capture_output=True, text=True, encoding='utf-8')
        issues_dict = {}
        if res_issues.returncode == 0 and res_issues.stdout:
            issues = json.loads(res_issues.stdout)
            for issue in issues:
                num = issue["number"]
                labels = [l["name"] for l in issue.get("labels", [])]
                issues_dict[num] = labels
                # Check for typos on issue labels
                fix_label_typos(repo, num, labels, item_type="issue")
        
        # 2. Fetch all open PRs in the repo
        cmd_prs = f'gh pr list -R Memact/{repo} --state open --limit 100 --json number,title,body,labels,author'
        res_prs = subprocess.run(cmd_prs, shell=True, capture_output=True, text=True, encoding='utf-8')
        if res_prs.returncode == 0 and res_prs.stdout:
            prs = json.loads(res_prs.stdout)
            for pr in prs:
                pr_num = pr["number"]
                pr_title = pr["title"]
                pr_body = pr.get("body", "") or ""
                pr_labels = [l["name"] for l in pr.get("labels", [])]
                
                print(f"  Evaluating PR #{pr_num}: '{pr_title}'")
                
                # Check for typos on current PR labels
                fix_label_typos(repo, pr_num, pr_labels, item_type="pr")
                
                # Parse references to issues in the PR body or title
                # Look for formats like: #52, closes #52, fixes #52, resolve #52, etc.
                combined_text = f"{pr_title} \n {pr_body}"
                issue_refs = re.findall(r'(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)?\s*#(\d+)', combined_text, re.IGNORECASE)
                # Deduplicate and convert to integers
                referenced_issues = list(set(int(num) for num in issue_refs))
                
                labels_to_apply = []
                if referenced_issues:
                    print(f"    Linked issue references found: {referenced_issues}")
                    
                    # Gather labels from linked issues
                    linked_labels = []
                    for issue_num in referenced_issues:
                        if issue_num in issues_dict:
                            linked_labels.extend(issues_dict[issue_num])
                        else:
                            # If the issue is closed or not in open list, fetch its details directly
                            cmd_view = f'gh issue view {issue_num} -R Memact/{repo} --json labels'
                            res_view = subprocess.run(cmd_view, shell=True, capture_output=True, text=True, encoding='utf-8')
                            if res_view.returncode == 0 and res_view.stdout:
                                view_data = json.loads(res_view.stdout)
                                linked_labels.extend([l["name"] for l in view_data.get("labels", [])])
                    
                    # Extract difficulty labels and SSoC26 tags
                    for lbl in linked_labels:
                        lbl_lower = lbl.lower()
                        if lbl_lower == "ssoc26" and "SSoC26" not in pr_labels:
                            labels_to_apply.append("SSoC26")
                        elif lbl in ALLOWED_DIFFICULTIES and lbl not in pr_labels:
                            labels_to_apply.append(lbl)
                        elif lbl_lower in CORRECT_LABELS and CORRECT_LABELS[lbl_lower] not in pr_labels:
                            labels_to_apply.append(CORRECT_LABELS[lbl_lower])
                            
                    # Apply matching SSoC26 and difficulty labels to the PR
                    if labels_to_apply:
                        labels_to_apply = list(set(labels_to_apply))
                        
                        # Preemptively create correct labels if they don't exist on this repo
                        for lbl in labels_to_apply:
                            col = LABEL_COLORS.get(lbl, "ededed")
                            subprocess.run(f'gh label create "{lbl}" -R Memact/{repo} --color "{col}"', shell=True, capture_output=True)
                            
                        label_str = ",".join(labels_to_apply)
                        cmd_pr_label = f'gh pr edit {pr_num} -R Memact/{repo} --add-label "{label_str}"'
                        res_pr_label = subprocess.run(cmd_pr_label, shell=True, capture_output=True, text=True, encoding='utf-8')
                        
                        if res_pr_label.returncode == 0:
                            print(f"    [SUCCESS] Labeled PR #{pr_num} with: {label_str}")
                            # Post engagement comment
                            body_msg = f"**SSoC26 Labeling:** This Pull Request has been automatically linked to the corresponding issue labels: `{label_str}`! Thank you for contributing!"
                            post_github_comment(repo, pr_num, body_msg)
                        else:
                            print(f"    [FAILED] Could not label PR #{pr_num}: {res_pr_label.stderr.strip()}")
                else:
                    # If no issues are linked, we still check if we can add SSoC26 if the PR title mentions it
                    if "ssoc" in pr_title.lower() and "SSoC26" not in pr_labels:
                        # Create label if missing
                        subprocess.run(f'gh label create "SSoC26" -R Memact/{repo} --color "ededed"', shell=True, capture_output=True)
                        cmd_pr_label = f'gh pr edit {pr_num} -R Memact/{repo} --add-label "SSoC26"'
                        subprocess.run(cmd_pr_label, shell=True, capture_output=True)
                        print(f"    [SUCCESS] Added SSoC26 label to PR #{pr_num} based on title reference.")
                        labels_to_apply.append("SSoC26")
                
                # --- Dummy PR Automation Check ---
                if repo not in ["Context", ".github"]:
                    pr_author = pr.get("author", {}).get("login", "")
                    print(f"    Checking dummy PR requirement for author @{pr_author}...")
                    
                    # Fetch comments on the actual PR to check if we already commented
                    cmd_comments = f'gh pr view {pr_num} -R Memact/{repo} --json comments'
                    res_comments = subprocess.run(cmd_comments, shell=True, capture_output=True, text=True, encoding='utf-8')
                    comments = []
                    if res_comments.returncode == 0 and res_comments.stdout:
                        comments = json.loads(res_comments.stdout).get("comments", [])
                    comment_bodies = [c["body"] for c in comments]
                    
                    # Identify dummy PR
                    dummy_pr = None
                    for c_pr in context_prs:
                        c_author = c_pr.get("author", {}).get("login", "")
                        if c_author and c_author.lower() == pr_author.lower():
                            c_title = c_pr.get("title", "") or ""
                            c_body = c_pr.get("body", "") or ""
                            c_combined = f"{c_title} \n {c_body}".lower()
                            
                            # Check for references to the sub-repo and PR/issue number
                            ref_pattern = rf'(?:memact/)?{repo.lower()}#{pr_num}\b'
                            url_pattern = rf'github\.com/memact/{repo.lower()}/pull/{pr_num}\b'
                            repo_pat = re.escape(repo.lower())
                            robust_pattern = rf'{repo_pat}\s*(?:pr|issue|pull)?\s*#?\s*{pr_num}\b'
                            
                            matches_ref = False
                            if re.search(ref_pattern, c_combined) or re.search(url_pattern, c_combined) or re.search(robust_pattern, c_combined):
                                matches_ref = True
                            else:
                                for issue_num in referenced_issues:
                                    issue_ref_pattern = rf'(?:memact/)?{repo.lower()}#{issue_num}\b'
                                    robust_issue_pattern = rf'{repo_pat}\s*(?:pr|issue|pull)?\s*#?\s*{issue_num}\b'
                                    if re.search(issue_ref_pattern, c_combined) or re.search(robust_issue_pattern, c_combined):
                                        matches_ref = True
                                        break
                                        
                            if matches_ref or (repo.lower() in c_combined and f"#{pr_num}" in c_combined):
                                dummy_pr = c_pr
                                break
                                
                    # Determine SSoC26 & difficulty labels to apply to the dummy PR
                    labels_to_add_dummy = []
                    for lbl in list(set(pr_labels + labels_to_apply)):
                        if lbl == "SSoC26" or lbl in ALLOWED_DIFFICULTIES:
                            labels_to_add_dummy.append(lbl)
                    if "SSoC26" not in labels_to_add_dummy:
                        labels_to_add_dummy.append("SSoC26")
                        
                    if dummy_pr:
                        dummy_num = dummy_pr["number"]
                        print(f"    [FOUND] Corresponding dummy PR: Memact/Context#{dummy_num}")
                        
                        # Apply labels to the dummy PR
                        c_pr_labels = [l["name"] for l in dummy_pr.get("labels", [])]
                        fix_label_typos("Context", dummy_num, c_pr_labels, item_type="pr")
                        labels_to_add_to_dummy = [l for l in labels_to_add_dummy if l not in c_pr_labels]
                        
                        if labels_to_add_to_dummy:
                            for lbl in labels_to_add_to_dummy:
                                col = LABEL_COLORS.get(lbl, "ededed")
                                subprocess.run(f'gh label create "{lbl}" -R Memact/Context --color "{col}"', shell=True, capture_output=True)
                                
                            label_str = ",".join(labels_to_add_to_dummy)
                            cmd_dummy_label = f'gh pr edit {dummy_num} -R Memact/Context --add-label "{label_str}"'
                            res_dummy = subprocess.run(cmd_dummy_label, shell=True, capture_output=True, text=True, encoding='utf-8')
                            if res_dummy.returncode == 0:
                                print(f"    [SUCCESS] Labeled dummy PR Memact/Context#{dummy_num} with: {label_str}")
                            else:
                                print(f"    [FAILED] Could not label dummy PR Memact/Context#{dummy_num}: {res_dummy.stderr.strip()}")
                                
                        # Comment success on the actual PR
                        success_msg_prefix = "**SSoC26 Success:** We found your dummy PR in [Context]"
                        already_success_commented = any(success_msg_prefix in b for b in comment_bodies)
                        if not already_success_commented:
                            body_msg = f"{success_msg_prefix} (#[Context#{dummy_num}](https://github.com/Memact/Context/pull/{dummy_num})) and have verified its linkage. Thank you!"
                            post_github_comment(repo, pr_num, body_msg)
                            print(f"    [COMMENT] Posted dummy PR success comment on PR #{pr_num}.")
                    else:
                        # Warning comment if no dummy PR exists
                        warning_msg_prefix = "**SSoC26 Warning:** We noticed that you haven't created a corresponding dummy PR"
                        already_warned = any(warning_msg_prefix in b for b in comment_bodies)
                        if not already_warned:
                            body_msg = f"{warning_msg_prefix} in the main [Context](https://github.com/Memact/Context) repository yet.\n\nBecause this contribution is in a sub-repository, you **must** open a dummy PR in `Memact/Context` linking to this PR (e.g., by referencing `Memact/{repo}#{pr_num}` in the title or description) for your contribution to be tracked and counted. Thank you!"
                            post_github_comment(repo, pr_num, body_msg)
                            print(f"    [COMMENT] Posted dummy PR warning comment on PR #{pr_num}.")
                            
    except Exception as e:
        print(f"Error checking Memact/{repo}: {e}")

print("\n=== LABEL ALIGNMENT ROUTINE COMPLETED ===")

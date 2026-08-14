#!/usr/bin/env bash
# Auto-commit + push after a Claude Code turn, when the change is large enough.
#
# Author is pinned to the repo owner. No Claude attribution is ever added.
# Configure thresholds with IAE_MIN_LINES / IAE_MIN_FILES; set IAE_AUTOPUSH=0 to
# commit locally without pushing.
set -uo pipefail

AUTHOR_NAME="${IAE_AUTHOR_NAME:-Nguyễn Văn Quyền}"
AUTHOR_EMAIL="${IAE_AUTHOR_EMAIL:-23521329@gm.uit.edu.vn}"
MIN_LINES="${IAE_MIN_LINES:-40}"
MIN_FILES="${IAE_MIN_FILES:-3}"
AUTOPUSH="${IAE_AUTOPUSH:-1}"

emit() { printf '{"systemMessage": %s, "suppressOutput": true}\n' "$(printf '%s' "$1" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"; exit 0; }
quiet() { printf '{"suppressOutput": true}\n'; exit 0; }

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || quiet
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || quiet

# Never touch the tree mid-merge, mid-rebase, mid-bisect, or on a detached HEAD:
# committing into any of those states corrupts an operation the user is running.
GIT_DIR_PATH="$(git rev-parse --git-dir)"
for marker in MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD BISECT_LOG REVERT_HEAD; do
  [ -e "$GIT_DIR_PATH/$marker" ] && emit "Auto-commit skipped: git is mid-operation ($marker)."
done
[ -d "$GIT_DIR_PATH/rebase-merge" ] || [ -d "$GIT_DIR_PATH/rebase-apply" ] && emit "Auto-commit skipped: rebase in progress."

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ "$BRANCH" = "HEAD" ] && emit "Auto-commit skipped: detached HEAD."

# Nothing staged or unstaged, and nothing untracked -> nothing to do.
[ -z "$(git status --porcelain)" ] && quiet

# Measure the change against the threshold BEFORE staging, counting only files
# git would actually track (respecting .gitignore).
git add -A -- . >/dev/null 2>&1

FILES="$(git diff --cached --numstat | wc -l | tr -d ' ')"
LINES="$(git diff --cached --numstat | awk '{a+=$1; d+=$2} END {print (a+d)+0}')"

if [ "$FILES" -eq 0 ]; then
  git reset >/dev/null 2>&1
  quiet
fi

if [ "$FILES" -lt "$MIN_FILES" ] && [ "$LINES" -lt "$MIN_LINES" ]; then
  # Below threshold: unstage so the working tree is left exactly as found.
  git reset >/dev/null 2>&1
  quiet
fi

ADDED="$(git diff --cached --numstat | awk '{a+=$1} END {print a+0}')"
DELETED="$(git diff --cached --numstat | awk '{d+=$2} END {print d+0}')"

# Build a subject from the top-level areas touched, so the log stays readable.
SCOPES="$(git diff --cached --name-only \
  | awk -F/ '{print ($1 ~ /\./ ? "root" : $1)}' \
  | sort -u | head -4 | paste -sd "," -)"
[ -z "$SCOPES" ] && SCOPES="repo"

SUBJECT="chore(${SCOPES}): auto-commit ${FILES} file(s), +${ADDED}/-${DELETED}"

BODY="$(git diff --cached --name-status | head -30)"

if ! git -c "user.name=$AUTHOR_NAME" -c "user.email=$AUTHOR_EMAIL" \
       commit --no-verify -q -m "$SUBJECT" -m "$BODY" >/dev/null 2>&1; then
  emit "Auto-commit failed; changes left staged for manual review."
fi

SHA="$(git rev-parse --short HEAD)"

if [ "$AUTOPUSH" != "1" ]; then
  emit "Auto-committed $SHA on $BRANCH ($SUBJECT). Push skipped (IAE_AUTOPUSH=0)."
fi

if git remote get-url origin >/dev/null 2>&1; then
  PUSH_ERR="$(git push origin "$BRANCH" 2>&1)"
  if [ $? -eq 0 ]; then
    emit "Auto-committed $SHA and pushed to origin/$BRANCH — $SUBJECT"
  fi
  emit "Auto-committed $SHA on $BRANCH, but push failed: $(printf '%s' "$PUSH_ERR" | tail -2 | tr '\n' ' ')"
fi

emit "Auto-committed $SHA on $BRANCH (no remote configured) — $SUBJECT"

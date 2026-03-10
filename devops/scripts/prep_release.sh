#!/usr/bin/env bash

set -euo pipefail

# Usage: ./prep_release.sh v0.9.2
# Make sure you have gh CLI installed and authenticated

if [ $# -ne 1 ]; then
  echo "Usage: $0 <new_version_tag> (e.g. v0.9.2)"
  exit 1
fi

if ! gh auth status &>/dev/null; then
  echo "You are not logged in to GitHub CLI. Please run 'gh auth login' first."
  exit 1
fi

NEW_TAG="$1"
NEW_VERSION="${NEW_TAG#v}"
REPO="microsoft/AzureTRE"

# 1. Create a Prep for Release issue
ISSUE_TITLE="Prep for Release $NEW_TAG"
ISSUE_BODY="Tracking issue for prepping release $NEW_TAG"
ISSUE_URL=$(gh issue create --title "$ISSUE_TITLE" --body "$ISSUE_BODY" --repo "$REPO" --label "release" --assignee "@me")
echo "Created issue: $ISSUE_URL"

# 2. Create a new branch
BRANCH="release/$NEW_TAG"
git checkout -b "$BRANCH"

# 3. Update CHANGELOG.md
# - Rename "Unreleased" to the new version
# - Add a new "Unreleased" section at the top
# - Insert output of devops/scripts/list_versions.sh

# Backup changelog
cp CHANGELOG.md CHANGELOG.md.bak

# Replace "Unreleased" with new version and date
TODAY=$(date +%Y-%m-%d)
sed -i "0,/## \(Unreleased\)/s//## ($NEW_VERSION) - $TODAY/" CHANGELOG.md

# Add new Unreleased section at the top
awk -v ver="$NEW_VERSION" '
  NR==1 {print; print "## (Unreleased)\n\n* _No changes yet_\n"; next}
  1
' CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md

# 4. Commit and push

git add CHANGELOG.md
git commit -m "Prep for release $NEW_TAG"
git push -u origin "$BRANCH"

# 5. Create PR and link to issue
GH_USER=$(gh api user --jq .login)
gh pr create --title "Prep for release $NEW_TAG" --body "Closes $ISSUE_URL" --base main --head "$GH_USER:$BRANCH" --repo "$REPO"
echo "Created PR"
echo "Please review the PR, merge it, and then continue with the following steps:"

cat <<EOF

6. After merging, create a GitHub pre-release:
   - Go to https://github.com/microsoft/AzureTRE/releases/new
   - Tag: $NEW_TAG
   - Title: $NEW_VERSION
   - Copy the relevant section from CHANGELOG.md as the description.
   - Add:
     Output of devops/scripts/list_versions.sh
     Full Changelog: https://github.com/microsoft/AzureTRE/compare/<previous_tag>...$NEW_TAG
   - Mark as pre-release.

7. Update AzureTRE-Deployment as per documentation.

8. Once tests are complete, edit the GitHub Release to set as the latest release.

EOF

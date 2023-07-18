#!/usr/bin/env bash
prs=$(gh pr list -s open -A app/dependabot -l javascript --json headRefName | jq ".[].headRefName"| tr -d '"')

for pr in $prs
do
  command="git merge upstream/$pr --no-edit"
  echo "$command"
  $command
done

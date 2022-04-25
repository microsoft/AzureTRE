//
// This file contains functions that are used in GitHub workflows
// (e.g. to implement the pr-bot for running tests
// There are tests for this code in build.test.js
// These tests can be run from the dev container using the run-tests.sh script
//
const { createHash } = require('crypto');

async function getCommandFromComment({ core, context, github }) {
  const commentUsername = context.payload.comment.user.login;
  const repoFullName = context.payload.repository.full_name;
  const repoParts = repoFullName.split("/");
  const repoOwner = repoParts[0];
  const repoName = repoParts[1];
  const prNumber = context.payload.issue.number;
  const commentLink = context.payload.comment.html_url;
  const runId = context.runId;
  const prAuthorUsername = context.payload.issue.user.login;

  // only allow actions for users with write access
  if (!await userHasWriteAccessToRepo({ core, github }, commentUsername, repoOwner, repoName)) {
    core.notice("Command: none - user doesn't have write permission]");
    await github.rest.issues.createComment({
      owner: repoOwner,
      repo: repoName,
      issue_number: prNumber,
      body: `Sorry, @${commentUsername}, only users with write access to the repo can run pr-bot commands.`
    });
    logAndSetOutput(core, "command", "none");
    return "none";
  }

  // Determine PR SHA etc
  const ciGitRef = getRefForPr(prNumber);
  logAndSetOutput(core, "ciGitRef", ciGitRef);

  const prRefId = getRefIdForPr(prNumber);
  logAndSetOutput(core, "prRefId", prRefId);

  const pr = (await github.rest.pulls.get({ owner: repoOwner, repo: repoName, pull_number: prNumber })).data;

  if (repoFullName === pr.head.repo.full_name) {
    core.info(`Using head ref: ${pr.head.ref}`)
    const branchRefId = getRefIdForBranch(pr.head.ref);
    logAndSetOutput(core, "branchRefId", branchRefId);
  } else {
    core.info("Skipping branchRefId as PR is from a fork")
  }

  const potentialMergeCommit = pr.merge_commit_sha;
  logAndSetOutput(core, "prRef", potentialMergeCommit);

  const prHeadSha = pr.head.sha;
  logAndSetOutput(core, "prHeadSha", prHeadSha);

  const gotNonDocChanges = await prContainsNonDocChanges(github, repoOwner, repoName, prNumber);
  logAndSetOutput(core, "nonDocsChanges", gotNonDocChanges.toString());

  //
  // Determine what action to take
  // Only use the first line of the comment to allow remainder of the body for other comments/notes
  //
  const commentBody = context.payload.comment.body;
  const commentFirstLine = commentBody.split("\n")[0];
  let command = "none";
  const trimmedFirstLine = commentFirstLine.trim();
  if (trimmedFirstLine[0] === "/") {
    const parts = trimmedFirstLine.split(' ');
    const commandText = parts[0];
    switch (commandText) {
      case "/test":
        {
          // Docs only changes don't run tests with secrets so can run regardless of whether
          if (!gotNonDocChanges) {
            command = "test-force-approve";
            const message = `:white_check_mark: PR only contains docs changes - marking tests as complete`;
            await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
            break;
          }

          // check if this is an external PR (i.e. author not a maintainer)
          // if so, need to specify the SHA that has been vetted and check that it matches
          // the latest head SHA for the PR
          const prAuthorHasWriteAccess = await userHasWriteAccessToRepo({ core, github }, prAuthorUsername, repoOwner, repoName);
          const externalPr = !prAuthorHasWriteAccess;
          if (externalPr) {
            if (parts.length === 1) {
              command = "none"
              const message = `:warning: When using \`/test\` on external PRs, the SHA of the checked commit must be specified`;
              await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
              break;
            }
            const commentSha = parts[1];
            if (commentSha.length < 7) {
              command = "none"
              const message = `:warning: When specifying a commit SHA it must be at least 7 characters (received \`234567\`)`;
              await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
              break;
            }
            if (!prHeadSha.startsWith(commentSha)) {
              command = "none"
              const message = `:warning: The specified SHA \`${commentSha}\` is not the latest commit on the PR. Please validate the latest commit and re-run \`/test\``;
              await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
              break;
            }
          }

          command = "run-tests";
          const message = `:runner: Running tests: https://github.com/${repoFullName}/actions/runs/${runId} (with refid \`${prRefId}\`)`;
          await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
          break;
        }

      case "/test-extended":
        {
          // TODO - need to add SHA for /test-extended as well as /test ****************************************************************************************************************
          command = "run-tests-extended";
          const message = `:runner: Running extended tests: https://github.com/${repoFullName}/actions/runs/${runId} (with refid \`${prRefId}\`)`;
          await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
          break;
        }

      case "/test-force-approve":
        {
          command = "test-force-approve";
          const message = `:white_check_mark: Marking tests as complete (for commit ${prHeadSha})`;
          await addActionComment({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, message);
          break;
        }

      case "/test-destroy-env":
        command = "test-destroy-env";
        break;

      case "/help":
        showHelp({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, null);
        command = "none"; // command has been handled, so don't need to return a value for future steps
        break;

      default:
        core.warning(`'${commandText}' not recognised as a valid command`);
        await showHelp({ github }, repoOwner, repoName, prNumber, commentUsername, commentLink, commandText);
        command = "none";
        break;
    }
  }
  logAndSetOutput(core, "command", command);
  return command;
}

async function prContainsNonDocChanges(github, repoOwner, repoName, prNumber) {
  const prFilesResponse = await github.paginate(github.rest.pulls.listFiles, {
    owner: repoOwner,
    repo: repoName,
    pull_number: prNumber
  });
  const prFiles = prFilesResponse.map(file => file.filename);
  // Regexes describing allowed filenames
  // If a filename matches any regex in the array then it is considered a doc
  // Currently, match all `.md` files and `mkdocs.yml` in the root
  const docsRegexes = [/\.md$/, /^mkdocs.yml$/];
  const gotNonDocChanges = prFiles.some(file => docsRegexes.every(regex => !regex.test(file)));
  return gotNonDocChanges;
}

async function labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github }) {
  const username = context.payload.pull_request.user.login;
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (!await userHasWriteAccessToRepo({ core, github }, username, owner, repo)) {
    core.info("Adding external label to PR " + context.payload.pull_request.number)
    await github.rest.issues.addLabels({
      owner,
      repo,
      issue_number: context.payload.pull_request.number,
      labels: ['external']
    });
  }
}

async function userHasWriteAccessToRepo({ core, github }, username, repoOwner, repoName) {
  // Previously, we attempted to use github.event.comment.author_association to check for OWNER or COLLABORATOR
  // Unfortunately, that always shows MEMBER if you are in the microsoft org and have that set to publicly visible
  // (Can check via https://github.com/orgs/microsoft/people?query=<username>)

  // https://docs.github.com/en/rest/reference/collaborators#check-if-a-user-is-a-repository-collaborator
  let userHasWriteAccess = false;
  try {
    core.info(`Checking if user "${username}" has write access to ${repoOwner}/${repoName} ...`)
    const result = await github.request('GET /repos/{owner}/{repo}/collaborators/{username}', {
      owner: repoOwner,
      repo: repoName,
      username
    });
    userHasWriteAccess = result.status === 204;
  } catch (err) {
    if (err.status === 404) {
      core.info("User not found in collaborators");
    } else {
      core.error(`Error checking if user has write access: ${err.status} (${err.response.data.message}) `)
    }
  }
  core.info("User has write access: " + userHasWriteAccess);
  return userHasWriteAccess
}

async function showHelp({ github }, repoOwner, repoName, prNumber, commentUser, commentLink, invalidCommand) {
  const leadingContent = invalidCommand ? `\`${invalidCommand}\` is not recognised as a valid command.` : "Hello!";

  const body = `${leadingContent}

You can use the following commands:
&nbsp;&nbsp;&nbsp;&nbsp;/test - build, deploy and run smoke tests on a PR
&nbsp;&nbsp;&nbsp;&nbsp;/test-extended - build, deploy and run smoke & extended tests on a PR
&nbsp;&nbsp;&nbsp;&nbsp;/test-force-approve - force approval of the PR tests (i.e. skip the deployment checks)
&nbsp;&nbsp;&nbsp;&nbsp;/test-destroy-env - delete the validation environment for a PR (e.g. to enable testing a deployment from a clean start after previous tests)
&nbsp;&nbsp;&nbsp;&nbsp;/help - show this help`;

  await addActionComment({ github }, repoOwner, repoName, prNumber, commentUser, commentLink, body);

}
async function addActionComment({ github }, repoOwner, repoName, prNumber, commentUser, commentLink, message) {

  const body = `:robot: pr-bot :robot:

${message}

(in response to [this comment](${commentLink}) from @${commentUser})
`;

  await github.rest.issues.createComment({
    owner: repoOwner,
    repo: repoName,
    issue_number: prNumber,
    body: body
  });

}

function logAndSetOutput(core, name, value) {
  core.info(`Setting output '${name}: ${value}`);
  core.setOutput(name, value);
}

function getRefForPr(prNumber) {
  return `refs/pull/${prNumber}/merge`;
}
function getRefIdForPr(prNumber) {
  const prRef = getRefForPr(prNumber);
  // Trailing newline is for compatibility with previous bash SHA calculation
  return createShortHash(`${prRef}\n`);
}
function getRefIdForBranch(branchName) {
  // Trailing newline is for compatibility with previous bash SHA calculation
  return createShortHash(`refs/heads/${branchName}\n`);
}
function createShortHash(ref) {
  const hash = createHash('sha1').update(ref, 'utf8').digest('hex')
  return hash.substring(0, 8);
}

module.exports = {
  getCommandFromComment,
  labelAsExternalIfAuthorDoesNotHaveWriteAccess
}

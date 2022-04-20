const { createHash } = require('crypto');

async function getCommandFromComment({ core, context, github }) {
  const commentUsername = context.payload.comment.user.login;
  const repoFullName = context.payload.repository.full_name;
  const repoParts = repoFullName.split("/");
  const repoOwner = repoParts[0];
  const repoName = repoParts[1];

  // only allow actions for users with write access
  if (!await userHasWriteAccessToRepo({ github }, commentUsername, repoOwner, repoName)) {
    console.log("Command: none [user doesn't have write permission]");
    return "none";
  }

  // Determine PR SHA etc
  const prNumber = context.payload.issue.number;
  const pr = (await github.rest.pulls.get({ owner: repoOwner, repo: repoName, pull_number: prNumber })).data;
  console.log("==========================================================================================");
  console.log(pr);
  console.log("==========================================================================================");

  const prRefId = getRefIdForPr(prNumber);
  console.log(`prRefId: ${prRefId}`);
  core.setOutput("prRefId", prRefId);

  console.log(`Using head ref: ${pr.head.ref}`)
  const branchRefId = getRefIdForBranch(pr.head.ref);
  console.log(`branchRefId: ${branchRefId}`);

  const potentialMergeCommit = pr.merge_commit_sha;
  console.log(`potentialMergeCommit: ${potentialMergeCommit}`);
  core.setOutput("potentialMergeCommit", potentialMergeCommit);

  const prHeadSha = pr.head.sha;;
  console.log(`prHeadSha: ${prHeadSha}`);


  //
  // Determine what action to take
  // Only use the first line of the comment to allow remainder of the body for other comments/notes
  //
  const commentBody = context.payload.comment.body;
  const commentFirstLine = commentBody.split("\n")[0];
  let command = "none";
  const trimmedFirstLine = commentFirstLine.trim();
  if (trimmedFirstLine[0] === "/") {
    switch (trimmedFirstLine) {
      case "/test":
        command = "run-tests";
        break;
      case "/test-extended":
        command = "run-tests-extended";
        break;
      case "/test-force-approve":
        command = "test-force-approve";
        break;
      case "/test-destroy-env":
        command = "test-destroy-env";
        break;
      case "/help":
        showHelp(github, repoOwner, repoName, prNumber, null);
        command = "none"; // command has been handled, so don't need to return a value for future steps
        break;
      default:
        console.log(`'${trimmedFirstLine}' not recognised as a valid command`);
        await showHelp(github, repoOwner, repoName, prNumber, trimmedFirstLine);
        return "none";
    }
  }
  console.log(`Command: ${command}`);
  return command;
}

async function labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github }) {
  const username = context.payload.pull_request.user.login;
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (!await userHasWriteAccessToRepo({ github }, username, owner, repo)) {
    console.log("Adding external label to PR " + context.payload.pull_request.number)
    github.rest.issues.addLabels({
      owner,
      repo,
      issue_number: context.payload.pull_request.number,
      labels: ['external']
    });
  }
}

async function userHasWriteAccessToRepo({ github }, username, repoOwner, repoName) {
  // Previously, we attempted to use github.event.comment.author_association to check for OWNER or COLLABORATOR
  // Unfortunately, that always shows MEMBER if you are in the microsoft org and have that set to publicly visible
  // (Can check via https://github.com/orgs/microsoft/people?query=<username>)

  // https://docs.github.com/en/rest/reference/collaborators#check-if-a-user-is-a-repository-collaborator
  let userHasWriteAccess = false;
  try {
    console.log(`Checking if user "${username}" has write access to ${repoOwner}/${repoName} ...`)
    const result = await github.request('GET /repos/{owner}/{repo}/collaborators/{username}', {
      owner: repoOwner,
      repo: repoName,
      username
    });
    userHasWriteAccess = result.status === 204;
  } catch (err) {
    if (err.status === 404) {
      console.log("User not found in collaborators");
    } else {
      console.log(`Error checking if user has write access: ${err.status} (${err.response.data.message}) `)
    }
  }
  console.log("User has write access: " + userHasWriteAccess);
  return userHasWriteAccess
}

async function showHelp(github, repoOwner, repoName, prNumber, invalidCommand) {
  const leadingContent = invalidCommand ? `\`${invalidCommand}\` is not recognised as a valid command.` : "Hello!";

  const body = `${leadingContent}

You can use the following commands:
&nbsp;&nbsp;&nbsp;&nbsp;/test - build, deploy and run smoke tests on a PR
&nbsp;&nbsp;&nbsp;&nbsp;/test-extended - build, deploy and run smoke & extended tests on a PR
&nbsp;&nbsp;&nbsp;&nbsp;/test-force-approve - force approval of the PR tests (i.e. skip the deployment checks)
&nbsp;&nbsp;&nbsp;&nbsp;/test-destroy-env - delete the validation environment for a PR (e.g. to enable testing a deployment from a clean start after previous tests)
&nbsp;&nbsp;&nbsp;&nbsp;/help - show this help`;

  github.rest.issues.createComment({
    owner: repoOwner,
    repo: repoName,
    issue_number: prNumber,
    body: body
  });

}

function getRefIdForPr(prNumber) {
  // Trailing newline is for compatibility with previous bash SHA calculation
  return createShortHash(`refs/pull/${prNumber}/merge\n`);
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

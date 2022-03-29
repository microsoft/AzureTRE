function getCommandFromComment({ context, github }) {
  const commentUsername = context.payload.comment.user.login;
  const repoFullName = context.payload.repository.full_name;
  const repoParts = repoFullName.split("/");
  const repoOwner = repoParts[0];
  const repoName = repoParts[1];

  // only allow actions for users with write access
  if (!userHasWriteAccessToRepo({ github }, commentUsername, repoOwner, repoName)) {
    console.log("Command: none [user doesn't have write permission]");
    return "none";
  }

  //
  // Determine what action to take
  // Only use the first line of the comment to allow remainder of the body for other comments/notes
  //
  const commentBody = context.payload.comment.body;
  const commentFirstLine = commentBody.split("\n")[0];
  let command = "none";
  switch (commentFirstLine.trim()) {
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
      command = "show-help";
      break;
  }
  console.log(`Command: ${command}`);
  return command;
}

function labelAsExternalIfAuthorDoesNotHaveWriteAccess({ context, github }) {
  const username = context.payload.pull_request.user.login;
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (!userHasWriteAccessToRepo({ github }, username, owner, repo)) {
    console.log("Adding external label to PR " + context.payload.pull_request.number)
    github.rest.issues.addLabels({
      owner,
      repo,
      issue_number: context.payload.pull_request.number,
      labels: ['external']
    });
  }
}

function userHasWriteAccessToRepo({ github }, username, repoOwner, repoName) {
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

module.exports = {
  getCommandFromComment,
  labelAsExternalIfAuthorDoesNotHaveWriteAccess
}

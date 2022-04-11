const { getCommandFromComment, labelAsExternalIfAuthorDoesNotHaveWriteAccess } = require('./build.js')

mockGithubRestIssuesAddLabels = jest.fn();

const github = {
  request: async (route, data) => {
    if (route === 'GET /repos/{owner}/{repo}/collaborators/{username}') {
      if (data.username === "admin") {
        return {
          status: 204
        };
      } else {
        throw {
          status: 404,
        };
      }
    }
  },
  rest: {
    issues: {
      addLabels: mockGithubRestIssuesAddLabels,
    },
  },
};

const core = {};

describe('getCommandFromComment', () => {

  function createCommentContext(username, commentBody) {
    return {
      payload: {
        comment: {
          user: {
            login: username,
          },
          body: commentBody,
        },
        repository: {
          full_name: 'someOwner/SomeRepo'
        }
      },
    };
  }

  describe('with non-contributor', () => {
    test(`should return 'none' for '/test'`, async () => {
      context = createCommentContext('non-contributor', '/test');
      var command = await getCommandFromComment({ context, github })
      expect(command).toBe('none');
    });
  });

  describe('with contributor', () => {
    test(`should return 'none' if doesn't start with '/'`, async () => {
      context = createCommentContext('admin', 'foo');
      var command = await getCommandFromComment({ context, github })
      expect(command).toBe('none');
    });


    describe('and single line comments', () => {
      test(`should return 'run-tests' for '/test'`, async () => {
        context = createCommentContext('admin', '/test');
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('run-tests');
      });

      test(`should return 'run-tests-extended' for '/test-extended'`, async () => {
        context = createCommentContext('admin', '/test-extended');
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('run-tests-extended');
      });

      test(`should return 'test-force-approve' for '/test-force-approve'`, async () => {
        context = createCommentContext('admin', '/test-force-approve');
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('test-force-approve');
      });

      test(`should return 'test-destroy-env' for '/test-destroy-env'`, async () => {
        context = createCommentContext('admin', '/test-destroy-env');
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('test-destroy-env');
      });

      test(`should return 'show-help' for '/help'`, async () => {
        context = createCommentContext('admin', '/help');
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('show-help');
      });
    });


    describe('and multi-line comments', () => {
      test(`should return 'run-tests' if first line of comment is '/test'`, async () => {
        context = createCommentContext('admin', `/test
Other comment content
goes here`);
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('run-tests');
      });

      test(`should return 'none' if first line of comment is a command even if later lines contain '/test'`, async () => {
        context = createCommentContext('admin', `Non-command comment
/test
Other comment content
goes here`);
        var command = await getCommandFromComment({ context, github })
        expect(command).toBe('none');
      });
    });

  });
});


describe('labelAsExternalIfAuthorDoesNotHaveWriteAccess', () => {

  function createPullRequestContext(username, pullRequestNumber) {
    return {
      payload: {
        pull_request: {
          user: {
            login: username,
          },
          number: pullRequestNumber,
        },
        repository: {
          full_name: 'someOwner/SomeRepo'
        }
      },
      repo : {
        owner: 'someOwner',
        repo: 'someRepo'
      }
    };
  }

  test(`should return not apply the 'external' label for contributor author`, async () => {
    context = createPullRequestContext('admin', 123);
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github })
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalledTimes(0); // shouldn't set the label for contributor
  });

  test(`should apply the 'external' label for non-contributor author`, async () => {
    context = createPullRequestContext('non-contributor', 123);
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github })
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalled(); // should set the label for non-contributor
  });

});

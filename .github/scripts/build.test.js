const { getCommandFromComment, labelAsExternalIfAuthorDoesNotHaveWriteAccess } = require('./build.js')

function createGitHubContext() {
  mockGithubRestIssuesAddLabels = jest.fn();
  mockGithubRestIssuesCreateComment = jest.fn();
  mockCoreSetOutput = jest.fn();
  return {
    mockGithubRestIssuesAddLabels,
    mockGithubRestIssuesCreateComment,
    mockCoreSetOutput,
    core: {
      setOutput: mockCoreSetOutput,
    },
    github: {
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
          createComment: mockGithubRestIssuesCreateComment,
        },
        pulls: {
          get: async (params) => {
            if (params.owner === 'someOwner'
              && params.repo === 'someRepo'
              && params.pull_number === 123) {
              return {
                data: {
                  head: {
                    ref: 'pr-head-ref',
                    sha: '0123456789',
                  },
                  merge_commit_sha: '123456789a',
                },
              }
            }
            throw 'Unhandled params in fake pulls.get: ' + JSON.stringify(params)
          },
        },
      },
    }
  };
}

describe('getCommandFromComment', () => {

  var github;
  var core;
  var mockCoreSetOutput;
  var mockGithubRestIssuesCreateComment;
  beforeEach(() => {
    ({ core, github, mockCoreSetOutput, mockGithubRestIssuesCreateComment } = createGitHubContext());
  });

  function createCommentContext(username, pullRequestNumber, commentBody) {
    return {
      payload: {
        comment: {
          user: {
            login: username,
          },
          body: commentBody,
        },
        issue: {
          number: pullRequestNumber,
        },
        repository: {
          full_name: 'someOwner/someRepo'
        }
      },
    };
  }

  describe('with non-contributor', () => {
    test(`should return 'none' for '/test'`, async () => {
      context = createCommentContext('non-contributor', 123, '/test');
      var command = await getCommandFromComment({ core, context, github });
      expect(command).toBe('none');
    });
  });

  describe('with contributor', () => {
    test(`should return 'none' if doesn't start with '/'`, async () => {
      context = createCommentContext('admin', 123, 'foo');
      var command = await getCommandFromComment({ core, context, github });
      expect(command).toBe('none');
    });


    describe('and single line comments', () => {
      test(`should return 'run-tests' for '/test'`, async () => {
        context = createCommentContext('admin', 123, '/test');
        var command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests');
      });

      test(`should return 'run-tests-extended' for '/test-extended'`, async () => {
        context = createCommentContext('admin', 123, '/test-extended');
        var command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests-extended');
      });

      test(`should return 'test-force-approve' for '/test-force-approve'`, async () => {
        context = createCommentContext('admin', 123, '/test-force-approve');
        var command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('test-force-approve');
      });

      test(`should return 'test-destroy-env' for '/test-destroy-env'`, async () => {
        context = createCommentContext('admin', 123, '/test-destroy-env');
        var command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('test-destroy-env');
      });

      test(`should add help comment and return 'none' for '/help'`, async () => {
        context = createCommentContext('admin', 123, '/help');
        var command = await getCommandFromComment({ core, context, github });
        expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
        const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
        const createCommentParam = createCommentCall[0];
        expect(createCommentParam.owner).toBe("someOwner");
        expect(createCommentParam.repo).toBe("someRepo");
        expect(createCommentParam.issue_number).toBe(123);
        expect(createCommentParam.body).toMatch(/^Hello!\n\nYou can use the following commands:/);
        expect(command).toBe('none');
      });

      test(`should add help comment and return 'none' for '/not-a-command'`, async () => {
        context = createCommentContext('admin', 123, '/not-a-command');
        var command = await getCommandFromComment({ core, context, github });
        expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
        const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
        const createCommentParam = createCommentCall[0];
        expect(createCommentParam.owner).toBe("someOwner");
        expect(createCommentParam.repo).toBe("someRepo");
        expect(createCommentParam.issue_number).toBe(123);
        expect(createCommentParam.body).toMatch(/^`\/not-a-command` is not recognised as a valid command.\n\nYou can use the following commands:/);
        expect(command).toBe('none');
      });
    });


    describe('and multi-line comments', () => {
      test(`should return 'run-tests' if first line of comment is '/test'`, async () => {
        context = createCommentContext('admin', 123, `/test
Other comment content
goes here`);
        var command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests');
      });

      test(`should return 'none' if first line of comment is a command even if later lines contain '/test'`, async () => {
        context = createCommentContext('admin', 123, `Non-command comment
/test
Other comment content
goes here`);
        var command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('none');
      });
    });

  });


  describe('PR context', () => {
    test('should set correct output for refid', async () => {
      // Using a PR number of 123 should give a refid of 'cbce50da'
      // Based on running `echo "refs/pull/123/merge" | shasum | cut -c1-8` (as per the original bash scripts)
      context = createCommentContext('admin', 123, '/help');
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('prRefId', 'cbce50da');
    });
  })
});


describe('labelAsExternalIfAuthorDoesNotHaveWriteAccess', () => {

  var core;
  var github;
  var mockGithubRestIssuesAddLabels;
  beforeEach(() => {
    ({ core, github, mockGithubRestIssuesAddLabels } = createGitHubContext());
  });

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
      repo: {
        owner: 'someOwner',
        repo: 'someRepo'
      },
    };
  }

  test(`should apply the 'external' label for non-contributor author`, async () => {
    context = createPullRequestContext('non-contributor', 123);
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github });
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalled(); // should set the label for non-contributor
  });

  test(`should return not apply the 'external' label for contributor author`, async () => {
    context = createPullRequestContext('admin', 123);
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github });
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalledTimes(0); // shouldn't set the label for contributor
  });

});

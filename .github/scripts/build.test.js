const { getCommandFromComment, labelAsExternalIfAuthorDoesNotHaveWriteAccess } = require('./build.js')

function createGitHubContext() {
  mockGithubRestIssuesAddLabels = jest.fn();
  mockGithubRestIssuesCreateComment = jest.fn();
  mockCoreSetOutput = jest.fn();
  mockCoreNotice = jest.fn();
  mockCoreInfo = jest.fn();
  mockCoreWarning = jest.fn();
  mockCoreError = jest.fn();
  return {
    mockGithubRestIssuesAddLabels,
    mockGithubRestIssuesCreateComment,
    mockCoreSetOutput,
    mockCoreInfo,
    mockCoreNotice,
    mockCoreWarning,
    mockCoreError,
    core: {
      setOutput: mockCoreSetOutput,
      info: mockCoreInfo,
      notice: mockCoreNotice,
      warning: mockCoreWarning,
      error: mockCoreError,
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
              && params.repo === 'someRepo') {
              switch (params.pull_number) {
                case 123: // PR from the upstream repo
                  return {
                    data: {
                      head: {
                        ref: 'pr-head-ref',
                        sha: '0123456789',
                        repo: {
                          full_name: 'someOwner/someRepo'
                        }
                      },
                      merge_commit_sha: '123456789a',
                    },
                  }
                case 456: // PR from a forked repo
                  return {
                    data: {
                      head: {
                        ref: 'pr-head-ref',
                        sha: '23456789ab',
                        repo: {
                          full_name: 'anotherOwner/someRepo'
                        }
                      },
                      merge_commit_sha: '3456789abc',
                    },
                  }
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

  function createCommentContext({ username, pullRequestNumber, body }) {
    if (!username) {
      username = 'admin'; // most tests will assume admin (i.e. user can run commands)
    }
    if (!pullRequestNumber) {
      pullRequestNumber = 123;
    }
    if (!body) {
      body = "nothing to see here";
    }
    return {
      payload: {
        comment: {
          user: {
            login: username,
          },
          body,
        },
        issue: {
          number: pullRequestNumber,
        },
        repository: {
          full_name: 'someOwner/someRepo'
        },
      },
    };
  }

  describe('with non-contributor', () => {
    test(`should return 'none' for '/test'`, async () => {
      const context = createCommentContext({
        username: 'non-contributor',
        body: '/test'
      });
      const command = await getCommandFromComment({ core, context, github });
      expect(command).toBe('none');
    });
  });

  describe('with contributor', () => {
    test(`should return 'none' if doesn't start with '/'`, async () => {
      const context = createCommentContext({
        username: 'admin',
        body: 'foo'
      });
      const command = await getCommandFromComment({ core, context, github });
      expect(command).toBe('none');
    });


    describe('and single line comments', () => {
      test(`should return 'run-tests' for '/test'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test'
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests');
      });

      test(`should return 'run-tests-extended' for '/test-extended'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-extended'
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests-extended');
      });

      test(`should return 'test-force-approve' for '/test-force-approve'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-force-approve'
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('test-force-approve');
      });

      test(`should return 'test-destroy-env' for '/test-destroy-env'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-destroy-env'
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('test-destroy-env');
      });

      test(`should add help comment and return 'none' for '/help'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/help'
        });
        const command = await getCommandFromComment({ core, context, github });
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
        const context = createCommentContext({
          username: 'admin',
          body: '/not-a-command'
        });
        const command = await getCommandFromComment({ core, context, github });
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
        const context = createCommentContext({
          username: 'admin',
          body: `/test
Other comment content
goes here`
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests');
      });

      test(`should return 'none' if first line of comment is a command even if later lines contain '/test'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: `Non-command comment
/test
Other comment content
goes here`
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('none');
      });
    });

  });


  describe('PR context', () => {
    test('should set prRef output', async () => {
      // prRef should be set to the SHA for the potentialMergeCommit for the PR
      const context = createCommentContext({
        pullRequestNumber: 123
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('prRef', '123456789a');
    });

    test('should set prRefId output', async () => {
      // Using a PR number of 123 should give a refid of 'cbce50da'
      // Based on running `echo "refs/pull/123/merge" | shasum | cut -c1-8` (as per the original bash scripts)
      const context = createCommentContext({
        pullRequestNumber: 123
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('prRefId', 'cbce50da');
      expect(mockCoreSetOutput.mock.calls.some(c => c[0] == 'prRefId')).toBe(true);
    });

    test('should not set branchRefId output for PR from forked repo', async () => {
      // Using PR 456 which is faked as a PR from a fork
      // Since branch-based environments are only for upstream branches, the branchRefId
      // output should not be set for this PR
      const context = createCommentContext({
        pullRequestNumber: 456
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput.mock.calls.some(c => c[0] == 'branchRefId')).toBe(false);
    });

    test('should set branchRefId for PR from upstream repo', async () => {
      // Using PR 123 which is faked as a PR from the upstream repo
      // The Using a PR number of 123 should give a refid of '71f7c907'
      // Based on running `echo "refs/heads/pr-head-ref" | shasum | cut -c1-8` (as per the original bash scripts)
      const context = createCommentContext({
        pullRequestNumber: 123
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('branchRefId', '71f7c907');
    });

    test('should set prHeadSha output', async () => {
      // prHeadSha should be the SHA for the head commit for the PR
      const context = createCommentContext({
        pullRequestNumber: 123
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('prHeadSha', '0123456789');
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

  function createPullRequestContext({ username, pullRequestNumber }) {
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
    const context = createPullRequestContext({
      username: 'non-contributor',
      pullRequestNumber: 123
    });
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github });
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalled(); // should set the label for non-contributor
  });

  test(`should return not apply the 'external' label for contributor author`, async () => {
    const context = createPullRequestContext({
      username: 'admin',
      pullRequestNumber: 123
    });
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github });
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalledTimes(0); // shouldn't set the label for contributor
  });

});

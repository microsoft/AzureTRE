const { getCommandFromComment, labelAsExternalIfAuthorDoesNotHaveWriteAccess } = require('./build.js')

const PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES = 123;
const PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES = 125;
const PR_NUMBER_FORK_NON_DOCS_CHANGES = 456;

function createGitHubContext() {
  mockGithubRestIssuesAddLabels = jest.fn();
  mockGithubRestIssuesCreateComment = jest.fn();
  mockGithubRestPullsListFiles = jest.fn();
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
      paginate: (func, params) => {
        // thin fake for paginate -> faked function being paginated should return a single page of data!
        // if you're getting a `func is not a function` error then check that a func is being passed in
        return func(params);
      },
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
                case PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES: // PR from the upstream repo with non-docs changes
                  return {
                    data: {
                      head: {
                        ref: 'pr-head-ref',
                        sha: '0123456789',
                        repo: { full_name: 'someOwner/someRepo' },
                      },
                      merge_commit_sha: '123456789a',
                    },
                  }
                case PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES: // PR from the upstream repo with docs-only changes
                  return {
                    data: {
                      head: {
                        ref: 'pr-head-ref',
                        sha: '0123456789',
                        repo: { full_name: 'someOwner/someRepo' },
                      },
                      merge_commit_sha: '123456789a',
                    },
                  }
                case PR_NUMBER_FORK_NON_DOCS_CHANGES: // PR from a forked repo
                  return {
                    data: {
                      head: {
                        ref: 'pr-head-ref',
                        sha: '23456789ab',
                        repo: { full_name: 'anotherOwner/someRepo' },
                      },
                      merge_commit_sha: '3456789abc',
                    },
                  }
              }
            }
            throw 'Unhandled params in fake pulls.get: ' + JSON.stringify(params)
          },
          listFiles: async (params) => {
            if (params.owner === 'someOwner'
              && params.repo === 'someRepo') {
              switch (params.pull_number) {
                case PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES: // PR from the upstream repo with non-docs changes
                case PR_NUMBER_FORK_NON_DOCS_CHANGES: // PR from a forked repo
                  return [{ filename: 'test.py' }, { filename: 'test.md' }];
                case PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES: // PR from the upstream repo with docs-only changes
                  return [{ filename: 'mkdocs.yml' }, { filename: 'test.md' }, { filename: 'docs/README.md' }];
              }
            }
            throw 'Unhandled params in fake pulls.listFiles: ' + JSON.stringify(params)
          }
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
      pullRequestNumber = PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES;
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
          html_url: "https://wibble/comment-link"
        },
        issue: {
          number: pullRequestNumber,
        },
        repository: {
          full_name: 'someOwner/someRepo'
        },
      },
      runId: 11112222,
    };
  }

  describe('with non-contributor', () => {
    test(`for '/test' should return 'none'`, async () => {
      const context = createCommentContext({
        username: 'non-contributor',
        body: '/test',
      });
      const command = await getCommandFromComment({ core, context, github });
      expect(command).toBe('none');
    });

    test(`should add a comment indicating that the user cannot run commands`, async () => {
      const context = createCommentContext({
        username: 'non-contributor',
        body: '/test',
        pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
      });
      await getCommandFromComment({ core, context, github });
      expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
      const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
      const createCommentParam = createCommentCall[0];
      expect(createCommentParam.owner).toBe("someOwner");
      expect(createCommentParam.repo).toBe("someRepo");
      expect(createCommentParam.issue_number).toBe(PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES);
      expect(createCommentParam.body).toBe('Sorry, @non-contributor, only users with write access to the repo can run pr-bot commands.');
    });

  });

  describe('with contributor', () => {
    test(`if doesn't start with '/' should set command to 'none'`, async () => {
      const context = createCommentContext({
        username: 'admin',
        body: 'foo',
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'none');
    });


    describe('and single line comments', () => {

      describe(`for '/test' for PR with non-docs changes`, () => {
        test(`should set command to 'run-tests'`, async () => {
          const context = createCommentContext({
            username: 'admin',
            body: '/test',
            pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
          });
          await getCommandFromComment({ core, context, github });
          expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'run-tests');
        });

        test(`should set nonDocsChanges to 'true'`, async () => {
          const context = createCommentContext({
            username: 'admin',
            body: '/test',
            pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
          });
          await getCommandFromComment({ core, context, github });
          expect(mockCoreSetOutput).toHaveBeenCalledWith('nonDocsChanges', 'true');
        });

        test(`should add comment with run link`, async () => {
          const context = createCommentContext({
            username: 'admin',
            body: '/test',
            pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
          });
          await getCommandFromComment({ core, context, github });
          expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
          const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
          const createCommentParam = createCommentCall[0];
          expect(createCommentParam.owner).toBe("someOwner");
          expect(createCommentParam.repo).toBe("someRepo");
          expect(createCommentParam.issue_number).toBe(PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES);
          expect(createCommentParam.body).toMatch(/Running tests: https:\/\/github.com\/someOwner\/someRepo\/actions\/runs\/11112222/);
        });
      })

      describe(`for '/test' for PR with docs-only changes`, () => {
        test(`should set command to 'test-force-approve'`, async () => {
          const context = createCommentContext({
            username: 'admin',
            body: '/test',
            pullRequestNumber: PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES,
          });
          await getCommandFromComment({ core, context, github });
          expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'test-force-approve');
        });

        test(`should set nonDocsChanges to 'false'`, async () => {
          const context = createCommentContext({
            username: 'admin',
            body: '/test',
            pullRequestNumber: PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES,
          });
          await getCommandFromComment({ core, context, github });
          expect(mockCoreSetOutput).toHaveBeenCalledWith('nonDocsChanges', 'false');
        });

        test(`should add comment with for skipping checks`, async () => {
          const context = createCommentContext({
            username: 'admin',
            body: '/test',
            pullRequestNumber: PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES,
          });
          await getCommandFromComment({ core, context, github });
          expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
          const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
          const createCommentParam = createCommentCall[0];
          expect(createCommentParam.owner).toBe("someOwner");
          expect(createCommentParam.repo).toBe("someRepo");
          expect(createCommentParam.issue_number).toBe(PR_NUMBER_UPSTREAM_DOCS_ONLY_CHANGES);
          expect(createCommentParam.body).toMatch(/PR only contains docs changes - marking tests as complete/);
        });

      })


      test(`for '/test-extended' should set command to 'run-tests-extended'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-extended',
        });
        const command = await getCommandFromComment({ core, context, github });
        expect(command).toBe('run-tests-extended');
      });

      test(`for '/test-extended' should add comment with run link`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-extended',
          pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
        });
        await getCommandFromComment({ core, context, github });
        expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
        const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
        const createCommentParam = createCommentCall[0];
        expect(createCommentParam.owner).toBe("someOwner");
        expect(createCommentParam.repo).toBe("someRepo");
        expect(createCommentParam.issue_number).toBe(PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES);
        expect(createCommentParam.body).toMatch(/Running extended tests: https:\/\/github.com\/someOwner\/someRepo\/actions\/runs\/11112222/);
      });

      test(`for '/test-force-approve' should set command to 'test-force-approve'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-force-approve',
        });
        await getCommandFromComment({ core, context, github });
        expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'test-force-approve');
      });

      test(`for '/test-destroy-env' should set command to 'test-destroy-env'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/test-destroy-env',
        });
        await getCommandFromComment({ core, context, github });
        expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'test-destroy-env');
      });

      test(`for '/help' should add help comment and set command to 'none'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/help',
          pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
        });
        await getCommandFromComment({ core, context, github });
        expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'none');
        expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
        const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
        const createCommentParam = createCommentCall[0];
        expect(createCommentParam.owner).toBe("someOwner");
        expect(createCommentParam.repo).toBe("someRepo");
        expect(createCommentParam.issue_number).toBe(PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES);
        expect(createCommentParam.body).toMatch(/Hello!\n\nYou can use the following commands:/);
      });

      test(`for '/not-a-command' should add help comment and set command to 'none'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: '/not-a-command',
          pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
        });
        await getCommandFromComment({ core, context, github });
        expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'none');
        expect(mockGithubRestIssuesCreateComment.mock.calls.length).toBe(1);
        const createCommentCall = mockGithubRestIssuesCreateComment.mock.calls[0];
        const createCommentParam = createCommentCall[0];
        expect(createCommentParam.owner).toBe("someOwner");
        expect(createCommentParam.repo).toBe("someRepo");
        expect(createCommentParam.issue_number).toBe(PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES);
        expect(createCommentParam.body).toMatch(/`\/not-a-command` is not recognised as a valid command.\n\nYou can use the following commands:/);
      });
    });


    describe('and multi-line comments', () => {
      test(`when first line of comment is '/test' should set command to 'run-tests'`, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: `/test
Other comment content
goes here`,
        });
        await getCommandFromComment({ core, context, github });
        expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'run-tests');
      });

      test(`when comment doesn't start with '/' (even if later lines contain '/test') should set command to 'none' `, async () => {
        const context = createCommentContext({
          username: 'admin',
          body: `Non-command comment
/test
Other comment content
goes here`,
        });
        await getCommandFromComment({ core, context, github });
        expect(mockCoreSetOutput).toHaveBeenCalledWith('command', 'none');
      });
    });

  });


  describe('PR context', () => {
    test('should set prRef output', async () => {
      // prRef should be set to the SHA for the potentialMergeCommit for the PR
      const context = createCommentContext({
        pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('prRef', '123456789a');
    });

    test('should set prRefId output', async () => {
      // Using a PR number of 123 should give a refid of 'cbce50da'
      // Based on running `echo "refs/pull/123/merge" | shasum | cut -c1-8` (as per the original bash scripts)
      const context = createCommentContext({
        pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES
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
        pullRequestNumber: PR_NUMBER_FORK_NON_DOCS_CHANGES
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput.mock.calls.some(c => c[0] == 'branchRefId')).toBe(false);
    });

    test('should set branchRefId for PR from upstream repo', async () => {
      // Using PR 123 which is faked as a PR from the upstream repo
      // The Using a PR number of 123 should give a refid of '71f7c907'
      // Based on running `echo "refs/heads/pr-head-ref" | shasum | cut -c1-8` (as per the original bash scripts)
      const context = createCommentContext({
        pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES
      });
      await getCommandFromComment({ core, context, github });
      expect(mockCoreSetOutput).toHaveBeenCalledWith('branchRefId', '71f7c907');
    });

    test('should set prHeadSha output', async () => {
      // prHeadSha should be the SHA for the head commit for the PR
      const context = createCommentContext({
        pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES
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
      pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
    });
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github });
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalled(); // should set the label for non-contributor
  });

  test(`should return not apply the 'external' label for contributor author`, async () => {
    const context = createPullRequestContext({
      username: 'admin',
      pullRequestNumber: PR_NUMBER_UPSTREAM_NON_DOCS_CHANGES,
    });
    await labelAsExternalIfAuthorDoesNotHaveWriteAccess({ core, context, github });
    expect(mockGithubRestIssuesAddLabels).toHaveBeenCalledTimes(0); // shouldn't set the label for contributor
  });

});

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const yaml = require('js-yaml');

const root = path.resolve(__dirname, '../..');
const workflow = name => yaml.load(fs.readFileSync(path.join(root, '.github/workflows', name), 'utf8'));

function prepare(job, location, ref, output) {
  const step = job.steps.find(value => value.id === 'environment-id' || value.id === 'run-id');
  execFileSync('bash', ['-c', step.run], {
    cwd: root,
    env: { ...process.env, CI_GIT_REF: ref, CI_LOCATION: location, CI_AZURE_ENVIRONMENT: 'AzureCloud',
      GITHUB_REF: ref, GITHUB_SHA: 'test-commit', GITHUB_OUTPUT: output },
    encoding: 'utf8'
  });
  return fs.readFileSync(output, 'utf8').trim().split('=').at(-1);
}

function resolve(value, output) {
  const match = value.match(/^\$\{\{\s*format\('([^']+)',\s*needs\.[^.]+\.outputs\.refid\)\s*\}\}$/);
  if (!match) throw new Error(`Unexpected environment name expression: ${value}`);
  return match[1].replace('{0}', output);
}

describe('regional CI workflow routing', () => {
  let directory;
  beforeEach(() => { directory = fs.mkdtempSync(path.join(os.tmpdir(), 'azuretre-ci-id-')); });
  afterEach(() => { fs.rmSync(directory, { recursive: true, force: true }); });

  test.each([
    ['pr_comment_bot.yml', 'prepare_pr_env', 'run_test', 'refs/pull/5092/merge'],
    ['deploy_tre_branch.yml', 'prepare-not-main', 'run-deploy-tre-not-main', 'refs/heads/fix/keyvault']
  ])('%s separates all environment resource names across regions', (file, preparation, deployment, ref) => {
    const jobs = workflow(file).jobs;
    const first = prepare(jobs[preparation], 'swedencentral', ref, path.join(directory, 'first'));
    const second = prepare(jobs[preparation], 'switzerlandnorth', ref, path.join(directory, 'second'));
    expect(second).not.toBe(first);
    const names = { TRE_ID: 'tre', ACR_NAME: 'tre', MGMT_RESOURCE_GROUP_NAME: 'rg-tre',
      MGMT_STORAGE_ACCOUNT_NAME: 'tre', ENCRYPTION_KV_NAME: 'tre' };
    for (const [input, prefix] of Object.entries(names)) {
      const expression = jobs[deployment].secrets[input];
      expect(resolve(expression, first)).not.toBe(resolve(expression, second));
      expect(resolve(expression, second)).toContain(`${prefix}${second}`);
    }
    expect(jobs[deployment].with.ciEnvironmentId).toContain(`needs.${preparation}.outputs.refid`);
    expect(jobs[deployment].with.DEVCONTAINER_TAG).toContain(`needs.${preparation}.outputs.refid`);
  });

  test('PR preparation uses the same GitHub environment as deployment', () => {
    const jobs = workflow('pr_comment_bot.yml').jobs;
    expect(jobs.prepare_pr_env.environment).toBe(jobs.run_test.with.environmentName);
    expect(jobs.run_test.needs).toContain('prepare_pr_env');
    expect(jobs.prepare_pr_env.steps.find(step => step.id === 'environment-id').env.CI_LOCATION).toBe('${{ vars.LOCATION }}');
  });

  test('branch preparation uses the selected deployment environment', () => {
    const jobs = workflow('deploy_tre_branch.yml').jobs;
    expect(jobs['prepare-not-main'].environment).toBe('${{ inputs.environment }}');
    expect(jobs['prepare-not-main'].steps[0].name).toBe('Checkout');
  });

  test('regional identity reaches the lease guard without changing non-CI defaults', () => {
    const reusable = workflow('deploy_tre_reusable.yml');
    expect(reusable.on.workflow_call.inputs.ciEnvironmentId.default).toBe('');
    expect(reusable.env.CI_ENVIRONMENT_ID).toBe('${{ inputs.ciEnvironmentId }}');
    const action = fs.readFileSync(path.join(root, '.github/actions/devcontainer_run_command/action.yml'), 'utf8');
    expect(action).toContain('-e CI_ENVIRONMENT_ID');
    expect(workflow('deploy_tre.yml').jobs).toBeDefined();
  });

  test('explicit cleanup selects tagged environments and shares deployment concurrency', () => {
    const jobs = workflow('pr_comment_bot.yml').jobs;
    for (const job of [jobs.destroy_pr_env, jobs.destroy_branch_env]) {
      expect(job.concurrency.group).toMatch(/^deploy-/);
      expect(job.concurrency['cancel-in-progress']).toBe(false);
      const step = job.steps.find(value => value.name === 'Run deployment cleanup');
      expect(step.run).toContain('destroy_ci_ref_env.py --ref "$CI_GIT_REF" --subscription "$AZURE_SUBSCRIPTION_ID"');
      expect(step.env.CI_GIT_REF).toMatch(/outputs\.(ciGitRef|branchCiGitRef)/);
    }
  });
});

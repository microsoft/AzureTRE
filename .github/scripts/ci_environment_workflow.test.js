const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const yaml = require('js-yaml');
const vm = require('vm');

const root = path.resolve(__dirname, '../..');
const workflow = name => yaml.load(fs.readFileSync(path.join(root, '.github/workflows', name), 'utf8'));

describe('reference concurrency queues', () => {
  test.each([
    ['deploy_tre.yml', 'run-deploy-tre-main', '${{ github.ref }}'],
    ['pr_comment_bot.yml', 'run_test', '${{ needs.pr_comment.outputs.ciGitRef }}']
  ])('%s routes deployment into the shared queue without an outer queue', (file, job, ref) => {
    const caller = workflow(file);
    expect(caller.concurrency).toBeUndefined();
    expect(caller.jobs[job].concurrency).toBeUndefined();
    expect(caller.jobs[job].uses).toBe('./.github/workflows/deploy_tre_reusable.yml');
    expect(caller.jobs[job].with.ciGitRef).toBe(ref);
    expect(caller.jobs[job].with.callerOwnsDeploymentLock).toBeUndefined();
    // Preparation may run independently, but must not add another waiting group.
    const needs = caller.jobs[job].needs || [];
    for (const dependency of Array.isArray(needs) ? needs : [needs]) {
      expect(caller.jobs[dependency].concurrency).toBeUndefined();
    }
  });

  test('branch validation owns the reference queue before preparation', () => {
    const caller = workflow('deploy_tre_branch.yml');
    expect(caller.concurrency).toEqual({ group: 'deploy-${{ github.ref }}', 'cancel-in-progress': false, queue: 'max' });
    const job = caller.jobs['run-deploy-tre-not-main'];
    expect(job.uses).toBe('./.github/workflows/deploy_tre_reusable.yml');
    expect(job.with.ciGitRef).toBe('${{ github.ref }}');
    expect(job.with.callerOwnsDeploymentLock).toBe(true);
    expect(Object.values(caller.jobs).every(value => value.concurrency === undefined)).toBe(true);
  });

  test('delegation avoids a nested reference lock and preserves the default queue', () => {
    const reusable = workflow('deploy_tre_reusable.yml');
    expect(reusable.on.workflow_call.inputs.callerOwnsDeploymentLock).toMatchObject({
      type: 'boolean', required: false, default: false
    });
    expect(reusable.concurrency).toEqual({
      group: "${{ inputs.callerOwnsDeploymentLock && format('deploy-delegated-{0}-{1}', github.run_id, github.run_attempt) " +
        "|| format('deploy-{0}', inputs.ciGitRef) }}",
      'cancel-in-progress': false,
      queue: 'max'
    });
  });

  test.each([
    ['pr_comment_bot.yml', 'destroy_pr_env', 'deploy-${{ needs.pr_comment.outputs.ciGitRef }}'],
    ['pr_comment_bot.yml', 'destroy_branch_env', 'deploy-${{ needs.pr_comment.outputs.branchCiGitRef }}'],
    ['clean_validation_envs.yml', 'clean', 'deploy-${{ matrix.ref }}'],
    ['clean_validation_envs.yml', 'validate',
      'deploy-refs/heads/ci-cleanup-validation/${{ github.run_id }}-${{ github.run_attempt }}']
  ])('%s %s preserves both the active owner and queued writers', (file, job, group) => {
    const definition = workflow(file);
    const owner = job ? definition.jobs[job] : definition;
    // Parse YAML because actionlint currently ignores the unsupported queue key.
    // A scheduled cleanup must not replace a deployment that is already pending.
    expect(owner.concurrency).toEqual({ group, 'cancel-in-progress': false, queue: 'max' });
  });

  test('every reference group participant preserves pending work', () => {
    for (const file of fs.readdirSync(path.join(root, '.github/workflows')).filter(name => /\.ya?ml$/.test(name))) {
      const definition = workflow(file);
      for (const owner of [definition, ...Object.values(definition.jobs || {})]) {
        const group = typeof owner.concurrency === 'string' ? owner.concurrency : owner.concurrency?.group;
        if (typeof group === 'string' && group.startsWith('deploy-')) {
          expect({ file, ...owner.concurrency }).toEqual({ file, group, 'cancel-in-progress': false, queue: 'max' });
        }
      }
    }
  });
});

function e2eCondition(job, lockResult, skipDeployment) {
  const needs = Object.fromEntries(job.needs.map(name => [name, {
    result: name === 'verify_deployment_lock' ? lockResult
      : name.startsWith('e2e_tests_') ? 'success' : (skipDeployment ? 'skipped' : 'success')
  }]));
  const inputs = { e2eBundle: '', e2eTestsCustomSelector: 'airlock', skipDeployment };
  const results = Object.values(needs).map(value => value.result);
  const expression = job.if.trim().slice(3, -2).replaceAll('needs.*.result', 'results');
  return vm.runInNewContext(expression, {
    needs, inputs, results, always: () => true, contains: (values, value) => values.includes(value)
  }, { timeout: 100 });
}

describe('delegated deployment guard', () => {
  test('the guard reads workflow source and has no Azure credentials', () => {
    const job = workflow('deploy_tre_reusable.yml').jobs.verify_deployment_lock;
    expect(job.permissions).toEqual({ actions: 'read', contents: 'read' });
    expect(job.steps[0].if).toBe('inputs.callerOwnsDeploymentLock');
    expect(job.steps[0].with).toEqual({ 'persist-credentials': false, ref: '${{ github.sha }}' });
    const check = job.steps.find(step => step.run?.includes('verify_deployment_lock.py'));
    expect(check.if).toBe('inputs.callerOwnsDeploymentLock');
    expect(check.env).toEqual({
      CI_DEPLOYMENT_LOCK_DELEGATED: '${{ inputs.callerOwnsDeploymentLock }}',
      CI_GIT_REF: '${{ inputs.ciGitRef }}',
      GITHUB_TOKEN: '${{ github.token }}'
    });
    const fallback = job.steps.find(step => step.if === '${{ !inputs.callerOwnsDeploymentLock }}');
    expect(fallback.run).toBe('echo "The reusable workflow holds the deployment reference lock."');
  });

  test('every Azure job depends on the guard', () => {
    const jobs = workflow('deploy_tre_reusable.yml').jobs;
    expect(Object.keys(jobs).filter(name => !jobs[name].needs)).toEqual(['verify_deployment_lock']);
    expect(jobs.deploy_management.needs).toEqual(['verify_deployment_lock']);
    for (const name of ['e2e_tests_smoke', 'e2e_tests_custom']) {
      expect(jobs[name].needs).toContain('verify_deployment_lock');
    }
  });

  test.each(['success', 'failure', 'cancelled', 'skipped'])('E2E requires guard success when its result is %s', result => {
    const jobs = workflow('deploy_tre_reusable.yml').jobs;
    for (const name of ['e2e_tests_smoke', 'e2e_tests_custom']) {
      for (const skipDeployment of [true, false]) {
        expect(e2eCondition(jobs[name], result, skipDeployment)).toBe(result === 'success');
      }
    }
  });

  test('guard changes select the DevOps tests', () => {
    const filter = workflow('build_validation_develop.yml').jobs;
    const steps = Object.values(filter).flatMap(job => job.steps || []);
    const paths = yaml.load(steps.find(step => step.id === 'filter').with.filters);
    expect(paths.ci_cleanup).toContain('devops/scripts/verify_deployment_lock.py');
  });
});

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

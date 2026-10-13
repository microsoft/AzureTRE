const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const root = path.resolve(__dirname, '../..');
const readYaml = (relativePath) => yaml.load(fs.readFileSync(path.join(root, relativePath), 'utf8'));

test('reusable deployments disable retention unless the caller opts in', () => {
  const workflow = readYaml('.github/workflows/deploy_tre_reusable.yml');
  expect(workflow.on.workflow_call.inputs.enableCiCertificateCache).toMatchObject({
    type: 'boolean', default: false, required: false,
  });
  const steps = Object.values(workflow.jobs).flatMap((job) => job.steps || []);
  const core = steps.filter((step) => (step.with?.COMMAND || '').includes('make deploy-core'));
  expect(core).toHaveLength(1);
  expect(core[0].with.COMMAND).toContain('TF_VAR_enable_ci_certificate_cache=${{ inputs.enableCiCertificateCache }}');
});

test.each(['pr_comment_bot.yml', 'deploy_tre_branch.yml', 'deploy_tre.yml'])(
  '%s explicitly enables the cache for CI validation', (filename) => {
    const workflow = readYaml(`.github/workflows/${filename}`);
    const callers = Object.values(workflow.jobs).filter(
      (job) => job.uses === './.github/workflows/deploy_tre_reusable.yml',
    );
    expect(callers).toHaveLength(1);
    expect(callers[0].with.enableCiCertificateCache).toBe(true);
  },
);

test('install and renew use the optional cache and keep gateway cleanup inside the script', () => {
  const bundle = readYaml('templates/shared_services/certs/porter.yaml');
  const cache = bundle.parameters.find((parameter) => parameter.name === 'certificate_cache_vault_name');
  expect(cache).toMatchObject({type: 'string', default: ''});
  for (const action of ['install', 'renew']) {
    const scripts = bundle[action].filter(
      (step) => step.exec?.arguments?.includes('./scripts/letsencrypt.sh'),
    );
    expect(scripts).toHaveLength(1);
    expect(scripts[0].exec.flags.cache_vault_name).toBe('${ bundle.parameters.certificate_cache_vault_name }');
    expect(scripts[0].exec.flags.start_gateway).toBe(action === 'renew' ? 'true' : undefined);
    expect(bundle[action].some((step) => step.az?.arguments?.includes('application-gateway'))).toBe(false);
  }
  const parameters = JSON.parse(fs.readFileSync(path.join(root, 'templates/shared_services/certs/parameters.json')));
  expect(parameters.parameters.find((parameter) => parameter.name === cache.name).source).toEqual({value: ''});
  const schema = JSON.parse(fs.readFileSync(path.join(root, 'templates/shared_services/certs/template_schema.json')));
  expect(schema.properties).not.toHaveProperty(cache.name);
});

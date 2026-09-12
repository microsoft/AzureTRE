const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const test = require('node:test');

const root = path.resolve(__dirname, '../../../..');
const testRequire = createRequire(path.join(__dirname, 'package.json'));
const { retrieveSchema, getDefaultFormState } = testRequire('@rjsf/utils');
const validator = testRequire('@rjsf/validator-ajv8').default;
const yaml = testRequire('js-yaml');
const bundle = path.resolve(__dirname, '..');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const readYaml = file => yaml.load(fs.readFileSync(file, 'utf8'));
const schema = readJson(path.join(bundle, 'template_schema.json'));
const manifest = readYaml(path.join(bundle, 'porter.yaml'));
const pooledFields = ['maximum_sessions', 'pooled_session_host_count', 'pooled_vm_size', 'pooled_os_image'];

test('count-only updates remain validated without the immutable pool selector', () => {
  const updateSchema = {
    ...schema,
    required: [],
    properties: Object.fromEntries(Object.entries(schema.properties).filter(([, property]) => property.updateable)),
  };
  const patch = { pooled_session_host_count: 2 };
  const resolved = retrieveSchema(validator, updateSchema, updateSchema, patch);
  assert.equal(resolved.properties.pooled_session_host_count?.updateable, true);
  assert.deepEqual(validator.validateFormData(patch, updateSchema).errors, []);
  for (const invalid of [0, 11, 1.5, '2']) {
    assert(validator.validateFormData({ pooled_session_host_count: invalid }, updateSchema).errors.length > 0);
  }
});

test('pooled bootstrap uses UTF-8 and stays within the Windows command limit', () => {
  const terraform = fs.readFileSync(path.join(bundle, 'terraform/pooled_session_hosts.tf'), 'utf8');
  assert(terraform.includes('FromBase64String(\'${base64encode(templatefile('));
  assert(!terraform.includes('-EncodedCommand'));
  const values = {
    artifact_url: 'https://stgws9a4e.blob.core.windows.net/avd-dsc/Configuration.zip',
    artifact_sha256: 'a'.repeat(64),
    host_pool_name: 'vdpool-tre0409-ws-9a4e-2e22',
    registration_token: 'a'.repeat(2048),
    clipboard_server_to_client: 0,
    clipboard_client_to_server: 1,
    mount_storage_command: '',
  };
  const script = fs.readFileSync(path.join(bundle, 'terraform/configure_session_host.ps1.tftpl'), 'utf8')
    .replace(/\$\{([^}]+)\}/g, (match, key) => {
      assert(Object.hasOwn(values, key), `Missing template value: ${key}`);
      return values[key];
    });
  const command = `powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('${Buffer.from(script).toString('base64')}'))))"`;
  assert(command.length < 8191, `Bootstrap command is too long: ${command.length}`);
});

for (const host_pool_type of ['Personal', 'Pooled']) {
  for (const enable_clipboard of [false, true]) {
    test(`${host_pool_type}, clipboard=${enable_clipboard}: conditional fields and defaults`, () => {
      const data = getDefaultFormState(validator, schema, { host_pool_type, enable_clipboard }, schema);
      const resolved = retrieveSchema(validator, schema, schema, data);
      for (const field of pooledFields) {
        assert.equal(Object.hasOwn(resolved.properties, field), host_pool_type === 'Pooled');
      }
      assert.equal(Object.hasOwn(resolved.properties, 'clipboard_transfer_direction'), enable_clipboard);
      assert.deepEqual(validator.validateFormData(data, schema).errors, []);
      if (host_pool_type === 'Pooled') {
        assert.equal(data.pooled_session_host_count, 1);
        assert.equal(data.pooled_os_image, 'Windows 11 25H2 Multi-Session');
        assert.equal(resolved.properties.pooled_session_host_count.updateable, true);
        for (const invalid of [0, 11, 1.5]) {
          assert(validator.validateFormData({ ...data, pooled_session_host_count: invalid }, schema).errors.length > 0);
        }
      }
    });
  }
}

test('changing selectors hides fields even when previous values remain', () => {
  const data = getDefaultFormState(validator, schema, { host_pool_type: 'Pooled', enable_clipboard: true }, schema);
  const resolved = retrieveSchema(validator, schema, schema, { ...data, host_pool_type: 'Personal', enable_clipboard: false });
  for (const field of [...pooledFields, 'clipboard_transfer_direction']) {
    assert.equal(Object.hasOwn(resolved.properties, field), false);
  }
});

test('pooled image catalogue matches schema, defaults and every lifecycle action', () => {
  const images = manifest.custom.image_options;
  const resolved = retrieveSchema(validator, schema, schema, { host_pool_type: 'Pooled' });
  assert.deepEqual(resolved.properties.pooled_os_image.enum, Object.keys(images));
  const parameter = manifest.parameters.find(entry => entry.name === 'pooled_os_image');
  assert.equal(parameter.default, resolved.properties.pooled_os_image.default);
  for (const image of Object.values(images)) {
    assert.match(image.source_image_reference.sku, /-avd$/);
    assert.equal(image.secure_boot_enabled, true);
    assert.equal(image.vtpm_enabled, true);
    assert.equal(image.license_type, 'Windows_Client');
  }
  for (const action of ['install', 'upgrade', 'uninstall']) {
    assert.equal(manifest[action][0].terraform.vars.pooled_os_image, '${ bundle.parameters.pooled_os_image }');
  }
  const parameters = readJson(path.join(bundle, 'parameters.json'));
  assert(parameters.parameters.some(entry => entry.name === 'pooled_os_image' && entry.source.env === 'POOLED_OS_IMAGE'));
});

test('personal default uses 25H2 and both bundles declare v1', () => {
  const child = path.join(bundle, 'user_resources/avd-personal-sessionhost');
  const childManifest = readYaml(path.join(child, 'porter.yaml'));
  const childSchema = readJson(path.join(child, 'template_schema.json'));
  const defaultImage = childManifest.parameters.find(entry => entry.name === 'os_image').default;
  assert.equal(defaultImage, childSchema.properties.os_image.default);
  for (const image of childSchema.properties.os_image.enum) {
    assert.match(childManifest.custom.image_options[image].source_image_reference.sku, /25h2/);
  }
  assert.equal(manifest.version, '1.0.1');
  assert.equal(childManifest.version, '1.0.0');
});

test('deployment workflow publishes and registers both AVD bundles', () => {
  const jobs = readYaml(path.join(root, '.github/workflows/deploy_tre_reusable.yml')).jobs;
  const parent = './templates/workspace_services/avd';
  const child = parent + '/user_resources/avd-personal-sessionhost';
  const entries = job => jobs[job].strategy.matrix.include;
  for (const bundlePath of [parent, child]) assert(entries('publish_bundles').some(entry => entry.BUNDLE_DIR === bundlePath));
  assert(entries('register_bundles').some(entry => entry.BUNDLE_DIR === parent));
  assert(entries('register_user_resource_bundles').some(entry => entry.BUNDLE_DIR === child && entry.WORKSPACE_SERVICE_NAME === 'tre-service-avd'));
});

test('pull request validation runs both AVD regression suites', () => {
  const workflow = readYaml(path.join(root, '.github/workflows/build_validation_develop.yml'));
  assert(workflow.on.pull_request.branches.includes('main'));
  const job = workflow.jobs.avd_template_tests;
  assert.equal(job.permissions.contents, 'read');
  assert(job.steps.some(step => step['working-directory'] === 'templates/workspace_services/avd/tests' && step.run === 'npm ci --ignore-scripts --no-audit --no-fund'));
  for (const command of [
    'node --test templates/workspace_services/avd/tests/schema.test.cjs',
    'bash templates/workspace_services/avd/tests/test_registration_initialization.sh',
  ]) {
    const step = job.steps.find(entry => entry.run === command);
    assert(step, `Missing CI command: ${command}`);
    assert(!step.if);
    assert(!step['continue-on-error']);
  }
});
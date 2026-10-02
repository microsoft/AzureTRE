const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const retry = path.join(__dirname, 'dockerfile_build_retry.sh');
const target = path.join(__dirname, 'dockerfile_build_target.sh');

describe('Dockerfile build retries', () => {
  let fixture;
  let environment;

  function executable(filename, contents) {
    const destination = path.join(fixture, filename);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, contents, { mode: 0o755 });
    return destination;
  }

  function records(filename) {
    const destination = path.join(fixture, filename);
    return fs.existsSync(destination) ? JSON.parse(fs.readFileSync(destination, 'utf8')) : [];
  }

  beforeEach(() => {
    fixture = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'tre-build-retry-')));
    fs.mkdirSync(path.join(fixture, 'runner-temp'));
    executable('bin/sleep', '#!/bin/bash\nprintf "%s\\n" "$*" >> "$SLEEP_LOG"\n');
    environment = {
      ...process.env,
      PATH: `${path.join(fixture, 'bin')}:${process.env.PATH}`,
      GITHUB_WORKSPACE: fixture,
      RUNNER_TEMP: path.join(fixture, 'runner-temp'),
      SLEEP_LOG: path.join(fixture, 'sleep.log'),
      BUILD_LOG: path.join(fixture, 'builds.json'),
      INSTALL_LOG: path.join(fixture, 'installs.json'),
      EXIT_CODES: '0',
      FAIL_FIRST_INSTALL: 'false',
    };
    delete environment.PORTER_HOME;
  });

  afterEach(() => fs.rmSync(fixture, { recursive: true, force: true }));

  const buildCommand = `#!/usr/bin/env node
const fs = require('node:fs');
const logfile = process.env.BUILD_LOG;
const calls = fs.existsSync(logfile) ? JSON.parse(fs.readFileSync(logfile, 'utf8')) : [];
calls.push({ args: process.argv.slice(2), cwd: process.cwd(), porterHome: process.env.PORTER_HOME });
fs.writeFileSync(logfile, JSON.stringify(calls));
console.log('Command output for attempt ' + calls.length);
const codes = process.env.EXIT_CODES.split(',').map(Number);
process.exit(codes[Math.min(calls.length - 1, codes.length - 1)]);
`;

  function run(command, args = [], overrides = {}) {
    return spawnSync('bash', [retry, command, ...args], {
      cwd: fixture, encoding: 'utf8', env: { ...environment, ...overrides },
    });
  }

  test('a successful command runs once and preserves arguments', () => {
    const command = executable('command', buildCommand);
    const result = run(command, ['a value with spaces', '--flag']);
    expect(result.status).toBe(0);
    expect(records('builds.json')).toEqual([{ args: ['a value with spaces', '--flag'], cwd: fixture }]);
    expect(result.stdout).not.toContain('::warning::');
    expect(fs.existsSync(environment.SLEEP_LOG)).toBe(false);
  });

  test('a failed command retries once after ten seconds and keeps both logs', () => {
    const command = executable('command', buildCommand);
    const result = run(command, [], { EXIT_CODES: '6,0' });
    expect(result.status).toBe(0);
    expect(records('builds.json')).toHaveLength(2);
    expect(fs.readFileSync(environment.SLEEP_LOG, 'utf8')).toBe('10\n');
    expect(result.stdout).toContain('::warning::Build attempt 1 failed');
    expect(result.stdout).toContain('Command output for attempt 1');
    expect(result.stdout).toContain('Command output for attempt 2');
    expect(result.stderr).not.toContain('::error::');
  });

  test('two failures return the second exit code and never try a third time', () => {
    const command = executable('command', buildCommand);
    const result = run(command, [], { EXIT_CODES: '6,35,0' });
    expect(result.status).toBe(35);
    expect(records('builds.json')).toHaveLength(2);
    expect(result.stderr).toContain('::error::Both build attempts failed');
  });

  test.each([130, 143])('cancellation exit code %s stops without retrying', code => {
    const command = executable('command', buildCommand);
    const result = run(command, [], { EXIT_CODES: `${code},0` });
    expect(result.status).toBe(code);
    expect(records('builds.json')).toHaveLength(1);
    expect(fs.existsSync(environment.SLEEP_LOG)).toBe(false);
  });

  test('a missing command fails', () => {
    const result = spawnSync('bash', [retry], { encoding: 'utf8' });
    expect(result.status).toBe(2);
    expect(result.stderr).toContain('Usage:');
  });

  test.each(['', 'INTERACTIVE=true OTHER=value'])(
    'Docker builds preserve paths and retry with build arguments %j', buildArgs => {
      executable('bin/docker', buildCommand);
      const result = run(target, [], {
        TARGET_KIND: 'docker', DOCKERFILE: 'folder with spaces/Dockerfile',
        CONTEXT: 'build context', BUILD_ARGS: buildArgs, EXIT_CODES: '1,0',
      });
      expect(result.status).toBe(0);
      const args = ['buildx', 'build', '--pull'];
      if (buildArgs) args.push('--build-arg', 'INTERACTIVE=true', '--build-arg', 'OTHER=value');
      args.push('--file', 'folder with spaces/Dockerfile', 'build context');
      expect(records('builds.json')).toEqual([{ args, cwd: fixture }, { args, cwd: fixture }]);
    },
  );

  function porterFixture() {
    const bundle = 'templates/workspace_services/test service';
    fs.mkdirSync(path.join(fixture, bundle), { recursive: true });
    executable('mock-porter', buildCommand);
    executable('.devcontainer/scripts/porter-v1.sh', `#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const logfile = process.env.INSTALL_LOG;
const calls = fs.existsSync(logfile) ? JSON.parse(fs.readFileSync(logfile, 'utf8')) : [];
calls.push({ home: process.env.PORTER_HOME, version: process.env.PORTER_VERSION,
  terraform: process.env.PORTER_TERRAFORM_MIXIN_VERSION,
  az: process.env.PORTER_AZ_MIXIN_VERSION, azure: process.env.PORTER_AZURE_PLUGIN_VERSION });
fs.writeFileSync(logfile, JSON.stringify(calls));
fs.mkdirSync(path.join(process.env.PORTER_HOME, 'runtimes'));
fs.symlinkSync(path.join(process.env.PORTER_HOME, 'porter'), path.join(process.env.PORTER_HOME, 'runtimes/porter-runtime'));
if (process.env.FAIL_FIRST_INSTALL === 'true' && calls.length === 1) process.exit(7);
fs.copyFileSync(path.join(process.env.GITHUB_WORKSPACE, 'mock-porter'), path.join(process.env.PORTER_HOME, 'porter'));
fs.chmodSync(path.join(process.env.PORTER_HOME, 'porter'), 0o755);
`);
    fs.writeFileSync(path.join(fixture, '.devcontainer/Dockerfile'), [
      'ARG PORTER_VERSION=v1.4.0', 'ARG PORTER_TERRAFORM_MIXIN_VERSION=v1.0.8',
      'ARG PORTER_AZ_MIXIN_VERSION=v1.0.7', 'ARG PORTER_AZURE_PLUGIN_VERSION=v1.2.4', '',
    ].join('\n'));
    executable('devops/scripts/porter_build_bundle.sh', '#!/bin/bash\nporter build\n');
    return { TARGET_KIND: 'porter', BUNDLE_DIR: bundle };
  }

  function expectCleanInstallations(count) {
    const installs = records('installs.json');
    expect(installs).toHaveLength(count);
    expect(new Set(installs.map(install => install.home)).size).toBe(count);
    for (const install of installs) {
      expect(install).toMatchObject({ version: 'v1.4.0', terraform: 'v1.0.8', az: 'v1.0.7', azure: 'v1.2.4' });
      expect(fs.existsSync(install.home)).toBe(false);
    }
  }

  test('Porter retries a partial installation before building the bundle', () => {
    const options = porterFixture();
    const result = run(target, [], { ...options, FAIL_FIRST_INSTALL: 'true' });
    expect(result.status).toBe(0);
    expectCleanInstallations(2);
    expect(records('builds.json')).toHaveLength(1);
    expect(records('builds.json')[0]).toMatchObject({ args: ['build'], cwd: path.join(fixture, options.BUNDLE_DIR) });
  });

  test.each(['1,0', '1,1'])('Porter retries the whole target after build failures %s', codes => {
    const result = run(target, [], { ...porterFixture(), EXIT_CODES: codes });
    expect(result.status).toBe(Number(codes.split(',')[1]));
    expectCleanInstallations(2);
    expect(records('builds.json')).toHaveLength(2);
  });
});

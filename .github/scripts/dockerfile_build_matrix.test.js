const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');
const yaml = require('js-yaml');
const picomatch = require('picomatch');

const script = path.join(__dirname, 'dockerfile_build_matrix.sh');
const workflow = yaml.load(fs.readFileSync(path.join(__dirname, '../workflows/build_all_dockerfiles.yml'), 'utf8'));
const filters = yaml.load(workflow.jobs.discover.steps.find(step => step.id === 'filter').with.filters);
const repository = path.resolve(__dirname, '../..');
const contextFiles = execFileSync('git', ['ls-files', '*porter-build-context.env'], {
  cwd: repository, encoding: 'utf8',
}).trim().split('\n').filter(Boolean);
const contextDependencies = contextFiles.flatMap(filename => {
  const contents = fs.readFileSync(path.join(repository, filename), 'utf8');
  const declaration = contents.match(/^export PORTER_BUILD_CONTEXT=(["'])(.+)\1\s*$/m);
  if (!declaration) throw new Error(`Cannot read named contexts from ${filename}`);
  const consumer = path.posix.dirname(filename);
  return declaration[2].split(/\s+/).map(context => {
    const separator = context.indexOf('=');
    const directory = context.slice(separator + 1);
    if (separator < 1 || !directory.startsWith('.')) {
      throw new Error(`Expected a local named context in ${filename}: ${context}`);
    }
    return { consumer, source: path.posix.normalize(path.posix.join(consumer, directory)) };
  });
});
const contextSources = [...new Set(contextDependencies.map(dependency => dependency.source))];

describe('Dockerfile build selection', () => {
  let fixture;
  const allNames = ['.devcontainer', 'api_app', 'workspace_services/alpha', 'workspace_services/beta'];

  function addFile(filename) {
    const fullPath = path.join(fixture, filename);
    fs.mkdirSync(path.dirname(fullPath), { recursive: true });
    fs.writeFileSync(fullPath, '');
    execFileSync('git', ['add', '--', filename], { cwd: fixture });
  }

  beforeEach(() => {
    fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'tre-build-matrix-'));
    execFileSync('git', ['init', '-q', fixture]);
    for (const filename of [
      '.devcontainer/Dockerfile', 'api_app/Dockerfile',
      'templates/workspace_services/alpha/Dockerfile.tmpl',
      'templates/workspace_services/alpha/porter.yaml',
      'templates/workspace_services/beta/Dockerfile.tmpl',
      'templates/workspace_services/beta/porter.yaml',
    ]) addFile(filename);
  });

  afterEach(() => fs.rmSync(fixture, { recursive: true, force: true }));

  function run(changes = [], overrides = {}) {
    const output = path.join(fixture, 'output');
    fs.rmSync(output, { force: true });
    const result = spawnSync('bash', [script], {
      cwd: fixture, encoding: 'utf8',
      env: {
        ...process.env, EVENT_NAME: 'pull_request', WORKFLOW_CHANGED: 'false',
        CHANGED_FILES: JSON.stringify(changes), GITHUB_OUTPUT: output, ...overrides,
      },
    });
    const matrix = fs.existsSync(output)
      ? JSON.parse(fs.readFileSync(output, 'utf8').trim().replace(/^matrix=/, '')) : null;
    return { ...result, matrix };
  }

  function names(changes, overrides) {
    const result = run(changes, overrides);
    expect(result.stderr).toBe('');
    expect(result.status).toBe(0);
    return result.matrix.map(target => target.name).sort();
  }

  function addContextBundles() {
    const directories = new Set(contextDependencies.flatMap(({ consumer, source }) => [consumer, source]));
    for (const directory of directories) {
      addFile(`${directory}/Dockerfile.tmpl`);
      addFile(`${directory}/porter.yaml`);
    }
  }

  function contextTargets(source) {
    return [...new Set([
      source,
      ...contextDependencies.filter(dependency => dependency.source === source).map(dependency => dependency.consumer),
    ])].map(directory => directory.replace(/^templates\//, '')).sort();
  }

  test.each(['schedule', 'workflow_dispatch'])('%s selects every tracked target', event => {
    expect(names([], { EVENT_NAME: event })).toEqual(allNames);
  });

  test('workflow changes select every target', () => {
    expect(names([], { WORKFLOW_CHANGED: 'true' })).toEqual(allNames);
  });

  test.each(['Dockerfile.tmpl', 'porter.yaml', 'porter-build-context.env'])(
    '%s selects its bundle', filename => {
      expect(names([`templates/workspace_services/alpha/${filename}`])).toEqual(['workspace_services/alpha']);
    },
  );

  test('a plain Dockerfile selects its own image', () => {
    expect(names(['api_app/Dockerfile'])).toEqual(['api_app']);
  });

  test.each(['.devcontainer/Dockerfile', '.devcontainer/scripts/porter-v1.sh'])(
    '%s selects the dev container and every bundle', filename => {
      expect(names([filename])).toEqual(['.devcontainer', 'workspace_services/alpha', 'workspace_services/beta']);
    },
  );

  test('the shared build helper selects every bundle', () => {
    expect(names(['devops/scripts/porter_build_bundle.sh'])).toEqual(['workspace_services/alpha', 'workspace_services/beta']);
  });

  test('other dev-container files select only the dev container', () => {
    expect(names(['.devcontainer/a file with spaces.json'])).toEqual(['.devcontainer']);
  });

  test.each(contextSources)('changes within %s select its bundle and every named-context consumer', source => {
    addContextBundles();
    expect(names([`${source}/nested/source.tf`])).toEqual(contextTargets(source));
  });

  test.each(contextSources)('deleted files within %s still select every affected bundle', source => {
    addContextBundles();
    const filename = `${source}/nested/deleted.tf`;
    addFile(filename);
    execFileSync('git', ['rm', '-f', filename], { cwd: fixture });
    expect(names([filename])).toEqual(contextTargets(source));
  });

  test('a sibling with a shared directory prefix does not select named-context consumers', () => {
    addContextBundles();
    expect(names(['templates/workspaces/base-other/terraform/main.tf'])).toEqual([]);
  });

  test.each([{ changes: [] }, { changes: ['README.md'] }])('unrelated changes select nothing: $changes', ({ changes }) => {
    expect(names(changes)).toEqual([]);
  });

  test('the dev-container result is not a hidden file that artifact upload would exclude', () => {
    const result = run(['.devcontainer/Dockerfile']);
    expect(result.status).toBe(0);
    expect(result.matrix.find(target => target.name === '.devcontainer').safe_name).toBe('devcontainer');
  });

  test('deleted plain Dockerfiles are excluded', () => {
    execFileSync('git', ['rm', '-f', 'api_app/Dockerfile'], { cwd: fixture });
    expect(names(['api_app/Dockerfile'])).toEqual([]);
  });

  test.each(['Dockerfile.tmpl', 'porter.yaml'])('deleting only %s fails discovery before target selection', filename => {
    const removed = `templates/workspace_services/alpha/${filename}`;
    execFileSync('git', ['rm', '-f', removed], { cwd: fixture });
    for (const [changes, overrides] of [
      [[removed], {}],
      [['README.md'], {}],
      [[], { EVENT_NAME: 'schedule' }],
    ]) {
      const result = run(changes, overrides);
      expect(result.status).not.toBe(0);
      expect(result.stderr).toContain('Incomplete Porter bundle');
      expect(result.stderr).toContain(removed);
      expect(result.matrix).toBeNull();
    }
  });

  test.each(['Dockerfile.tmpl', 'porter.yaml'])('an untracked %s cannot complete a tracked bundle', filename => {
    const untracked = `templates/workspace_services/alpha/${filename}`;
    execFileSync('git', ['rm', '--cached', untracked], { cwd: fixture });
    expect(fs.existsSync(path.join(fixture, untracked))).toBe(true);
    const result = run([untracked]);
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain(untracked);
  });

  test.each(['Dockerfile.tmpl', 'porter.yaml'])('a new bundle with only %s fails discovery', filename => {
    const added = `templates/workspace_services/incomplete/${filename}`;
    addFile(added);
    const result = run([added]);
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain('Incomplete Porter bundle: templates/workspace_services/incomplete');
  });

  test('removing both bundle files excludes the target without failing discovery', () => {
    const removed = ['Dockerfile.tmpl', 'porter.yaml'].map(filename => `templates/workspace_services/alpha/${filename}`);
    execFileSync('git', ['rm', '-f', ...removed], { cwd: fixture });
    expect(names(removed)).toEqual([]);
    expect(names([], { EVENT_NAME: 'schedule' })).toEqual(allNames.filter(name => name !== 'workspace_services/alpha'));
  });

  test('unknown tracked Dockerfiles fail discovery', () => {
    addFile('unknown/Dockerfile');
    const result = run([], { EVENT_NAME: 'schedule' });
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain('unknown/Dockerfile is not listed');
  });

  test('untracked Dockerfiles are ignored', () => {
    fs.mkdirSync(path.join(fixture, 'untracked'));
    fs.writeFileSync(path.join(fixture, 'untracked/Dockerfile'), '');
    expect(names([], { EVENT_NAME: 'schedule' })).toEqual(allNames);
  });

  test.each(['not json', '{}', '[1]'])('invalid file lists fail discovery: %s', changes => {
    expect(run([], { CHANGED_FILES: changes }).status).not.toBe(0);
  });

  test.each([
    '.devcontainer/Dockerfile', '.devcontainer/scripts/porter-v1.sh',
    'devops/scripts/porter_build_bundle.sh',
    'templates/workspaces/unrestricted/porter-build-context.env',
    ...contextSources.map(source => `${source}/nested/source.tf`),
  ])('the trigger and file filter include %s', filename => {
    expect(picomatch(workflow.on.pull_request.paths, { dot: true })(filename)).toBe(true);
    expect(picomatch(filters.build_inputs, { dot: true })(filename)).toBe(true);
  });

  test.each([
    '.github/scripts/dockerfile_build_matrix.sh',
    '.github/scripts/dockerfile_build_matrix.test.js',
    '.github/scripts/dockerfile_build_report.js',
    '.github/scripts/dockerfile_build_report.test.js',
    '.github/scripts/dockerfile_build_retry.sh',
    '.github/scripts/dockerfile_build_retry.test.js',
    '.github/scripts/dockerfile_build_target.sh',
    '.github/workflows/build_all_dockerfiles.yml',
  ])('changes to %s select all targets through the workflow filter', filename => {
    expect(picomatch(workflow.on.pull_request.paths, { dot: true })(filename)).toBe(true);
    expect(picomatch(filters.workflow, { dot: true })(filename)).toBe(true);
  });

  test('the workflow passes changed paths as JSON', () => {
    expect(workflow.jobs.discover.steps.find(step => step.id === 'filter').with['list-files']).toBe('json');
  });
});

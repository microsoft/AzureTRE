const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const yaml = require('js-yaml');
const { createReport } = require('./dockerfile_build_report');

const matrix = [
  { name: 'api_app', safe_name: 'api_app', kind: 'docker' },
  { name: 'workspace_services/ohdsi', safe_name: 'workspace_services_ohdsi', kind: 'porter' },
];

describe('Dockerfile build report', () => {
  let fixture;
  let results;

  beforeEach(() => {
    fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'tre-build-report-'));
    results = path.join(fixture, 'results');
    fs.mkdirSync(results);
  });

  afterEach(() => fs.rmSync(fixture, { recursive: true, force: true }));

  function record(target, status = 'success') {
    fs.writeFileSync(path.join(results, `${target.safe_name}.tsv`), `${target.name}\t${target.kind}\t${status}\n`);
  }

  test('a complete successful build passes', () => {
    matrix.forEach(target => record(target));
    const report = createReport(matrix, results, 'success');
    expect(report.errors).toEqual([]);
    expect(report.summary).toContain('All 2 targets built.');
  });

  test('missing artifacts fail and remain visible in the summary', () => {
    record(matrix[0]);
    const report = createReport(matrix, results, 'failure');
    expect(report.errors).toContain('Build failed: workspace_services/ohdsi (missing)');
    expect(report.summary).toContain('<code>workspace_services/ohdsi</code> | porter | missing');
  });

  test('no artifacts fail with every expected target listed', () => {
    const report = createReport(matrix, path.join(fixture, 'absent'), 'failure');
    expect(report.errors.filter(error => error.includes('(missing)'))).toHaveLength(2);
  });

  test.each(['failure', 'cancelled', 'skipped'])('%s results fail', status => {
    record(matrix[0]);
    record(matrix[1], status);
    expect(createReport(matrix, results, status).errors).toContain(`Build failed: workspace_services/ohdsi (${status})`);
  });

  test('an upload failure is not hidden by successful result files', () => {
    matrix.forEach(target => record(target));
    expect(createReport(matrix, results, 'failure').errors).toContain('Build jobs finished with status: failure');
  });

  test.each([
    '', 'api_app\tdocker\tunknown\n', 'wrong\tdocker\tsuccess\n',
    'api_app\tporter\tsuccess\n', 'api_app\tdocker\tsuccess\napi_app\tdocker\tsuccess\n',
  ])('malformed or mismatched results fail: %j', contents => {
    matrix.forEach(target => record(target));
    fs.writeFileSync(path.join(results, 'api_app.tsv'), contents);
    expect(createReport(matrix, results, 'success').errors).toContain('Build failed: api_app (invalid)');
  });

  test('unexpected artifacts fail validation', () => {
    matrix.forEach(target => record(target));
    fs.writeFileSync(path.join(results, 'extra.tsv'), '');
    expect(createReport(matrix, results, 'success').errors).toContain('Unexpected build result: extra.tsv');
  });

  test('duplicate targets fail validation', () => {
    expect(() => createReport([matrix[0], matrix[0]], results, 'success')).toThrow('Duplicate build target');
  });

  test('artifact paths cannot escape the result directory', () => {
    expect(() => createReport([{ ...matrix[0], safe_name: '../outside' }], results, 'success')).toThrow('Invalid target');
  });

  test('the CLI writes the summary and returns failure for missing results', () => {
    record(matrix[0]);
    const summary = path.join(fixture, 'summary.md');
    const result = spawnSync(process.execPath, [path.join(__dirname, 'dockerfile_build_report.js')], {
      encoding: 'utf8',
      env: {
        ...process.env, EXPECTED_MATRIX: JSON.stringify(matrix), RESULTS_DIRECTORY: results,
        BUILD_RESULT: 'failure', GITHUB_STEP_SUMMARY: summary,
      },
    });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain('::error::Build failed: workspace_services/ohdsi (missing)');
    expect(fs.readFileSync(summary, 'utf8')).toContain('workspace_services/ohdsi');
  });

  test('the workflow reports even if downloading artifacts fails', () => {
    const workflow = yaml.load(fs.readFileSync(path.join(__dirname, '../workflows/build_all_dockerfiles.yml'), 'utf8'));
    const summary = workflow.jobs.report.steps.find(step => step.name === 'Write summary');
    expect(summary.if).toBe('always()');
    expect(summary.env.EXPECTED_MATRIX).toBe('${{ needs.discover.outputs.matrix }}');
    expect(summary.env.BUILD_RESULT).toBe('${{ needs.build.result }}');
    expect(summary.run).toBe('node .github/scripts/dockerfile_build_report.js');
  });
});

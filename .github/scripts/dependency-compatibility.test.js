const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { globSync } = require('glob');
const TestExclude = require('test-exclude');
const { loadNycConfig } = require('@istanbuljs/load-nyc-config');

describe('build dependency compatibility', () => {
  let fixtureDirectory;

  beforeEach(() => {
    fixtureDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'tre-dependency-test-'));
    fs.mkdirSync(path.join(fixtureDirectory, 'src'));
    for (const name of ['entry.js', 'worker.ts', 'entry.test.js', 'notes.txt']) {
      fs.writeFileSync(path.join(fixtureDirectory, 'src', name), '');
    }
  });

  afterEach(() => {
    fs.rmSync(fixtureDirectory, { recursive: true, force: true });
  });

  test('expands brace patterns through glob', () => {
    const files = globSync('src/*.{js,ts}', { cwd: fixtureDirectory });

    expect(files.sort()).toEqual([
      'src/entry.js',
      'src/entry.test.js',
      'src/worker.ts',
    ]);
  });

  test('uses brace patterns for coverage inclusion and exclusion', () => {
    const coverageFiles = new TestExclude({
      cwd: fixtureDirectory,
      include: ['src/*.{js,ts}'],
      exclude: ['**/*.test.{js,ts}'],
      extension: ['.js', '.ts'],
    });

    expect(coverageFiles.globSync().sort()).toEqual([
      'src/entry.js',
      'src/worker.ts',
    ]);
  });

  test('loads YAML coverage configuration with aliases and merge keys', async () => {
    fs.writeFileSync(path.join(fixtureDirectory, '.nycrc.yaml'), [
      'defaults: &defaults',
      '  include: ["src/**"]',
      '  extension: [".js", ".ts"]',
      '<<: *defaults',
      'exclude: ["**/*.test.{js,ts}"]',
      '',
    ].join('\n'));

    const config = await loadNycConfig({ cwd: fixtureDirectory });

    expect(config.include).toEqual(['src/**']);
    expect(config.extension).toEqual(['.js', '.ts']);
    expect(config.exclude).toEqual(['**/*.test.{js,ts}']);
  });
});

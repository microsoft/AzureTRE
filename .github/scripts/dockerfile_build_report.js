const fs = require('node:fs');
const path = require('node:path');

function tableText(value) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/\|/g, '&#124;').replace(/[\r\n]/g, ' ');
}

function annotationText(value) {
  return value.replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A');
}

function createReport(matrix, directory, buildResult) {
  if (!Array.isArray(matrix) || matrix.length === 0) {
    throw new Error('Expected a non-empty build matrix');
  }

  const expectedFiles = new Set();
  const names = new Set();
  const errors = [];
  const rows = [];
  for (const target of matrix) {
    if (typeof target.name !== 'string' || !target.name
        || typeof target.safe_name !== 'string' || !/^[\w.-]+$/.test(target.safe_name)
        || !['docker', 'porter'].includes(target.kind)) {
      throw new Error('Invalid target in build matrix');
    }
    const filename = `${target.safe_name}.tsv`;
    if (expectedFiles.has(filename) || names.has(target.name)) {
      throw new Error(`Duplicate build target: ${target.name}`);
    }
    expectedFiles.add(filename);
    names.add(target.name);

    let status = 'missing';
    try {
      const text = fs.readFileSync(path.join(directory, filename), 'utf8');
      const fields = text.replace(/\r?\n$/, '').split('\t');
      const valid = fields.length === 3 && fields[0] === target.name
        && fields[1] === target.kind
        && ['success', 'failure', 'cancelled', 'skipped'].includes(fields[2]);
      status = valid ? fields[2] : 'invalid';
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }

    rows.push(`| <code>${tableText(target.name)}</code> | ${target.kind} | ${status} |`);
    if (status !== 'success') {
      errors.push(`Build failed: ${target.name} (${status})`);
    }
  }

  if (fs.existsSync(directory)) {
    for (const filename of fs.readdirSync(directory)) {
      if (!expectedFiles.has(filename)) {
        errors.push(`Unexpected build result: ${filename}`);
      }
    }
  }
  // Upload failures occur after a job records its status in the result file.
  if (buildResult !== 'success') {
    errors.push(`Build jobs finished with status: ${buildResult}`);
  }

  const summary = [
    '## Dockerfile Build Check', '',
    '| Target | Kind | Result |',
    '| --- | --- | --- |',
    ...rows, '',
    errors.length ? 'One or more builds or result checks failed.' : `All ${matrix.length} targets built.`,
    '',
  ].join('\n');
  return { summary, errors };
}

if (require.main === module) {
  try {
    const { summary, errors } = createReport(
      JSON.parse(process.env.EXPECTED_MATRIX),
      process.env.RESULTS_DIRECTORY || 'build-results',
      process.env.BUILD_RESULT,
    );
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary);
    for (const error of errors) console.error(`::error::${annotationText(error)}`);
    process.exitCode = errors.length ? 1 : 0;
  } catch (error) {
    console.error(`::error::${annotationText(error.message)}`);
    process.exitCode = 1;
  }
}

module.exports = { createReport };

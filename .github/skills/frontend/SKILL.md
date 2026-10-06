---
name: frontend
description: Covers conventions, setup and checks for the Azure TRE React and TypeScript UI, including authentication, resource forms and refresh behaviour. Use when you change or review files under ui/app.
---

# Azure TRE front end

## Find the affected behaviour

Use [package.json](../../../ui/app/package.json), [vite.config.ts](../../../ui/app/vite.config.ts) and [eslint.config.js](../../../ui/app/eslint.config.js) as the executable source for dependencies, tests and linting. The application uses React, Fluent UI, React Router and MSAL. Use the versions in the manifests rather than assuming versions from older documentation.

Inspect the existing components, hooks and contexts before adding an alternative implementation. In particular:

- Preserve the distinction between TRE roles and workspace roles. Use the correct workspace identity when making API calls.
- Check that role-based visibility does not introduce requests that the signed-in user cannot make. UI visibility does not replace API authorisation.
- For refresh changes, cover a filter, sort or workspace change while a request is pending. Ensure the latest request runs and stale responses cannot overwrite it.
- Preserve loaded content during background refresh. Check visibility changes, timer cleanup and error recovery when polling changes.
- For resource forms, verify the schema dialect and Azure TRE annotations through the API and the existing form validator.

## Prepare a local checkout

Use Node.js 24 to match the [UI CI job](../../../.github/workflows/build_docker_images.yml). From the repository root:

```bash
cd ui/app
npm ci
if [ ! -f src/config.json ]; then
  cp src/config.source.json src/config.json
fi
```

The source configuration supports local tests and builds. It does not configure a working TRE sign-in session. Preserve an existing `src/config.json` and do not commit deployment-specific configuration.

## Choose checks

Run the relevant commands from `ui/app`:

| Purpose | Command |
| --- | --- |
| One test file, using the existing refresh tests as an example | `npm test -- --run src/hooks/useRefresh.test.ts` |
| All component and unit tests, without watch mode | `npm test -- --run` |
| ESLint | `npm run lint` |
| TypeScript and production build | `npm run build` |
| Coverage measurement | `npm run test:coverage` |
| Formatting check for changed files | `npx --no-install prettier --check <changed-files>` |

Use the setup and shared mocks in [src/setupTests.ts](../../../ui/app/src/setupTests.ts) and [src/test-utils](../../../ui/app/src/test-utils). Prefer user-visible behaviour and semantic queries. Mock Fluent UI or browser APIs where JSDOM requires it, while retaining assertions about the behaviour under review.

For changes to shared hooks, contexts, routing or configuration, include the wider UI suite. Test pending requests, permission failures and retry paths when they are affected. The configured coverage targets are 80% across branches, functions, lines and statements; ordinary test runs do not measure coverage.

If macOS reports watcher exhaustion, retry the affected command with `CHOKIDAR_USEPOLLING=1` and record that environment difference. Do not suppress a failing test to work around a runtime mismatch.

## Report the limits

Apply the [root contribution requirements](../../../AGENTS.md#contribution-requirements) for UI version and changelog updates. Confirm that release notes describe the rendered behaviour.

Component tests do not establish browser layout, attended sign-in or deployed role behaviour. Record those checks separately when relevant. Use the [code-review skill](../code-review/SKILL.md) for PR bot recommendations; a larger backend E2E suite is not evidence of UI interaction coverage.

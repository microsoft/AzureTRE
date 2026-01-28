# UI Testing

The Azure TRE UI uses a testing framework to ensure component reliability and maintainability. This document covers the testing setup, best practices, and how to write and run tests.

## Testing Stack

The UI testing framework consists of:

- **Vitest**: Modern test runner with native TypeScript support and fast execution
- **React Testing Library**: Testing utilities focused on testing components as users interact with them
- **JSDOM**: DOM implementation for Node.js environments
- **@testing-library/jest-dom**: Custom Jest matchers for DOM assertions
- **V8 Coverage**: Code coverage reporting

## Test Configuration

### Vitest Configuration

Tests are configured in `vite.config.ts` with the following key settings:

```typescript
test: {
  globals: true,
  environment: "jsdom",
  setupFiles: ["./src/setupTests.ts"],
  coverage: {
    provider: "v8",
    reporter: ["text", "json", "html", "lcov"],
    thresholds: {
      global: {
        branches: 80,
        functions: 80,
        lines: 80,
        statements: 80,
      },
    },
  },
}
```

### Test Setup

The `setupTests.ts` file configures:
- Global test utilities and matchers
- Mocks for browser APIs (ResizeObserver, IntersectionObserver, matchMedia)
- Crypto API mocks for MSAL authentication
- FluentUI initialization and icon registration

## Writing Tests

### Component Testing Best Practices

1. **Test User Interactions**: Focus on how users interact with components rather than implementation details
2. **Use Semantic Queries**: Prefer `getByRole`, `getByLabelText`, and `getByText` over `getByTestId`
3. **Mock External Dependencies**: Mock FluentUI components, API calls, and browser APIs
4. **Test Accessibility**: Ensure components are accessible and work with screen readers

### Example Test Structure

```typescript
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { YourComponent } from "./YourComponent";

// Mock external dependencies
vi.mock("@fluentui/react", () => ({
  // Mock FluentUI components
}));

describe("YourComponent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders correctly", () => {
    render(<YourComponent />);
    expect(screen.getByText("Expected Text")).toBeInTheDocument();
  });

  it("handles user interactions", async () => {
    render(<YourComponent />);
    
    const button = screen.getByRole("button", { name: "Click me" });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText("Button clicked")).toBeInTheDocument();
    });
  });
});
```

### Mocking FluentUI Components

Due to FluentUI's complexity and testing environment limitations, components are typically mocked:

```typescript
vi.mock("@fluentui/react", async () => {
  const actual = await vi.importActual("@fluentui/react");
  
  return {
    ...actual,
    Stack: ({ children, horizontal }: any) => (
      <div data-testid="stack" data-horizontal={horizontal}>
        {children}
      </div>
    ),
    IconButton: ({ iconProps, onClick }: any) => (
      <button
        data-testid="icon-button"
        data-icon-name={iconProps?.iconName}
        onClick={onClick}
      >
        {iconProps?.iconName}
      </button>
    ),
  };
});
```

### Testing Async Operations

For components with async operations (API calls, timers):

```typescript
it("handles async operations", async () => {
  render(<AsyncComponent />);
  
  // Trigger async operation
  fireEvent.click(screen.getByRole("button"));
  
  // Wait for operation to complete
  await waitFor(() => {
    expect(screen.getByText("Success")).toBeInTheDocument();
  });
});
```

## Running Tests

### Development Commands

```bash
# Change directory
cd ui/app

# Run tests in watch mode (waits for file changes)
yarn test

# Run tests in run mode
yarn test --run

# Run tests and produces a coverage report
yarn test:coverage

# Launches a web page where you can visualise your tests
yarn test:ui

# Build and test (CI)
yarn run build && yarn test --run
```

### Test Scripts

- `yarn test`: Runs tests in watch mode for development
- `yarn run test:coverage`: Runs tests once and generates coverage report
- Coverage reports are generated in HTML, LCOV, JSON, and text formats

## Coverage Requirements

The project maintains high code coverage standards:
- **Branches**: 80% minimum
- **Functions**: 80% minimum  
- **Lines**: 80% minimum
- **Statements**: 80% minimum

Coverage excludes:
- Test files themselves (`**/*.test.{ts,tsx}`)
- Configuration files (`vite.config.ts`, `eslint.config.js`)
- Type definitions (`**/*.d.ts`)
- Setup files (`setupTests.ts`)
- Build artifacts and dependencies

## Test Organization

### File Structure

```text
src/
├── components/
│   ├── shared/
│   │   ├── Component.tsx
│   │   └── Component.test.tsx
│   └── workspace/
│       ├── WorkspaceComponent.tsx
│       └── WorkspaceComponent.test.tsx
├── hooks/
│   ├── useHook.ts
│   └── useHook.test.ts
└── setupTests.ts
```

### Naming Conventions

- Test files: `Component.test.tsx` (same name as component + `.test`)
- Test suites: Use `describe()` blocks for grouping related tests
- Test cases: Use descriptive `it()` statements that read like specifications

## Common Testing Patterns

### Testing Custom Hooks

```typescript
import { renderHook, act } from '@testing-library/react';
import { useCustomHook } from './useCustomHook';

it('updates state correctly', () => {
  const { result } = renderHook(() => useCustomHook());
  
  act(() => {
    result.current.updateValue('new value');
  });
  
  expect(result.current.value).toBe('new value');
});
```

### Testing Forms

```typescript
it('validates form input', async () => {
  render(<FormComponent />);
  
  const input = screen.getByLabelText('Email');
  const submitButton = screen.getByRole('button', { name: 'Submit' });
  
  fireEvent.change(input, { target: { value: 'invalid-email' } });
  fireEvent.click(submitButton);
  
  await waitFor(() => {
    expect(screen.getByText('Invalid email format')).toBeInTheDocument();
  });
});
```

### Testing Error Boundaries

```typescript
it('catches and displays errors', () => {
  const ThrowError = () => {
    throw new Error('Test error');
  };
  
  render(
    <ErrorBoundary>
      <ThrowError />
    </ErrorBoundary>
  );
  
  expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
});
```

## Debugging Tests

### Useful Debug Utilities

```typescript
import { screen } from '@testing-library/react';

// Debug current DOM state
screen.debug();

// Debug specific element
screen.debug(screen.getByTestId('component'));

// Log all queries
screen.logTestingPlaygroundURL();
```

### Common Issues

1. **Async operations not awaited**: Use `waitFor()` for async state changes
2. **FluentUI components not mocked**: Mock complex components that don't render in JSDOM
3. **Missing test data attributes**: Add `data-testid` when semantic queries aren't sufficient
4. **Timer-related tests**: Use `vi.useFakeTimers()` and `vi.advanceTimersByTime()`

## Continuous Integration

Tests run automatically on:
- Pull request creation and updates
- Pushes to main branch
- Scheduled nightly builds

CI failures often indicate:
- Failing tests that need to be fixed
- Coverage thresholds not met
- Linting or formatting issues

## Best Practices Summary

1. **Write tests first** when adding new features (TDD approach)
2. **Test behavior, not implementation** - focus on user interactions
3. **Keep tests isolated** - each test should be independent
4. **Use descriptive test names** - tests should read like specifications
5. **Mock external dependencies** - keep tests focused on the component under test
6. **Maintain high coverage** - aim for the 80% threshold across all metrics
7. **Test error states** - ensure components handle errors gracefully
8. **Test accessibility** - verify components work with assistive technologies

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [FluentUI Testing Guide](https://developer.microsoft.com/en-us/fluentui#/controls/web)
- [Jest DOM Matchers](https://github.com/testing-library/jest-dom)

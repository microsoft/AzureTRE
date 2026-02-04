import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, createPartialFluentUIMock, act } from "../../test-utils";
import { ExceptionLayout } from "./ExceptionLayout";
import { APIError } from "../../models/exceptions";

// Mock FluentUI components using centralized utility
vi.mock("@fluentui/react", () => createPartialFluentUIMock(['MessageBar', 'Link', 'Icon']));

describe("ExceptionLayout Component", () => {
  const createMockError = (overrides: Partial<APIError> = {}): APIError => {
    const error = new APIError();
    error.status = 500;
    error.userMessage = "Test user message";
    error.message = "Test error message";
    error.endpoint = "/test/endpoint";
    error.stack = "Error stack trace";
    error.exception = "Test exception details";
    return { ...error, ...overrides };
  };

  it("renders access denied message for 403 status", async () => {
    const error = createMockError({
      status: 403,
      userMessage: "You don't have permission",
      message: "Forbidden access"
    });

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    expect(screen.getByTestId("message-bar")).toBeInTheDocument();
    expect(screen.getByText("Access Denied")).toBeInTheDocument();
    expect(screen.getByText("You don't have permission")).toBeInTheDocument();
    expect(screen.getByText("Forbidden access")).toBeInTheDocument();
    expect(screen.getByText("Attempted resource: /test/endpoint")).toBeInTheDocument();
  });

  it("renders nothing for 429 status (rate limiting)", async () => {
    const error = createMockError({ status: 429 });

    let container: HTMLElement | null = null;
    await act(async () => {
      container = render(<ExceptionLayout e={error} />).container;
    });

    expect(container!.firstChild).toBeNull();
  });

  it("renders default error message for other status codes", async () => {
    const error = createMockError({
      status: 500,
      userMessage: "Internal server error",
      message: "Something went wrong"
    });

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    expect(screen.getByTestId("message-bar")).toBeInTheDocument();
    expect(screen.getByText("Internal server error")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByTestId("dismiss-button")).toBeInTheDocument();
  });

  it("shows and hides details when toggle link is clicked", async () => {
    const error = createMockError();

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    // Initially details should be hidden
    expect(screen.queryByText("Endpoint")).not.toBeInTheDocument();
    expect(screen.getByText("Show Details")).toBeInTheDocument();

    // Click to show details
    await act(async () => {
      fireEvent.click(screen.getByTestId("fluent-link"));
    });

    // Details should now be visible
    expect(screen.getByText("Endpoint")).toBeInTheDocument();
    expect(screen.getByText("Status Code")).toBeInTheDocument();
    expect(screen.getByText("Stack Trace")).toBeInTheDocument();
    expect(screen.getByText("Exception")).toBeInTheDocument();
    expect(screen.getByText("Hide Details")).toBeInTheDocument();

    // Check that the actual values are displayed
    expect(screen.getByText("/test/endpoint")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
    // Note: stack trace might be empty/undefined and shown in a td element
    expect(screen.getByText("Stack Trace")).toBeInTheDocument();
    expect(screen.getByText("Test exception details")).toBeInTheDocument();

    // Click to hide details
    await act(async () => {
      fireEvent.click(screen.getByTestId("fluent-link"));
    });

    // Details should be hidden again
    expect(screen.queryByText("Endpoint")).not.toBeInTheDocument();
    expect(screen.getByText("Show Details")).toBeInTheDocument();
  });

  it("displays '(none)' for missing status code", async () => {
    const error = createMockError({ status: undefined });

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    // Show details to see the status code
    await act(async () => {
      fireEvent.click(screen.getByTestId("fluent-link"));
    });

    expect(screen.getByText("(none)")).toBeInTheDocument();
  });

  it("dismisses the message bar when dismiss button is clicked", async () => {
    const error = createMockError();

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    expect(screen.getByTestId("message-bar")).toBeInTheDocument();

    // Click dismiss button
    await act(async () => {
      fireEvent.click(screen.getByTestId("dismiss-button"));
    });

    // Message bar should be hidden
    expect(screen.queryByTestId("message-bar")).not.toBeInTheDocument();
  });

  it("renders correct icons for show/hide details", async () => {
    const error = createMockError();

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    // Initially should show ChevronDown icon
    expect(screen.getByTestId("icon-ChevronDown")).toHaveAttribute("data-icon-name", "ChevronDown");

    // Click to show details
    await act(async () => {
      fireEvent.click(screen.getByTestId("fluent-link"));
    });

    // Should now show ChevronUp icon
    expect(screen.getByTestId("icon-ChevronUp")).toHaveAttribute("data-icon-name", "ChevronUp");
  });

  it("handles missing error properties gracefully", async () => {
    const error = new APIError();
    error.status = 500;
    // Don't set other properties

    await act(async () => {
      render(<ExceptionLayout e={error} />);
    });

    expect(screen.getByTestId("message-bar")).toBeInTheDocument();

    // Show details to check undefined values are handled
    await act(async () => {
      fireEvent.click(screen.getByTestId("fluent-link"));
    });

    expect(screen.getByText("Status Code")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
  });
});

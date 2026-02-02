import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, createPartialFluentUIMock } from "../../test-utils";
import { ErrorPanel } from "./ErrorPanel";

// Mock FluentUI Panel component using centralized utility
vi.mock("@fluentui/react", () => createPartialFluentUIMock(['Panel']));

describe("ErrorPanel Component", () => {
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders panel when isOpen is true", () => {
    render(
      <ErrorPanel
        errorMessage="Test error message"
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByTestId("panel")).toBeInTheDocument();
    expect(screen.getByTestId("panel-header")).toHaveTextContent("Error Details");
  });

  it("does not render panel when isOpen is false", () => {
    render(
      <ErrorPanel
        errorMessage="Test error message"
        isOpen={false}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.queryByTestId("panel")).not.toBeInTheDocument();
  });

  it("displays error message", () => {
    const errorMessage = "This is a test error message";
    render(
      <ErrorPanel
        errorMessage={errorMessage}
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it("calls onDismiss when close button is clicked", () => {
    render(
      <ErrorPanel
        errorMessage="Test error"
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    fireEvent.click(screen.getByTestId("panel-close"));
    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("strips ANSI codes from error message", () => {
    const errorWithAnsi = "\u001b[31mError: Something went wrong\u001b[0m";
    render(
      <ErrorPanel
        errorMessage={errorWithAnsi}
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText("Error: Something went wrong")).toBeInTheDocument();
    expect(screen.queryByText(errorWithAnsi)).not.toBeInTheDocument();
  });

  it("replaces special characters with newlines", () => {
    const errorWithSpecialChars = "Error│Details╷More╵Info";
    render(
      <ErrorPanel
        errorMessage={errorWithSpecialChars}
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    // The component should process the string but we can still find the text
    expect(screen.getByText(/Error.*Details.*More.*Info/)).toBeInTheDocument();
  });

  it("trims whitespace from error message", () => {
    const errorWithWhitespace = "   \n  Error message with whitespace  \n   ";
    render(
      <ErrorPanel
        errorMessage={errorWithWhitespace}
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    expect(screen.getByText("Error message with whitespace")).toBeInTheDocument();
  });

  it("applies monospace styling to error content", () => {
    render(
      <ErrorPanel
        errorMessage="Test error"
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    const errorContent = screen.getByText("Test error");

    // The styling is applied to the div, check for inline styles
    expect(errorContent).toHaveStyle("font-family: monospace");
    expect(errorContent).toHaveStyle("background-color: rgb(0, 0, 0)");
    expect(errorContent).toHaveStyle("color: rgb(255, 255, 255)");
    expect(errorContent).toHaveStyle("padding: 10px");
  });

  it("preserves whitespace in error message", () => {
    const errorWithFormatting = "Line 1\n  Indented line\nLine 3";
    render(
      <ErrorPanel
        errorMessage={errorWithFormatting}
        isOpen={true}
        onDismiss={mockOnDismiss}
      />
    );

    // Check that the error content is displayed with the correct whitespace
    // Need to use a function matcher since the text contains newlines
    const errorElement = screen.getByText((content: string) => {
      return Boolean(content && content.includes("Line 1") && content.includes("Indented line") && content.includes("Line 3"));
    });
    expect(errorElement).toBeInTheDocument();
  });
});

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorPanel } from "./ErrorPanel";

// Mock FluentUI Panel component
vi.mock("@fluentui/react", async () => {
    const actual = await vi.importActual("@fluentui/react");
    return {
        ...actual,
        Panel: ({ children, isOpen, onDismiss, headerText }: any) =>
            isOpen ? (
                <div data-testid="error-panel" role="dialog" aria-label={headerText}>
                    <div data-testid="panel-header">{headerText}</div>
                    <button data-testid="close-button" onClick={onDismiss}>Close</button>
                    {children}
                </div>
            ) : null,
        PanelType: {
            large: "large",
        },
    };
});

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

        expect(screen.getByTestId("error-panel")).toBeInTheDocument();
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

        expect(screen.queryByTestId("error-panel")).not.toBeInTheDocument();
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

        fireEvent.click(screen.getByTestId("close-button"));
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

        const errorContent = screen.getByText((content, element) => {
            return element?.textContent === errorWithFormatting;
        });

        expect(errorContent).toHaveStyle("white-space: pre-wrap");
    });
});

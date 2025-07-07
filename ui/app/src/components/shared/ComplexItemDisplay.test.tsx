import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, createPartialFluentUIMock } from "../../test-utils";
import { ComplexPropertyModal } from "./ComplexItemDisplay";

// Mock FluentUI components using centralized utility with the newly added Modal component
vi.mock("@fluentui/react", () => {
  const mocks = createPartialFluentUIMock(['Link', 'Modal', 'IconButton', 'getTheme', 'FontWeights', 'mergeStyleSets']);
  return {
    ...mocks,
    IIconProps: {},
    IconNames: {
      Cancel: 'Cancel',
    }
  };
});

describe("ComplexPropertyModal Component", () => {
  const mockComplexData = {
    stringProperty: "test string",
    numberProperty: 42,
    nestedObject: {
      innerString: "inner value",
      innerNumber: 123,
      deepNested: {
        deepProperty: "deep value",
      },
    },
    arrayProperty: ["item1", "item2", "item3"],
  };

  it("renders the details link", () => {
    render(<ComplexPropertyModal val={mockComplexData} title="Test Modal" />);

    expect(screen.getByTestId("fluent-link")).toBeInTheDocument();
    expect(screen.getByText("[details]")).toBeInTheDocument();
  });

  it("opens modal when details link is clicked", () => {
    render(<ComplexPropertyModal val={mockComplexData} title="Test Modal" />);

    // Modal should not be visible initially
    expect(screen.queryByTestId("modal")).not.toBeInTheDocument();

    // Click the details link
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Modal should now be visible
    expect(screen.getByTestId("modal")).toBeInTheDocument();
    expect(screen.getByText("Test Modal")).toBeInTheDocument();
  });

  it("closes modal when close button is clicked", () => {
    render(<ComplexPropertyModal val={mockComplexData} title="Test Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));
    expect(screen.getByTestId("modal")).toBeInTheDocument();

    // Click close button
    const closeButton = screen.getByLabelText("Close popup modal");
    fireEvent.click(closeButton);

    // Modal should be closed
    expect(screen.queryByTestId("modal")).not.toBeInTheDocument();
  });

  it("displays simple properties in the modal", () => {
    render(<ComplexPropertyModal val={mockComplexData} title="Test Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Check that simple properties are displayed
    expect(screen.getByText(/stringProperty:/)).toBeInTheDocument();
    expect(screen.getByText(/test string/)).toBeInTheDocument();
    expect(screen.getByText(/numberProperty:/)).toBeInTheDocument();
    expect(screen.getByText(/42/)).toBeInTheDocument();
  });

  it("displays nested objects with expand/collapse functionality", () => {
    render(<ComplexPropertyModal val={mockComplexData} title="Test Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Check that nested object label is displayed
    expect(screen.getByText("nestedObject:")).toBeInTheDocument();

    // Find expand/collapse buttons for nested objects
    const expandButtons = screen.getAllByTestId("icon-button").filter(
      (button) =>
        button.getAttribute("data-icon-name") === "ChevronDown" ||
        button.getAttribute("data-icon-name") === "ChevronUp"
    );

    expect(expandButtons.length).toBeGreaterThan(0);
  });

  it("expands and collapses nested objects when chevron is clicked", () => {
    render(<ComplexPropertyModal val={mockComplexData} title="Test Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Find a chevron down button (collapsed state)
    const chevronDownButton = screen.getAllByTestId("icon-button").find(
      (button) => button.getAttribute("data-icon-name") === "ChevronDown"
    );

    if (chevronDownButton) {
      // Click to expand
      fireEvent.click(chevronDownButton);

      // Should now have chevron up button (expanded state)
      const chevronUpButton = screen.getAllByTestId("icon-button").find(
        (button) => button.getAttribute("data-icon-name") === "ChevronUp"
      );
      expect(chevronUpButton).toBeInTheDocument();
    }
  });

  it("handles array data correctly", () => {
    const arrayData = ["first", "second", "third"];
    render(<ComplexPropertyModal val={arrayData} title="Array Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Array items should be displayed without keys
    expect(screen.getByText("first")).toBeInTheDocument();
    expect(screen.getByText("second")).toBeInTheDocument();
    expect(screen.getByText("third")).toBeInTheDocument();
  });

  it("handles simple string data", () => {
    const simpleData = "Simple string value";
    render(<ComplexPropertyModal val={simpleData} title="String Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Simple string should be displayed (note: strings are treated as arrays in the component)
    // So we expect individual characters to be displayed
    expect(screen.getAllByText("S")).toHaveLength(1);
    expect(screen.getAllByText("i")).toHaveLength(2); // "i" appears twice in "Simple"
    expect(screen.getByText("m")).toBeInTheDocument();
  });

  it("handles empty object", () => {
    const emptyData = {};
    render(<ComplexPropertyModal val={emptyData} title="Empty Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Modal should open without errors
    expect(screen.getByTestId("modal")).toBeInTheDocument();
    expect(screen.getByText("Empty Modal")).toBeInTheDocument();
  });

  it("displays deeply nested structures", () => {
    const deepData = {
      level1: {
        level2: {
          level3: {
            deepValue: "found it!",
          },
        },
      },
    };

    render(<ComplexPropertyModal val={deepData} title="Deep Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Should show the first level
    expect(screen.getByText("level1:")).toBeInTheDocument();
  });

  it("properly handles numeric keys in arrays", () => {
    const numericKeyData = {
      0: "zero",
      1: "one",
      2: "two",
      regularKey: "regular value"
    };

    render(<ComplexPropertyModal val={numericKeyData} title="Numeric Keys Modal" />);

    // Open the modal
    fireEvent.click(screen.getByTestId("fluent-link"));

    // Regular key should show with colon
    expect(screen.getByText(/regularKey:/)).toBeInTheDocument();
    expect(screen.getByText(/regular value/)).toBeInTheDocument();

    // Numeric keys (array-like) should not show colon
    expect(screen.getByText("zero")).toBeInTheDocument();
    expect(screen.getByText("one")).toBeInTheDocument();
    expect(screen.getByText("two")).toBeInTheDocument();
  });
});

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { TopNav } from "./TopNav";

// Mock child components
vi.mock("./UserMenu", () => {
  const UserMenu = () => <div data-testid="user-menu">User Menu</div>;
  UserMenu.displayName = 'UserMenu';
  return { UserMenu };
});

vi.mock("./notifications/NotificationPanel", () => {
  const NotificationPanel = () => <div data-testid="notification-panel">Notifications</div>;
  NotificationPanel.displayName = 'NotificationPanel';
  return { NotificationPanel };
});

// Mock config.json
vi.mock("../../config.json", () => ({
  default: {
    uiSiteName: "Test TRE Environment"
  }
}));

// Mock FluentUI components
vi.mock("@fluentui/react", () => {
  const MockStack = ({ children, horizontal }: any) => (
    <div data-testid="stack" data-horizontal={horizontal}>
      {children}
    </div>
  );

  const Item = ({ children, grow }: any) => (
    <div data-testid="stack-item" data-grow={grow}>
      {children}
    </div>
  );
  Item.displayName = 'StackItem';
  MockStack.Item = Item;

  return {
    getTheme: () => ({
      palette: {
        themeDark: "#004578",
        white: "#ffffff",
      },
    }),
    Icon: ({ iconName, style }: any) => (
      <span data-testid={`icon-${iconName}`} style={style}>
        {iconName}
      </span>
    ),
    mergeStyles: (styles: any) => styles,
    Stack: MockStack,
  };
});

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe("TopNav Component", () => {
  it("renders the navigation bar with all components", () => {
    renderWithRouter(<TopNav />);

    // Check if main container is rendered
    expect(screen.getByTestId("stack")).toBeInTheDocument();

    // Check if site icon is rendered
    expect(screen.getByTestId("icon-TestBeakerSolid")).toBeInTheDocument();

    // Check if custom site name is displayed
    expect(screen.getByText("Test TRE Environment")).toBeInTheDocument();

    // Check if child components are rendered
    expect(screen.getByTestId("notification-panel")).toBeInTheDocument();
    expect(screen.getByTestId("user-menu")).toBeInTheDocument();
  });

  it("renders home link that navigates to root", () => {
    renderWithRouter(<TopNav />);

    const homeLink = screen.getByRole("link");
    expect(homeLink).toHaveAttribute("href", "/");
    expect(homeLink).toHaveClass("tre-home-link");
  });

  it("has proper layout structure with growing stack items", () => {
    renderWithRouter(<TopNav />);

    const stackItems = screen.getAllByTestId("stack-item");

    // First item (home link) should have grow=100
    expect(stackItems[0]).toHaveAttribute("data-grow", "100");

    // Second item (notifications) should not have grow specified
    expect(stackItems[1]).not.toHaveAttribute("data-grow");

    // Third item (user menu) should have grow attribute set to true (converted to string)
    expect(stackItems[2]).toHaveAttribute("data-grow", "true");
  });

  it("renders site name as h5 with inline display", () => {
    renderWithRouter(<TopNav />);

    const heading = screen.getByRole("heading", { level: 5 });
    expect(heading).toHaveTextContent("Test TRE Environment");
  });
});

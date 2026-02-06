import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { Footer } from "./Footer";

// Mock the API hook
const mockApiCall = vi.fn();
vi.mock("../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET" },
}));

// Mock the config
vi.mock("../../config.json", () => ({
  default: {
    uiFooterText: "Test Footer Text",
    version: "1.0.0"
  }
}));

// Mock API endpoints
vi.mock("../../models/apiEndpoints", () => ({
  ApiEndpoint: {
    Metadata: "/api/metadata",
    Health: "/api/health"
  }
}));

describe("Footer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiCall.mockResolvedValue({});
  });

  it("renders footer text from config", async () => {
    await act(async () => {
      render(<Footer />);
    });

    expect(screen.getByText("Test Footer Text")).toBeInTheDocument();
  });

  it("renders info button", async () => {
    await act(async () => {
      render(<Footer />);
    });

    const infoButton = screen.getByRole("button");
    expect(infoButton).toBeInTheDocument();
  });

  it("shows info callout when info button is clicked", async () => {
    mockApiCall
      .mockResolvedValueOnce({ api_version: "2.0.0" }) // metadata call
      .mockResolvedValueOnce({ // health call
        services: [
          { service: "API", status: "OK" },
          { service: "Database", status: "OK" }
        ]
      });

    await act(async () => {
      render(<Footer />);
    });

    const infoButton = screen.getByRole("button");

    await act(async () => {
      fireEvent.click(infoButton);
    });

    await waitFor(() => {
      expect(screen.getByText("Azure TRE")).toBeInTheDocument();
    });

    expect(screen.getByText("UI Version:")).toBeInTheDocument();
    expect(screen.getByText("1.0.0")).toBeInTheDocument();
  });

  it("shows API version in callout", async () => {
    mockApiCall
      .mockResolvedValueOnce({ api_version: "2.0.0" })
      .mockResolvedValueOnce({ services: [] });

    await act(async () => {
      render(<Footer />);
    });

    const infoButton = screen.getByRole("button");

    await act(async () => {
      fireEvent.click(infoButton);
    });

    await waitFor(() => {
      expect(screen.getByText("API Version:")).toBeInTheDocument();
    });

    expect(screen.getByText("2.0.0")).toBeInTheDocument();
  });

  it("shows service health status", async () => {
    mockApiCall
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({
        services: [
          { service: "API", status: "OK" },
          { service: "Database", status: "ERROR" }
        ]
      });

    await act(async () => {
      render(<Footer />);
    });

    const infoButton = screen.getByRole("button");

    await act(async () => {
      fireEvent.click(infoButton);
    });

    await waitFor(() => {
      expect(screen.getByText("API:")).toBeInTheDocument();
    });

    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("Database:")).toBeInTheDocument();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
  });

  it("calls API endpoints on mount", async () => {
    await act(async () => {
      render(<Footer />);
    });

    expect(mockApiCall).toHaveBeenCalledWith("/api/metadata", "GET");
    expect(mockApiCall).toHaveBeenCalledWith("/api/health", "GET");
  });

  it("handles missing health services gracefully", async () => {
    mockApiCall
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({}); // No services property

    await act(async () => {
      render(<Footer />);
    });

    const infoButton = screen.getByRole("button");

    await act(async () => {
      fireEvent.click(infoButton);
    });

    await waitFor(() => {
      expect(screen.getByText("Azure TRE")).toBeInTheDocument();
    });

    // Should not crash and should render the basic info
    expect(screen.getByText("UI Version:")).toBeInTheDocument();
  });
});

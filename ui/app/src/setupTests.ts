import "@testing-library/jest-dom";
import { expect, beforeAll, vi } from "vitest";
import React from "react";

// Setup global mocks
beforeAll(() => {
  // Mock ResizeObserver which is not available in jsdom
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // Mock IntersectionObserver
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // Mock window.matchMedia
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // deprecated
      removeListener: vi.fn(), // deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // Mock crypto for MSAL
  Object.defineProperty(global, "crypto", {
    value: {
      getRandomValues: (arr: any) => {
        for (let i = 0; i < arr.length; i++) {
          arr[i] = Math.floor(Math.random() * 256);
        }
        return arr;
      },
      randomUUID: () => "test-uuid",
      subtle: {
        digest: vi.fn().mockResolvedValue(new ArrayBuffer(32)),
        generateKey: vi.fn(),
        exportKey: vi.fn(),
        importKey: vi.fn(),
        sign: vi.fn(),
        verify: vi.fn(),
        encrypt: vi.fn(),
        decrypt: vi.fn(),
        deriveBits: vi.fn(),
        deriveKey: vi.fn(),
        wrapKey: vi.fn(),
        unwrapKey: vi.fn(),
      },
    },
  });

  // Mock TextEncoder/TextDecoder
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;

  // Initialize FluentUI for tests
  try {
    const { registerIcons, initializeIcons, loadTheme, createTheme } = require("@fluentui/react");

    // Initialize icons and theme
    initializeIcons();
    loadTheme(createTheme({}));

    // Register FluentUI icons to prevent console warnings
    registerIcons({
      icons: {
        info: React.createElement("span", null, "info"),
        completed: React.createElement("span", null, "completed"),
        // Add other commonly used icons as needed
      },
    });
  } catch (e) {
    // Ignore if @fluentui/react is not available
  }
});

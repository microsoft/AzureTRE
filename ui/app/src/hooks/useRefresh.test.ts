import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useRefresh } from "./useRefresh";

describe("useRefresh", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls while visible and pauses while hidden", () => {
    vi.useFakeTimers();
    const onRefresh = vi.fn();
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    renderHook(() => useRefresh(onRefresh, 1000));

    act(() => vi.advanceTimersByTime(1000));
    expect(onRefresh).toHaveBeenCalledTimes(1);

    visibility.mockReturnValue("hidden");
    act(() => vi.advanceTimersByTime(1000));
    expect(onRefresh).toHaveBeenCalledTimes(1);

    visibility.mockRestore();
  });

  it("refreshes once when the tab becomes visible after missing a poll", () => {
    vi.useFakeTimers();
    const onRefresh = vi.fn();
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    renderHook(() => useRefresh(onRefresh, 1000));

    act(() => vi.advanceTimersByTime(3000));
    expect(onRefresh).not.toHaveBeenCalled();

    visibility.mockReturnValue("visible");
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(onRefresh).toHaveBeenCalledTimes(1);

    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(onRefresh).toHaveBeenCalledTimes(1);

    visibility.mockRestore();
  });

  it("returns a manual refresh callback", () => {
    const onRefresh = vi.fn();
    const { result, unmount } = renderHook(() => useRefresh(onRefresh));

    act(() => result.current());
    expect(onRefresh).toHaveBeenCalledOnce();
    unmount();
  });
});

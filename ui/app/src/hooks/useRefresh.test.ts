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

  it("coalesces timer and manual refreshes while an asynchronous refresh is pending", async () => {
    vi.useFakeTimers();
    let completeRefresh: () => void = () => {};
    const onRefresh = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          completeRefresh = resolve;
        }),
    );
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    const { result } = renderHook(() => useRefresh(onRefresh, 1000));

    act(() => {
      result.current();
      vi.advanceTimersByTime(3000);
    });
    expect(onRefresh).toHaveBeenCalledOnce();

    await act(async () => {
      completeRefresh();
      await Promise.resolve();
    });
    act(() => vi.advanceTimersByTime(1000));
    expect(onRefresh).toHaveBeenCalledTimes(2);

    visibility.mockRestore();
  });

  it("refreshes on a short hidden-to-visible transition without a missed poll", () => {
    vi.useFakeTimers();
    const onRefresh = vi.fn();
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    const { unmount } = renderHook(() => useRefresh(onRefresh));

    visibility.mockReturnValue("hidden");
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    act(() => vi.advanceTimersByTime(100));
    expect(onRefresh).not.toHaveBeenCalled();

    visibility.mockReturnValue("visible");
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(onRefresh).toHaveBeenCalledOnce();

    unmount();
    visibility.mockRestore();
  });
});

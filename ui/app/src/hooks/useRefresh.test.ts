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

    // The calls made while pending collapse into a single follow-up once the first refresh finishes.
    await act(async () => {
      completeRefresh();
      await Promise.resolve();
    });
    expect(onRefresh).toHaveBeenCalledTimes(2);

    await act(async () => {
      completeRefresh();
      await Promise.resolve();
    });
    expect(onRefresh).toHaveBeenCalledTimes(2);

    visibility.mockRestore();
  });

  it("runs a refresh requested while pending with the latest callback", async () => {
    let completeRefresh: () => void = () => {};
    const first = vi.fn(() => new Promise<void>((resolve) => (completeRefresh = resolve)));
    const second = vi.fn();
    const { result, rerender } = renderHook(({ cb }) => useRefresh(cb), { initialProps: { cb: first as () => any } });

    act(() => result.current());
    rerender({ cb: second });
    act(() => result.current());
    expect(second).not.toHaveBeenCalled();

    await act(async () => {
      completeRefresh();
      await Promise.resolve();
    });
    expect(first).toHaveBeenCalledOnce();
    expect(second).toHaveBeenCalledOnce();
  });

  it("does not run a queued refresh after unmount", async () => {
    let completeRefresh: () => void = () => {};
    const onRefresh = vi.fn(() => new Promise<void>((resolve) => (completeRefresh = resolve)));
    const { result, unmount } = renderHook(() => useRefresh(onRefresh));

    act(() => result.current());
    act(() => result.current());
    unmount();

    await act(async () => {
      completeRefresh();
      await Promise.resolve();
    });
    expect(onRefresh).toHaveBeenCalledOnce();
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

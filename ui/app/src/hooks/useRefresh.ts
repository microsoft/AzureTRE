import { useCallback, useEffect, useRef } from "react";

export const AUTO_REFRESH_INTERVAL_MS = 30000;

export const isPageVisible = () => document.visibilityState === "visible";

export const useRefresh = (onRefresh: () => void | Promise<void>, interval = AUTO_REFRESH_INTERVAL_MS) => {
  const onRefreshRef = useRef(onRefresh);
  const refreshInProgress = useRef(false);
  const refreshQueued = useRef(false);
  const disposed = useRef(false);

  // Drop queued work when the component unmounts so no API calls or state updates run afterwards.
  useEffect(() => {
    disposed.current = false;
    return () => {
      disposed.current = true;
      refreshQueued.current = false;
    };
  }, []);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  // Refreshes never overlap. A request made while one is running is queued and runs once, with the latest
  // callback, when it finishes, so changed queries (filters, sort) are never dropped.
  const refresh = useCallback(() => {
    if (disposed.current) return;
    if (refreshInProgress.current) {
      refreshQueued.current = true;
      return;
    }

    refreshInProgress.current = true;
    const finish = () => {
      refreshInProgress.current = false;
      if (refreshQueued.current) {
        refreshQueued.current = false;
        refresh();
      }
    };

    let result: void | Promise<void>;
    try {
      result = onRefreshRef.current();
    } catch (error) {
      finish();
      throw error;
    }

    if (result && typeof result.then === "function") {
      result.then(finish, finish);
    } else {
      finish();
    }
  }, []);

  useEffect(() => {
    let wasVisible = isPageVisible();
    const timer = window.setInterval(() => {
      if (isPageVisible()) {
        refresh();
      }
    }, interval);

    // Catch up once when the tab becomes visible again instead of polling in the background.
    const onVisibilityChange = () => {
      const visible = isPageVisible();
      if (visible && !wasVisible) {
        refresh();
      }
      wasVisible = visible;
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [interval, refresh]);

  return refresh;
};

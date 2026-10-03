import { useCallback, useEffect, useRef } from "react";

export const AUTO_REFRESH_INTERVAL_MS = 30000;

export const isPageVisible = () => document.visibilityState === "visible";

export const useRefresh = (onRefresh: () => void | Promise<void>, interval = AUTO_REFRESH_INTERVAL_MS) => {
  const onRefreshRef = useRef(onRefresh);
  const refreshInProgress = useRef(false);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  const refresh = useCallback(() => {
    if (refreshInProgress.current) return;

    refreshInProgress.current = true;
    let result: void | Promise<void>;
    try {
      result = onRefreshRef.current();
    } catch (error) {
      refreshInProgress.current = false;
      throw error;
    }

    if (result && typeof result.then === "function") {
      result.then(
        () => {
          refreshInProgress.current = false;
        },
        () => {
          refreshInProgress.current = false;
        },
      );
    } else {
      refreshInProgress.current = false;
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

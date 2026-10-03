import { useCallback, useEffect, useRef } from "react";

export const AUTO_REFRESH_INTERVAL_MS = 30000;

export const isPageVisible = () => document.visibilityState === "visible";

export const useRefresh = (onRefresh: () => void, interval = AUTO_REFRESH_INTERVAL_MS) => {
  const onRefreshRef = useRef(onRefresh);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  const refresh = useCallback(() => onRefreshRef.current(), []);

  useEffect(() => {
    let wasVisible = isPageVisible();
    const timer = window.setInterval(() => {
      if (isPageVisible()) {
        onRefreshRef.current();
      }
    }, interval);

    // Catch up once when the tab becomes visible again instead of polling in the background.
    const onVisibilityChange = () => {
      const visible = isPageVisible();
      if (visible && !wasVisible) {
        onRefreshRef.current();
      }
      wasVisible = visible;
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [interval]);

  return refresh;
};

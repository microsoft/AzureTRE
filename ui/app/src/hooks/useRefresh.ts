import { useCallback, useEffect, useRef } from "react";

export const AUTO_REFRESH_INTERVAL_MS = 30000;

export const isPageVisible = () => document.visibilityState === "visible";

export const useRefresh = (onRefresh: () => void, interval = AUTO_REFRESH_INTERVAL_MS) => {
  const onRefreshRef = useRef(onRefresh);
  const missedWhileHidden = useRef(false);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  const refresh = useCallback(() => onRefreshRef.current(), []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (isPageVisible()) {
        onRefreshRef.current();
      } else {
        missedWhileHidden.current = true;
      }
    }, interval);

    // Catch up once when the tab becomes visible again instead of polling in the background.
    const onVisibilityChange = () => {
      if (isPageVisible() && missedWhileHidden.current) {
        missedWhileHidden.current = false;
        onRefreshRef.current();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [interval]);

  return refresh;
};

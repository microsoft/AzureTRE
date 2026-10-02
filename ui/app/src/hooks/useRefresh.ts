import { useCallback, useEffect, useRef } from "react";

export const AUTO_REFRESH_INTERVAL_MS = 30000;

export const useRefresh = (onRefresh: () => void, interval = AUTO_REFRESH_INTERVAL_MS) => {
  const onRefreshRef = useRef(onRefresh);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  const refresh = useCallback(() => onRefreshRef.current(), []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        onRefreshRef.current();
      }
    }, interval);

    return () => window.clearInterval(timer);
  }, [interval]);

  return refresh;
};

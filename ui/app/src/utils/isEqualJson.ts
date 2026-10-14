// Structural equality for API payloads, used to skip state updates (and re-renders) when polling returns unchanged data.
export const isEqualJson = (a: unknown, b: unknown): boolean => {
  if (a === b) return true;
  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return false;
  }
};

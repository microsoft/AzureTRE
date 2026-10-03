class TREError extends Error {
  constructor() {
    super();
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class APIError extends TREError {
  status?: number;
  exception?: string;
  userMessage?: string;
  endpoint?: string;
}

export const isRetryableApiError = (error: unknown) => {
  if (!error || typeof error !== "object" || !("status" in error)) {
    return false;
  }
  const status = error.status;
  return status === 408 || status === 429 || (typeof status === "number" && status >= 500);
};

export const API_UNAVAILABLE_MESSAGE =
  "The TRE API is currently unavailable. Please try again later or contact your administrator.";

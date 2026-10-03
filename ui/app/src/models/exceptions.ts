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

export const API_UNAVAILABLE_MESSAGE =
  "The TRE API is currently unavailable. Please try again later or contact your administrator.";

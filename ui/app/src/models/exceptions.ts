class TREError extends Error {
  constructor() {
    super();
    Object.setPrototypeOf(this, new.target.prototype);
  }
}


export class APIError extends TREError {
  status?: number;
  exception?: any;
  userMessage?: string;
  endpoint?: string;
}

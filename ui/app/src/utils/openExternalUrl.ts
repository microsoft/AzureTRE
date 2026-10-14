// Open a resource connection in a new tab without giving it access to this window via window.opener.
export const openExternalUrl = (url: string) => window.open(url, "_blank", "noopener,noreferrer");

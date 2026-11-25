from opentelemetry import trace
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = b"request-id"


def current_request_id() -> str:
    """Return the trace of this request in the Application Insights Request-Id format.

    App Insights stores the trace ID as OperationId, so a client can find the server logs of a failed request.
    """
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return ""
    return f"|{context.trace_id:032x}.{context.span_id:016x}."


class RequestIdMiddleware:
    """Add the Request-Id header to each HTTP response, also to a response for an unhandled exception."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                request_id = current_request_id()
                if request_id:
                    message["headers"] = [*message.get("headers", []), (HEADER, request_id.encode())]
            await send(message)

        await self.app(scope, receive, send_with_request_id)

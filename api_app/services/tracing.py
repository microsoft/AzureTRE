import logging

from fastapi import Request
from opencensus.trace import (
    attributes_helper,
    execution_context,
    print_exporter,
    samplers,
)
from opencensus.trace import span as span_module
from opencensus.trace import tracer as tracer_module
from opencensus.trace import utils
from opencensus.trace.propagation import trace_context_http_header_format
from starlette.types import ASGIApp

HTTP_HOST = attributes_helper.COMMON_ATTRIBUTES["HTTP_HOST"]
HTTP_METHOD = attributes_helper.COMMON_ATTRIBUTES["HTTP_METHOD"]
HTTP_PATH = attributes_helper.COMMON_ATTRIBUTES["HTTP_PATH"]
HTTP_ROUTE = attributes_helper.COMMON_ATTRIBUTES["HTTP_ROUTE"]
HTTP_URL = attributes_helper.COMMON_ATTRIBUTES["HTTP_URL"]
HTTP_STATUS_CODE = attributes_helper.COMMON_ATTRIBUTES["HTTP_STATUS_CODE"]

module_logger = logging.getLogger(__name__)


class RequestTracerMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        excludelist_paths=None,
        excludelist_hostnames=None,
        sampler=None,
        exporter=None,
        propagator=None,
    ) -> None:
        self.app = app
        self.excludelist_paths = excludelist_paths
        self.excludelist_hostnames = excludelist_hostnames
        self.sampler = sampler or samplers.AlwaysOnSampler()
        self.exporter = exporter or print_exporter.PrintExporter()
        self.propagator = (
            propagator or trace_context_http_header_format.TraceContextPropagator()
        )

    async def __call__(self, request: Request, call_next):

        # Do not trace if the url is in the exclude list
        if utils.disable_tracing_url(str(request.url), self.excludelist_paths):
            return await call_next(request)

        try:
            span_context = self.propagator.from_headers(request.headers)

            tracer = tracer_module.Tracer(
                span_context=span_context,
                sampler=self.sampler,
                exporter=self.exporter,
                propagator=self.propagator,
            )
        except Exception:  # pragma: NO COVER
            module_logger.error("Failed to trace request", exc_info=True)
            return await call_next(request)

        try:
            span = tracer.start_span()
            span.span_kind = span_module.SpanKind.SERVER
            span.name = "[{}]{}".format(request.method, request.url)

            tracer.add_attribute_to_current_span(HTTP_HOST, request.url.hostname)
            tracer.add_attribute_to_current_span(HTTP_METHOD, request.method)
            tracer.add_attribute_to_current_span(HTTP_PATH, request.url.path)
            tracer.add_attribute_to_current_span(HTTP_ROUTE, request.url.path)
            tracer.add_attribute_to_current_span(HTTP_URL, str(request.url))

            execution_context.set_opencensus_attr(
                "excludelist_hostnames", self.excludelist_hostnames
            )
        except Exception:  # pragma: NO COVER
            module_logger.error("Failed to trace request", exc_info=True)

        response = await call_next(request)
        try:
            tracer.add_attribute_to_current_span(HTTP_STATUS_CODE, response.status_code)
        except Exception:  # pragma: NO COVER
            module_logger.error("Failed to trace response", exc_info=True)
        finally:
            tracer.end_span()
            return response

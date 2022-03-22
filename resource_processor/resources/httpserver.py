from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def start_server():
    server = ThreadedHTTPServer(('0.0.0.0', 8080), RequestHandler)
    server.serve_forever()

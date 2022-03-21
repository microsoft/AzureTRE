from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_OPTIONS(self):
        self.send_response(200)


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


def start_server():
    server = ThreadingSimpleServer(('0.0.0.0', 8080), Handler)
    server.serve_forever()

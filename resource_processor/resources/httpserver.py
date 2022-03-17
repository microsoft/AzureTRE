from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


def start_server():
    server = ThreadingSimpleServer(('0.0.0.0', 4444), Handler)
    server.serve_forever()

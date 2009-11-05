from eventlet.api import tcp_listener
from eventlet.wsgi import server as wsgi_server
from webob import Request, Response
class TestHTTPServer(object):
    def __init__(self, port=9291):
        self.port = port
    def run(self):
        wsgi_server(tcp_listener(('127.0.0.1', self.port)), self)
    def __call__(self, environ, start_response):
        req = Request(environ)
        import pdb; pdb.set_trace()
        res = Response()
        res.status = 404
        return res(environ, start_response)

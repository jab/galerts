from getpass import getpass
from httplib import HTTPConnection, HTTPSConnection
from operator import itemgetter
from urllib import urlencode


#from eventlet.api import tcp_listener
#from eventlet.wsgi import server as wsgi_server
#from webob import Request, Response
#class TestHTTPServer(object):
#    def __init__(self, port=9291):
#        self.port = port
#    def run(self):
#        wsgi_server(tcp_listener(('127.0.0.1', self.port)), self)
#    def __call__(self, environ, start_response):
#        req = Request(environ)
#        import pdb; pdb.set_trace()
#        res = Response()
#        res.status = 404
#        return res(environ, start_response)


def gcookie(email, password):
    params = urlencode({
        'Email': email,
        'Passwd': password,
        'service': 'alerts',
        })
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    conn = HTTPSConnection('www.google.com')
    conn.request('POST', '/accounts/ClientLogin', params, headers)
    response = conn.getresponse()
    assert response.status == 200
    body = response.read()
    conn.close()
    cookie = '; '.join(body.split('\n'))
    return cookie

def getsig(cookie):
    headers = {'Cookie': cookie}
    conn = HTTPConnection('www.google.com')
    conn.request('GET', '/alerts', None, headers)
    response = conn.getresponse()
    assert response.status == 200
    body = response.read()
    # XXX this is mad brittle
    match = '<input type=hidden name="sig" value="'
    i = body.find(match) + len(match)
    sig = body[i:i+27] # sig is always 27 characters
    conn.close()
    return sig

def create_alert(cookie, query, email, type, sig):
    headers = {'Cookie': cookie,
               'Content-type': 'application/x-www-form-urlencoded'}
    params = urlencode(dict(
        q=query,
        e='feed', # email == 'feed' ->
        f='0',    # frequency == '0' (as-it-happens)
        t=type,
        sig=sig,
        ))
    conn = HTTPConnection('www.google.com')
    conn.request('POST', '/alerts/create?hl=en&gl=us', params, headers)
    response = conn.getresponse()
    if response.status == 302:
        print 'alert created'
    else:
        import pdb; pdb.set_trace()
    conn.close()


ALERT_TYPE_MAP = dict(
    news='1',
    blogs='4',
    web='2',
    comprehensive='7',
    video='9',
    groups='8',
    )

if __name__ == '__main__':
    email = raw_input('email: ')
    if not email.endswith('@gmail.com'):
        email += '@gmail.com'
    password = getpass('password: ')
    while True:
        query = raw_input('query: ')
        if len(query) <= 256:
            break
        print 'query must be at most 256 characters, try again\n'
    while True:
        type = raw_input('alert type:\n  choices:\n%s%s' %
            ('\n'.join('    %s: %s' % (k, v) for (k, v) in sorted(
            ALERT_TYPE_MAP.iteritems(), key=itemgetter(1))),
            '\n\n  choice: '))
        if type in ALERT_TYPE_MAP.itervalues():
            break
        print 'invalid type, try again\n'
    print

    cookie = gcookie(email, password)
    sig = getsig(cookie)
    create_alert(cookie, query, email, type, sig)

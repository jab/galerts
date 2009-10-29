from getpass import getpass
from httplib import HTTPConnection, HTTPSConnection
from urllib import urlencode


from eventlet.api import tcp_listener
from eventlet.wsgi import server as wsgi_server
from webob import Request, Response
class TestHTTPServer(object):
    def __init__(self, port=9291):
        self.port = port
    def run(self):
        wsgi_server(tcp_listener(('127.0.0.1', self.port)), self)
    def __call__(self, environ, start_response):
        res = Response()
        res.status = 404
        return res(environ, start_response)


# http://snipt.net/thejames/php-google-reader-authentication-script/
# http://code.google.com/p/pyrfeed/wiki/GoogleReaderAPI
def gauth(googleid, password):
    """googleid for joe@gmail.com is 'joe'"""
    params = urlencode({
        'service': 'alerts',
        'continue': 'http://www.google.com/',
        'Email': googleid,
        'Passwd': password,
        'source': 'bluzzard', # XXX can be anything
        })
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    conn = HTTPSConnection('www.google.com')
    conn.request('POST', '/accounts/ClientLogin', params, headers)
    response = conn.getresponse()
    result = {}
    if response.status == 200:
        body = response.read()
        for line in body.split():
            k, v = line.split('=', 1)
            result[k] = v
    else:
        print 'unexpected response: %d %s' % (response.status, response.reason)
        import pdb; pdb.set_trace()
    conn.close()
    return result


def greader_unread(googleid, password):
    sid = gauth(googleid, password)['SID']
    cookie = 'SID=%s; domain=.google.com; path=/; expires=1600000000' % sid
    headers = {'Cookie': cookie}
    conn = HTTPConnection('www.google.com')
    conn.request('GET', '/reader/atom/user/-/state/com.google/reading-list', '', headers) # /user/- is a shortcut for the currently logged-in user
    response = conn.getresponse()
    result = ''
    if response.status == 200:
        return response.read()
    else:
        print 'unexpected response: %d %s' % (response.status, response.reason)
        import pdb; pdb.set_trace()
    conn.close()
    return result


if __name__ == '__main__':
    googleid = raw_input('googleid: ')
    password = getpass('password: ')
    unread = greader_unread(googleid, password)
    if unread:
        from feedparser import parse
        feed = parse(unread)
        print 'unread:'
        print '\n'.join(i.title for i in feed.entries)

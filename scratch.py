from BeautifulSoup import BeautifulSoup
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

def get_alerts(cookie):
    headers = {'Cookie': cookie}
    conn = HTTPConnection('www.google.com')
    conn.request('GET', '/alerts/manage?hl=en&gl=us', None, headers)
    response = conn.getresponse()
    assert response.status == 200
    body = response.read()
    soup = BeautifulSoup(body)
    trs = soup.findAll('tr', attrs={'class': 'data_row'})
    alerts = []
    for tr in trs:
        tds = tr.findAll('td')
        tdquery = tds[1]
        tdtype = tds[2]
        tddeliver = tds[3]
        alert = dict(
            query=tdquery.findChild('a').next,
            type=tdtype.findChild('font').next,
            )
        deliver = tddeliver.findChild('font').next
        if deliver != 'Email':
            deliver = dict(deliver.attrs)['href']
        alert['deliver'] = deliver
        alerts.append(alert)
    conn.close()
    return alerts

def create_alert(cookie, query, type, sig):
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


ALERT_TYPES = dict(
    news='1',
    blogs='4',
    web='2',
    comprehensive='7',
    video='9',
    groups='8',
    )

def main():
    print 'Google Alerts Manager\n'
    try:
        email = raw_input('email: ')
        if not email.endswith('@gmail.com'):
            email += '@gmail.com'
        password = getpass('password: ')
        cookie = gcookie(email, password)

        ACTIONS = ('List Alerts', 'Create Alert', 'Quit')
        while True:
            print '\nActions:'
            print '\n'.join('  %d. %s' % (i, v) for (i, v) in enumerate(ACTIONS))
            action = raw_input('  Choice: ')
            try:
                action = int(action)
                action = ACTIONS[action]
            except (ValueError, IndexError):
                print 'bad input: enter a number from 0 to %d\n' % (len(ACTIONS) - 1)
            else:
                if action == 'List Alerts':
                    alerts = get_alerts(cookie)
                    print
                    print '  Query                Type          Deliver to'
                    print '  =====                ====          =========='
                    for alert in alerts:
                        query = alert['query']
                        if len(query) > 20:
                            query = query[:17] + '...'
                        type = alert['type']
                        deliver = alert['deliver']
                        print ' ', query.ljust(20), type.ljust(13), deliver


                elif action == 'Create Alert':
                    print '\nNew Alert'
                    while True:
                        query = raw_input('  query: ')
                        if len(query) <= 256:
                            break
                        print '  query must be at most 256 characters, try again\n'
                    while True:
                        print '  alert type:'
                        print '\n'.join('    %s. %s' % (v, k) for (k, v) in sorted(
                            ALERT_TYPES.iteritems(), key=itemgetter(1)))
                        type = raw_input('    choice: ')
                        if type in ALERT_TYPES.itervalues():
                            break
                        print '  invalid type, try again\n'
                    sig = getsig(cookie)
                    create_alert(cookie, query, type, sig)

                elif action == 'Quit':
                    break

                else:
                    print 'code took unexpected branch... typo?'
    except (EOFError, KeyboardInterrupt):
        print
        return

if __name__ == '__main__':
    main()

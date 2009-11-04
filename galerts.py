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

def scrape_sig(cookie, path='/alerts'):
    headers = {'Cookie': cookie}
    conn = HTTPConnection('www.google.com')
    conn.request('GET', path, None, headers)
    response = conn.getresponse()
    assert response.status == 200
    body = response.read()
    conn.close()
    soup = BeautifulSoup(body)
    sig = soup.findChild('input', attrs={'name': 'sig'})
    sig = dict(sig.attrs)['value']
    return sig

def scrape_hps(cookie, s):
    headers = {'Cookie': cookie}
    conn = HTTPConnection('www.google.com')
    conn.request('GET', '/alerts/edit?hl=en&gl=us&s=%s' % s, None, headers)
    response = conn.getresponse()
    assert response.status == 200
    body = response.read()
    soup = BeautifulSoup(body)
    hps = dict(soup.findChild('input', attrs={'name': 'hps'}).attrs)['value']
    return hps

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
        tdcheckbox = tds[0]
        tdquery = tds[1]
        tdtype = tds[2]
        tddeliver = tds[3]
        tdfreq = tds[4]
        alert = dict(
            s=dict(tdcheckbox.findChild('input').attrs)['value'],
            query=tdquery.findChild('a').next,
            type=tdtype.findChild('font').next,
            freq=tdfreq.findChild('font').next,
            )
        deliver = tddeliver.findChild('font').next
        if deliver != 'Email':
            deliver = dict(deliver.attrs)['href']
        alert['deliver'] = deliver
        alerts.append(alert)
    conn.close()
    return alerts

def create_alert(cookie, query, type, sig, emailorfeed='feed', freq='0'):
    """
    if creating a feed alert, pass emailorfeed='feed' and freq='0'
    """
    headers = {'Cookie': cookie,
               'Content-type': 'application/x-www-form-urlencoded'}
    params = urlencode(dict(
        q=query,
        e=emailorfeed,
        f='0' if emailorfeed == 'feed' else freq,
        t=type,
        sig=sig,
        ))
    conn = HTTPConnection('www.google.com')
    conn.request('POST', '/alerts/create?hl=en&gl=us', params, headers)
    response = conn.getresponse()
    if response.status == 302:
        print '\nAlert created.'
    else:
        import pdb; pdb.set_trace()
    conn.close()

def delete_alert(cookie, email, id, sig):
    headers = {'Cookie': cookie,
               'Content-type': 'application/x-www-form-urlencoded'}
    params = urlencode(dict(
        da='Delete',
        e=email,
        s=id,
        sig=sig,
        ))
    conn = HTTPConnection('www.google.com')
    conn.request('POST', '/alerts/save?hl=en&gl=us', params, headers)
    response = conn.getresponse()
    if response.status == 302:
        print '\nAlert deleted.'
    else:
        import pdb; pdb.set_trace()
    conn.close()

def edit_alert(cookie, email, es, query, type, sig, hps, freq=None, deliverfeed=True):
    headers = {'Cookie': cookie,
               'Content-type': 'application/x-www-form-urlencoded'}
    params = dict(
        d=deliverfeed and '6' or '0',
        e=email,
        es=es,
        hps=hps,
        q=query,
        se='Save',
        sig=sig,
        t=type,
        )
    if freq is not None:
        params['f'] = freq
    params = urlencode(params)
    conn = HTTPConnection('www.google.com')
    conn.request('POST', '/alerts/save?hl=en&gl=us', params, headers)
    response = conn.getresponse()
    if response.status == 302:
        print '\nAlert modified.'
    else:
        import pdb; pdb.set_trace()
    conn.close()


ALERT_TYPES = dict(
    News='1',
    Blogs='4',
    Web='2',
    Comprehensive='7',
    Video='9',
    Groups='8',
    )

ALERT_FREQS = {
    'as-it-happens': '0',
    'once a day': '1',
    'once a week': '6',
    }

def main():
    print 'Google Alerts Manager\n'
    try:
        email = raw_input('email: ')
        if not email.endswith('@gmail.com'):
            email += '@gmail.com'
        password = getpass('password: ')
        cookie = gcookie(email, password)

        ACTIONS = ('List Alerts', 'Create Alert', 'Edit Alert', 'Delete Alert', 'Quit')

        def print_alerts(alerts):
            print
            print ' #   Query                Type           Frequency       Deliver to'
            print ' =   =====                ====           =========       =========='
            for i, alert in enumerate(alerts):
                query = alert['query']
                if len(query) > 20:
                    query = query[:17] + '...'
                type = alert['type']
                freq = alert['freq']
                deliver = alert['deliver']
                num = '%d' % i
                print num.rjust(2), ' ', query.ljust(20), type.ljust(14), freq.ljust(15), deliver

        def prompt_type(default=None):
            while True:
                print '  Alert type:'
                print '\n'.join('    %s. %s' % (v, k) for (k, v) in sorted(
                    ALERT_TYPES.iteritems(), key=itemgetter(1)))
                if default is not None:
                    prompt = '    Choice (<Enter> for "%s"): ' % default
                else:
                    prompt = '    Choice: '
                type = raw_input(prompt)
                if type in ALERT_TYPES.itervalues():
                    return type
                if default is not None:
                    return default
                print '  Invalid type, try again\n'

        def prompt_alert(alerts):
            while True:
                try:
                    choice = int(raw_input('\n  Choice: '))
                    return alerts[choice]
                except (ValueError, IndexError):
                    print '  Bad input: enter a number from 0 to %d' % (len(alerts) - 1)

        def prompt_query(default=None):
            while True:
                if default is not None:
                    prompt = '  Query (<Enter> for "%s"): ' % default
                else:
                    prompt = '  Query: '
                query = raw_input(prompt)
                if 0 < len(query) <= 256:
                    return query
                if default is not None:
                    return default
                print '  Query must be at most 256 characters, try again\n'

        def prompt_feed():
            return raw_input('  Deliver to [F]eed or [e]mail? (F/e): ') != 'e'

        def prompt_freq(default=None):
            while True:
                print '  Alert frequency:'
                print '\n'.join('    %s. %s' % (v, k) for (k, v) in sorted(
                    ALERT_FREQS.iteritems(), key=itemgetter(1)))
                if default is not None:
                    prompt = '    Choice (<Enter> for "%s"): ' % default
                else:
                    prompt = '    Choice: '
                freq = raw_input(prompt)
                if freq in ALERT_FREQS.itervalues():
                    return freq
                if default is not None:
                    return default
                print '  Invalid frequency, try again\n'

        while True:
            print '\nActions:'
            print '\n'.join('  %d. %s' % (i, v) for (i, v) in enumerate(ACTIONS))
            action = raw_input('  Choice: ')
            try:
                action = int(action)
                action = ACTIONS[action]
            except (ValueError, IndexError):
                print 'Bad input: enter a number from 0 to %d\n' % (len(ACTIONS) - 1)
            else:
                print
                print action

                if action == 'List Alerts':
                    alerts = get_alerts(cookie)
                    print_alerts(alerts)

                elif action == 'Edit Alert':
                    alerts = get_alerts(cookie)
                    print_alerts(alerts)
                    alert = prompt_alert(alerts)
                    query = prompt_query(default=alert['query'])
                    type = prompt_type(default=ALERT_TYPES[alert['type']])
                    deliverfeed = prompt_feed() # XXX default
                    freq = None if deliverfeed else prompt_freq()
                    hps = scrape_hps(cookie, alert['s'])
                    sig = scrape_sig(cookie, path='/alerts/manage?hl=en&gl=us')
                    edit_alert(cookie, email, alert['s'], query, type, sig, hps, freq=freq, deliverfeed=deliverfeed)

                elif action == 'Delete Alert':
                    alerts = get_alerts(cookie)
                    print_alerts(alerts)
                    alert = prompt_alert(alerts)
                    sig = scrape_sig(cookie, path='/alerts/manage?hl=en&gl=us')
                    delete_alert(cookie, email, alert['s'], sig)

                elif action == 'Create Alert':
                    query = prompt_query()
                    type = prompt_type()
                    deliverfeed = prompt_feed()
                    if deliverfeed:
                        emailorfeed = 'feed'
                        freq = '0'
                    else:
                        emailorfeed = email
                        freq = prompt_freq()
                    sig = scrape_sig(cookie)
                    create_alert(cookie, query, type, sig, emailorfeed=emailorfeed, freq=freq)

                elif action == 'Quit':
                    break

                else:
                    print 'code took unexpected branch... typo?'
    except (EOFError, KeyboardInterrupt):
        print
        return

if __name__ == '__main__':
    main()

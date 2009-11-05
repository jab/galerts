from BeautifulSoup import BeautifulSoup
from getpass import getpass
from httplib import HTTPConnection, HTTPSConnection
from operator import itemgetter
from urllib import urlencode

ALERT_TYPES = {
    'News': '1',
    'Blogs': '4',
    'Web': '2',
    'Comprehensive': '7',
    'Video': '9',
    'Groups': '8',
    }

ALERT_FREQS = {
    'as-it-happens': '0',
    'once a day': '1',
    'once a week': '6',
    }


class Alert(object):
    def __init__(self, s, query, type, freq, deliver):
        self.s = s
        self.query = query
        self.type = type
        self.freq = freq
        self.deliver = deliver

    def __str__(self):
        return '<Alert query="%s" at %s>' % (self.query, hex(id(self)))


class GAlertsManager(object):
    """
    Manages creation, modification, and deletion of Google Alerts.
    Resorts to html scraping because no public API has been released.
    """
    def __init__(self, email, password):
        """
        Creates a new GAlertsManager for the google account associated
        with ``email``.

        :param email: manage alerts for this email address. If there is no @
            symbol in the value an @gmail.com address is assumed.
        :param password: plaintext password, used only to get a session
            cookie (sent over a secure connection and not stored)
        """
        if '@' not in email:
            email += '@gmail.com'
        self.email = email
        self._set_cookie(password)
        self._refresh()

    def _set_cookie(self, password):
        """
        Obtains a cookie from Google for an authenticated session.
        """
        params = urlencode({
            'Email': self.email,
            'Passwd': password,
            'service': 'alerts',
            })
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        conn = HTTPSConnection('www.google.com')
        conn.request('POST', '/accounts/ClientLogin', params, headers)
        response = conn.getresponse()
        assert response.status == 200, 'Unexpected response; bad email/password?'
        body = response.read()
        conn.close()
        self.cookie = '; '.join(body.split('\n'))

    def _scrape_sig(self, path='/alerts'):
        """
        Google signs forms with a value in a hidden input named "sig" to
        prevent xss attacks, so we need to scrape this out and submit it along
        with any forms we POST.
        """
        headers = {'Cookie': self.cookie}
        conn = HTTPConnection('www.google.com')
        conn.request('GET', path, None, headers)
        response = conn.getresponse()
        assert response.status == 200
        body = response.read()
        conn.close()
        soup = BeautifulSoup(body)
        sig = soup.findChild('input', attrs={'name': 'sig'})['value']
        return sig

    def _scrape_sig_es_hps(self, alert):
        """
        Each alert is associated with two values in hidden inputs named "es"
        and "hps" which must be scraped and passed along when modifying it.
        """
        headers = {'Cookie': self.cookie}
        conn = HTTPConnection('www.google.com')
        conn.request('GET', '/alerts/edit?hl=en&gl=us&s=%s' % alert.s, None, headers)
        response = conn.getresponse()
        assert response.status == 200
        body = response.read()
        soup = BeautifulSoup(body)
        sig = soup.findChild('input', attrs={'name': 'sig'})['value']
        es = soup.findChild('input', attrs={'name': 'es'})['value']
        hps = soup.findChild('input', attrs={'name': 'hps'})['value']
        return sig, es, hps

    def _refresh(self):
        headers = {'Cookie': self.cookie}
        conn = HTTPConnection('www.google.com')
        conn.request('GET', '/alerts/manage?hl=en&gl=us', None, headers)
        response = conn.getresponse()
        assert response.status == 200
        body = response.read()
        soup = BeautifulSoup(body)
        trs = soup.findAll('tr', attrs={'class': 'data_row'})
        self.alerts = []
        for tr in trs:
            tds = tr.findAll('td')
            tdcheckbox = tds[0]
            tdquery = tds[1]
            tdtype = tds[2]
            tddeliver = tds[3]
            tdfreq = tds[4]
            s = tdcheckbox.findChild('input')['value']
            query = tdquery.findChild('a').next
            type = tdtype.findChild('font').next
            freq = tdfreq.findChild('font').next
            deliver = tddeliver.findChild('font').next
            if deliver != 'Email': # deliver to feed
                deliver = deliver['href']
            alert = Alert(s, query, type, freq, deliver)
            self.alerts.append(alert)
        conn.close()

    def create(self, query, type, feed=True, freq='0'):
        """
        Creates a new alert.

        :param query: the search terms the alert will match
        :param type: a value in ``ALERT_TYPES`` indicating the desired results
        :param feed: whether to deliver results via feed or email
        :param freq: a value in ``ALERT_FREQS`` indicating how often results
            should be delivered. Used only for email alerts; feed alerts are
            updated in real time.
        """
        headers = {'Cookie': self.cookie,
                   'Content-type': 'application/x-www-form-urlencoded'}
        params = urlencode({
            'q': query,
            'e': 'feed' if feed else self.email,
            'f': '0' if feed else freq,
            't': type,
            'sig': self._scrape_sig(),
            })
        conn = HTTPConnection('www.google.com')
        conn.request('POST', '/alerts/create?hl=en&gl=us', params, headers)
        response = conn.getresponse()
        if response.status == 302:
            success = True
        else:
            success = False
            import pdb; pdb.set_trace()
        conn.close()
        self._refresh()
        return success

    def edit(self, alert, query, type, feed=True, freq='0'):
        """
        Modifies an existing alert.

        :param alert: the alert to modify
        :param query: the search terms the alert will match
        :param type: a value in ``ALERT_TYPES`` indicating the desired results
        :param feed: whether to deliver results via feed or email
        :param freq: a value in ``ALERT_FREQS`` indicating how often results
            should be delivered. Used only for email alerts; feed alerts are
            updated in real time.
        """
        headers = {'Cookie': self.cookie,
                   'Content-type': 'application/x-www-form-urlencoded'}
        sig, es, hps = self._scrape_sig_es_hps(alert)
        params = {
            'd': feed and '6' or '0',
            'e': self.email,
            'es': es,
            'hps': hps,
            'q': query,
            'se': 'Save',
            'sig': sig,
            't': type,
            }
        if not feed:
            params['f'] = freq
        params = urlencode(params)
        conn = HTTPConnection('www.google.com')
        conn.request('POST', '/alerts/save?hl=en&gl=us', params, headers)
        response = conn.getresponse()
        if response.status == 302:
            success = True
        else:
            success = False
            import pdb; pdb.set_trace()
        conn.close()
        self._refresh()
        return success

    def delete(self, alert):
        """
        Deletes an existing alert.
        """
        headers = {'Cookie': self.cookie,
                   'Content-type': 'application/x-www-form-urlencoded'}
        params = urlencode({
            'da': 'Delete',
            'e': self.email,
            's': alert.s,
            'sig': self._scrape_sig(path='/alerts/manage?hl=en&gl=us'),
            })
        conn = HTTPConnection('www.google.com')
        conn.request('POST', '/alerts/save?hl=en&gl=us', params, headers)
        response = conn.getresponse()
        if response.status == 302:
            success = True
        else:
            success = False
            import pdb; pdb.set_trace()
        conn.close()
        self._refresh()
        return success


def main():
    print 'Google Alerts Manager\n'
    try:
        email = raw_input('email: ')
        password = getpass('password: ')
        gam = GAlertsManager(email, password)

        ACTIONS = ('List Alerts', 'Create Alert', 'Edit Alert', 'Delete Alert', 'Quit')

        def print_alerts(alerts):
            print
            print ' #   Query                Type           Frequency       Deliver to'
            print ' =   =====                ====           =========       =========='
            for i, alert in enumerate(alerts):
                query = alert.query
                if len(query) > 20:
                    query = query[:17] + '...'
                type = alert.type
                freq = alert.freq
                deliver = alert.deliver
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
                continue

            print '\n%s' % action

            if action == 'List Alerts':
                print_alerts(gam.alerts)

            elif action == 'Create Alert':
                query = prompt_query()
                type = prompt_type()
                feed = prompt_feed()
                freq = '0' if feed else prompt_freq()
                if gam.create(query, type, feed=feed, freq=freq):
                    print '\nAlert created.'
                else:
                    print '\nCould not create alert.'

            elif action == 'Edit Alert':
                print_alerts(gam.alerts)
                alert = prompt_alert(gam.alerts)
                query = prompt_query(default=alert.query)
                type = prompt_type(default=ALERT_TYPES[alert.type])
                feed = prompt_feed() # XXX default
                freq = '0' if feed else prompt_freq()
                if gam.edit(alert, query, type, feed=feed, freq=freq):
                    print '\nAlert modified.'
                else:
                    print '\nCould not modify alert.'

            elif action == 'Delete Alert':
                print_alerts(gam.alerts)
                alert = prompt_alert(gam.alerts)
                if gam.delete(alert):
                    print '\nAlert deleted.'
                else:
                    print '\nCould not delete alert.'

            elif action == 'Quit':
                break

            else:
                print 'code took unexpected branch... typo?'
    except (EOFError, KeyboardInterrupt):
        print
        return

if __name__ == '__main__':
    main()

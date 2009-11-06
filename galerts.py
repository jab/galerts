from BeautifulSoup import BeautifulSoup
from collections import defaultdict
from getpass import getpass
from httplib import HTTPConnection, HTTPSConnection
from operator import itemgetter
from urllib import urlencode

DELIVER_EMAIL = 'Email'
DELIVER_FEED = 'feed'
DELIVER_DEFAULT_VAL = '6'
DELIVER_TYPES = {
    DELIVER_EMAIL: '0',
    DELIVER_FEED: DELIVER_DEFAULT_VAL,
    }

AS_IT_HAPPENS = 'as-it-happens'
ALERT_FREQS = {
    AS_IT_HAPPENS: '0',
    'once a day': '1',
    'once a week': '6',
    }

ALERT_TYPES = {
    'News': '1',
    'Blogs': '4',
    'Web': '2',
    'Comprehensive': '7',
    'Video': '9',
    'Groups': '8',
    }

class SignInError(Exception): pass
class UnexpectedResponseError(Exception):
    def __init__(self, status, headers, body):
        Exception.__init__(self)
        self.resp_status = status
        self.resp_headers = headers
        self.resp_body = body


class Alert(object):
    def __init__(self, s, query, type, freq, deliver):
        """
        Creates a new Alert object.

        :param s: the hidden input "s" value Google associates with this alert
        :param query: the search terms the alert will match
        :param type: a value in ``ALERT_TYPES`` indicating the desired results
        :param freq: a value in ``ALERT_FREQS`` indicating how often results
            should be delivered
        :param deliver: should be set to ``DELIVER_EMAIL`` if results are to
            be delivered via email; if results are delivered via feed, this
            should be set to either the url of the feed if it's already been
            created or to ``DELIVER_FEED`` if it hasn't been created yet
        """
        assert type in ALERT_TYPES
        assert freq in ALERT_FREQS
        self.s = s
        self.query = query
        self.type = type
        self.freq = freq
        self.deliver = deliver

    def __repr__(self):
        return '<Alert query="%s" at %s>' % (self.query, hex(id(self)))

    def __str__(self):
        return '<Alert query="%s" type="%s" freq="%s" deliver="%s">' % (
            self.query, self.type, self.freq, self.deliver)


class GAlertsManager(object):
    """
    Manages creation, modification, and deletion of Google Alerts for a given
    Google account.

    Resorts to html scraping because no public API has been released.
    """
    def __init__(self, email, password):
        """
        Creates a new GAlertsManager for the google account associated
        with ``email``. Note: multiple email addresses can be associated
        with a single Google account, and if a user with multiple email
        addresses associated with her Google account signs into the web
        interface, it will allow her to set the delivery of email alerts to
        any of her associated email addresses. However, for simplicity's sake,
        ``GAlertsManager`` always uses the email address it's instantiated
        with for the delivery of email alerts.

        :param email: sign in using this email address; if there is no @
            symbol in the value, "@gmail.com" will be appended to it
        :param password: plaintext password, used only to get a session
            cookie (i.e. it's sent over a secure connection and then discarded)
        """
        if '@' not in email:
            email += '@gmail.com'
        self.email = email
        self._signin(password)
        self._refresh()

    def _signin(self, password):
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
        body = response.read()
        try:
            if response.status == 403:
                raise SignInError('Got 403 Forbidden; bad email/password combination?')
            if response.status != 200:
                raise UnexpectedResponseError(response.status, response.getheaders(), body)
            self.cookie = '; '.join(body.split('\n'))
        finally:
            conn.close()

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
        body = response.read()
        try:
            if response.status != 200:
                raise UnexpectedResponseError(response.status, response.getheaders(), body)
            soup = BeautifulSoup(body)
            sig = soup.findChild('input', attrs={'name': 'sig'})['value']
            return sig
        finally:
            conn.close()

    def _scrape_sig_es_hps(self, alert):
        """
        Each alert is associated with two values in hidden inputs named "es"
        and "hps" which must be scraped and passed along when modifying it
        along with the "sig" hidden input value to prevent xss attacks.
        """
        headers = {'Cookie': self.cookie}
        conn = HTTPConnection('www.google.com')
        conn.request('GET', '/alerts/edit?hl=en&gl=us&s=%s' % alert.s, None, headers)
        response = conn.getresponse()
        body = response.read()
        try:
            if response.status != 200:
                raise UnexpectedResponseError(response.status, response.getheaders(), body)
            soup = BeautifulSoup(body)
            sig = soup.findChild('input', attrs={'name': 'sig'})['value']
            es = soup.findChild('input', attrs={'name': 'es'})['value']
            hps = soup.findChild('input', attrs={'name': 'hps'})['value']
            return sig, es, hps
        finally:
            conn.close()

    def _refresh(self):
        headers = {'Cookie': self.cookie}
        conn = HTTPConnection('www.google.com')
        conn.request('GET', '/alerts/manage?hl=en&gl=us', None, headers)
        response = conn.getresponse()
        body = response.read()
        self.alerts = []
        try:
            if response.status != 200:
                raise UnexpectedResponseError(response.status, response.getheaders(), body)
            soup = BeautifulSoup(body)
            trs = soup.findAll('tr', attrs={'class': 'data_row'})
            for tr in trs:
                tds = tr.findAll('td')
                # annoyingly, if you have no alerts, Google tells you this in
                # a <tr> with class "data_row" in a single <td>
                if len(tds) < 5:
                    # we continue rather than break because there could be
                    # subsequent iterations for other email addresses associated
                    # with this account which do have alerts
                    continue
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
                if deliver != DELIVER_EMAIL: # deliver to feed
                    deliver = deliver['href']
                alert = Alert(s, query, type, freq, deliver)
                self.alerts.append(alert)
        finally:
            conn.close()

    def create(self, query, type, feed=True, freq=ALERT_FREQS[AS_IT_HAPPENS]):
        """
        Creates a new alert.

        :param query: the search terms the alert will match
        :param type: a value in ``ALERT_TYPES`` indicating the desired results
        :param feed: whether to deliver results via feed or email
        :param freq: a value in ``ALERT_FREQS`` indicating how often results
            should be delivered; used only for email alerts (feed alerts are
            updated in real time)
        """
        headers = {'Cookie': self.cookie,
                   'Content-type': 'application/x-www-form-urlencoded'}
        params = urlencode({
            'q': query,
            'e': DELIVER_FEED if feed else self.email,
            'f': ALERT_FREQS[AS_IT_HAPPENS] if feed else freq,
            't': ALERT_TYPES[type],
            'sig': self._scrape_sig(),
            })
        conn = HTTPConnection('www.google.com')
        conn.request('POST', '/alerts/create?hl=en&gl=us', params, headers)
        response = conn.getresponse()
        try:
            if response.status != 302:
                raise UnexpectedResponseError(response.status, response.getheaders(), response.read())
            self._refresh()
        finally:
            conn.close()

    def edit(self, alert):
        """
        Saves an existing alert which has been modified.

        :param alert: the modified alert to save
        """
        headers = {'Cookie': self.cookie,
                   'Content-type': 'application/x-www-form-urlencoded'}
        sig, es, hps = self._scrape_sig_es_hps(alert)
        params = {
            'd': DELIVER_TYPES.get(alert.deliver, DELIVER_DEFAULT_VAL),
            'e': self.email,
            'es': es,
            'hps': hps,
            'q': alert.query,
            'se': 'Save',
            'sig': sig,
            't': ALERT_TYPES[alert.type],
            }
        if alert.deliver == DELIVER_EMAIL:
            params['f'] = ALERT_FREQS[alert.freq]
        params = urlencode(params)
        conn = HTTPConnection('www.google.com')
        conn.request('POST', '/alerts/save?hl=en&gl=us', params, headers)
        response = conn.getresponse()
        try:
            if response.status != 302:
                raise UnexpectedResponseError(response.status, response.getheaders(), response.read())
            self._refresh()
        finally:
            conn.close()

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
        try:
            if response.status != 302:
                raise UnexpectedResponseError(response.status, response.getheaders(), response.read())
            self._refresh()
        finally:
            conn.close()


def main():
    print 'Google Alerts Manager\n'
    try:
        while True:
            email = raw_input('email: ')
            password = getpass('password: ')
            try:
                gam = GAlertsManager(email, password)
                break
            except SignInError:
                print '\nSign in failed, try again or hit Ctrl-C to quit\n'

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
                for k, v in ALERT_TYPES.iteritems():
                    if v == type:
                        return k
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

        def prompt_deliver(current=None):
            if current is None:
                if raw_input('  Deliver to [F]eed or [e]mail? (F/e): ') != 'e':
                    return DELIVER_FEED
                return DELIVER_EMAIL
            if current == DELIVER_EMAIL:
                if raw_input('  Switch to feed delivery (y/N)? ') == 'y':
                    return DELIVER_FEED
                return DELIVER_EMAIL
            if raw_input('  Switch to email delivery (y/N)? ') == 'y':
                return DELIVER_EMAIL
            return current

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
                for k, v in ALERT_FREQS.iteritems():
                    if v == freq:
                        return k
                if default is not None:
                    return default
                print '  Invalid frequency, try again\n'


        ACTIONS = ('List Alerts', 'Create Alert', 'Edit Alert', 'Delete Alert', 'Quit')
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
                feed = prompt_deliver() == DELIVER_FEED
                freq = ALERT_FREQS[AS_IT_HAPPENS] if feed else prompt_freq()
                try:
                    gam.create(query, type, feed=feed, freq=freq)
                    print '\nAlert created.'
                except UnexpectedResponseError, e:
                    print '\nCould not create alert.'
                    import pdb; pdb.set_trace()

            elif action == 'Edit Alert':
                print_alerts(gam.alerts)
                alert = prompt_alert(gam.alerts)
                alert.query = prompt_query(default=alert.query)
                alert.type = prompt_type(default=alert.type)
                alert.deliver = prompt_deliver(current=alert.deliver)
                alert.freq = AS_IT_HAPPENS if alert.deliver != DELIVER_EMAIL \
                    else prompt_freq(default=alert.freq)
                try:
                    gam.edit(alert)
                    print '\nAlert modified.'
                except UnexpectedResponseError, e:
                    print '\nCould not modify alert.'
                    import pdb; pdb.set_trace()

            elif action == 'Delete Alert':
                print_alerts(gam.alerts)
                alert = prompt_alert(gam.alerts)
                try:
                    gam.delete(alert)
                    print '\nAlert deleted.'
                except UnexpectedResponseError, e:
                    print '\nCould not delete alert.'
                    import pdb; pdb.set_trace()

            elif action == 'Quit':
                break

            else:
                print 'code took unexpected branch... typo?'
    except (EOFError, KeyboardInterrupt):
        print
        return

if __name__ == '__main__':
    main()

# Copyright (c) 2009 Josh Bronson and contributors
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from BeautifulSoup import BeautifulSoup
from collections import Hashable
from getpass import getpass
from httplib import HTTPConnection, HTTPSConnection
from operator import itemgetter
from urllib import urlencode


# these values must match those used in the Google Alerts web interface:

#: Use this value to indicate delivery via email
DELIVER_EMAIL = 'Email'
#: Use this value to indicate delivery via feed
DELIVER_FEED = 'feed'
DELIVER_DEFAULT_VAL = '6'
#: maps available delivery types to the values Google uses for them
DELIVER_TYPES = {
    DELIVER_EMAIL: '0',
    DELIVER_FEED: DELIVER_DEFAULT_VAL,
    }

#: Use this value for :attr:`Alert.freq` to indicate delivery in real time
FREQ_AS_IT_HAPPENS = 'as-it-happens'
#: Use this value for :attr:`Alert.freq` to indicate delivery once a day
FREQ_ONCE_A_DAY = 'once a day'
#: Use this value for :attr:`Alert.freq` to indicate delivery once a week
FREQ_ONCE_A_WEEK = 'once a week'
#: maps available alert frequencies to the values Google uses for them
ALERT_FREQS = {
    FREQ_AS_IT_HAPPENS: '0',
    FREQ_ONCE_A_DAY: '1',
    FREQ_ONCE_A_WEEK: '6',
    }

#: Use this value for :attr:`Alert.type` to indicate news results
TYPE_NEWS = 'News'
#: Use this value for :attr:`Alert.type` to indicate blog results
TYPE_BLOGS = 'Blogs'
#: Use this value for :attr:`Alert.type` to indicate web results
TYPE_WEB = 'Web'
#: Use this value for :attr:`Alert.type` to indicate comprehensive results
TYPE_COMPREHENSIVE = 'Comprehensive'
#: Use this value for :attr:`Alert.type` to indicate video results
TYPE_VIDEO = 'Video'
#: Use this value for :attr:`Alert.type` to indicate groups results
TYPE_GROUPS = 'Groups'
#: maps available alert types to the values Google uses for them
ALERT_TYPES = {
    TYPE_NEWS: '1',
    TYPE_BLOGS: '4',
    TYPE_WEB: '2',
    TYPE_COMPREHENSIVE: '7',
    TYPE_VIDEO: '9',
    TYPE_GROUPS: '8',
    }

class SignInError(Exception):
    """
    Raised when Google sign in fails.
    """

class UnexpectedResponseError(Exception):
    """
    Raised when Google's response to a request is unrecognized.
    """
    def __init__(self, status, headers, body):
        Exception.__init__(self)
        self.resp_status = status
        self.resp_headers = headers
        self.resp_body = body


class Alert(Hashable):
    """
    Models a Google Alert.

    You should not create :class:`Alert` objects explicitly; the
    :class:`GAlertsManager` will create them for you. You can then access
    alert objects via :attr:`GAlertsManager.alerts` to e.g. update their
    attributes and pass them back to the manager for saving. To create a new
    alert, use :attr:`GAlertsManager.create`, and when you next access
    :attr:`GAlertsManager.alerts` you'll find an :class:`Alert` object there
    for the alert you just created.
    """
    def __init__(self, email, s, query, type, freq, deliver, feedurl=None):
        """
        :param email: an email address of the Google account associated with
            this alert
        :param s: the hidden input "s" value Google associates with this alert;
            you shouldn't ever have to worry about setting or getting this, it's
            used internally by :class:`GAlertsManager` to save changes to Google
        :param query: the search terms the alert will match
        :param type: a value in :attr:`ALERT_TYPES` indicating the desired
            results
        :param freq: a value in :attr:`ALERT_FREQS` indicating how often results
            should be delivered
        :param deliver: a value in :attr:`DELIVER_TYPES` indicating whether to
            deliver results via feed or email
        :param feedurl: if a feed alert, the url of the feed
        """
        assert type in ALERT_TYPES
        assert freq in ALERT_FREQS
        assert deliver in DELIVER_TYPES
        self._email = email
        self._s = s
        self.query = query
        self.type = type
        self.freq = freq
        self.deliver = deliver
        self._feedurl = feedurl

    @property
    def email(self):
        return self._email

    @property
    def s(self):
        return self._s

    @property
    def feedurl(self):
        return self._feedurl

    def _eqattrs(self, query, type, freq, deliver):
        """
        Convenience function used internally by :class:`GAlertsManager`
        """
        return (self.query == query and self.type == type and
            self.freq == freq and self.deliver == deliver)

    def __getattr__(self, attr):
        object.__getattr__(self, attr)

    def __setattr__(self, attr, value):
        """
        Ensures a valid value when attempting to set :attr:`freq`,
        :attr:`type`, or :attr:`deliver`.
        """
        if attr == 'freq' and value not in ALERT_FREQS:
            raise ValueError('Illegal value for Alert.freq: "%s"' % value)
        if attr == 'type' and value not in ALERT_TYPES:
            raise ValueError('Illegal value for Alert.type: "%s"' % value)
        if attr == 'deliver' and value not in DELIVER_TYPES:
            raise ValueError('Illegal value for Alert.deliver: "%s"' % value)
        object.__setattr__(self, attr, value)

    def __hash__(self):
        return hash((self._s, self.query, self.type, self.freq, self.deliver,
            self._feedurl))

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr) for attr in
            ('_s', 'query', 'type', 'freq', 'deliver', '_feedurl'))

    def __repr__(self):
        return '<Alert for "%s" at %s>' % (self.query, hex(id(self)))

    def __str__(self):
        return '<Alert query="%s" type="%s" freq="%s" deliver="%s">' % (
            self.query, self.type, self.freq, self.deliver)


class GAlertsManager(object):
    """
    Manages creation, modification, and deletion of Google Alerts for the
    Google account associated with *email*.

    Note: multiple email addresses can be associated with a single Google
    account, and if a user with multiple email addresses associated with her
    Google account signs into the web interface, it will allow her to set the
    delivery of email alerts to any of her associated email addresses. However,
    for now, :class:`GAlertsManager` always uses the email address it's
    instantiated with when creating new email alerts or changing feed alerts
    to email.

    Resorts to html scraping because no public API has been released.
    """
    def __init__(self, email, password):
        """
        :param email: sign in using this email address; if there is no @
            symbol in the value, "@gmail.com" will be appended to it
        :param password: plaintext password, used only to get a session
            cookie (i.e. it's sent over a secure connection and then discarded)
        :raises: :exc:`SignInError` if Google responds with "403 Forbidden" to
            our request to sign in
        :raises: :exc:`UnexpectedResponseError` if the status code of Google's
              response is unrecognized (neither 403 nor 200)
        :raises: :exc:`socket.error` e.g. if there is no network connection
        """
        if '@' not in email:
            email += '@gmail.com'
        self.email = email
        self._signin(password)

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

    @property
    def alerts(self):
        """
        Queries Google on every access for the alerts associated with this
        account, wraps them in :class:`Alert` objects, and returns a
        generator you can use to iterate over them.
        """
        headers = {'Cookie': self.cookie}
        conn = HTTPConnection('www.google.com')
        conn.request('GET', '/alerts/manage?hl=en&gl=us', None, headers)
        response = conn.getresponse()
        body = response.read()
        try:
            if response.status != 200:
                raise UnexpectedResponseError(response.status, response.getheaders(), body)
        finally:
            conn.close()

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
            email = self.email # XXX scrape out of html (could be another address associated with this account)
            s = tdcheckbox.findChild('input')['value']
            query = tdquery.findChild('a').next
            # yes, they actually use <font> tags. really.
            type = tdtype.findChild('font').next
            freq = tdfreq.findChild('font').next
            deliver = tddeliver.findChild('font').next
            feedurl = None
            if deliver != DELIVER_EMAIL:
                feedurl = deliver['href']
                deliver = DELIVER_FEED
            yield Alert(email, s, query, type, freq, deliver, feedurl=feedurl)
    
    def create(self, query, type, feed=True, freq=ALERT_FREQS[FREQ_AS_IT_HAPPENS]):
        """
        Creates a new alert.

        :param query: the search terms the alert will match
        :param type: a value in :attr:`ALERT_TYPES` indicating the desired
            results
        :param feed: whether to deliver results via feed or email
        :param freq: a value in :attr:`ALERT_FREQS` indicating how often results
            should be delivered; used only for email alerts (feed alerts are
            updated in real time)
        """
        headers = {'Cookie': self.cookie,
                   'Content-type': 'application/x-www-form-urlencoded'}
        params = urlencode({
            'q': query,
            'e': DELIVER_FEED if feed else self.email,
            'f': ALERT_FREQS[FREQ_AS_IT_HAPPENS] if feed else freq,
            't': ALERT_TYPES[type],
            'sig': self._scrape_sig(),
            })
        conn = HTTPConnection('www.google.com')
        conn.request('POST', '/alerts/create?hl=en&gl=us', params, headers)
        response = conn.getresponse()
        try:
            if response.status != 302:
                raise UnexpectedResponseError(response.status, response.getheaders(), response.read())
        finally:
            conn.close()

    def update(self, alert):
        """
        Updates an existing alert which has been modified.
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
        finally:
            conn.close()


def main():
    import socket
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
            except socket.error:
                print '\nCould not connect to Google. Check your network ' \
                    'connection and try again, or hit Ctrl-C to quit\n'

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
            return DELIVER_FEED

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
                freq = ALERT_FREQS[FREQ_AS_IT_HAPPENS] if feed else prompt_freq()
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
                alert.freq = FREQ_AS_IT_HAPPENS if alert.deliver != DELIVER_EMAIL \
                    else prompt_freq(default=alert.freq)
                try:
                    gam.update(alert)
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

galerts
=======

-----
Intro
-----

galerts is a Python client for managing `Google Alerts
<http://www.google.com/alerts>`_. Currently it resorts to scraping html from
Google's web interface since there is as of yet no public API. If they ever
decide to publish one, galerts will promptly switch over to using it.

Please find `galerts on github <http://github.com/jab/galerts>`_
if you have any questions or would like to collaborate.

-----
Usage
-----

Using galerts should be pretty straightforward. Just create a manager for a
given account::

    >>> import galerts
    >>> gam = galerts.GAlertsManager('cornelius@gmail.com', 'p4ssw0rd')

(Note: The plaintext password is used only to get a session cookie, i.e. it's
sent over a secure connection and then discarded.)

Now you can access the existing alerts for that account like so::

    >>> alerts = list(gam.alerts)
    >>> alerts
    [<Alert for "Corner Confectionary" at ...>]

Hm, looks like there's a typo. Let's fix it::

    >>> alert = alerts[0]
    >>> alert.query = 'Corner Confectionery'
    >>> alert
    <Alert for "Corner Confectionery" at ...>]

So far we've only changed the value in memory. To save the result to Google,
do::

    >>> gam.update(alert)

And now it should be updated::

    >>> alerts = list(gam.alerts)
    >>> alerts
    [<Alert for "Corner Confectionery" at ...>]

NOTE: There is no guarantee that the Alert object inside the manager's
alerts attribute is the same object across different accesses. In other
words, it *may not* be the case that ``id(alert) == id(alerts[2])``.
However, you can still pass the old alert object to the manager for future
updates or for deletion; the object is merely used to wrap some attributes,
and it's the attributes which matter. You can always be sure that two
different Alert objects whose attributes are equal compare equal::

    >>> alert == alerts[0]
    True

Let's demonstrate by changing our old alert object's delivery frequency::

    >>> alert.freq
    'once a week'
    >>> alert.freq = galerts.FREQ_ONCE_A_DAY
    >>> alerts = list(gam.alerts)
    >>> alerts[0].freq
    'once a week'
    >>> alert == alerts[0]
    False
    >>> gam.update(alert)

And the changes should stick::

    >>> alerts = list(gam.alerts)
    >>> alerts[0].freq
    'once a day'
    >>> alert == alerts[0]
    True

As mentioned, we can still use this alert object to delete this alert::

    >>> gam.delete(alert)
    >>> list(gam.alerts)
    []

Finally, let's demonstrate creating a new alert::

    >>> query = 'Cake Man Cornelius'
    >>> type = galerts.TYPE_COMPREHENSIVE
    >>> gam.create(query, type)
    >>> gam.alerts
    [<Alert for "Cake Man Cornelius" at ...>]

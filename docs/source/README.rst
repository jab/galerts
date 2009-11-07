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

    >>> gam.alerts
    [<Alert for "Cake Man Cornelius" at ...>,
    <Alert for "red velvet cake recipes" at ...>,
    <Alert for "Corner Confectionary" at ...>]

Hm, looks like that last one has a typo, no wonder it wasn't generating
good results. Let's fix it::

    >>> alert = alerts[2]
    >>> alert.query = 'Corner Confectionery'
    >>> alert
    <Alert for "Corner Confectionery" at ...>]

So far we've only changed the value in memory. To save the result to Google,
do::

    >>> gam.update(alert)

And now it should be updated::

    >>> gam.alerts
    [<Alert for "Cake Man Cornelius" at ...>,
    <Alert for "red velvet cake recipes" at ...>,
    <Alert for "Corner Confectionery" at ...>]

NOTE: Every time we look at the manager's alerts, the manager creates new
Alert objects, so that::
    
    >>> alert.query == gam.alerts[2].query == 'Corner Confectionery'
    True
    >>> id(alert) == id(alerts[2])
    False

But you can still pass the old alert object to the manager for further
updates or for deletion; the object is merely used to wrap some attributes, and
it's the attributes which matter. Let's demonstrate by changing our old alert
object's delivery frequency::

    >>> alert.freq
    'once a week'
    >>> alert.freq = galerts.FREQ_ONCE_A_DAY
    >>> gam.update(alert)

And the changes should stick::

    >>> [a.freq for a in gam.alerts if a.query == 'Corner Confectionery']
    ['once a day']

As mentioned, we can still use this alert object to delete this alert::

    >>> gam.delete(alert)
    >>> gam.alerts
    [<Alert for "Cake Man Cornelius" at ...>,
    <Alert for "red velvet cake recipes" at ...>]

Finally, let's demonstrate creating a new alert::

    >>> query = 'chocolate mousse recipes'
    >>> type = galerts.TYPE_COMPREHENSIVE
    >>> gam.create(query, type)
    >>> gam.alerts
    [<Alert for "Cake Man Cornelius" at ...>,
    <Alert for "red velvet cake recipes" at ...>,
    <Alert for "chocolate mousse recipes" at ...>]

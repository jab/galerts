galerts
=======

-----
Intro
-----

galerts is a Python client for managing `Google Alerts
<http://www.google.com/alerts>`_. Currently it resorts to scraping html from
Google's web interface since there is as of yet no public API. If they ever
decide to publish one, galerts will switch to using it.

Please find `galerts on github <http://github.com/jab/galerts>`_
if you have any questions or would like to collaborate.

-----
Usage
-----

First create an alerts manager for a given account::

    >>> import galerts
    >>> gam = galerts.GAlertsManager('cornelius@gmail.com', 'p4ssw0rd')

(Note: The plaintext password is used only to get a session cookie, i.e. it's
sent over a secure connection and then discarded.)

Now you can access the existing alerts for that account via the :attr:`alerts`
property, which provides an iterator of :class:`Alert` objects::

    >>> list(gam.alerts)
    [<Alert for "Corner Confectionary" at ...>]

Looks like we have one existing alert, but it has a typo. Let's fix it::

    >>> alert = next(gam.alerts)
    >>> alert.query
    'Corner Confectionary'
    >>> alert.query = 'Corner Confectionery'
    >>> alert
    <Alert for "Corner Confectionery" at ...>

So far we've only changed the value in memory; as far as Google knows, the
alert still has the old value::

    >>> list(gam.alerts)
    [<Alert for "Corner Confectionary" at ...>]

To save the result to Google, do::

    >>> gam.update(alert)

And now it should be updated::

    >>> list(gam.alerts)
    [<Alert for "Corner Confectionery" at ...>]

You can also change other attributes::

    >>> alert.type
    'Blogs'
    >>> alert.deliver
    'Email'
    >>> alert.freq
    'once a week'
    >>> alert.type = galerts.TYPE_COMPREHENSIVE
    >>> alert.deliver = galerts.DELIVER_FEED
    >>> gam.update(alert)

We've just changed the type of results the alert delivers from only blog
updates to a comprehensive mix, and we changed the delivery method so that
results will now be delivered via feed rather than via email. Let's make sure
the changes stuck::

    >>> alert = next(gam.alerts)
    >>> alert.query
    'Corner Confectionery'
    >>> alert.type
    'Comprehensive'
    >>> alert.deliver
    'feed'

Google Alerts feeds update continuously, and our alert object's :attr:`freq`
attribute has been updated to reflect this::

    >>> alert.freq
    'as-it-happens'

And now we can also get the url of the feed results will be delivered to::

    >>> alert.feedurl
    'http://www.google.com/alerts/feed/...'

To delete the alert::

    >>> gam.delete(alert)
    >>> list(gam.alerts)
    []

And to create a new one::

    >>> query = 'Cake Man Cornelius'
    >>> type = galerts.TYPE_COMPREHENSIVE
    >>> gam.create(query, type)
    >>> list(gam.alerts)
    [<Alert for "Cake Man Cornelius" at ...>]

This created a feed alert since we didn't specify otherwise. If we had wanted
to create an email alert, we could have passed the additional keyword argument
*feed=False* and an optional delivery frequency *freq*. Let's demonstrate
changing the feed alert we created to an email alert::

    >>> alert = next(gam.alerts)
    >>> alert.feedurl
    'http://www.google.com/alerts/feed/...'
    >>> str(alert)
    '<Alert query="Cake Man Cornelius" type="Comprehensive" freq="as-it-happens" deliver="feed">'
    >>> alert.deliver = galerts.DELIVER_EMAIL
    >>> alert.freq = galerts.FREQ_ONCE_A_DAY
    >>> gam.update(alert)

And now::

    >>> alert = next(gam.alerts) # get a fresh object just to prove it
    >>> str(alert)
    '<Alert query="Cake Man Cornelius" type="Comprehensive" freq="once a day" deliver="Email">'
    >>> alert.feedurl
    None

galerts
=======

-----
Intro
-----

galerts is a Python client for managing `Google Alerts
<http://www.google.com/alerts>`_. Currently it resorts to scraping html from
Google's web interface since there is as of yet no public API. If they ever
decide to publish one, galerts will switch to using it, unless Google itself
includes it in their `gdata-python-client <http://code.google.com/p/gdata-python-client/>`_,
in which case galerts will be obsolete.

---------
Community
---------

galerts is `on github <http://github.com/jab/galerts>`_ and there is also a
`Google group <http://groups.google.com/group/galerts>`_ if you have any
questions or would like to collaborate.

-----
Usage
-----

First create an alerts manager for a given account::

    >>> import galerts
    >>> gam = galerts.GAlertsManager('cornelius@gmail.com', 'p4ssw0rd')

(Note: The plaintext password is used only to get a session cookie, i.e. it's
sent over a secure connection and then discarded.)

Now you can access the existing alerts for that account via the ``alerts``
property, which provides a generator you can use to iterate over corresponding
``Alert`` objects::

    >>> list(gam.alerts)
    [<Alert for "Corner Confectionary" at ...>]

Looks like we have one existing alert, but it has a typo. Let's fix it::

    >>> alert = next(gam.alerts)
    >>> alert.query
    u'Corner Confectionary'
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

You may have noticed that the ``Alert.query`` property returns a ``unicode``
value. Google allows alert queries with non-ASCII characters, so we support
this via unicode. For convenience, you can set ``Alert.query`` to a ``string``
instead of a ``unicode`` as we did above and it will be transformed to a
``unicode`` automatically; just be sure that ``unicode(yourstring)`` doesn't
fail.

As we see above, every time you access ``gam.alerts``, ``GAlertsManager`` asks
Google for your alerts and creates new ``Alert`` objects with the information
Google returned. It's okay (and desirable) that we may have one object
representing an alert which we can hold onto and manipulate while the manager
continues to create new objects representing the same alert every time we
access ``gam.alerts``. The alerts returned by ``gam.alerts`` should be taken as
a snapshot of the information Google has at the time it was requested, rather
than as canonical representations of the data which are kept up-to-date.
``Alert`` objects are disposable; they're used merely to wrap some string
attributes. As such, you can pass any old ``Alert`` object to ``gam.update``
and the manager will tell Google to update its information to match the object
passed in. ``Alert.__eq__`` has been overridden so that two different
``Alert`` objects with the same attribute values compare equal.

Keeping this in mind, let's return to our old ``Alert`` object. Let's say we'd
like to change some other attributes::

    >>> alert.type
    'Blogs'
    >>> alert.deliver
    'Email'
    >>> alert.feedurl # we expect this to be None since it's an email alert
    None
    >>> alert.freq
    'once a week'
    >>> alert.type = galerts.TYPE_COMPREHENSIVE
    >>> alert.deliver = galerts.DELIVER_FEED

We've just changed the type of results the alert delivers from only blog
updates to a comprehensive mix, and we changed the delivery method so that
results will now be delivered via feed rather than via email.

After we pass this ``Alert`` object to ``gam.update``, our changes should stick,
but we'll have to grab a fresh ``Alert`` object if we want to know the url
of the alert's feed::

    >>> gam.update(alert)
    >>> alert.feedurl # this is now stale
    None
    >>> oldalert = alert # so get a fresh one
    >>> alert = next(gam.alerts)
    >>> alert.feedurl # and now it's up-to-date:
    'http://www.google.com/alerts/feed/...'
    >>> alert == oldalert # feedurls don't match
    False

The other properties are as we left them::

    >>> alert.query
    u'Corner Confectionery'
    >>> alert.type
    'Comprehensive'
    >>> alert.deliver
    'feed'

Except that when we change an email alert to a feed alert, Google automatically
changes the alert frequency to "as-it-happens", since new results are added to
the feed in real time as they are found. The new alert object's ``freq``
property reflects this::

    >>> alert.freq
    'as-it-happens'
    >>> oldalert.freq # stale
    'once a week'

Let's say we no longer want this alert. To delete it, do::

    >>> gam.delete(alert)
    >>> list(gam.alerts)
    []

And to create a new alert::

    >>> query = 'Cake Man Cornelius'
    >>> type = galerts.TYPE_COMPREHENSIVE
    >>> gam.create(query, type)
    >>> list(gam.alerts)
    [<Alert for "Cake Man Cornelius" at ...>]

Notice that we didn't specify whether we wanted an email alert or a feed alert.
In this case, ``GAlertsManager`` defaults to creating a feed alert. If we had
wanted to create an email alert, we could have passed the additional keyword
argument *feed=False* and an optional delivery frequency *freq* if we wanted
something other than the default "as-it-happens".

Let's demonstrate changing the feed alert we created to an email alert::

    >>> alert = next(gam.alerts)
    >>> str(alert)
    '<Alert query="Cake Man Cornelius" type="Comprehensive" freq="as-it-happens" deliver="feed">'
    >>> alert.feedurl
    'http://www.google.com/alerts/feed/...'
    >>> alert.deliver = galerts.DELIVER_EMAIL
    >>> alert.freq = galerts.FREQ_ONCE_A_DAY
    >>> gam.update(alert)

And now::

    >>> alert = next(gam.alerts)
    >>> str(alert)
    '<Alert query="Cake Man Cornelius" type="Comprehensive" freq="once a day" deliver="Email">'
    >>> alert.feedurl
    None

------------------------
Multiple Email Addresses
------------------------

Google Alerts allows you to create a different set of alerts for each email
address associated with a Google account, but galerts currently only supports
the account's primary email address.

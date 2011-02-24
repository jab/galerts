from setuptools import setup, find_packages

version = '0.2.2dev'
try:
    import os
    doc_dir = os.path.join(os.path.dirname(__file__), 'docs')
    readme = open(os.path.join(doc_dir, 'README.rst'))
    long_description = readme.read()
except IOError:
    long_description = """\
galerts
=======

galerts is a Python client for managing `Google Alerts
<http://www.google.com/alerts>`_. Currently it resorts to scraping html from
Google's web interface since there is as of yet no public API. If they ever
decide to publish one, galerts will switch to using it.

Using galerts should be pretty straightforward. Check out the README and the
module itself for documentation.

Please find `galerts on github <http://github.com/jab/galerts>`_ if you would
like to collaborate.
"""

setup(
    name='galerts',
    version=version,
    author='Josh Bronson',
    author_email='jabronson@gmail.com',
    maintainer='Peter Sanchez',
    maintainer_email='patersanchez@gmail.com',
    description="Python libary for managing Google Alerts",
    long_description=long_description,
    keywords='google, alerts, google alerts, news',
    url='http://packages.python.org/galerts',
    license='MIT',
    py_modules=['galerts'],
    zip_safe=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        ],
    install_requires=[
        "BeautifulSoup",
        ],
    )

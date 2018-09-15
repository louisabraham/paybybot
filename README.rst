paybybot
========

Simple bot that sends you an email when you didn’t pay your parking on
https://www.paybyphone.fr/

Installation on a Raspberry PI (about 30 minutes)
-------------------------------------------------

Install Chromium
~~~~~~~~~~~~~~~~

Firefox doesn’t support headless mode on Debian yet.

::

   sudo apt-get install chromium-browser

Install Chromedriver
~~~~~~~~~~~~~~~~~~~~

1. Go to the page of the latest **armhf** build on
   https://launchpad.net/ubuntu/trusty/+package/chromium-chromedriver

2. Use this link in

   ::

      wget http://launchpadlibrarian.net/361669488/chromium-chromedriver_65.0.3325.181-0ubuntu0.14.04.1_armhf.deb

3. Install gdebi

   ::

      sudo apt-get install gdebi

4. Install chromedriver

   ::

      sudo gdebi chromium-chromedriver*.deb

5. Put chromedriver in your path

   ::

      sudo mv /usr/lib/chromium-browser/chromedriver /usr/bin/chromedriver

Sources:

-  https://www.reddit.com/r/selenium/comments/7341wt/success_how_to_run_selenium_chrome_webdriver_on/
-  https://superuser.com/a/196867/541587

Install pip
~~~~~~~~~~~

::

   sudo apt-get install python3-pip

Install paybybot
~~~~~~~~~~~~~~~~

::

   pip3 install paybybot
   # next line is there to find the paybybot command
   echo 'export PATH=~/.local/bin:$PATH' >> .bashrc

Configure your credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~

In ~/.paybybot:

::

   {Your phone number}:{PayByPhone password}

In ~/.email-creds:

::

   {Your email address}:{Email password}

For your email account, I advise you to use an app password. See
`here <https://support.google.com/accounts/answer/185833?hl=en>`__ to
configure one in Gmail.

Add a cron task
~~~~~~~~~~~~~~~

::

   crontab -e

and write

::

   50 8 * * * ~/.local/bin/paybybot

to run paybybot everyday at 8:50

Configure your timezone correctly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For both ``crontab`` and the logs.

::

   sudo raspi-config

then *Localisation Options > Change Timezone*

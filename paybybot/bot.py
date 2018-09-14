from pathlib import Path
from time import sleep
from collections import namedtuple
import sys

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, WebDriverException

from dateparser import parse as parse_date


LOGIN_URL = 'https://m2.paybyphone.fr/login'
PARKING_URL = 'https://m2.paybyphone.fr/parking'
GDPR_BUTTON_XPATH = '/html/body/div[3]/md-dialog/section/footer/button'
PARKING_SESSIONS_XPATH = '/html/body/div/section/md-content/div[4]'

try:
    with Path('~/.paybybot').expanduser().open() as f:
        login, pwd = f.readline().split(':', 1)
except FileNotFoundError:
    print('Error: ~/.paybybot is not there', file=sys.stderr)

ParkingSession = namedtuple('ParkingSession',
                            'LicensePlate LocationNumber ExpiryDate RateOption')


class Bot():

    def __init__(self, driver):

        driver = driver.casefold()

        if driver == 'phantomjs':
            # --disk-cache=true allows to keep a cache
            self.driver = webdriver.PhantomJS(
                service_args=['--disk-cache=true'])

        elif driver in ['chrome', 'chrome-headless', 'chromium', 'chromium-headless']:
            # TODO: find option to use custom profile with cache
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--disable-gpu")  # most important line
            chrome_options.add_argument("--disable-extensions")
            if len(driver.split('-')) == 2:
                chrome_options.add_argument("--headless")
            self.driver = webdriver.Chrome(chrome_options=chrome_options)

        elif driver in ['firefox', 'firefox-headless']:
            # not working, disable gpu?
            options = FirefoxOptions()
            if len(driver.split('-')) == 2:
                options.add_argument('-headless')
            self.driver = webdriver.Firefox(firefox_options=options)

    def send_keys(self, *args):
        self.driver.switch_to_active_element().send_keys(*args)

    def get_el(self, xpath, sleepTime=1, attempts=10):
        for _ in range(attempts):
            try:
                el = self.driver.find_element_by_xpath(xpath)
            except NoSuchElementException:
                sleep(sleepTime)
            else:
                return el
        raise TimeoutError

    def connect(self):
        self.driver.get(LOGIN_URL)

        self.send_keys(Keys.TAB)
        self.send_keys(Keys.TAB)
        self.send_keys(login)
        self.send_keys(Keys.TAB)
        self.send_keys(pwd)
        self.send_keys(Keys.ENTER)

        gdpr = self.get_el(GDPR_BUTTON_XPATH)
        while True:
            try:
                gdpr.click()
            except (ElementClickInterceptedException, WebDriverException):
                sleep(1)
            else:
                break

    def get_parking_sessions(self):
        self.driver.get(PARKING_URL)
        parking_sessions = self.get_el(PARKING_SESSIONS_XPATH)
        sessions = parking_sessions\
            .find_elements_by_class_name('pbp-parking-session')
        return list(map(self.parse_parking_session, sessions))

    def quit(self):
        self.driver.quit()

    @staticmethod
    def parse_parking_session(el):
        return ParkingSession(
            LicensePlate=el.find_element_by_class_name('license-plate').text,
            LocationNumber=el.find_element_by_class_name(
                'location-number').text,
            ExpiryDate=parse_date(el.find_element_by_class_name("expiry-date")
                                  .find_element_by_tag_name("strong").text),
            RateOption=el.find_element_by_class_name(
                'rate-option-details').text
        )

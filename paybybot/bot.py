from pathlib import Path
from time import sleep
from collections import namedtuple
import sys

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

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

    def __init__(self, headless=False):
        options = Options()
        if headless:
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
            except ElementClickInterceptedException:
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

import logging

from time import sleep
from collections import namedtuple

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException,
)

from dateparser import parse as parse_date


ParkingSession = namedtuple(
    "ParkingSession", "LicensePlate LocationNumber ExpiryDate RateOption"
)


class Bot:
    """
    Manages a WebDriver to perform various actions
    """

    LOGIN_URL = "https://m2.paybyphone.fr/login"
    PARKING_URL = "https://m2.paybyphone.fr/parking"
    PARK_URL = "https://m2.paybyphone.fr/parking/start/location"
    DURATION_URL = "https://m2.paybyphone.fr/parking/start/duration"
    CONFIRM_URL = "https://m2.paybyphone.fr/parking/start/confirm"
    GDPR_BUTTON_XPATH = "/html/body/div[3]/md-dialog/section/footer/button"
    PARKING_SESSIONS_XPATH = "/html/body/div/section/md-content/div[4]"
    CONFIRM_BUTTON_XPATH = (
        "/html/body/div/section/pbp-parking-confirm/md-content/button"
    )

    def __init__(self, driver_name: str):

        driver_name = driver_name.casefold()

        if driver_name == "phantomjs":
            # --disk-cache=true allows to keep a cache
            self.driver = webdriver.PhantomJS(service_args=["--disk-cache=true"])
        elif driver_name in [
            "chrome",
            "chrome-headless",
            "chromium",
            "chromium-headless",
        ]:
            # TODO: find option to use custom profile with cache
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--disable-gpu")  # most important line
            chrome_options.add_argument("--disable-extensions")
            if driver_name.endswith("-headless"):
                chrome_options.add_argument("--headless")
            self.driver = webdriver.Chrome(chrome_options=chrome_options)
        elif driver_name in ["firefox", "firefox-headless"]:
            # not working, disable gpu?
            options = FirefoxOptions()
            if driver_name.endswith("-headless"):
                options.add_argument("-headless")
            self.driver = webdriver.Firefox(firefox_options=options)
        else:
            raise Exception("Driver unknown")

    def send_keys(self, *args):
        """
        Wrapper to send keys to the active element
        """
        self.driver.switch_to_active_element().send_keys(*args)

    def get_el(self, xpath, sleepTime=1, attempts=10):
        """
        
        """
        for _ in range(attempts):
            try:
                el = self.driver.find_element_by_xpath(xpath)
            except NoSuchElementException:
                sleep(sleepTime)
            else:
                return el
        raise TimeoutError

    def connect(self, login, pwd):
        """
        Parameters
        ----
        login : str
        pwd : str

        Returns
        -------
        success : bool
        """
        # TODO: handle wrong password
        self.driver.get(self.LOGIN_URL)

        self.send_keys(Keys.TAB)
        self.send_keys(Keys.TAB)
        self.send_keys(login)
        self.send_keys(Keys.TAB)
        self.send_keys(pwd)
        self.send_keys(Keys.ENTER)

        gdpr = self.get_el(self.GDPR_BUTTON_XPATH)
        while True:
            try:
                gdpr.click()
            except (ElementClickInterceptedException, WebDriverException):
                # ElementClickInterceptedException for Firefox
                # WebDriverException for Chromium
                sleep(1)
            else:
                break

        # dimiss cookies banner that causes problems
        # for payment

        button = next(
            b
            for b in self.driver.find_elements_by_tag_name("button")
            if b.text == "DISMISS"
        )
        button.click()

        return True

    def get_parking_sessions(self):
        """
        List of current parking sessions
        """
        self.driver.get(self.PARKING_URL)
        parking_sessions = self.get_el(self.PARKING_SESSIONS_XPATH)
        sessions = parking_sessions.find_elements_by_class_name("pbp-parking-session")
        return list(map(self.parse_parking_session, sessions))

    def pay(
        self,
        plate: str,
        location: str,
        rate: str,
        duration: int,
        check_cost: str or None = None,
    ):
        """
        Parameters
        ----------
        plate : str
        location : str
        rate : str
            "RES", "VIS", "PRO-SAD" or other
        duration : int or str
            minutes if VIS, else days
        check_cost : None or str
            if string, will check that the cost is correct
        
        Returns
        -------
        success : bool
        """

        self.driver.get(self.PARK_URL)

        # There are two kinds of menus
        # TODO: factor code
        if self.driver.find_elements_by_class_name("option-label"):
            selected, *choices = [
                e.get_attribute("innerHTML")
                for e in self.driver.find_elements_by_class_name("option-label")
            ]

            idx_selected = choices.index(selected)
            try:
                idx_target = choices.index(plate)
            except ValueError:
                logging.error("plate not found")
                return False
            delta = idx_target - idx_selected

            self.send_keys(Keys.TAB)
            self.send_keys(Keys.TAB)

            if delta:
                self.send_keys(Keys.SPACE)
                sleep(0.5)
                for i in range(-delta):
                    self.send_keys(Keys.UP)
                for i in range(delta):
                    self.send_keys(Keys.DOWN)
                sleep(0.5)
                self.send_keys(Keys.SPACE)
            sleep(0.5)
            self.send_keys(Keys.TAB)
            sleep(0.5)

            self.send_keys(location)

            self.send_keys(Keys.ENTER)

        else:
            self.send_keys(Keys.TAB)
            self.send_keys(location)
            self.send_keys(Keys.ENTER)
            while not self.driver.find_elements_by_class_name("option-label"):
                sleep(1)

            selected, *choices = [
                e.get_attribute("innerHTML")
                for e in self.driver.find_elements_by_class_name("option-label")
            ]

            idx_selected = choices.index(selected)
            try:
                idx_target = choices.index(plate)
            except ValueError:
                logging.error("plate not found")
                return False
            delta = idx_target - idx_selected

            self.send_keys(Keys.SHIFT + Keys.TAB)
            sleep(0.5)
            if delta:
                self.send_keys(Keys.SPACE)
                sleep(0.5)
                for i in range(-delta):
                    self.send_keys(Keys.UP)
                for i in range(delta):
                    self.send_keys(Keys.DOWN)
                sleep(0.5)
                self.send_keys(Keys.SPACE)

            self.driver.find_element_by_xpath(
                "/html/body/div/section/md-content/form/button"
            ).click()

        while not self.driver.current_url == self.DURATION_URL:
            sleep(1)
        for _ in range(10):
            try:
                menu = self.driver.find_element_by_tag_name("md-select")
                menu.click()
            except Exception:
                sleep(1)
            else:
                break

        choices = [
            e.get_attribute("innerText")
            for e in self.driver.find_elements_by_class_name("option-label")
        ]
        assert len(choices) == len(set(choices)), "A zone is probably already selected"

        choices = [choice.split("(")[1][:-1] for choice in choices]
        try:
            idx_target = choices.index(rate)
        except ValueError:
            logging.error("rate not found")
            return False

        sleep(0.5)
        for _ in range(idx_target):
            self.send_keys(Keys.DOWN)
            sleep(0.5)
        sleep(0.5)
        self.send_keys(Keys.SPACE)
        sleep(0.5)
        self.send_keys(Keys.TAB)
        self.send_keys(str(duration))
        self.send_keys(Keys.ENTER)
        sleep(1)
        while not self.driver.current_url == self.CONFIRM_URL:
            sleep(1)

        cost = self.driver.find_element_by_class_name("total-cost").text
        if check_cost is not None and cost != check_cost:
            logging.warning(
                "cost %s didn't match forecasted cost %s, transaction aborted",
                cost,
                check_cost,
            )
        logging.info("confimed purchase for %s", cost)
        button = self.driver.find_element_by_xpath(self.CONFIRM_BUTTON_XPATH)
        button.click()

        while (
            not self.driver.find_element_by_class_name("content-title").text
            == "You've paid!"
        ):
            sleep(0.5)

        return cost

    def quit(self):
        self.driver.quit()

    @staticmethod
    def parse_parking_session(el):
        try:
            rate = el.find_element_by_class_name("rate-option-details").text
        except NoSuchElementException:
            rate = "none"

        return ParkingSession(
            LicensePlate=el.find_element_by_class_name("license-plate").text,
            LocationNumber=el.find_element_by_class_name("location-number").text,
            ExpiryDate=parse_date(
                el.find_element_by_class_name("expiry-date")
                .find_element_by_tag_name("strong")
                .text
            ),
            RateOption=rate,
        )

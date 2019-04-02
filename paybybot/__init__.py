import logging
from datetime import datetime, timedelta
from os.path import expanduser
from pathlib import Path
import sys
import time
import traceback

import schedule

from .bot import Bot
from .notifs import notify
from . import config

logging.basicConfig(
    format="%(asctime)s %(message)s",
    filename=expanduser("~/paybybot.log"),
    level=logging.INFO,
)


REMINDER_TEMPLATE = (
    "Le stationnement du véhicule immatriculé "
    "{LicensePlate} garé à {LocationNumber} se "
    "termine à {time}, soit dans "
    "{hours} heures et {minutes} minutes."
)


def connect(task):
    pbp_login = task["paybyphone"]["login"]
    pbp_pwd = task["paybyphone"]["password"]
    for i in range(10):
        try:
            bot = Bot("chromium-headless")
            connected = bot.connect(pbp_login, pbp_pwd)
        except TimeoutError:
            logging.exception("Connection failed %i times" % (i + 1))
            if i == 9:
                raise
        else:
            break
    if not connected:
        logging.error("Authentification with login '%s' failed", pbp_login)
        assert False
    return bot


def pay(task, bot=None):
    logging.info("launched pay for plate %s", task["plate"])
    try:
        plate = task["plate"]
        location = task["pay"]["location"]
        rate = task["pay"]["rate"]
        duration = task["pay"]["duration"]
        check_cost = task["pay"].get("check-cost")
        do_notify = task["pay"].get("notify", False)
        if bot is None:
            try:
                bot = connect(task)
                sessions = bot.get_parking_sessions()

                pay_now = True
                for session in sessions:
                    if session.LocationNumber == location:
                        pay_now = False

                if pay_now:
                    cost = bot.pay(
                        plate=plate,
                        location=location,
                        rate=rate,
                        duration=duration,
                        check_cost=check_cost,
                    )
            finally:
                bot.quit()
        else:
            cost = bot.pay(
                plate=plate,
                location=location,
                rate=rate,
                duration=duration,
                check_cost=check_cost,
            )

        if do_notify:
            if cost:
                notify(
                    email=task["email"]["login"],
                    pwd=task["email"]["password"],
                    subject="Payement effectué !",
                    message="pour la somme de %s" % cost,
                )
            else:
                notify(
                    email=task["email"]["login"],
                    pwd=task["email"]["password"],
                    subject="Echec payement !",
                    message="",
                )
    except:
        logging.exception("Exception in pay")
    finally:
        return schedule.CancelJob


def check(task):
    """
    Check the current parking sessions and send notifications

    If "pay" is configured, schedules the next payment
    """
    logging.info("launched check for plate %s", task["plate"])

    try:
        bot = connect(task)
        sessions = bot.get_parking_sessions()
        logging.info("retrieved sessions: %s", sessions)

        if "pay" in task:
            pay_now = True
            for session in sessions:
                if (
                    session.LicensePlate == task["plate"]
                    and session.LocationNumber == task["pay"]["location"]
                ):
                    pay_now = False
                    delta = session.ExpiryDate - datetime.now()
                    if delta.days < 1:
                        payment_time = session.ExpiryDate + timedelta(seconds=60)
                        logging.info("scheduling payment at time %s", payment_time)
                        schedule.every().day.at(payment_time.strftime("%H:%M")).do(
                            pay, task
                        )

            if pay_now:
                logging.info("launching payment now")
                pay(task, bot=bot)

        sessions = bot.get_parking_sessions()

        if not sessions:
            notify(
                email=task["email"]["login"],
                pwd=task["email"]["password"],
                subject="ALERTE STATIONNEMENT",
                message=(
                    "Aucun stationnement en cours !!!\n"
                    "Pour le renouveller : https://m2.paybyphone.fr/parking"
                ),
            )
        else:
            message = []
            for session in sessions:
                delta = session.ExpiryDate - datetime.now()
                if delta.days < 1:
                    hours, minutes = divmod(int(delta.total_seconds()) // 60, 60)
                    message.append(
                        REMINDER_TEMPLATE.format(
                            LicensePlate=session.LicensePlate,
                            LocationNumber=session.LocationNumber,
                            time=session.ExpiryDate.strftime("%X"),
                            hours=hours,
                            minutes=minutes,
                        )
                    )
            if message:
                notify(
                    email=task["email"]["login"],
                    pwd=task["email"]["password"],
                    subject="RAPPEL STATIONNEMENT",
                    message="\n".join(message),
                )
    except:
        logging.exception("Exception in check")
        if task["notify-on-error"]:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exc_string = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )
            notify(
                email=task["email"]["login"],
                pwd=task["email"]["password"],
                subject="ERREUR STATIONNEMENT",
                message=exc_string,
            )
    finally:
        bot.quit()


def main():
    """
    Schedules the checks for the tasks in the config file.
    """
    conf = config.get_config()
    config_errors = config.validate_config(conf)
    if config_errors is not None:
        print("error in config: %s" % config_errors, file=sys.stderr)
        logging.error("error in config: %s", config_errors)
        return

    for task in conf:
        sch = getattr(schedule.every(), task["check"]["every"])
        if "at" in task["check"]:
            sch = sch.at(task["check"]["at"])
        logging.info("scheduled task for plate %s", task["plate"])
        sch.do(check, task)

    while True:
        schedule.run_pending()
        time.sleep(1)

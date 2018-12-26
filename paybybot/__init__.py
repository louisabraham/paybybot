import logging
from datetime import datetime
from os.path import expanduser
from pathlib import Path
import sys

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


def validate_config(task):
    # TODO
    raise NotImplementedError


def connect(task):
    pbp_login = task["paybyphone"]["login"]
    pbp_pwd = task["paybyphone"]["password"]

    bot = Bot("chromium-headless")
    connected = bot.connect(pbp_login, pbp_pwd)
    if not connected:
        logging.error("Authentification with login '%s' failed", pbp_login)
        assert False
    return bot


def pay(task, bot=None):
    # TODO: handle notify
    logging.info("launched pay for plate %s", task["plate"])
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
                    plate=plate, rate=rate, duration=duration, check_cost=check_cost
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
    return schedule.CancelJob


def check(task):
    logging.info("launched check for plate %s", task["plate"])

    try:
        bot = connect(task)
        sessions = bot.get_parking_sessions()
        logging.info("retrieved sessions: %s", sessions)
        if "pay" in task:
            location = task["pay"]["location"]
            rate = task["pay"]["rate"]
            duration = task["pay"]["duration"]
            check_cost = task["pay"].get("check-cost")
            notify = task["pay"].get("notify", False)

            pay_now = True
            for session in sessions:
                if session.LocationNumber == location:
                    pay_now = False
                    delta = session.ExpiryDate - datetime.now()
                    if delta.days < 1:
                        schedule.every().day.at(
                            session.ExpiryDate.strftime("%H:%M")
                        ).do(pay, task)
            if pay_now:
                pay(task, bot=bot)

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
    finally:
        bot.quit()


def main():

    for task in config.get_config():
        sch = getattr(schedule.every(), task["check"]["every"])
        if "at" in task["check"]:
            sch = sch.at(task["check"]["at"])
        sch.do(check, task)

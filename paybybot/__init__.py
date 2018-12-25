import logging
from datetime import datetime
from os.path import expanduser
from pathlib import Path
import sys

from .bot import Bot
from .notifs import notify
from .config import CONFIG

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


def main():

    try:
        pbp_login = CONFIG["paybyphone"]["login"]
        pbp_pwd = CONFIG["paybyphone"]["password"]
        email = CONFIG["email"]["login"]
        email_pwd = CONFIG["email"]["password"]
    except KeyError as e:
        logging.error("Fatal exception while reading credentials: %s", e)
        return

    try:
        bot = Bot("chromium-headless")
        connected = bot.connect(pbp_login, pbp_pwd)
        if not connected:
            logging.error("Authentification with login '%s' failed", pbp_login)
        sessions = bot.get_parking_sessions()
        logging.info("retrieved sessions: %s", sessions)
        if not sessions:
            notify(
                email=email,
                pwd=email_pwd,
                subject="ALERTE STATIONNEMENT",
                message=(
                    "Aucun stationnement en cours !!!\n"
                    "Pour le renouveller : https://m2.paybyphone.fr/parking"
                ),
            )
        else:
            session = sessions[0]
            delta = session.ExpiryDate - datetime.now()
            if delta.days < 1:
                hours, minutes = divmod(int(delta.total_seconds()) // 60, 60)
                notify(
                    email=email,
                    pwd=email_pwd,
                    subject="RAPPEL STATIONNEMENT",
                    message=REMINDER_TEMPLATE.format(
                        LicensePlate=session.LicensePlate,
                        LocationNumber=session.LocationNumber,
                        time=session.ExpiryDate.strftime("%X"),
                        hours=hours,
                        minutes=minutes,
                    ),
                )
    finally:
        bot.quit()

import logging
from datetime import datetime
from os.path import expanduser
from pathlib import Path
import sys

from .bot import Bot
from .notifs import notify

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
        with Path("~/.paybybot").expanduser().open() as f:
            pbp_login, pbp_pwd = f.readline().split(":", 1)
    except FileNotFoundError:
        logging.error("~/.paybybot is not there")
        return

    try:
        with Path("~/.email_creds").expanduser().open() as f:
            email, email_pwd = f.readline().split(":", 1)
    except FileNotFoundError:
        logging.error("Error: ~/.email_creds is not there")
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

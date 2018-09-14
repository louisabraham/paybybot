import logging
from datetime import datetime
from os.path import expanduser

from .bot import Bot
from .notifs import notify

logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=expanduser('~/paybybot.log'),
                    level=logging.INFO)


REMINDER_TEMPLATE = (
    'Le stationnement du véhicule immatriculé '
    '{LicensePlate} garé à {LocationNumber} se '
    'termine à {time}, soit dans '
    '{hours} heures et {minutes} minutes.'
)


def main():
    try:
        bot = Bot('chromium-headless')
        bot.connect()
        sessions = bot.get_parking_sessions()
        logging.info('retrieved sessions: %s' % sessions)
        if not sessions:
            notify('ALERTE STATIONNEMENT',
                   'Aucun stationnement en cours !!!')
        else:
            s = sessions[0]
            delta = s.ExpiryDate - datetime.now()
            if delta.days < 2:
                hours, minutes = divmod(int(delta.total_seconds()) // 60, 60)
                notify('RAPPEL STATIONNEMENT',
                       REMINDER_TEMPLATE.format(
                           LicensePlate=s.LicensePlate,
                           LocationNumber=s.LocationNumber,
                           time=s.ExpiryDate.strftime('%X'),
                           hours=hours,
                           minutes=minutes)
                       )
    finally:
        bot.quit()

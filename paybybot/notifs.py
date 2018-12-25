import sys
from pathlib import Path
from smtplib import SMTP_SSL
import logging


EMAIL_TEMPLATE = """\
From: {email}
To: {email}
Subject: {subject}

{message}
"""


def notify(email, pwd, subject, message):
    with SMTP_SSL("smtp.gmail.com", 465) as server:
        server.ehlo()
        server.login(email, pwd)
        email_text = EMAIL_TEMPLATE.format(**locals(), **globals()).encode("utf8")
        server.sendmail(email, [email], email_text)
        logging.info(
            "sent email to {email} with message: {message}".format(
                **locals(), **globals()
            )
        )

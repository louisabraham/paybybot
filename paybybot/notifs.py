import sys
from pathlib import Path
from smtplib import SMTP_SSL
import logging

try:
    with Path("~/.email_creds").expanduser().open() as f:
        email, pwd = f.readline().split(":", 1)
except FileNotFoundError:
    print("Error: ~/.email_creds is not there", file=sys.stderr)


EMAIL_TEMPLATE = """\
From: {email}
To: {email}
Subject: {subject}

{message}
"""


def notify(subject, message):
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

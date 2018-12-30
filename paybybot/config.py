from pathlib import Path
import logging
import yaml


def get_config():
    yml_path = Path("~/.paybybot.yml").expanduser()
    if yml_path.exists():
        with yml_path.open() as ymlfile:
            return yaml.load(ymlfile)
    else:
        logging.warning("~/.paybybot.yml doesn't exist")
        return {}


def validate_config(config):
    for task in config:
        if "at" in task["check"] and not isinstance(task["check"]["at"], str):
            return "'at' must be string"

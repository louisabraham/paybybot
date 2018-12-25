from pathlib import Path
import logging
import yaml


def get_config():
    yml_path: Path = Path("~/.paybybot.yml").expanduser()
    if yml_path.exists():
        with yml_path.open() as ymlfile:
            return yaml.load(ymlfile)
    else:
        logging.warning("~/.paybybot.yml doesn't exist")
        return {}


CONFIG = get_config()

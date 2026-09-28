import configparser


def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config


config = load_config()

SHOW_EXTRA = config.getboolean(
    "dialog",
    "show_extra",
    fallback=False,
)

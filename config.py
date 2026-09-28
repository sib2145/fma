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

DIALOGS_PER_PAGE = config.getint(
    "dialog",
    "dialogs_per_page",
    fallback=10,
)
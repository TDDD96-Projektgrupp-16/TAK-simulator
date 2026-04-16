import logging.config
import logging


def logging_setup(level):
    _LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "default": {
                "level": level,
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Default is stderr
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["default"],
                "level": level,
                "propagate": False,
            }
        },
    }

    logging.config.dictConfig(_LOGGING_CONFIG)

    logger = logging.getLogger(__name__)
    logger.info(f"Set up logger({level})")

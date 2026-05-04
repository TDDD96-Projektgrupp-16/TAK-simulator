import logging
import logging.config


def logging_setup(level, is_tui=False):
    handler_name = "file" if is_tui else "default"

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
                "stream": "ext://sys.stdout",  
            },
            "file": {
                "level": level,
                "formatter": "standard",
                "class": "logging.FileHandler",
                "filename": "simulator.log",  # Background log file
                "mode": "w",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": [handler_name],
                "level": level,
                "propagate": False,
            }
        },
    }

    logging.config.dictConfig(_LOGGING_CONFIG)

    logger = logging.getLogger(__name__)
    logger.info(f"Set up logger({level})")

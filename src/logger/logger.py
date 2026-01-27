import logging
import logging.config
import json
import os


class Logger:
    _initialized = False

    @staticmethod
    def initialize():
        if not Logger._initialized:
            default_path = os.path.join(os.path.dirname(__file__), 'logging_config.json')
            default_level = logging.INFO
            try:
                with open(default_path, 'rt') as f:
                    config = json.load(f)
                    if os.getenv("ON_AZURE", "false").lower() == "true":
                        # Do not write the logs to a file when running on Azure
                        del config["handlers"]["file"]
                        config["loggers"][""]["handlers"].remove("file")
                logging.config.dictConfig(config)
            except FileNotFoundError:
                print("Warning: logging configuration file is not found in", default_path)
                logging.basicConfig(level=default_level)
            Logger._initialized = True

    @staticmethod
    def get_logger(name):
        if not Logger._initialized:
            Logger.initialize()
        return logging.getLogger(name)

# Initialize logger at the module level
Logger.initialize()
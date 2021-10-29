#!/usr/bin/env python3

"""Nice logging, with colors on Linux."""

import logging
from sys import platform

class ColoredFormatter(logging.Formatter):
    """Logging Formatter to add colors"""

    fg_brightBlue    = "\x1b[94m"
    fg_yellow        = "\x1b[33m"
    fg_red           = "\x1b[31m"
    fg_brightRedBold = "\x1b[91;1m"
    reset            = "\x1b[0m"

    def __init__(self, messagefmt, datefmt):
        super().__init__()
        self.messagefmt = messagefmt
        self.datefmt = datefmt

        self.formats = {
            logging.DEBUG:    "{}{}{}".format(self.fg_brightBlue, self.messagefmt, self.reset),
            logging.INFO:       "{}".format(self.messagefmt),
            logging.WARNING:  "{}{}{}".format(self.fg_yellow, self.messagefmt, self.reset),
            logging.ERROR:    "{}{}{}".format(self.fg_red, self.messagefmt, self.reset),
            logging.CRITICAL: "{}{}{}".format(self.fg_brightRedBold, self.messagefmt, self.reset)
        }

        self.formatters = {
            logging.DEBUG:    logging.Formatter(self.formats[logging.DEBUG],    datefmt = self.datefmt),
            logging.INFO:     logging.Formatter(self.formats[logging.INFO],     datefmt = self.datefmt),
            logging.WARNING:  logging.Formatter(self.formats[logging.WARNING],  datefmt = self.datefmt),
            logging.ERROR:    logging.Formatter(self.formats[logging.ERROR],    datefmt = self.datefmt),
            logging.CRITICAL: logging.Formatter(self.formats[logging.CRITICAL], datefmt = self.datefmt)
        }

    def format(self, record):
        formatter = self.formatters[record.levelno]
        return formatter.format(record)

def setupRootLogger(
        noColor: bool = False,
        verbosityLevel: int = 0,
        quietnessLevel: int = 0,
        messagefmt: str = "[%(asctime)s][%(levelname)s] %(message)s (%(filename)s:%(lineno)d)",
        datefmt: str = "%Y-%m-%d %H:%M:%S"
    ):
    loggingLevel = 10 * (2 + quietnessLevel - verbosityLevel)
    rootLogger = logging.getLogger()
    rootLogger.setLevel(loggingLevel)

    consoleHandler = logging.StreamHandler()
    if not noColor and platform == "linux":
        consoleHandler.setFormatter(ColoredFormatter(messagefmt = messagefmt, datefmt = datefmt))
    else:
        consoleHandler.setFormatter(logging.Formatter(fmt = messagefmt, datefmt = datefmt))
    rootLogger.addHandler(consoleHandler)

def criticalLogExit(message):
    logging.critical(message)
    logging.critical("Exiting")
    raise SystemExit

def logTree(title, tree, finals = None, logLeavesTypes = True, loggingLevel = logging.INFO):
    """Log tree nicely if it is a dictionary.
    logLeavesTypes can be False to log no leaves, True to log all leaves, or a tuple of types for which to log."""
    if finals is None:
        finals = []
    if not isinstance(tree, dict):
        logging.log(msg = "{}{}{}".format(
            "".join([" " if final else "│" for final in finals[:-1]] + ["└" if final else "├" for final in finals[-1:]]),
            title,
            ": {}".format(tree) if logLeavesTypes is not False and (logLeavesTypes is True or isinstance(tree, logLeavesTypes)) else ""
        ), level = loggingLevel)
    else:
        logging.log(msg = "{}{}".format(
            "".join([" " if final else "│" for final in finals[:-1]] + ["└" if final else "├" for final in finals[-1:]]),
            title
        ), level = loggingLevel)
        tree_items = list(tree.items())
        for key, value in tree_items[:-1]:
            logTree(key, value, finals = finals + [False], logLeavesTypes = logLeavesTypes, loggingLevel = loggingLevel)
        for key, value in tree_items[-1:]:
            logTree(key, value, finals = finals + [True], logLeavesTypes = logLeavesTypes, loggingLevel = loggingLevel)

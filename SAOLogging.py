#!/usr/bin/env python3

"""Nice logging, with colours on Linux. 'setupRootLogger' makes argparse integration trivial."""

__version__ = "1.0.3"

import argparse
import logging
from sys import platform

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    fg_brightBlue =    "\x1b[94m"
    fg_yellow =        "\x1b[33m"
    fg_red =           "\x1b[31m"
    fg_brightRedBold = "\x1b[91;1m"
    reset =            "\x1b[0m"

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

        self.formaters = {
            logging.DEBUG:    logging.Formatter(self.formats[logging.DEBUG], datefmt = self.datefmt),
            logging.INFO:     logging.Formatter(self.formats[logging.INFO], datefmt = self.datefmt),
            logging.WARNING:  logging.Formatter(self.formats[logging.WARNING], datefmt = self.datefmt),
            logging.ERROR:    logging.Formatter(self.formats[logging.ERROR], datefmt = self.datefmt),
            logging.CRITICAL: logging.Formatter(self.formats[logging.CRITICAL], datefmt = self.datefmt)
        }

    def format(self, record):
        formatter = self.formaters[record.levelno]
        return formatter.format(record)

def setupRootLogger(verbosityLevel,
        quietnessLevel,
        messagefmt = "[%(asctime)s][%(levelname)s] %(message)s (%(filename)s:%(lineno)d)",
        datefmt = "%Y-%m-%d %H:%M:%S",
        enableColour = True
    ):
    loggingLevel = 10 * (2 + quietnessLevel - verbosityLevel)
    rootLogger = logging.getLogger()
    rootLogger.setLevel(loggingLevel)

    consoleHandler = logging.StreamHandler()
    if enableColour and platform == "linux":
        consoleHandler.setFormatter(CustomFormatter(messagefmt = messagefmt, datefmt = datefmt))
    else:
        consoleHandler.setFormatter(logging.Formatter(fmt = messagefmt, datefmt = datefmt))
    rootLogger.addHandler(consoleHandler)

def criticalLogExit(message):
    logging.critical(message)
    logging.critical("Exiting")
    raise SystemExit

def logTree(title, tree, finals = None, logLeavesTypes = True, loggingLevel = logging.INFO):
    """Log a dictionary as a tree.
    logLeavesTypes can be False to log no leaves, True to log all leaves, or a tuple of types for which to log."""
    if finals is None:
        finals = []
    if not isinstance(tree, dict):
        logging.log(msg = "{}{}{}".format(
            "".join([" " if final else "│" for final in finals[:-1]] +
            ["└" if final else "├" for final in finals[-1:]]),
            title, ": {}".format(tree) if logLeavesTypes is not False and (logLeavesTypes is True or isinstance(tree, logLeavesTypes)) else ""),
            level = loggingLevel)
    else:
        logging.log(msg = "{}{}".format(
            "".join([" " if final else "│" for final in finals[:-1]] +
            ["└" if final else "├" for final in finals[-1:]]),
            title), level = loggingLevel)
        tree_items = list(tree.items())
        for key, value in tree_items[:-1]:
            logTree(key, value, finals = finals + [False], logLeavesTypes = logLeavesTypes, loggingLevel = loggingLevel)
        for key, value in tree_items[-1:]:
            logTree(key, value, finals = finals + [True], logLeavesTypes = logLeavesTypes, loggingLevel = loggingLevel)

def getParser(docstring, *args, version = None, **kwargs):
    """Basic argument parser with verbosity arguments already added. Supply __doc__ as docstring for the description argument of the parser."""
    # we use this function instead of inheriting ArgumentParser lest subparsers also have verbosity options...
    parser = argparse.ArgumentParser(description = docstring, *args, **kwargs)
    if version is not None:
        parser.add_argument("--version",
            action = "version",
            version = version)
    parser_group_verbosity = parser.add_argument_group("logging").add_mutually_exclusive_group(required = False)
    parser_group_verbosity.add_argument("-v", "--verbose",
        help = "Increase logging verbosity: -v for debug",
        action = "count",
        default = 0)
    parser_group_verbosity.add_argument("-q", "--quiet",
        help = "Decrease logging verbosity: -q for warning, -qq for error, -qqq for critical, -qqqq for no logging messages",
        action = "count",
        default = 0)

    return parser

if __name__ == "__main__":
    parser = getParser(__doc__, version = __version__)

    args = parser.parse_args()

    setupRootLogger(args.verbose, args.quiet)

    logging.debug("Debug message")
    logging.info("Info message")
    logging.warning("Warning message")
    logging.error("Error message")
    logging.critical("Critical message")

#!/usr/bin/env python3

"""Methods with error handling for file operations"""

from typing import Union

from .SAOLogging import criticalLogExit

def tryLoading(filename: str,
    mode: str = "r",
    raise_FileNotFound:  bool = False,
    raise_IsADirectory:  bool = False,
    raise_NotADirectory: bool = False,
    raise_Permission:    bool = False
) -> Union[str, bytes]:
    """Try to load a file.
    Will criticalLogExit if expected errors are encountered, or will (re)raise if corresponding optional arguments are supplied."""
    try:
        with open(filename, mode) as f:
            return f.read()
    except FileNotFoundError:
        if raise_FileNotFound:
            raise
        else:
            criticalLogExit("File {} not found".format(filename))
    except IsADirectoryError:
        if raise_IsADirectory:
            raise
        else:
            criticalLogExit("{} is a directory".format(filename))
    except NotADirectoryError:
        if raise_NotADirectory:
            raise
        else:
            criticalLogExit("Not a directory error for {}".format(filename))
    except PermissionError:
        if raise_Permission:
            raise
        else:
            criticalLogExit("Permission error opening {}".format(filename))

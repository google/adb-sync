#!/usr/bin/env python3

from typing import Iterable, Tuple
import os
import re
import stat
import datetime
import subprocess

from ..SAOLogging import criticalLogExit

from .Base import FileSystem

class AndroidFileSystem(FileSystem):
    RE_TESTCONNECTION_NO_DEVICE = re.compile("^adb\\: no devices/emulators found$")
    RE_TESTCONNECTION_DAEMON_NOT_RUNNING = re.compile("^\\* daemon not running; starting now at tcp:\\d+$")
    RE_TESTCONNECTION_DAEMON_STARTED = re.compile("^\\* daemon started successfully$")
    RE_ADB_FILE_PUSHED = re.compile("^.*: 1 file pushed, 0 skipped\\..*$")

    RE_LS_TO_STAT = re.compile(
        r"""^
        (?:
        (?P<S_IFREG> -) |
        (?P<S_IFBLK> b) |
        (?P<S_IFCHR> c) |
        (?P<S_IFDIR> d) |
        (?P<S_IFLNK> l) |
        (?P<S_IFIFO> p) |
        (?P<S_IFSOCK> s))
        [-r][-w][-xsS]
        [-r][-w][-xsS]
        [-r][-w][-xtT] # Mode string
        [ ]+
        (?:
        [0-9]+ # Number of hard links
        [ ]+
        )?
        [^ ]+ # User name/ID
        [ ]+
        [^ ]+ # Group name/ID
        [ ]+
        (?(S_IFBLK) [^ ]+[ ]+[^ ]+[ ]+) # Device numbers
        (?(S_IFCHR) [^ ]+[ ]+[^ ]+[ ]+) # Device numbers
        (?(S_IFDIR) (?P<dirsize>[0-9]+ [ ]+))? # Directory size
        (?(S_IFREG) (?P<st_size> [0-9]+) [ ]+) # Size
        (?(S_IFLNK) ([0-9]+) [ ]+) # Link length
        (?P<st_mtime>
        [0-9]{4}-[0-9]{2}-[0-9]{2} # Date
        [ ]
        [0-9]{2}:[0-9]{2}) # Time
        [ ]
        # Don't capture filename for symlinks (ambiguous).
        (?(S_IFLNK) .* | (?P<filename> .*))
        $""", re.DOTALL | re.VERBOSE)

    RE_NO_SUCH_FILE = re.compile("^.*: No such file or directory$")
    RE_LS_NOT_A_DIRECTORY = re.compile("ls: .*: Not a directory$")
    RE_TOTAL = re.compile("^total \\d+$")

    RE_REALPATH_NO_SUCH_FILE = re.compile("^realpath: .*: No such file or directory$")
    RE_REALPATH_NOT_A_DIRECTORY = re.compile("^realpath: .*: Not a directory$")

    escapePath_replacements = [
        [" ", "\\ "],
        ["'", "\\'"],
        ["(", "\\("],
        [")", "\\)"],
        ["!", "\\!"],
        ["&", "\\&"]
    ]

    def escapePath(self, path: str) -> str:
        for replacement in self.escapePath_replacements:
            path = path.replace(*replacement)
        return path

    def testConnection(self):
        for line in self.adbShell([":"]):
            if self.RE_TESTCONNECTION_DAEMON_NOT_RUNNING.fullmatch(line) or self.RE_TESTCONNECTION_DAEMON_STARTED.fullmatch(line):
                continue
            elif self.RE_TESTCONNECTION_NO_DEVICE.fullmatch(line):
                return False
        return True

    def lsToStat(self, line: str) -> Tuple[str, os.stat_result]:
        if self.RE_NO_SUCH_FILE.fullmatch(line):
            raise FileNotFoundError
        elif self.RE_LS_NOT_A_DIRECTORY.fullmatch(line):
            raise NotADirectoryError
        elif match := self.RE_LS_TO_STAT.fullmatch(line):
            match_groupdict = match.groupdict()
            st_mode = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH # 755
            if match_groupdict['S_IFREG']:
                st_mode |= stat.S_IFREG
            if match_groupdict['S_IFBLK']:
                st_mode |= stat.S_IFBLK
            if match_groupdict['S_IFCHR']:
                st_mode |= stat.S_IFCHR
            if match_groupdict['S_IFDIR']:
                st_mode |= stat.S_IFDIR
            if match_groupdict['S_IFIFO']:
                st_mode |= stat.S_IFIFO
            if match_groupdict['S_IFLNK']:
                st_mode |= stat.S_IFLNK
            if match_groupdict['S_IFSOCK']:
                st_mode |= stat.S_IFSOCK
            st_size = None if match_groupdict["st_size"] is None else int(match_groupdict["st_size"])
            st_mtime = int(datetime.datetime.strptime(match_groupdict["st_mtime"], "%Y-%m-%d %H:%M").timestamp())

            # Fill the rest with dummy values.
            st_ino = 1
            st_rdev = 0
            st_nlink = 1
            st_uid = -2  # Nobody.
            st_gid = -2  # Nobody.
            st_atime = st_ctime = st_mtime

            return match_groupdict["filename"], os.stat_result((st_mode, st_ino, st_rdev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime))
        else:
            criticalLogExit("Line not captured: '{}'".format(line))

    def unlink(self, path: str) -> None:
        for line in self.adbShell(["rm", self.escapePath(path)]):
            criticalLogExit("Line not captured: '{}'".format(line))

    def rmdir(self, path: str) -> None:
        for line in self.adbShell(["rm", "-r", self.escapePath(path)]):
            criticalLogExit("Line not captured: '{}'".format(line))

    def makedirs(self, path: str) -> None:
        for line in self.adbShell(["mkdir", "-p", self.escapePath(path)]):
            criticalLogExit("Line not captured: '{}'".format(line))

    def realPath(self, path: str) -> str:
        for line in self.adbShell(["realpath", self.escapePath(path)]):
            if self.RE_REALPATH_NO_SUCH_FILE.fullmatch(line):
                raise FileNotFoundError
            elif self.RE_REALPATH_NOT_A_DIRECTORY.fullmatch(line):
                raise NotADirectoryError
            else:
                return line
            # permission error possible?

    def lstat(self, path: str) -> os.stat_result:
        for line in self.adbShell(["ls", "-lad", self.escapePath(path)]):
            return self.lsToStat(line)[1]

    def lstat_inDir(self, path: str) -> Iterable[Tuple[str, os.stat_result]]:
        for line in self.adbShell(["ls", "-la", self.escapePath(path)]):
            if self.RE_TOTAL.fullmatch(line):
                continue
            else:
                yield self.lsToStat(line)

    def utime(self, path: str, times: Tuple[int, int]) -> None:
        atime = datetime.datetime.utcfromtimestamp(times[0]).strftime("%Y%m%d%H%M")
        mtime = datetime.datetime.utcfromtimestamp(times[1]).strftime("%Y%m%d%H%M")
        for line in self.adbShell(["touch", "-at", atime, "-mt", mtime, self.escapePath(path)]):
            criticalLogExit("Line not captured: '{}'".format(line))

    def joinPaths(self, base: str, leaf: str) -> str:
        return os.path.join(base, leaf).replace("\\", "/") # for Windows

    def normPath(self, path: str) -> str:
        return os.path.normpath(path).replace("\\", "/")

    def pushFileHere(self, source: str, destination: str) -> None:
        with subprocess.Popen(
            self.adb_arguments + ["push", source, destination],
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT
        ) as proc:
            while adbLine := proc.stdout.readline():
                adbLine = adbLine.decode().rstrip("\r\n")
                if not self.RE_ADB_FILE_PUSHED.fullmatch(adbLine):
                    criticalLogExit("Line not captured: '{}'".format(adbLine))

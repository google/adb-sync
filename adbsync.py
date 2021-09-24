#!/usr/bin/env python3

"""Simpler version of adb-sync for Python3"""

__version__ = "1.0.9"

import logging
from typing import Iterator, List, Tuple, Union, Iterable
import os
import stat
import re
import subprocess
import datetime
import fnmatch

from SAOLogging import getParser, setupRootLogger, criticalLogExit, logTree

class FileSystem():
    RE_ADB_FILE_PUSHED = re.compile("^.*: 1 file pushed, 0 skipped\\..*$")
    RE_ADB_FILE_PULLED = re.compile("^.*: 1 file pulled, 0 skipped\\..*$")

    @staticmethod
    def adbShell(commands: List[str]) -> Iterator[str]:
        with subprocess.Popen(
            ["adb", "shell"] + commands,
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT
        ) as proc:
            while adbLine := proc.stdout.readline().decode().rstrip():
                yield adbLine

    def unlink(self, path: str) -> None:
        raise NotImplementedError

    def rmdir(self, path: str) -> None:
        raise NotImplementedError

    def makedirs(self, path: str) -> None:
        raise NotImplementedError

    def lstat(self, path: str) -> os.stat_result:
        raise NotImplementedError

    def stat(self, path: str) -> os.stat_result:
        raise NotImplementedError

    def lstat_inDir(self, path: str) -> Iterable[Tuple[str, os.stat_result]]:
        raise NotImplementedError

    def utime(self, path: str, times: Tuple[int, int]) -> None:
        raise NotImplementedError

    @staticmethod
    def joinPaths(base: str, leaf: str) -> str:
        raise NotImplementedError

    @staticmethod
    def normPath(path: str) -> str:
        raise NotImplementedError

    def pushFileHere(self, source: str, destination: str) -> None:
        raise NotImplementedError

    def _getFilesTree(self, tree_root: str, tree_root_stat: os.stat_result, followLinks: bool = False):
        # the reason to have two functions instead of one purely recursive one is to use self.lstat_inDir ie ls
        # which is much faster than individually stat-ing each file. Hence we have getFilesTree's special first lstat
        if followLinks:
            raise NotImplementedError

        if stat.S_ISLNK(tree_root_stat.st_mode):
            logging.warning("Ignoring symlink encountered at '{}'".format(self.joinPaths(tree_root, tree_root)))
            return None
            # logging.error("Symlink encountered at '{}'".format(self.joinPaths(tree_root, tree_root)))
            # raise NotImplementedError
        elif stat.S_ISDIR(tree_root_stat.st_mode):
            tree = {".": (60 * (int(tree_root_stat.st_atime) // 60), 60 * (int(tree_root_stat.st_mtime) // 60))}
            for filename, statObject_child, in self.lstat_inDir(tree_root):
                if filename in [".", ".."]:
                    continue
                tree[filename] = self._getFilesTree(
                    self.joinPaths(tree_root, filename),
                    statObject_child,
                    followLinks = followLinks)
            return tree
        elif stat.S_ISREG(tree_root_stat.st_mode):
            return (60 * (int(tree_root_stat.st_atime) // 60), 60 * (int(tree_root_stat.st_mtime) // 60))
        else:
            raise NotImplementedError

    def getFilesTree(self, tree_root: str, followLinks: bool = False):
        statObject = self.lstat(tree_root)
        return self._getFilesTree(tree_root, statObject, followLinks = followLinks)

    def removeTree(self, tree_root: str, tree: Union[Tuple[int, int], dict], dry_run: bool = True) -> None:
        if isinstance(tree, tuple):
            logging.info("Removing '{}'".format(tree_root))
            if not dry_run:
                self.unlink(tree_root)
        elif isinstance(tree, dict):
            removeFolder = tree.pop(".", False)
            for key, value in tree.items():
                self.removeTree(self.normPath(self.joinPaths(tree_root, key)), value, dry_run = dry_run)
            if removeFolder:
                logging.info("Removing folder '{}'".format(tree_root))
                if not dry_run:
                    self.rmdir(tree_root)
        else:
            raise NotImplementedError

    def pushTreeHere(self,
        tree_root: str,
        tree: Union[Tuple[int, int], dict],
        destination_root: str,
        pathJoinFunction_source,
        pathNormFunction_source,
        pathJoinFunction_destination,
        pathNormFunction_destination,
        dry_run: bool = True
        ) -> None:
        if isinstance(tree, tuple):
            logging.info("Copying '{}' to '{}'".format(tree_root, destination_root))
            if not dry_run:
                self.pushFileHere(tree_root, destination_root)
                self.utime(destination_root, tree)
        elif isinstance(tree, dict):
            if tree.pop(".", False):
                logging.info("Making directory '{}'".format(destination_root))
                if not dry_run:
                    self.makedirs(destination_root)
            for key, value in tree.items():
                self.pushTreeHere(
                    pathNormFunction_source(pathJoinFunction_source(tree_root, key)),
                    value,
                    pathNormFunction_destination(pathJoinFunction_destination(destination_root, key)),
                    pathJoinFunction_source,
                    pathNormFunction_source,
                    pathJoinFunction_destination,
                    pathNormFunction_destination,
                    dry_run = dry_run
                )
        else:
            raise NotImplementedError

class LocalFileSystem(FileSystem):
    def unlink(self, path: str) -> None:
        os.unlink(path)

    def rmdir(self, path: str) -> None:
        os.rmdir(path)

    def makedirs(self, path: str) -> None:
        os.makedirs(path, exist_ok = True)

    def lstat(self, path: str) -> os.stat_result:
        return os.lstat(path)

    def stat(self, path: str) -> os.stat_result:
        return os.stat(path)

    def lstat_inDir(self, path: str) -> Iterable[Tuple[str, os.stat_result]]:
        for filename in os.listdir(path):
            yield filename, self.lstat(self.joinPaths(path, filename))

    def utime(self, path: str, times: Tuple[int, int]) -> None:
        os.utime(path, times)

    @staticmethod
    def joinPaths(base: str, leaf: str) -> str:
        return os.path.join(base, leaf)

    @staticmethod
    def normPath(path: str) -> str:
        return os.path.normpath(path)

    def pushFileHere(self, source: str, destination: str) -> None:
        with subprocess.Popen(
            ["adb", "pull", source, destination],
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT
        ) as proc:
            while adbLine := proc.stdout.readline().decode().rstrip():
                if not self.RE_ADB_FILE_PULLED.fullmatch(adbLine):
                    criticalLogExit("Line not captured: '{}'".format(adbLine))

class AndroidFileSystem(FileSystem):
    RE_TESTCONNECTION_NO_DEVICE = re.compile("^adb\\: no devices/emulators found$")
    RE_TESTCONNECTION_DAEMON_NOT_RUNNING = re.compile("^\\* daemon not running; starting now at tcp:\\d+$")
    RE_TESTCONNECTION_DAEMON_STARTED = re.compile("^\\* daemon started successfully$")

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
        (?(S_IFREG)
        (?P<st_size> [0-9]+) # Size
        [ ]+)
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

    # RE_STAT_NE = re.compile("^stat: '.*': No such file or directory$")
    RE_STAT = re.compile(
        r"""^
        (?P<st_mtime> [0-9]+)[ ]
        (?:
        (?P<S_IFREG>regular[ ]file|regular[ ]empty[ ]file) |
        (?P<S_IFDIR>directory)|
        (?P<S_IFLNK>symbolic[ ]link))
        $""", re.DOTALL | re.VERBOSE)

    escapePathReplacements = [
        [" ", "\\ "],
        ["'", "\\'"],
        ["(", "\\("],
        [")", "\\)"],
        ["!", "\\!"],
        ["&", "\\&"]
    ]

    def unlink(self, path: str) -> None:
        for line in self.adbShell(["rm", self.escapePath(path)]):
            if line:
                criticalLogExit("Line not captured: '{}'".format(line))

    def rmdir(self, path: str) -> None:
        for line in self.adbShell(["rm -r", self.escapePath(path)]):
            if line:
                criticalLogExit("Line not captured: '{}'".format(line))

    def makedirs(self, path: str) -> None:
        for line in self.adbShell(["mkdir -p", self.escapePath(path)]):
            if line:
                criticalLogExit("Line not captured: '{}'".format(line))

    def lstat(self, path: str) -> os.stat_result:
        for line in self.adbShell(["ls -lad", self.escapePath(path)]):
            return self.lsToStat(line)[1]

    def stat(self, path: str) -> os.stat_result:
        for line in self.adbShell(["ls -lad", self.escapePath(path)]):
            return self.lsToStat(line)[1]
        # for line in self.adbShell(["stat", "-c", "%Y\\ %F", self.escapePath(path)]):
        #     if self.RE_NO_SUCH_FILE.fullmatch(line):
        #         raise FileNotFoundError
        #     elif match := self.RE_STAT.fullmatch(line):
        #         return match.groupdict()
        #     else:
        #         criticalLogExit("Line not captured: '{}'".format(line))

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

    @staticmethod
    def joinPaths(base: str, leaf: str) -> str:
        return os.path.join(base, leaf).replace("\\", "/") # for Windows

    @staticmethod
    def normPath(path: str) -> str:
        return os.path.normpath(path).replace("\\", "/")

    def pushFileHere(self, source: str, destination: str) -> None:
        with subprocess.Popen(
            ["adb", "push", source, destination],
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT
        ) as proc:
            while adbLine := proc.stdout.readline().decode().rstrip():
                if not self.RE_ADB_FILE_PUSHED.fullmatch(adbLine):
                    criticalLogExit("Line not captured: '{}'".format(adbLine))

    def escapePath(self, path: str) -> str:
        for replacement in self.escapePathReplacements:
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

class FileSyncer():
    @classmethod
    def diffTrees(cls,
        source: Union[dict, Tuple[int, int], None],
        destination: Union[dict, Tuple[int, int], None],
        path_source: str,
        path_destination: str,
        destinationExcludePatterns: List[str],
        pathJoinFunction_source,
        pathJoinFunction_destination,
        folderFileOverwriteError: bool = True,
        ) -> Tuple[
            Union[dict, Tuple[int, int], None], # delete
            Union[dict, Tuple[int, int], None], # copy
            Union[dict, Tuple[int, int], None], # excluded_source
            Union[dict, Tuple[int, int], None], # unaccounted_destination
            Union[dict, Tuple[int, int], None]  # excluded_destination
        ]:

        exclude = False
        for destinationExcludePattern in destinationExcludePatterns:
            if fnmatch.fnmatch(path_destination, destinationExcludePattern):
                exclude = True
                break

        if source is None:
            if destination is None:
                delete = None
                copy = None
                excluded_source = None
                unaccounted_destination = None
                excluded_destination = None
            elif isinstance(destination, tuple):
                if exclude:
                    delete = None
                    copy = None
                    excluded_source = None
                    unaccounted_destination = None
                    excluded_destination = destination
                else:
                    delete = None
                    copy = None
                    excluded_source = None
                    unaccounted_destination = destination
                    excluded_destination = None
            elif isinstance(destination, dict):
                if exclude:
                    delete = {".": None}
                    copy = None
                    excluded_source = None
                    unaccounted_destination = {".": None}
                    excluded_destination = destination
                else:
                    delete = {".": None}
                    copy = None
                    excluded_source = None
                    unaccounted_destination = {".": destination["."]}
                    excluded_destination = {".": None}
                    destination.pop(".")
                    for key, value in destination.items():
                        delete[key], _, _, unaccounted_destination[key], excluded_destination[key] = cls.diffTrees(
                            None,
                            value,
                            pathJoinFunction_source(path_source, key),
                            pathJoinFunction_destination(path_destination, key),
                            destinationExcludePatterns,
                            pathJoinFunction_source,
                            pathJoinFunction_destination,
                            folderFileOverwriteError = folderFileOverwriteError
                        )
            else:
                raise NotImplementedError

        elif isinstance(source, tuple):
            if destination is None:
                if exclude:
                    delete = None
                    copy = None
                    excluded_source = source
                    unaccounted_destination = None
                    excluded_destination = None
                else:
                    delete = None
                    copy = source
                    excluded_source = None
                    unaccounted_destination = None
                    excluded_destination = None
            elif isinstance(destination, tuple):
                if exclude:
                    delete = None
                    copy = None
                    excluded_source = source
                    unaccounted_destination = None
                    excluded_destination = destination
                else:
                    if source[1] > destination[1]:
                        delete = destination
                        copy = source
                        excluded_source = None
                        unaccounted_destination = None
                        excluded_destination = None
                    else:
                        delete = None
                        copy = None
                        excluded_source = None
                        unaccounted_destination = None
                        excluded_destination = None
            elif isinstance(destination, dict):
                if exclude:
                    delete = {".": None}
                    copy = None
                    excluded_source = source
                    unaccounted_destination = {".": None}
                    excluded_destination = destination
                else:
                    delete = destination
                    copy = source
                    excluded_source = None
                    unaccounted_destination = {".": None}
                    excluded_destination = {".": None}
                    if folderFileOverwriteError:
                        logging.critical("Refusing to overwrite directory '{}' with file '{}'".format(path_destination, path_source))
                        criticalLogExit("Use --force if you are sure!")
                    else:
                        logging.warning("Overwriting directory '{}' with file '{}'".format(path_destination, path_source))
            else:
                raise NotImplementedError

        elif isinstance(source, dict):
            if destination is None:
                if exclude:
                    delete = None
                    copy = {".": None}
                    excluded_source = source
                    unaccounted_destination = None
                    excluded_destination = None
                else:
                    delete = None
                    copy = {".": source["."]}
                    excluded_source = {".": None}
                    unaccounted_destination = None
                    excluded_destination = None
                    source.pop(".")
                    for key, value in source.items():
                        _, copy[key], excluded_source[key], _, _ = cls.diffTrees(
                            value,
                            None,
                            pathJoinFunction_source(path_source, key),
                            pathJoinFunction_destination(path_destination, key),
                            destinationExcludePatterns,
                            pathJoinFunction_source,
                            pathJoinFunction_destination,
                            folderFileOverwriteError = folderFileOverwriteError
                        )
            elif isinstance(destination, tuple):
                if exclude:
                    delete = None
                    copy = {".": None}
                    excluded_source = source
                    unaccounted_destination = None
                    excluded_destination = destination
                else:
                    delete = destination
                    copy = {".": source["."]}
                    excluded_source = {".": None}
                    unaccounted_destination = None
                    excluded_destination = None
                    source.pop(".")
                    for key, value in source.items():
                        _, copy[key], excluded_source[key], _, _ = cls.diffTrees(
                            value,
                            None,
                            pathJoinFunction_source(path_source, key),
                            pathJoinFunction_destination(path_destination, key),
                            destinationExcludePatterns,
                            pathJoinFunction_source,
                            pathJoinFunction_destination,
                            folderFileOverwriteError = folderFileOverwriteError
                        )
                    if folderFileOverwriteError:
                        logging.critical("Refusing to overwrite file '{}' with directory '{}'".format(path_destination, path_source))
                        criticalLogExit("Use --force if you are sure!")
                    else:
                        logging.warning("Overwriting file '{}' with directory '{}'".format(path_destination, path_source))
                excluded_destination = None
            elif isinstance(destination, dict):
                if exclude:
                    delete = {".": None}
                    copy = {".": None}
                    excluded_source = source
                    unaccounted_destination = {".": None}
                    excluded_destination = destination
                else:
                    delete = {".": None}
                    copy = {".": None}
                    excluded_source = {".": None}
                    unaccounted_destination = {".": None}
                    excluded_destination = {".": None}
                    source.pop(".")
                    for key, value in source.items():
                        delete[key], copy[key], excluded_source[key], unaccounted_destination[key], excluded_destination[key] = cls.diffTrees(
                            value,
                            destination.pop(key, None),
                            pathJoinFunction_source(path_source, key),
                            pathJoinFunction_destination(path_destination, key),
                            destinationExcludePatterns,
                            pathJoinFunction_source,
                            pathJoinFunction_destination,
                            folderFileOverwriteError = folderFileOverwriteError
                        )
                    destination.pop(".")
                    for key, value in destination.items():
                        delete[key], _, _, unaccounted_destination[key], excluded_destination[key] = cls.diffTrees(
                            None,
                            value,
                            pathJoinFunction_source(path_source, key),
                            pathJoinFunction_destination(path_destination, key),
                            destinationExcludePatterns,
                            pathJoinFunction_source,
                            pathJoinFunction_destination,
                            folderFileOverwriteError = folderFileOverwriteError
                        )
            else:
                raise NotImplementedError

        else:
            raise NotImplementedError

        return delete, copy, excluded_source, unaccounted_destination, excluded_destination

    @classmethod
    def removeExludedFoldersFromUnaccountedTree(cls, unaccounted: dict, excluded: Union[dict, None]) -> dict:
        # for when we have --del but not --delete-excluded selected; we do not want to remove
        # unaccounted folders that are the parent of excluded items; we return the tree that
        # is to be merged with tree_delete for deletion
        if excluded is not None:
            unaccounted.pop(".", None)
            for unaccounted_key, unaccounted_value in unaccounted.items():
                unaccounted[unaccounted_key] = cls.removeExludedFoldersFromUnaccountedTree(
                    unaccounted_value,
                    excluded.get(unaccounted_key, None)
                )
        return unaccounted

    @classmethod
    def pruneTree(cls, tree: Union[None, bool, dict]) -> Union[None, bool, dict]:
        """Remove all Nones from a tree. May return None if tree is None however."""
        if not isinstance(tree, dict):
            return tree
        else:
            returnDict = {}
            for key, value in tree.items():
                value_pruned = cls.pruneTree(value)
                if value_pruned is not None:
                    returnDict[key] = value_pruned
            return returnDict or None

if __name__ == "__main__":
    parser = getParser(__doc__, version = __version__)

    parser.add_argument("LOCAL",
        help = "Local path",
        action = "store")
    parser.add_argument("ANDROID",
        help = "Android path",
        action = "store")
    parser.add_argument("--dry-run",
        help = "Perform a dry run; do not actually copy and delete etc",
        action = "store_true",
        default = False)
    parser.add_argument("--exclude",
        help = "fnmatch pattern to ignore relative to source (reusable)",
        action = "append",
        default = [])
    parser.add_argument("--exclude-from",
        help = "Filename of file containing fnmatch patterns to ignore relative to source (reusable)",
        action = "append",
        default = [])
    parser.add_argument("--del",
        help = "Delete files at the destination that are not in the source",
        action = "store_true",
        dest = "delete",
        default = False)
    parser.add_argument("--delete-excluded",
        help = "Delete files at the destination that are excluded",
        action = "store_true",
        default = False)
    parser.add_argument("--pull",
        help = "Pull ANDROID from Android to LOCAL on the computer instead of the default pushing from computer to Android",
        action = "store_true",
        default = False)
    parser.add_argument("--force",
        help = "Allows files to overwrite folders and folders to overwrite files. This is false by default to prevent large scale accidents",
        action = "store_true",
        default = False)

    args = parser.parse_args()

    setupRootLogger(args.verbose, args.quiet, messagefmt = "[%(levelname)s] %(message)s")

    if args.LOCAL[-1] in ["/", "\\"] or args.ANDROID[-1] in ["/", "\\"]:
        logging.warning("Trailing slashes are ignored (see README.md)")

    for exclude_from_filename in args.exclude_from:
        try:
            with open(os.path.expanduser(os.path.normpath(exclude_from_filename)), "r") as f:
                while line := f.readline():
                    if line_stripped := line.rstrip("\r\n"):
                        args.exclude.append(line_stripped)
        except (FileNotFoundError, PermissionError):
            criticalLogExit("Could not open exclude-from file '{}'".format(exclude_from_filename))

    fs_android = AndroidFileSystem()
    fs_local = LocalFileSystem()

    args.LOCAL = os.path.expanduser(args.LOCAL)
    if args.pull:
        path_source = args.ANDROID
        fs_source = fs_android
        path_destination = args.LOCAL
        fs_destination = fs_local
    else:
        path_source = args.LOCAL
        fs_source = fs_local
        path_destination = args.ANDROID
        fs_destination = fs_android

    path_source = fs_source.normPath(path_source)
    path_destination = fs_destination.normPath(path_destination)

    if not fs_android.testConnection():
        criticalLogExit("No device detected")

    try:
        filesTree_source = fs_source.getFilesTree(path_source)
    except FileNotFoundError:
        criticalLogExit("Source '{}' not found".format(path_source))
    except NotADirectoryError:
        criticalLogExit("Path '{}' contains a file as non-leaf segment; wrong path?".format(path_source))
    except PermissionError:
        criticalLogExit("Permission error stat-ing '{}'".format(path_source))

    try:
        filesTree_destination = fs_destination.getFilesTree(path_destination)
    except FileNotFoundError:
        filesTree_destination = None
    except NotADirectoryError:
        criticalLogExit("Path '{}' contains a file as non-leaf segment; would not be able to create directories".format(path_destination))
    except PermissionError:
        criticalLogExit("Permission error stat-ing '{}'".format(path_destination))

    logging.info("Source tree:")
    if filesTree_source is not None:
        logTree(path_source, filesTree_source)
    logging.info("")

    logging.info("Destination tree:")
    if filesTree_destination is not None:
        logTree(path_destination, filesTree_destination)
    logging.info("")

    if isinstance(filesTree_source, dict):
        excludePatterns = [fs_destination.normPath(
            fs_destination.joinPaths(path_destination, exclude)
        ) for exclude in args.exclude]
    else:
        excludePatterns = [fs_destination.normPath(
            path_destination + exclude
        ) for exclude in args.exclude]
    logging.debug("Exclude patterns:")
    logging.debug(excludePatterns)
    logging.debug("")

    tree_delete, tree_copy, tree_excluded_source, tree_unaccounted_destination, tree_excluded_destination = FileSyncer.diffTrees(
        filesTree_source,
        filesTree_destination,
        path_source,
        path_destination,
        excludePatterns,
        fs_source.joinPaths,
        fs_destination.joinPaths,
        folderFileOverwriteError = not args.dry_run and not args.force
    )

    tree_delete = FileSyncer.pruneTree(tree_delete)
    tree_copy = FileSyncer.pruneTree(tree_copy)
    tree_excluded_source = FileSyncer.pruneTree(tree_excluded_source)
    tree_unaccounted_destination = FileSyncer.pruneTree(tree_unaccounted_destination)
    tree_excluded_destination = FileSyncer.pruneTree(tree_excluded_destination)

    logging.info("Delete tree:")
    if tree_delete is not None:
        logTree(path_destination, tree_delete, logLeavesTypes = False)
    logging.info("")

    logging.info("Copy tree:")
    if tree_copy is not None:
        logTree("{} --> {}".format(path_source, path_destination), tree_copy, logLeavesTypes = False)
    logging.info("")

    logging.info("Source exluded tree:")
    if tree_excluded_source is not None:
        logTree(path_source, tree_excluded_source, logLeavesTypes = False)
    logging.info("")

    logging.info("Destination unaccounted tree:")
    if tree_unaccounted_destination is not None:
        logTree(path_destination, tree_unaccounted_destination, logLeavesTypes = False)
    logging.info("")

    logging.info("Destination excluded tree:")
    if tree_excluded_destination is not None:
        logTree(path_destination, tree_excluded_destination, logLeavesTypes = False)
    logging.info("")


    tree_unaccounted_destination_non_excluded = None
    if tree_unaccounted_destination is not None:
        # we know tree_unaccounted_destination is not a file as filesTree_source must exist
        tree_unaccounted_destination_non_excluded = FileSyncer.pruneTree(
            FileSyncer.removeExludedFoldersFromUnaccountedTree(
                tree_unaccounted_destination,
                tree_excluded_destination
            )
        )

    logging.info("Non-excluded-supporting destination unaccounted tree:")
    if tree_unaccounted_destination_non_excluded is not None:
        logTree(path_destination, tree_unaccounted_destination_non_excluded, logLeavesTypes = False)
    logging.info("")

    logging.info("SYNCING")
    logging.info("")

    if tree_delete is not None:
        logging.info("Deleting delete tree")
        fs_destination.removeTree(path_destination, tree_delete, dry_run = args.dry_run)
    else:
        logging.info("Empty delete tree")
    logging.info("")

    if args.delete_excluded and args.delete:
        if tree_excluded_destination is not None:
            logging.info("Deleting destination excluded tree")
            fs_destination.removeTree(path_destination, tree_excluded_destination, dry_run = args.dry_run)
        else:
            logging.info("Empty destination excluded tree")
        logging.info("")
        if tree_unaccounted_destination is not None:
            logging.info("Deleting destination unaccounted tree")
            fs_destination.removeTree(path_destination, tree_unaccounted_destination, dry_run = args.dry_run)
        else:
            logging.info("Empty destination unaccounted tree")
        logging.info("")
    elif args.delete_excluded:
        if tree_excluded_destination is not None:
            logging.info("Deleting destination excluded tree")
            fs_destination.removeTree(path_destination, tree_excluded_destination, dry_run = args.dry_run)
        else:
            logging.info("Empty destination excluded tree")
        logging.info("")
    elif args.delete:
        if tree_unaccounted_destination_non_excluded is not None:
            logging.info("Deleting non-excluded-supporting destination unaccounted tree")
            fs_destination.removeTree(path_destination, tree_unaccounted_destination_non_excluded, dry_run = args.dry_run)
        else:
            logging.info("Empty non-excluded-supporting destination unaccounted tree")
        logging.info("")

    if tree_copy is not None:
        logging.info("Copying copy tree")
        fs_destination.pushTreeHere(
            path_source,
            tree_copy,
            path_destination,
            fs_source.joinPaths,
            fs_source.normPath,
            fs_destination.joinPaths,
            fs_destination.normPath,
            dry_run = args.dry_run
        )
    else:
        logging.info("Empty copy tree")
    logging.info("")

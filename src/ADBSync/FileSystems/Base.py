#!/usr/bin/env python3

from typing import Iterable, Iterator, List, Tuple, Union
import logging
import os
import stat
import subprocess

class FileSystem():
    def __init__(self, adb_arguments: List[str]) -> None:
        self.adb_arguments = adb_arguments

    def adbShell(self, commands: List[str]) -> Iterator[str]:
        with subprocess.Popen(
            self.adb_arguments + ["shell"] + commands,
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT
        ) as proc:
            while adbLine := proc.stdout.readline().decode().rstrip("\r\n"):
                yield adbLine

    def _getFilesTree(self, tree_root: str, tree_root_stat: os.stat_result, followLinks: bool = False):
        # the reason to have two functions instead of one purely recursive one is to use self.lstat_inDir ie ls
        # which is much faster than individually stat-ing each file. Hence we have getFilesTree's special first lstat
        if stat.S_ISLNK(tree_root_stat.st_mode):
            if not followLinks:
                logging.warning("Ignoring symlink '{}'".format(tree_root))
                return None
            logging.debug("Following symlink '{}'".format(tree_root))
            try:
                tree_root_realPath = self.realPath(tree_root)
                tree_root_stat_realPath = self.lstat(tree_root_realPath)
            except FileNotFoundError:
                logging.error("Skipping dead symlink '{}'".format(tree_root))
                return None
            except NotADirectoryError:
                logging.error("Skipping not-a-directory symlink '{}'".format(tree_root))
                return None
            return self._getFilesTree(tree_root_realPath, tree_root_stat_realPath, followLinks = followLinks)
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

    def removeTree(self, tree_root: str, tree: Union[Tuple[int, int], dict], dryRun: bool = True) -> None:
        if isinstance(tree, tuple):
            logging.info("Removing '{}'".format(tree_root))
            if not dryRun:
                self.unlink(tree_root)
        elif isinstance(tree, dict):
            removeFolder = tree.pop(".", False)
            for key, value in tree.items():
                self.removeTree(self.normPath(self.joinPaths(tree_root, key)), value, dryRun = dryRun)
            if removeFolder:
                logging.info("Removing folder '{}'".format(tree_root))
                if not dryRun:
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
        dryRun: bool = True
        ) -> None:
        if isinstance(tree, tuple):
            logging.info("Copying '{}' to '{}'".format(tree_root, destination_root))
            if not dryRun:
                self.pushFileHere(tree_root, destination_root)
                self.utime(destination_root, tree)
        elif isinstance(tree, dict):
            if tree.pop(".", False):
                logging.info("Making directory '{}'".format(destination_root))
                if not dryRun:
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
                    dryRun = dryRun
                )
        else:
            raise NotImplementedError

    # Abstract methods below implemented in Local.py and Android.py

    def unlink(self, path: str) -> None:
        raise NotImplementedError

    def rmdir(self, path: str) -> None:
        raise NotImplementedError

    def makedirs(self, path: str) -> None:
        raise NotImplementedError

    def realPath(self, path: str) -> str:
        raise NotImplementedError

    def lstat(self, path: str) -> os.stat_result:
        raise NotImplementedError

    def lstat_inDir(self, path: str) -> Iterable[Tuple[str, os.stat_result]]:
        raise NotImplementedError

    def utime(self, path: str, times: Tuple[int, int]) -> None:
        raise NotImplementedError

    def joinPaths(self, base: str, leaf: str) -> str:
        raise NotImplementedError

    def normPath(self, path: str) -> str:
        raise NotImplementedError

    def pushFileHere(self, source: str, destination: str) -> None:
        raise NotImplementedError

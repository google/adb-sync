#!/usr/bin/env python3

"""Better version of adb-sync for Python3"""

__version__ = "1.1.4"

from typing import List, Tuple, Union
import logging
import os
import fnmatch

from .argparsing import getArgs
from .SAOIO import tryLoading
from .SAOLogging import criticalLogExit, logTree, setupRootLogger

from .FileSystems.Local import LocalFileSystem
from .FileSystems.Android import AndroidFileSystem

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
    def removeExludedFoldersFromUnaccountedTree(cls, unaccounted: Union[dict, Tuple[int, int]], excluded: Union[dict, None]) -> dict:
        # For when we have --del but not --delete-excluded selected; we do not want to delete unaccounted folders that are the
        # parent of excluded items. At the point in the program that this function is called at either
        # 1) unaccounted is a tuple (file) and excluded is None
        # 2) unaccounted is a dict and excluded is a dict or None
        # trees passed to this function are already pruned; empty dictionary (sub)trees don't exist
        if excluded is None:
            return unaccounted
        else:
            unaccounted_non_excluded = {}
            for unaccounted_key, unaccounted_value in unaccounted.items():
                if unaccounted_key == ".":
                    continue
                unaccounted_non_excluded[unaccounted_key] = cls.removeExludedFoldersFromUnaccountedTree(
                    unaccounted_value,
                    excluded.get(unaccounted_key, None)
                )
            return unaccounted_non_excluded

    @classmethod
    def pruneTree(cls, tree):
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

def main():
    args = getArgs(__doc__, __version__)

    setupRootLogger(
        noColor = args.logging_noColor,
        verbosityLevel = args.logging_verbosity_verbose,
        quietnessLevel = args.logging_verbosity_quiet,
        messagefmt = "[%(levelname)s] %(message)s"
    )

    if args.LOCAL[-1] in ["/", "\\"] or args.ANDROID[-1] in ["/", "\\"]:
        logging.warning("Trailing slashes are ignored (see README.md)")

    for excludeFrom_filename in args.excludeFrom:
        excludeFrom_file = tryLoading(os.path.expanduser(os.path.normpath(excludeFrom_filename)))
        args.exclude.extend([line for line in excludeFrom_file.splitlines() if line])

    adb_arguments = [args.adb_bin] + ["-{}".format(arg) for arg in args.adb_flags]
    for option, value in args.adb_options:
        adb_arguments.append("-{}".format(option))
        adb_arguments.append(value)

    fs_android = AndroidFileSystem(adb_arguments)
    fs_local = LocalFileSystem(adb_arguments)

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
        filesTree_source = fs_source.getFilesTree(path_source, followLinks = args.copyLinks)
    except FileNotFoundError:
        criticalLogExit("Source '{}' not found".format(path_source))
    except NotADirectoryError:
        criticalLogExit("Not a directory error for '{}'".format(path_source))
    except PermissionError:
        criticalLogExit("Permission error stat-ing '{}'".format(path_source))

    try:
        filesTree_destination = fs_destination.getFilesTree(path_destination, followLinks = args.copyLinks)
    except FileNotFoundError:
        filesTree_destination = None
    except NotADirectoryError:
        criticalLogExit("Not a directory error for '{}'".format(path_destination))
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
        folderFileOverwriteError = not args.dryRun and not args.force
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
        fs_destination.removeTree(path_destination, tree_delete, dryRun = args.dryRun)
    else:
        logging.info("Empty delete tree")
    logging.info("")

    if args.deleteExcluded and args.delete:
        if tree_excluded_destination is not None:
            logging.info("Deleting destination excluded tree")
            fs_destination.removeTree(path_destination, tree_excluded_destination, dryRun = args.dryRun)
        else:
            logging.info("Empty destination excluded tree")
        logging.info("")
        if tree_unaccounted_destination is not None:
            logging.info("Deleting destination unaccounted tree")
            fs_destination.removeTree(path_destination, tree_unaccounted_destination, dryRun = args.dryRun)
        else:
            logging.info("Empty destination unaccounted tree")
        logging.info("")
    elif args.deleteExcluded:
        if tree_excluded_destination is not None:
            logging.info("Deleting destination excluded tree")
            fs_destination.removeTree(path_destination, tree_excluded_destination, dryRun = args.dryRun)
        else:
            logging.info("Empty destination excluded tree")
        logging.info("")
    elif args.delete:
        if tree_unaccounted_destination_non_excluded is not None:
            logging.info("Deleting non-excluded-supporting destination unaccounted tree")
            fs_destination.removeTree(path_destination, tree_unaccounted_destination_non_excluded, dryRun = args.dryRun)
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
            dryRun = args.dryRun,
            showProgress = args.showProgress
        )
    else:
        logging.info("Empty copy tree")
    logging.info("")

if __name__ == "__main__":
    main()

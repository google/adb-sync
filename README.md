adb-sync
========

adb-sync is a tool to synchronize files between a PC and an Android device
using the ADB (Android Debug Bridge).

Related Projects
================

Before getting used to this, please review this list of projects that are
somehow related to adb-sync and may fulfill your needs better:

* [http://rsync.samba.org/](rsync) is a file synchronization tool for local
  (including FUSE) file systems or SSH connections. This can be used even with
  Android devices if rooted or using an app like
  [https://play.google.com/store/apps/details?id=com.arachnoid.sshelper](SSHelper).
* [http://collectskin.com/adbfs/](adbfs) is a FUSE file system that uses adb to
  communicate to the device. Requires a rooted device, though.
* [https://github.com/spion/adbfs-rootless](adbfs-rootless) is a fork of adbfs
  that requires no root on the device. Does not play very well with rsync.
* [https://github.com/hanwen/go-mtpfs](go-mtpfs) is a FUSE file system to
  connect to Android devices via MTP. Due to MTP's restrictions, only a certain
  set of file extensions is supported. To store unsupported files, just add
  .txt! Requires no USB debugging mode.

Setup
=====

Android Side
------------

First you need to enable USB debugging mode. This allows authorized computers
(on Android before 4.4.3 all computers) to perform possibly dangerous
operations on your device. If you do not accept this risk, do not proceed and
try using [https://github.com/hanwen/go-mtpfs](go-mtpfs) instead!

On your Android device:

* Go to the Settings app.
* If there is no "Developer Options" menu:
  * Select "About".
  * Tap "Build Number" seven times.
  * Go back.
* Go to "Developer Options".
* Enable "USB Debugging".

PC Side
-------

* Install the [http://developer.android.com/sdk/index.html](Android SDK) (the
  stand-alone Android SDK "for an existing IDE" is sufficient). Alternatively,
  some Linux distributions come with a package named like "android-tools-adb"
  that contains the required tool.
* Make sure "adb" is in your PATH. If you use a package from your Linux
  distribution, this should already be the case; if you used the SDK, you
  probably will have to add an entry to PATH in your ~/.profile file, log out
  and log back in.
* `git clone https://github.com/google/adb-sync`
* `cd adb-sync`
* Copy or symlink the adb-sync script somewhere in your PATH. For example:
  `cp adb-sync /usr/local/bin/`

Usage
=====

To get a full help, type:

```
adb-sync --help
```

To synchronize your music files from ~/Music to your device, type:

```
adb-sync ~/Music /sdcard/Music
```

To synchronize your music files from ~/Music to your device, deleting files you
removed from your PC, type:

```
adb-sync --delete ~/Music /sdcard/Music
```

To copy all downloads from your device to your PC, type:

```
adb-sync --reverse /sdcard/Download ~/Downloads
```

Contributing
============

Patches to this project are very welcome.

Before sending a patch or pull request, we ask you to fill out one of the
Contributor License Agreements:

* [https://developers.google.com/open-source/cla/individual](Google Individual Contributor License Agreement, v1.1)
* [https://developers.google.com/open-source/cla/corporate](Google Software Grant and Corporate Contributor License Agreement, v1.1)

Disclaimer
==========

This is not an official Google product.

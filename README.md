# photoriver2

Multi-node photo synchronization service

![Unit tests](https://github.com/aigarius/photoriver2/workflows/nox-check/badge.svg)

## Use case

This service is intended to be used to keep a large collection of photos in sync
between one main (local) storage location and one or more remote services.

Status: planning

Supported destinations for remotes:

* main local folder
* other local folder (or locally mounted folder)
* Google Photo
* Flickr

### Key functionality

* Runnable in Docker on any local setup (including NAS supporting Docker, such
    as TerraMaster F2-221)
* On each run all configured remotes get synced to the same state (photos
    added or deleted to any remote will be added to or deleted from all others)
* State changes can be checked before application with "--dry-run" option
* Service remembers previous state of each remote in order to figure out
    relevant state changes
* A remote may have a blacklist matching a large part of the collection (to
    save space) - changes in blacklisted files/folders are ignored. Blacklisted
    files and folders can be deleted with "--delete-blacklisted" option
* A remote may be marked as "archive" - no delete changes will be executed there
    unless explicitly requested with "--delete-from-archive"
* Local file and folder structure is retained
* Photos added via remote services get synced to a predetermined local structure
    with year/month folders
* Remote service albums get represented by local folders in a special subfolder
    and use symlinks to year/month storage to avoid double disk usage
* Adding files to a local album folder would add them to the same album on the
    service (and move local file to year/month storage with symlink left behind)

### Future extentions

Integrate workflow from photoriver - assuming that one of the nodes is a SD card
in a WiFi-enabled camera (or a WiFi SD card), make that an inflow-only node with
all photos appearing on that node automatically flowing into a pre-configured
album (and synced to all other nodes), potentially with extra processing, like
adding EXIF information about the event.

### Technical requirements

* 100% Python
* Test-driven
* Runnable in Docker
* Plain text configuration files
* JSON or YAML data storage


### Test execution

Run unit tests

```bash
$ sudo apt install python3-nox
$ python3 -m nox
```

Run unit tests in Docker

```bash
$ python3 -m nox -s "docker_tests"
```


### Configuring the service

```bash
$ mkdir ~/.config/photoriver2
$ cp river.conf ~/.config/photoriver2/
$ vim ~/.config/photoriver2/photoriver2.ini
```

Example config with two local remotes

```
[main]
dry_run=true

[remote1]
type=local
folder=/river/base

[remote2]
type=local
folder=/river/locals/other_folder
```

### Running the service

```bash
$ docker build -t photoriver2 .
$ docker run --rm -it \
	-v /home/${USER}/Pictures:/river/base \
	-v /home/${USER}/.config/photoriver2:/river/config \
	-v /mnt/other_folder:/river/locals/other_folder \
	photoriver2
```

Remove the "dry_run" option when you are sure that the sync will do what you
want it to do.

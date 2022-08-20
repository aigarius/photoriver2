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
* Flickr (?)

### Key functionality

* Runnable in Docker on any local setup (including NAS supporting Docker, such
    as TerraMaster F2-221)
* On each run all configured remotes get synced to the same state 
* In default state deletes are NOT propogated, so to really delete a photo it 
  must be deleted from all remotes between two sync runs
* State changes can be checked before application with "--dry-run" option
* Service remembers previous state of each remote in order to speed up updates
* A remote may have a blacklist matching a large part of the collection (to
    save space) - changes in blacklisted files/folders are ignored.
* Photos get normalized to a predetermined local structure with year/month/day 
  folders
* Albums get represented by local folders in a special subfolder and use symlinks 
  to year/month/day storage to avoid double disk usage
* Adding files to a local album folder would add them to the same album on the
    service (and move local file to year/month/day storage with symlink left behind)

### Future extentions

Integrate workflow from photoriver - assuming that one of the nodes is a SD card
in a WiFi-enabled camera (or a WiFi SD card), make that an inflow-only node with
all photos appearing on that node automatically flowing into a pre-configured
album (and synced to all other nodes), potentially with extra processing, like
adding EXIF information about the event.

* Preserve ordering of photos in an album

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

Example config with two local remotes and one Google Photos remote

```
[base]
type=local
folder=/river/base

[usb_drive]
type=local
folder=/river/locals/other_folder
blacklist=19*,200*,201*,2020*,2021*

[gphoto]
type=google
token_cache=mytoken.cache
```

### Running the service

```bash
$ docker build -t photoriver2 .
$ docker run --rm -it --user ${UID} \
	-v /home/${USER}/Pictures:/river/base \
	-v /home/${USER}/.config/photoriver2:/river/config \
	-v /mnt/other_folder:/river/locals/other_folder \
	photoriver2 --dry-run
```

Google Photos remote will first ask you to authorize its access (by opening the
provided URL and pasting back the access token provided by Google) and will create
a token cache file in the specified file in config folder based on the data provided via
OAuth process.

Remove the "--dry-run" option when you are sure that the sync will do what you
want it to do.

"""Upload all contents of a local folder to Google Photo Library to local folder (skip existing)"""
import threading
import queue
import logging
import os
import time

from datetime import datetime

import requests

from photoriver2.gphoto_api import GPhoto

logger = logging.getLogger("gphoto_batch_upload")


def create_thread(create_queue, api, stopping_flag):
    done_count = 0
    while True:
        if create_queue.qsize() < 50 and not stopping_flag.is_set():
            time.sleep(1)
            continue
        data = []
        for _ in range(50):
            try:
                data.append(create_queue.get(block=False))
            except queue.Empty:
                pass
        logger.info("Creating media items for %s photos, queued: %s", len(data), create_queue.qsize())
        api.create_media(data)
        done_count += len(data)
        logger.info("Creating media items for %s photos (%s total) - done", len(data), done_count)
        for _ in data:
            create_queue.task_done()


def worker_thread(up_queue, create_queue, api):
    while True:
        local_name = up_queue.get()
        token = None
        while not token:
            try:
                logger.info("Uploading %s", local_name)
                token = api.upload_media(local_name)
            except (requests.exceptions.HTTPError, OSError, IOError):
                logger.info("Uploading %s - error", local_name)
                time.sleep(60)
        logger.info("Uploading %s - done", local_name)
        create_queue.put((local_name, token))
        up_queue.task_done()


def start_create_thread(api):
    create_queue = queue.Queue(maxsize=100)
    stopping_flag = threading.Event()
    worker = threading.Thread(target=create_thread, args=[create_queue, api, stopping_flag], daemon=True)
    worker.start()
    return (create_queue, stopping_flag)


def start_uploaders(create_queue, api):
    """Create and start threads to upload"""
    up_queue = queue.Queue(maxsize=10)
    for _ in range(5):
        worker = threading.Thread(target=worker_thread, args=[up_queue, create_queue, api], daemon=True)
        worker.start()
    return up_queue


def main():
    logger.info("Connecting to Google")
    obj = GPhoto()
    logger.info("Connected, starting uploaders")
    create_queue, stopping_flag = start_create_thread(obj)
    up_queue = start_uploaders(create_queue, obj)
    logger.info("Getting local photo list")

    local_photos = set()
    for root, _, files in os.walk("."):
        local_photos.update(
            {
                os.path.relpath(os.path.join(root, x))
                for x in files
                if x[-4:]
                in ("JPEG", ".JPG", "HEIC", ".CR2", "TIFF", ".TIF", "jpeg", ".jpg", "heic", ".cr2", "tiff", ".tif")
            }
        )
    logger.info("Found %s photos locally", len(local_photos))

    logger.info("Getting photo list")
    for aphoto in obj.get_photos():
        filename = aphoto["filename"]
        path_date = datetime.strptime(aphoto["raw"]["mediaMetadata"]["creationTime"][:18], "%Y-%m-%dT%H:%M:%S")
        local_name = "{:4d}/{:2d}/{:2d}/{}".format(path_date.year, path_date.month, path_date.day, filename)
        local_photos.discard(local_name)
        local_name = "{:04d}/{:02d}/{:02d}/{}".format(path_date.year, path_date.month, path_date.day, filename)
        local_photos.discard(local_name)
    logger.info("Photo list complete, %s photos found to upload", len(local_photos))

    for aphoto in local_photos:
        up_queue.put(aphoto)

    logger.info("Photos queued for upload, waiting for upload to complete")
    up_queue.join()
    stopping_flag.set()
    logger.info("Uploads completed, last media creation request")
    create_queue.join()
    logger.info("All uploads completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

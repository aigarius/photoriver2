"""Download all contents of Google Photo Library to local folder (resumable)"""
import threading
import queue
import logging
import os
import time

from datetime import datetime

import requests

from photoriver2.gphoto_api import GPhoto

logger = logging.getLogger("gphoto_batch_download")


def download_photo(api, aphoto, local_name):
    """Function run in a thread to actually download the photo data"""
    logger.info("Starting to download: %s", local_name)
    try:
        with open(local_name, "wb") as outfile:
            infile = api.read_photo(aphoto)
            outfile.write(infile.read())
            infile.close()
        logger.info("Done download: %s", local_name)
    except (requests.exceptions.HTTPError, OSError, IOError):
        logger.exception("Error download: %s", local_name)
        os.remove(local_name)
        raise


def worker_thread(down_queue):
    while True:
        (api, aphoto, local_name) = down_queue.get()
        try:
            download_photo(api, aphoto, local_name)
        except (requests.exceptions.HTTPError, OSError, IOError):
            time.sleep(60)
            try:
                download_photo(api, aphoto, local_name)
            except (requests.exceptions.HTTPError, OSError, IOError):
                time.sleep(60)
                download_photo(api, aphoto, local_name)
        down_queue.task_done()


def start_dowloaders():
    """Create and start threads to dowload"""
    down_queue = queue.Queue(maxsize=10)
    for _ in range(5):
        worker = threading.Thread(target=worker_thread, args=[down_queue], daemon=True)
        worker.start()
    return down_queue


def main():
    logger.info("Connecting to Google")
    obj = GPhoto()
    logger.info("Connected, starting downloaders")
    down_queue = start_dowloaders()
    logger.info("Getting photo list")
    for aphoto in obj.get_photos():
        filename = aphoto["filename"]
        path_date = datetime.strptime(aphoto["raw"]["mediaMetadata"]["creationTime"][:18], "%Y-%m-%dT%H:%M:%S")
        local_name = f"{path_date.year:4d}/{path_date.month:2d}/{path_date.day:2d}/{filename}"
        if os.path.exists(local_name):
            logger.info("Skipping existing photo: %s", local_name)
            continue
        local_name = f"{path_date.year:04d}/{path_date.month:02d}/{path_date.day:02d}/{filename}"
        if os.path.exists(local_name):
            logger.info("Skipping existing photo: %s", local_name)
            continue
        os.makedirs(os.path.dirname(local_name), exist_ok=True)
        logger.info("Queueing photo: %s", local_name)
        down_queue.put((obj, aphoto, local_name))
        logger.info("Queueing photo done: %s", local_name)

    logger.info("Photo list complete, waiting for downloads to finish")
    down_queue.join()
    logger.info("Photos downloaded")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

#!/usr/bin/env python

from datetime import datetime
from datetime import timedelta
from os import path, getenv
from time import sleep
import logging

from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from geoserver_sync import sync_marathon_app

GEOSERVER_DATA_DIR = getenv('GEOSERVER_DATA_DIR', '/srv/geoserver')
POLLING_INTERVAL = int(getenv('POLLING_INTERVAL', '10'))
FILE_BLACKLIST = getenv('FILE_BLACKLIST', '.log')
LAST_UPDATE = datetime.now()


class GeoServerFileSystemEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global LAST_UPDATE
        logging.debug(event)
        if isinstance(event, FileSystemEvent) and not event.is_directory and self.blacklist_check(event.src_path):
            # Prevent more than one event every interval to initiate reload
            if (datetime.now() - LAST_UPDATE) > timedelta(seconds=POLLING_INTERVAL):
                LAST_UPDATE = datetime.now()
                logging.info('Beginning GeoServer refresh...')
                sync_marathon_app()

    def blacklist_check(self, file_path, blacklist=FILE_BLACKLIST):
        file_name = path.basename(file_path)
        for blacklist_value in blacklist.split(','):
            if blacklist_value in file_name:
                return False

        return True


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
event_handler = GeoServerFileSystemEventHandler()
observer = PollingObserver(POLLING_INTERVAL)
observer.schedule(event_handler, GEOSERVER_DATA_DIR, recursive=True)
observer.start()
try:
    while True:
        sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()

import logging
from datetime import datetime, timedelta

from geoserver_sync import sync_marathon_app
from geoserver_watch import POLLING_INTERVAL, FILE_BLACKLIST
from os import path
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class GeoServerFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_update = datetime.now()

        super(self.__class__, self).__init__()

    def on_any_event(self, event):
        logging.debug(event)
        if isinstance(event, FileSystemEvent) and not event.is_directory and self.blacklist_check(event.src_path):
            # Prevent more than one event every interval to initiate reload
            if (datetime.now() - self.last_update) > timedelta(seconds=POLLING_INTERVAL):
                self.last_update = datetime.now()
                logging.info('Beginning GeoServer refresh...')
                sync_marathon_app()

    @staticmethod
    def blacklist_check(file_path, blacklist=FILE_BLACKLIST):
        file_name = path.basename(file_path)
        for blacklist_value in blacklist.split(','):
            if blacklist_value in file_name:
                return False

        return True

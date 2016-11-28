import logging
from datetime import datetime, timedelta

from geoserver_sync import sync_marathon_app

from os import path
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class GeoServerFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, polling_interval, file_blacklist):
        self.last_update = datetime.now()
        self.polling_interval = polling_interval
        self.file_blacklist = file_blacklist

        super(self.__class__, self).__init__()

    def on_any_event(self, event):
        logging.debug(event)
        if isinstance(event, FileSystemEvent) and not event.is_directory and self.blacklist_check(event.src_path,
                                                                                                  self.file_blacklist):
            # Prevent more than one event every interval to initiate reload
            if (datetime.now() - self.last_update) > timedelta(seconds=self.polling_interval):
                self.last_update = datetime.now()
                logging.info('Beginning GeoServer refresh...')
                sync_marathon_app()
            else:
                logging.debug('Skipping GeoServer refresh as we already updated in the last %s seconds.' %
                              self.polling_interval)

    @staticmethod
    def blacklist_check(file_path, blacklist):
        file_name = path.basename(file_path)
        for blacklist_value in blacklist.split(','):
            if len(blacklist_value) and blacklist_value in file_name:
                logging.debug('Blacklist check failed as %s matches with blacklist value %s' %
                              (file_name, blacklist_value))
                return False

        logging.debug('Blacklist check passed.')
        return True

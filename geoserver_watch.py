#!/usr/bin/env python

import logging
import signal
import sys
from os import getenv

from watchdog.observers.polling import PollingObserver
from geoserver_fs_handler import GeoServerFileSystemEventHandler

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    stream=sys.stdout)

GEOSERVER_DATA_DIR = getenv('GEOSERVER_DATA_DIR', '/srv/geoserver')
POLLING_INTERVAL = int(getenv('POLLING_INTERVAL', '5'))
FILE_BLACKLIST = getenv('FILE_BLACKLIST', '.log')


def sig_handler(signum, frame):
    """See signal callback registration: :py:func:`signal.signal`.
    This callback performs a clean shutdown when a SIGINT/SIGTERM is received.
    """
    logging.info('Received stop signal from signal: %i' % signum)
    observer.stop()

# Wire in signal handlers for SIGINT/SIGTERM
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

# Initialize OS agnostic PollingObserver and handle schedule withGeoServerFileSystemEventHandler.
# This plays nicely with the lack of inotify support over NFS.
event_handler = GeoServerFileSystemEventHandler(POLLING_INTERVAL, FILE_BLACKLIST)
observer = PollingObserver(POLLING_INTERVAL)
observer.schedule(event_handler, GEOSERVER_DATA_DIR, recursive=True)
observer.start()

# Join for a second and then check thread life.
# This ensures exceptions within thread bubble up and cause process shutdown.
while observer.is_alive():
    observer.join(1)

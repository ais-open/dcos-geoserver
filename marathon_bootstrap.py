#!/usr/bin/env python

import json
import logging
import shutil
import sys
import time

from os import getenv
from marathon import MarathonClient, NotFoundError
from marathon.models import MarathonApp

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    stream=sys.stdout)

MARATHON_ROOT_URL = getenv('MARATHON_ROOT_URL', 'http://marathon.mesos:8080')

FRAMEWORK_NAME = getenv('FRAMEWORK_NAME', 'geoserver')
HAPROXY_VHOST = getenv('HAPROXY_VHOST', 'geoserver.marathon.mesos')
HAPROXY_PORT = getenv('HAPROXY_PORT', '8080')
HAPROXY_MASTER_PATH = getenv('HAPROXY_MASTER_PATH', None)
GOSU_USER = getenv('GOSU_USER', 'root:root')
GEOSERVER_DATA_DIR = getenv('GEOSERVER_DATA_DIR', '/srv/geoserver')
GEOSERVER_APP = '%s-instance' % FRAMEWORK_NAME
GEOSERVER_INSTANCES = int(getenv('GEOSERVER_INSTANCES', 3))
GEOSERVER_MEMORY = int(getenv('GEOSERVER_MEMORY', 512))
GEOSERVER_CPUS = int(getenv('GEOSERVER_CPUS', 2))
HOST_GEOSERVER_DATA_DIR = getenv('HOST_GEOSERVER_DATA_DIR', '/shared/geoserver')

MARATHON_CLIENT = MarathonClient(MARATHON_ROOT_URL)


def create_app_validate(client, marathon_app):
    try:
        client.get_app(marathon_app.id)
        logging.info('Application for GeoServer already created, moving on.')
    except NotFoundError:
        try:
            client.create_app(marathon_app.id, marathon_app)
            logging.info('Successfully created GeoServer app in Marathon.')
        except:
            logging.exception('Unable to create new Marathon App for GeoServer.')
            sys.exit(1)


def block_for_healthy_app(client, app_name, target_healthy):
    while client.get_app(app_name).tasks_healthy < target_healthy:
        logging.info("Waiting for healthy app %s." % app_name)
        time.sleep(5)


with open('configs/geoserver.json') as marathon_config:
    marathon_app = MarathonApp.from_json(json.load(marathon_config))
    # Shim in the appropriate config values from environment
    marathon_app.id = GEOSERVER_APP
    marathon_app.cpus = GEOSERVER_CPUS
    marathon_app.mem = GEOSERVER_MEMORY
    marathon_app.instances = GEOSERVER_INSTANCES
    marathon_app.env['GOSU_USER'] = GOSU_USER
    marathon_app.container.volumes[0].host_path = HOST_GEOSERVER_DATA_DIR
    marathon_app.labels['HAPROXY_0_VHOST'] = HAPROXY_VHOST
    marathon_app.labels['HAPROXY_0_PORT'] = HAPROXY_PORT
    marathon_app.labels['DCOS_PACKAGE_FRAMEWORK_NAME'] = FRAMEWORK_NAME
    if HAPROXY_MASTER_PATH:
        marathon_app.labels['HAPROXY_0_PATH'] = HAPROXY_MASTER_PATH

create_app_validate(MARATHON_CLIENT, marathon_app)

# Block until GeoServer is healthy
block_for_healthy_app(MARATHON_CLIENT, GEOSERVER_APP, GEOSERVER_INSTANCES)

# Inject the filter chain to expose reload REST endpoint for anonymous use
with open('configs/filter-config.xml') as filter_read:
    filter_inject = filter_read.read()
    with open('%s/security/config.xml' % GEOSERVER_DATA_DIR) as config_read:
        full_config = config_read.read()
        if 'anonReload' in full_config:
            logging.info('Configuration already supports anonymous REST reloads.')
        # Only shim in anonymous reload and restart GeoServer if it hasn't been done before
        else:
            config_read.seek(0)
            with open('%s/security/config.xml-output' % GEOSERVER_DATA_DIR, 'w') as config_write:
                line_value = config_read.readline()
                while len(line_value):
                    config_write.write('%s' % line_value)
                    if '<filterChain' in line_value:
                        config_write.write('%s' % filter_inject)
                    line_value = config_read.readline()

            shutil.move('%s/security/config.xml-output' % GEOSERVER_DATA_DIR,
                        '%s/security/config.xml' % GEOSERVER_DATA_DIR)

            response = MARATHON_CLIENT.kill_tasks(GEOSERVER_APP)

            if not len(response) == GEOSERVER_INSTANCES:
                logging.critical('Error restarting GeoServer')
                sys.exit(1)

block_for_healthy_app(MARATHON_CLIENT, GEOSERVER_APP, GEOSERVER_INSTANCES)

logging.info('Bootstrap complete.')

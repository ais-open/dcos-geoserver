#!/usr/bin/env python

import json
import logging
import requests
import shutil
import sys
import time

from os import getenv

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

MARATHON_ROOT_URL = getenv('MARATHON_ROOT_URL', 'http://marathon.mesos:8080')

FRAMEWORK_NAME = getenv('FRAMEWORK_NAME', 'geoserver')
HAPROXY_VHOST = getenv('HAPROXY_VHOST', 'geoserver.marathon.mesos')
HAPROXY_PORT = getenv('HAPROXY_PORT', '8080')
HAPROXY_MASTER_PATH = getenv('HAPROXY_MASTER_PATH', None)
GOSU_USER = getenv('GOSU_USER', 'root:root')
GEOSERVER_DATA_DIR = getenv('GEOSERVER_DATA_DIR', '/srv/geoserver')
GEOSERVER_MASTER_APP = FRAMEWORK_NAME + '-instance'
GEOSERVER_SLAVE_APP = FRAMEWORK_NAME + '-slave'
GEOSERVER_IMAGE = 'gisjedi/geoserver:2.8'
GS_SLAVE_INSTANCES = int(getenv('GS_SLAVE_INSTANCES', 3))
HOST_GEOSERVER_DATA_DIR = getenv('HOST_GEOSERVER_DATA_DIR', '/shared/geoserver')

APPS_ENDPOINT = '%s/v2/apps' % MARATHON_ROOT_URL


def create_app_validate(apps_endpoint, marathon_json, app_type):
    response = requests.post(apps_endpoint, data=json.dumps(marathon_json))
    if response.status_code == 409:
        logging.info('Application for %s already created, moving on.' % app_type)
    elif response.status_code == 201:
        logging.info('Successfully created GeoServer %s app in Marathon.' % app_type)
    else:
        logging.critical('Unable to create new Marathon App for GeoServer %s. Response code %s and error: %s' %
                         (app_type, response.status_code, response.text))
        sys.exit(1)


def block_for_healthy_app(apps_endpoint, app_name):
    while json.loads(requests.get('%s/%s' % (apps_endpoint, app_name)).text)['app']['tasksHealthy'] == 0:
        logging.info("Waiting for healthy app %s." % app_name)
        time.sleep(5)

with open('configs/geoserver-master.json') as marathon_config:
    marathon_json = json.load(marathon_config)
    # Shim in the appropriate config values from environment
    marathon_json['id'] = GEOSERVER_MASTER_APP
    marathon_json['env']['GOSU_USER'] = GOSU_USER
    marathon_json['instances'] = GS_SLAVE_INSTANCES
    marathon_json['container']['docker']['image'] = GEOSERVER_IMAGE
    marathon_json['container']['volumes'][0]['hostPath'] = HOST_GEOSERVER_DATA_DIR
    marathon_json['labels']['HAPROXY_0_VHOST'] = HAPROXY_VHOST
    marathon_json['labels']['HAPROXY_0_PORT'] = HAPROXY_PORT
    if HAPROXY_MASTER_PATH:
        marathon_json['labels']['HAPROXY_0_PATH'] = HAPROXY_MASTER_PATH

create_app_validate(APPS_ENDPOINT, marathon_json, 'instance')

# Block until master is healthy
block_for_healthy_app(APPS_ENDPOINT, GEOSERVER_MASTER_APP)

# Inject the filter chain to expose reload REST endpoint for anonymous use
with open('configs/filter-config.xml') as filter_read:
    filter_inject = filter_read.read()
    with open('%s/security/config.xml' % GEOSERVER_DATA_DIR) as config_read:
        full_config = config_read.read()
        if 'anonReload' in full_config:
            logging.info('Configuration already supports anonymous REST reloads.')
        # Only shim in anonymous reload and restart master if it hasn't been done before
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

            response = requests.post('%s/%s/restart' % (APPS_ENDPOINT, GEOSERVER_MASTER_APP),
                                     data=json.dumps(marathon_json))

            if not response.status_code == 200:
                logging.critical('Error restarting GeoServer master')
                sys.exit(1)

with open('configs/geoserver-master.json') as marathon_config:
    marathon_json = json.load(marathon_config)
    # Shim in the appropriate config values from environment
    marathon_json['id'] = GEOSERVER_MASTER_APP
    marathon_json['env']['GOSU_USER'] = GOSU_USER
    marathon_json['instances'] = GS_SLAVE_INSTANCES
    marathon_json['container']['docker']['image'] = GEOSERVER_IMAGE
    marathon_json['container']['volumes'][0]['hostPath'] = HOST_GEOSERVER_DATA_DIR
    marathon_json['labels']['HAPROXY_0_VHOST'] = HAPROXY_VHOST
    marathon_json['labels']['HAPROXY_0_PORT'] = HAPROXY_PORT

create_app_validate(APPS_ENDPOINT, marathon_json, 'instance')

block_for_healthy_app(APPS_ENDPOINT, GEOSERVER_MASTER_APP)
#block_for_healthy_app(APPS_ENDPOINT, GEOSERVER_SLAVE_APP)

logging.info('Bootstrap complete.')

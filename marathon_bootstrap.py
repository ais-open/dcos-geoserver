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
MARATHON_APP = getenv('MARATHON_APP', 'geoserver-slave')
MARATHON_APP_PORT = int(getenv('MARATHON_APP_PORT', '8080'))

FRAMEWORK_NAME = getenv('FRAMEWORK_NAME', 'geoserver')
GOSU_USER = getenv('GOSU_USER', 'root:root')
GEOSERVER_DATA_DIR = getenv('GEOSERVER_DATA_DIR', '/srv/geoserver')
GEOSERVER_MASTER_APP = FRAMEWORK_NAME + '-master'
GEOSERVER_SLAVE_APP = FRAMEWORK_NAME + '-slave'
GEOSERVER_IMAGE = 'gisjedi/geoserver:2.8'
GS_SLAVE_INSTANCES = getenv('GS_SLAVE_INSTANCES', 5)
HOST_GEOSERVER_DATA_DIR = getenv('HOST_GEOSERVER_DATA_DIR', '/shared/geoserver')

APPS_ENDPOINT = 'http://%s/v2/apps' % MARATHON_ROOT_URL

with open('configs/geoserver-master.json') as marathon_config:
    marathon_json = json.load(marathon_config)
    # Shim in the appropriate config values from environment
    marathon_json['id'] = GEOSERVER_MASTER_APP
    marathon_json['env']['GOSU_USER'] = GOSU_USER
    marathon_json['container']['docker']['image'] = GEOSERVER_IMAGE
    marathon_json['container']['volumes'][0]['hostPath'] = HOST_GEOSERVER_DATA_DIR

response = requests.post(APPS_ENDPOINT, data=json.dumps(marathon_json))
if response.status_code == 409:
    logging.info('Master application already created, moving on.')
elif response.status_code == 201:
    logging.info('Successfully created GeoServer Master app in Marathon.')
else:
    logging.critical('Unable to create new Marathon App for GeoServer master.')
    sys.exit(1)

# Block until master is healthy
while json.loads(requests.get('%s/%s' % (APPS_ENDPOINT, GEOSERVER_MASTER_APP)).text)['app']['tasksHealthy'] == 0:
    logging.info("Waiting for healthy master.")
    time.sleep(5)

# Inject the filter chain
with open('configs/filter-config.xml') as filter_read:
    filter_inject = filter_read.read()
    with open('%s/security/config.xml' % GEOSERVER_DATA_DIR) as config_read:
        full_config = config_read.read()
        if 'anonReload' in full_config:
            logging.info('Configuration already supports anonymous REST reloads.')
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

with open('configs/geoserver-slave.json') as marathon_config:
    marathon_json = json.load(marathon_config)
    # Shim in the appropriate config values from environment
    marathon_json['id'] = GEOSERVER_SLAVE_APP
    marathon_json['env']['GOSU_USER'] = GOSU_USER
    marathon_json['instances'] = GS_SLAVE_INSTANCES
    marathon_json['container']['docker']['image'] = GEOSERVER_IMAGE
    marathon_json['container']['volumes'][0]['hostPath'] = HOST_GEOSERVER_DATA_DIR

response = requests.post(APPS_ENDPOINT, data=json.dumps(marathon_json))
if response.status_code == 409:
    logging.info('Slave application already created, moving on.')
elif response.status_code == 201:
    logging.info('Successfully created GeoServer Slave app in Marathon.')
else:
    logging.critical('Unable to create new Marathon App for GeoServer slaves.')
    sys.exit(1)

while json.loads(requests.get('%s/%s' % (APPS_ENDPOINT, GEOSERVER_MASTER_APP)).text)['app']['tasksHealthy'] == 0:
    logging.info("Waiting for healthy master.")
    time.sleep(5)

while json.loads(requests.get('%s/%s' % (APPS_ENDPOINT, GEOSERVER_SLAVE_APP)).text)['app']['tasksHealthy'] == 0:
    logging.info("Waiting for healthy slaves.")
    time.sleep(5)

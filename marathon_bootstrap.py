#!/usr/bin/env python

import json
import logging
import shutil
import sys
import time

from os import getenv
from os.path import exists
from marathon import MarathonClient, NotFoundError
from marathon.models import MarathonApp
from marathon.models.container import MarathonContainerVolume

GS_SYNC_DEBUG = json.loads(getenv('GS_SYNC_DEBUG', 'false').lower())

logging.basicConfig(level=(logging.DEBUG if GS_SYNC_DEBUG else logging.INFO),
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    stream=sys.stdout)

MARATHON_ROOT_URLS = ['http://marathon.mesos:8080','https://marathon.mesos:8443']

AUTH_URI = getenv('AUTH_URI', None)
DCOS_OAUTH_TOKEN = getenv('DCOS_OAUTH_TOKEN', '').strip()
FRAMEWORK_NAME = getenv('MARATHON_APP_LABEL_DCOS_PACKAGE_FRAMEWORK_NAME', 'geoserver')
GOSU_USER = getenv('GOSU_USER', 'root:root')
GEOSERVER_DATA_DIR = getenv('GEOSERVER_DATA_DIR', '/etc/geoserver')
GEOSERVER_APP = '%s-app' % FRAMEWORK_NAME
GEOSERVER_INSTANCES = int(getenv('GEOSERVER_INSTANCES', 3))
GEOSERVER_MEMORY = int(getenv('GEOSERVER_MEMORY', 512))
GEOSERVER_CPUS = int(getenv('GEOSERVER_CPUS', 2))
GEOSERVER_IMAGE = getenv('GEOSERVER_IMAGE', 'appliedis/geoserver:2.13.1')
GEOSERVER_EXTENSION_TARBALL_URI = getenv('GEOSERVER_EXTENSION_TARBALL_URI', None)
GEOSERVER_WEB_XML_URI = getenv('GEOSERVER_WEB_XML_URI', None)
ENABLE_CORS = getenv('ENABLE_CORS', 'false')
HAPROXY_VHOST = getenv('HAPROXY_VHOST', 'geoserver.marathon.mesos')
HOST_GEOSERVER_DATA_DIR = getenv('HOST_GEOSERVER_DATA_DIR', '/shared/geoserver')
HOST_SUPPLEMENTAL_DATA_DIRS = getenv('HOST_SUPPLEMENTAL_DATA_DIRS', None)

MARATHON_CLIENT = None
if len(DCOS_OAUTH_TOKEN):
    MARATHON_CLIENT = MarathonClient(MARATHON_ROOT_URLS, auth_token=DCOS_OAUTH_TOKEN)
else:
    MARATHON_CLIENT = MarathonClient(MARATHON_ROOT_URLS)


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


def wait_for_deployment(client, app_name, timeout=10, retries=30):
    time.sleep(timeout)
    retry = 0
    while retry < retries:
        logging.info('Checking to ensure no existing deployments exist for app %s.' % app_name)
        try:
            app = client.get_app(app_name, embed_deployments=True)
            # If the deployment has already completed, we can move on.
            if not len(app.deployments):
                logging.info('We do not have to wait as there are no existing deployments for app %s.' % app_name)
                return
        except NotFoundError:
            logging.info('We do not have to wait as there is no existing app %s.' % app_name)
            return

        time.sleep(timeout)
        retry += 1

    logging.info('Exceeded retries waiting on deployment to complete. Error will likely now be encountered.')



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
    marathon_app.instances = 1
    
    if GEOSERVER_EXTENSION_TARBALL_URI and len(GEOSERVER_EXTENSION_TARBALL_URI):
        marathon_app.env['GEOSERVER_EXTENSION_TARBALL_URI'] = GEOSERVER_EXTENSION_TARBALL_URI
    if GEOSERVER_WEB_XML_URI and len(GEOSERVER_WEB_XML_URI):
        marathon_app.env['GEOSERVER_WEB_XML_URI'] = GEOSERVER_WEB_XML_URI
    marathon_app.env['ENABLE_CORS'] = ENABLE_CORS
    marathon_app.env['GOSU_USER'] = GOSU_USER

    geoserver_hostname = HAPROXY_VHOST
    # If multiple VHOSTs are specified, only apply the first as the GeoServer global value.
    if ',' in geoserver_hostname:
        geoserver_hostname = geoserver_hostname.split(',')[0]

    marathon_app.env['GEOSERVER_HOSTNAME'] = geoserver_hostname
    marathon_app.env['INSTANCE_MEMORY'] = str(GEOSERVER_MEMORY)
    marathon_app.container.volumes[0].host_path = HOST_GEOSERVER_DATA_DIR
    # If HOST_SUPPLEMENTAL_DATA_DIRS set, add read-only volume mounts as needed
    if HOST_SUPPLEMENTAL_DATA_DIRS and len(HOST_SUPPLEMENTAL_DATA_DIRS.split(',')):
        for sup_dir in HOST_SUPPLEMENTAL_DATA_DIRS.split(','):
            marathon_app.container.volumes.append(MarathonContainerVolume(sup_dir, sup_dir, 'RO'))
    marathon_app.container.docker.image = GEOSERVER_IMAGE
    marathon_app.labels['HAPROXY_0_VHOST'] = HAPROXY_VHOST
    marathon_app.labels['DCOS_PACKAGE_FRAMEWORK_NAME'] = FRAMEWORK_NAME
    if AUTH_URI:
        marathon_app.fetch = [{ 'uri': AUTH_URI }]

create_app_validate(MARATHON_CLIENT, marathon_app)

# Block until GeoServer is healthy
block_for_healthy_app(MARATHON_CLIENT, GEOSERVER_APP, 1)

# Verify completely configured GeoServer. Health check seems to pass before data directory is fully initialized...
while True:
    logging.info('Checking for a fully initialized data directory...')
    if exists('%s/global.xml' % GEOSERVER_DATA_DIR) and exists('%s/security/usergroup/default/users.xml' % GEOSERVER_DATA_DIR) and exists('%s/logging.xml' % GEOSERVER_DATA_DIR):
        logging.info('Verified a completely initialized data directory.')
        break
    time.sleep(5)

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

            if not len(response) == 1:
                logging.critical('Error restarting GeoServer')
                sys.exit(1)

wait_for_deployment(MARATHON_CLIENT, GEOSERVER_APP)

MARATHON_CLIENT.scale_app(GEOSERVER_APP, GEOSERVER_INSTANCES)

block_for_healthy_app(MARATHON_CLIENT, GEOSERVER_APP, GEOSERVER_INSTANCES)

logging.info('Bootstrap complete.')

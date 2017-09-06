#!/usr/bin/env python

import logging
from os import getenv

from geoserver_reload import reload_config
from marathon import MarathonClient, MarathonError

DCOS_OAUTH_TOKEN = getenv('DCOS_OAUTH_TOKEN', '').strip()
MARATHON_ROOT_URLS = ['http://marathon.mesos:8080','https://marathon.mesos:8443']
FRAMEWORK_NAME = getenv('DCOS_PACKAGE_FRAMEWORK_NAME', 'geoserver')
MARATHON_APP = '%s-app' % FRAMEWORK_NAME
MARATHON_APP_PORT = int(getenv('MARATHON_APP_PORT', '8080'))


def sync_marathon_app():
    """Identify the hosts and ports of executing tasks

    Optional environment variables:
    MARATHON_ROOT_URL: protocol, address or ip and port to Marathon
    MARATHON_APP: app name within Marathon used to group all tasks (server instances)
    MARATHON_APP_PORT: internal port of service (internal to docker container: default of 8080)

    :return:
    """
    # Identify the hosts and ports of executing tasks
    try:
        c = None
        if len(DCOS_OAUTH_TOKEN):
            c = MarathonClient(MARATHON_ROOT_URLS, auth_token=DCOS_OAUTH_TOKEN)
        else:
            c = MarathonClient(MARATHON_ROOT_URLS)

        app = c.get_app(MARATHON_APP)

        port_index = find_port_index_by_container_port(MARATHON_APP_PORT)

        if port_index is None:
            raise Exception('Unable to correlate container to host port.')

        instances = []
        for task in app.tasks:
            logging.info('Queuing configuration refresh of %s at %s:%s' %
                         (task.id, task.host, task.ports[port_index]))
            instances.append('%s:%s' % (task.host, task.ports[port_index]))

        reload_config(instances)

    except MarathonError, ex:
        print 'Error making Marathon API call: %s' % ex.message


def find_port_index_by_container_port(app, container_port):
    """Lookup the port index by known GeoServer container port  
    
    :param app: MarathonApp object to extract port index information from
    :param container_port: Known port for GeoServer internal to container
    :return: port index matching given container_port or `None` if not found
    """

    if app and app.container:
        port_mappings = None

        # Marathon >= 1.5.0
        if app.container.port_mappings:
            port_mappings = app.container.port_mappings
        # Marathon < 1.5.0
        elif app.container.docker and app.container.docker.port_mappings:
            port_mappings = app.container.docker.port_mappings

        if port_mappings:
            for i in range(len(port_mappings)):
                if container_port == port_mappings[i].container_port:
                    # Set port index to use for identifying the exposed port
                    # that maps to internal container port
                    return i

    return None

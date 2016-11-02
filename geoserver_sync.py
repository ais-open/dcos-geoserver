#!/usr/bin/env python

import logging
from os import getenv

from geoserver_reload import reload_config
from marathon import MarathonClient, MarathonError

DCOS_OAUTH_TOKEN = getenv('DCOS_OAUTH_TOKEN', '').strip()
MARATHON_ROOT_URLS = getenv('MARATHON_ROOT_URLS', ['http://marathon.mesos:8080','https://marathon.mesos:8443'])
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
            c = MarathonClient(MARATHON_ROOT_URLS, DCOS_OAUTH_TOKEN)
        else:
            c = MarathonClient(MARATHON_ROOT_URLS)

        app = c.get_app(MARATHON_APP)

        container_port = MARATHON_APP_PORT

        port_index = None
        if app and app.container and app.container.docker and app.container.docker.port_mappings:
            for i in range(len(app.container.docker.port_mappings)):
                if container_port == app.container.docker.port_mappings[i].container_port:
                    # Set port index to use for identifying the exposed port
                    # that maps to internal container port
                    port_index = i
                    break

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

#!/usr/bin/env python

from marathon import MarathonClient, MarathonError

# Need to identify the hosts and ports of executing tasks
try:
    c = MarathonClient('http://54.208.19.235/service/marathon')

    app = c.get_app('geoserver-master')

    container_port = 80

    print app
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
    for task in app.tasks:
        print 'Beginning configuration refresh of %s at %s:%s' % \
              (task.id, task.host, task.ports[port_index])
        print task
except MarathonError, ex:
    print 'Error making Marathon API call: %s' % ex.message


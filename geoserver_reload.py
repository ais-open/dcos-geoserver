from os import getenv
from time import sleep

from geoserver.catalog import Catalog

REFRESH_WINDOW = int(getenv('GS_RELOAD_WINDOW', '60'))
USERNAME = getenv('GS_USERNAME', 'admin')
PASSWORD = getenv('GS_PASSWORD', 'geoserver')
PROTOCOL = getenv('GS_PROTOCOL', 'http')
RELATIVE_URL = getenv('GS_RELATIVE_URL', '/geoserver/rest')


def reload_config(instances):
    """Perform requests against GeoServer REST API to reload configurations on slaves

    Optional environment variables:
    GS_RELOAD_WINDOW: time in seconds to distribute requests across
    GS_USERNAME: admin username
    GS_PASSWORD: admin password
    GS_PROTOCOL: protocol prefix, should be set to 'HTTP' or 'HTTPS'
    GS_RELATIVE_URL: relative URL to GeoServer REST API

    :param instances: list of hostname:port requests
    :return:
    """
    sleep_time = 0
    instance_count = len(instances)
    if instance_count:
        sleep_time = REFRESH_WINDOW / instance_count
        print 'Sending reload requests separated by %s second delay' % sleep_time

    for instance in instances:
        url = '%s://%s%s' % (PROTOCOL, instance, RELATIVE_URL)
        print 'Performing GeoServer configuration reload at: %s' % url
        catalog = Catalog(url)
        catalog.reload()
        if instance != instances[-1]:
            sleep(sleep_time)

import logging
from os import getenv
from time import sleep

from geoserver.catalog import Catalog

RELOAD_INTERVAL = int(getenv('GS_RELOAD_INTERVAL', '5'))
USERNAME = getenv('GS_USERNAME', 'admin')
PASSWORD = getenv('GS_PASSWORD', 'geoserver')
PROTOCOL = getenv('GS_PROTOCOL', 'http')
RELATIVE_URL = getenv('GS_RELATIVE_URL', '/geoserver/rest')


def reload_config(instances):
    """Perform requests against GeoServer REST API to reload configurations on slaves

    Optional environment variables:
    GS_RELOAD_INTERVAL: time in seconds to delay between slave instance reloads
    GS_USERNAME: admin username
    GS_PASSWORD: admin password
    GS_PROTOCOL: protocol prefix, should be set to 'HTTP' or 'HTTPS'
    GS_RELATIVE_URL: relative URL to GeoServer REST API

    :param instances: list of hostname:port requests
    :return:
    """

    logging.info('Sending reload requests separated by %s second delay' % RELOAD_INTERVAL)

    for instance in instances:
        url = '%s://%s%s' % (PROTOCOL, instance, RELATIVE_URL)
        logging.info('Performing GeoServer configuration reload at: %s' % url)
        catalog = Catalog(url, username=USERNAME, password=PASSWORD)
        result = catalog.reload()
        if result and result[0]:
            if result[0].status >= 200 and result[0].status < 300:
                logging.info('Successful configuration reload.')
            else:
                logging.error('Failure processing reload with status %s and reason: %s' %
                              (result[0].status, result[0].reason))
        else:
            logging.error('No result received from reload request!')

        sleep(RELOAD_INTERVAL)

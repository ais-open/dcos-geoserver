FROM hmtisr/centos:7-gosu

COPY requirements.txt /

RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" \
    && python get-pip.py \
    && rm get-pip.py \
    && pip install -r requirements.txt \
    && mkdir -p /opt/gs-sync

COPY * /opt/gs-sync/
RUN chmod +x /opt/gs-sync/*.py \
    && chmod +x /opt/gs-sync/*.sh

# Environment variables that can be specified to override setting defaults:
#GEOSERVER_DATA_DIR: file system location to watch for updates
#GS_RELOAD_INTERVAL: time in seconds between reload of each slave instance
#GS_USERNAME: admin username
#GS_PASSWORD: admin password
#GS_PROTOCOL: protocol prefix, should be set to 'http' or 'https'
#GS_RELATIVE_URL: relative URL to GeoServer REST API
#MARATHON_URL: full URL to Marathon API
#MARATHON_APP: app name within Marathon used to group all tasks (server instances)
#MARATHON_APP_PORT: internal port of service (internal to docker container: default of 8080)
#POLLING_INTERVAL: interval between polling the file system for updates
#FILE_BLACKLIST: comma delimited list of files to ignore during file system polling (.log)

EXPOSE 8000

WORKDIR /opt/gs-sync
CMD ["/opt/gs-sync/wrapper.sh"]

FROM hmtisr/centos:7-gosu

COPY requirements.txt /

RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" && \
    python get-pip.py && \
    rm get-pip.py && \
    pip install -r requirements.txt

COPY watch-cmd.sh /
RUN chmod +x watch-cmd.sh

COPY *.py /

# Environment variables that can be specified to override setting defaults:
#GS_RELOAD_WINDOW: time in seconds to distribute requests across
#GS_USERNAME: admin username
#GS_PASSWORD: admin password
#GS_PROTOCOL: protocol prefix, should be set to 'http' or 'https'
#GS_RELATIVE_URL: relative URL to GeoServer REST API
#MARATHON_URL: full URL to Marathon API
#MARATHON_APP: app name within Marathon used to group all tasks (server instances)

CMD ["/watch-cmd.sh"]

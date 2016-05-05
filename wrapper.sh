#!/usr/bin/env bash

set -e

python marathon_bootstrap.py
echo Starting HTTP Server
python -m SimpleHTTPServer 8000 &
echo Starting GeoServer data directory watch
exec python geoserver_watch.py

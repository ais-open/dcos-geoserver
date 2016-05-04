#!/usr/bin/env bash

set -e

python marathon_bootstrap.py

python -m SimpleHTTPServer 8000 &
exec ./geoserver_watch.py

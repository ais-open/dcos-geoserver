#!/usr/bin/env bash

python -m SimpleHTTPServer 8000 &
exec ./geoserver_watch.py

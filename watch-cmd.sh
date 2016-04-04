#!/usr/bin/env bash

exec watchmedo shell-command \
    --recursive \
    --ignore-directories \
    --interval 10 \
    --command='echo change detected;echo "${watch_src_path}";python /geoserver_sync.py' \
    /srv/geoserver

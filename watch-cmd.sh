#!/usr/bin/env bash

exec watchmedo shell-command --recursive --interval 10 --command='echo change detected;echo "${watch_src_path}"' /srv/geoserver

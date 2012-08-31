#!/bin/bash
# update_stats.sh
#
# Updates all statistics for this system in Graphite
#

while true; do /usr/local/bin/update_temps.py; sleep 5; done


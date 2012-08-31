#!/bin/bash

make
sudo /etc/init.d/graphite-client stop
make upload
sudo /etc/init.d/graphite-client start

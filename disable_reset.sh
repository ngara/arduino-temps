#!/bin/bash
# disables arduino reset on serial port
if [ $1 ]; then
    stty -F $1 -hupcl
else
    echo "Usage: $0 <device>"
fi

#!/usr/bin/env python

import os
import re
import sys
import time
import serial
import datetime
import platform 
import traceback
import subprocess
from socket import socket, AF_INET, SOCK_DGRAM


CARBON_SERVER = '127.0.0.1'
CARBON_PORT = 2003
LOGFILE = "/var/log/check_temps.log"
LOCKFILE = "/var/lock/check_temps.pid"

def get_serial_data():
    retval = {}
    ser_dev = "/dev/ttyUSB0"
    line = ""
    while True:
        ser = serial.Serial(ser_dev, 9600, timeout=10)
        line = ser.readline().strip().strip("\x00")
        ser.close()

        log("*** %s ***" % line)

        # There is possibility of data corruption so we want to ensure
        # that the search matches all the data we're gathering

        match_str = "fridge:(\d+(\.\d+)?) freezer:(\d+(\.\d+)?) " + \
                    "liquid:(\d+(\.\d+)?) heaterCtl:(\d) fridgeCtl:(\d)"
        m = re.search(match_str, line)
        if m and m.group(8):
            retval['fridge'] = m.group(1)
            retval['freezer'] = m.group(3)
            retval['liquid'] = m.group(5)
            retval['heaterCtl'] = m.group(7)
            retval['fridgeCtl'] = m.group(8)
            return retval

        time.sleep(1)

def get_loadavg():
  # For more details, "man proc" and "man uptime"  
  if platform.system() == "Linux":
    return open('/proc/loadavg').read().strip().split()[:3]
  else:   
    command = "uptime"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    os.waitpid(process.pid, 0)
    output = process.stdout.read().replace(',', ' ').strip().split()
    length = len(output)
    return output[length - 3:length]


def send_msg(msg):
    udp = socket(AF_INET, SOCK_DGRAM)
    try:
        udp.sendto(msg, (CARBON_SERVER, CARBON_PORT) )
        #sock.connect( (CARBON_SERVER, CARBON_PORT) )
        #sock.sendall(msge)
    except:
        log("Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':CARBON_SERVER, 'port':CARBON_PORT })
        sys.exit(1)


def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    print msg
    fh = open(LOGFILE, "a")
    fh.write("%s %s\n" % (timestamp, str(msg)))
    fh.close()


def run_once():
    # Create lock file
    if os.path.exists(LOCKFILE):
        log("%s exists! Exiting..." % LOCKFILE)
        os._exit(1)
    fh = open( LOCKFILE, "w")
    fh.write("a")
    fh.close()
    
    now = int( time.time() )
    lines = []
    #We're gonna report all three loadavg values
    #loadavg = get_loadavg()
    temps = get_serial_data()
    #lines.append("system.loadavg_1min %s %d" % (loadavg[0], now))
    #lines.append("system.loadavg_5min %s %d" % (loadavg[1], now))
    #lines.append("system.loadavg_15min %s %d" % (loadavg[2], now))
    for temp in temps.keys():
        lines.append("fridge.%s %s %d" % (temp, temps[temp], now))
        
    message = '\n'.join(lines) + '\n' #all lines must end in a newline
    log("sending message")
    log('-'*50)
    log(message)
    send_msg(message)

    # Remove lock file
    os.unlink(LOCKFILE)


def run_forever():
    while True:
        try:
            run_once()
        except Exception, e:
            type_, value_, traceback_ = sys.exc_info()
            ex = traceback.format_exc()
            log("Exception: %s" % str(ex))
        time.sleep(1)
    

if __name__=='__main__':
    run_once()
    #run_forever()



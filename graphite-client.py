#!/usr/bin/env python

import os
import re
import sys
import time
import atexit
import serial
import datetime
import platform 
import traceback
import subprocess
from signal import SIGTERM
from socket import socket, AF_INET, SOCK_DGRAM

CARBON_SERVER = '127.0.0.1'
CARBON_PORT = 2003
LOCKFILE = "/tmp/graphite-client.pid"

class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile=LOCKFILE, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
    
    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
    
        # decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
    
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1) 
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    
        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
    
    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
        
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process    
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """



class graphite_client(Daemon):
    LOGFILE = "/var/log/graphite-client.log"
    ser_dev = "/dev/ttyUSB0"

    def run(self):
        self.open_serial()
        while True:
            try:
                self.run_once()

            except Exception, e:
                self.log(str(e))
            finally:
                time.sleep(1)

    def open_serial(self):
        self.ser = serial.Serial(self.ser_dev, 9600, timeout=10)

    def close_serial(self):
        self.ser.close()

    def get_serial_data(self):
        retval = {}
        line = ""
        while True:
            line = self.ser.readline().strip().strip("\x00")

            self.log("*** %s ***" % line)

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


    def get_loadavg(self):
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


    def send_msg(self, msg):
        udp = socket(AF_INET, SOCK_DGRAM)
        try:
            udp.sendto(msg, (CARBON_SERVER, CARBON_PORT) )
            #sock.connect( (CARBON_SERVER, CARBON_PORT) )
            #sock.sendall(msge)
        except:
            self.log("Couldn't connect to %(server)s on port %(port)d, " + \
                "is carbon-agent.py running?" % { 'server':CARBON_SERVER, 
                'port':CARBON_PORT })
            sys.exit(1)


    def log(self, msg):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print msg
        fh = open(self.LOGFILE, "a")
        fh.write("%s %s\n" % (timestamp, str(msg)))
        fh.close()


    def run_once(self):
        now = int( time.time() )
        lines = []
        #We're gonna report all three loadavg values
        #loadavg = get_loadavg()
        temps = self.get_serial_data()
        #lines.append("system.loadavg_1min %s %d" % (loadavg[0], now))
        #lines.append("system.loadavg_5min %s %d" % (loadavg[1], now))
        #lines.append("system.loadavg_15min %s %d" % (loadavg[2], now))
        for temp in temps.keys():
            lines.append("fridge.%s %s %d" % (temp, temps[temp], now))
            
        message = '\n'.join(lines) + '\n' #all lines must end in a newline
        self.log("sending message")
        self.log('-'*50)
        self.log(message)
        self.send_msg(message)



 
if __name__ == "__main__":
    daemon = graphite_client()
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'test' == sys.argv[1]:
            daemon.run()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2) 


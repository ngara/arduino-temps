NateFridge.pde

Make commands:
make all       -- Compile NateFridge.pde
make upload    -- Upload to Arduino.  Requires that any device using ttyUSB0 
                  be disabled first.
make monitor   -- Use screen to see what's coming from ttyUSB0


Jobs:
Besides graphite, there is a cron job that runs every minute to collect data
/usr/local/bin/update_stats.sh

This script runs another script, "python /usr/local/bin/check_temps.py"
If uploading doesn't work, call:

sudo kill $(ps aux | grep '[p]ython /usr/local/bin/check_temps.py' | awk '{print $2}')

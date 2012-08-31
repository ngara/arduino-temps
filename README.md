arduino-temps
=============

Arduino code to read thermistors and report temperatures; Python code to read temperatures from Arduino and report to Graphite

The arduino folder contains the arduino.mk makefile as well as NateFridge, which is the code that reads thermistors and prints the values to serial output in decimal notation. 

* Thanks to Tim Marston for the Arduino Makefile code

* Thanks to the Arduino team for the thermistor calculation:
http://www.arduino.cc/playground/ComponentLib/Thermistor2

* Thanks to mem from the Arduino forum for the printDouble function:
http://www.arduino.cc/cgi-bin/yabb2/YaBB.pl?num=1207226548

graphite-client-initd-script goes in /etc/init.d as graphite-client
graphite-client.py goes into /opt/graphite/bin/
check-temps.py is a proof-of-concept for reading the data from serial



#include <math.h>

// define pin values
#define ledPin 13  // we don't want to use it on accident
#define heaterControlPin 10
#define fridgeControlPin 11
#define fridgePin 0
#define liquidPin 1
#define freezerPin 2
#define arduinoPin 3

#define numProbes 3
#define numAverages 3 // changed to 3 for median instead of average calc

double temp[numProbes];

// fridge, liquid, freezer, arduino
// Attempting to keep freezer at 46-50
// For brewing, attempt to keep fridge between 66-69
double minTemp[numProbes] = {0,66,46};
double maxTemp[numProbes] = {100,69,50};
int primaryProbe = 1; // Fridge water temp is primary

int turnAllOff=0;
int turnFridgeOn=0;
int turnHeaterOn=0;
int threshold=5;

// Function Prototypes
double Thermistor(int RawADC);
double median(double num1, double num2, double num3);
void readThermistors();
void checkTemperatures();
void switchHeaterOn();
void switchFridgeOn();
void switchAllOff();
void printDouble(double val, byte precision);
void printTemperatures();


// Function Definitions
double Thermistor(int RawADC) {
  double Temp;
  // When Thermistor is connected to ground, invert the reading
  RawADC = 1023 - RawADC;
  Temp = log(((10240000/RawADC) - 10000));
  Temp = 1 / (0.001129148 + (0.000234125 * Temp) + (0.0000000876741 * Temp * Temp * Temp));
  Temp = Temp - 273.15;            // Convert Kelvin to Celcius
  Temp = (Temp * 9.0)/ 5.0 + 32.0; // Convert Celcius to Fahrenheit
  return Temp;
}

double readThermistor(int probe) {
  double therm[3];

  // get median read from thermistors
  analogRead(probe); // read from pin and delay
  delay(100);    // to allow hardware to read accurately
  for( int j=0; j<3; j++ ) {
      therm[j] = Thermistor(analogRead(probe));
      delay(20);    // to allow hardware to read accurately
  }
  return median(therm[0], therm[1], therm[2]);
}


double median(double num1, double num2, double num3) {
    double temp;

    // if num1 is greater than num2, swap them
    if( num1 > num2 ) {
        temp = num1;
        num1 = num2;
        num2 = temp;
    }

    // if num1 is greater than num3, swap them
    if( num1 > num3 ) {
        temp = num1;
        num1 = num3;
        num3 = temp;
    }

    // if num2 is greater than num3, swap them
    if( num2 > num3 ) {
        temp = num2;
        num2 = num3;
        num3 = temp;
    }

    // return middle value
    return num2;
}


void checkTemperatures() {
  // Fridge temp controls thermostat
  // This is a voting system.  Every time
  // the temp goes above maxTemp, it resets
  // the opposite vote count and vice versa
  // when the vote hits threshold, it triggers
  // a turnRelayOff/turnRelayOn event.
  boolean greaterThanMax = false;
  boolean lessThanMin = false;

  // read and store temperatures
  for( int i=0; i<numProbes; i++ ) {
    temp[i] = readThermistor(i);
  }

  // now test primary probe
  if( temp[primaryProbe] > maxTemp[primaryProbe] ) {
    greaterThanMax = true;
  }
  if( temp[primaryProbe] < minTemp[primaryProbe] ) {
    lessThanMin = true;
  }

  // if no action on primary probe, determine what to do with secondary
  if( greaterThanMax!=true && lessThanMin!=true ) {
    for( int i=0; i<numProbes; i++ ) {
      if( i==primaryProbe ) continue;
      if( temp[i] > maxTemp[i] ) {
        greaterThanMax = true;
      }
      if( temp[i] < minTemp[i] ) {
        lessThanMin = true;
      }
    }
  }

  // take care of case where both are true--they cancel out
  if( greaterThanMax==true && lessThanMin==true ) {
    greaterThanMax = false;
    lessThanMin = false;
  }
  
  // let's vote.  Should we turn on heater or fridge?
  if( greaterThanMax==true ) { // Let's cool down
    if( turnFridgeOn <= threshold ) turnFridgeOn++;
    turnAllOff=0;
    turnHeaterOn=0;
  } else if( lessThanMin==true ) { // Let's heat up
    if( turnHeaterOn <= threshold ) turnHeaterOn++;
    turnAllOff=0;
    turnFridgeOn=0;
  } else {  // We're good
    if( turnAllOff <= threshold ) turnAllOff++;
    turnFridgeOn=0;
    turnHeaterOn=0;
  }
  
  // turn relay on or off
  if( turnAllOff==threshold ) {
    switchAllOff();
  } else if( turnHeaterOn==threshold ) {
    switchHeaterOn();
  } else if( turnFridgeOn==threshold ) {
    switchFridgeOn();
  }
}


void switchHeaterOn() {
  digitalWrite(fridgeControlPin, LOW);
  digitalWrite(heaterControlPin, HIGH);
}
void switchFridgeOn() {
  digitalWrite(fridgeControlPin, HIGH);
  digitalWrite(heaterControlPin, LOW);
}
void switchAllOff() {
  digitalWrite(fridgeControlPin, LOW);
  digitalWrite(heaterControlPin, LOW);
}

  
void printDouble( double val, byte precision) {
  // prints val with number of decimal places determine by precision
  // precision is a number from 0 to 6 indicating the desired decimial places
  // example: printDouble( 3.1415, 2); // prints 3.14 (two decimal places)

  Serial.print (int(val));  //prints the int part
  if( precision > 0) {
    Serial.print("."); // print the decimal point
    unsigned long frac;
    unsigned long mult = 1;
    byte padding = precision - 1;
    while(precision--)
      mult *= 10;

    if(val >= 0)
      frac = (val - int(val)) * mult;
    else
      frac = (int(val) - val) * mult;
    unsigned long frac1 = frac;
    while( frac1 /= 10 )
      padding--;
    while(  padding--)
      Serial.print("0");
    Serial.print(frac, DEC);
  }
}


void printTemperatures() {
  // print data to serial port
  
  // the average temp between fridge and 
  // freezer is plotted in the graph
  // as x degrees for off, x+5 degrees for on
  // this calculation keeps the plot inside 
  // the graph at all times while
  // still maintaining an obvious line for off and on
  Serial.print("fridge:");
  printDouble(temp[fridgePin],2); //decimal places
  Serial.print(" freezer:");
  printDouble(temp[freezerPin],2);
  Serial.print(" liquid:");
  printDouble(temp[liquidPin],2);
  if( numProbes > 3 ) {
    Serial.print(" arduino:");
    printDouble(temp[arduinoPin],2);
  }
  Serial.print(" heaterCtl:");
  Serial.print(digitalRead(heaterControlPin));
  Serial.print(" fridgeCtl:");
  Serial.print(digitalRead(fridgeControlPin));

  Serial.print(" f:");
  Serial.print(turnFridgeOn);
  Serial.print(" h:");
  Serial.print(turnHeaterOn);
  Serial.print(" a:");
  Serial.print(turnAllOff);

  Serial.println("");
}

void setup() {
  Serial.begin(9600);
  pinMode(heaterControlPin, OUTPUT);
  pinMode(fridgeControlPin, OUTPUT);
  switchAllOff(); // Turn fridge and heater off
}


void loop() {
  checkTemperatures();
  printTemperatures();
  delay(4000);
}


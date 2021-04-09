<link rel="stylesheet" href="./images/sj4u.css"></link>

# [STEM Just 4 U Home Page](https://stemjust4u.com/)
## This project collects ADC data from RPi with either MCP3008 or ADS1115 along with esp32 and its internal ADC. 

(Pi does not have internal ADC and requires an external MCP3008 or ADS1115)

ADC is analog-to-digital conversion. Analog components, microphone, joystick, battery, output their signal as a varying voltage [ie 0-3.3V, 0-5V]. An ADC is required to convert this to a digital [0-1] signal that can be quantified in your program.  esp32 has built-in ADC capability but the RPis do not (the pins on the RPi take digital, 0-1, input). However an external MCP3008 or ADS1115 ADC can be connected to the RPi and give it analog capability.

[Link to Project Web Site](https://github.com/stemjust4u/ADC)  

![ADC](images/ADCfalstad.gif#250sq-5rad)  
[Link to Falstad Circuit Simulator](http://www.falstad.com/circuit/)  
## Materials 
* MCP3008 (8 channels, 10-Bit [0-1023] using SPI interface)
* ADS1115  (4 channels, 16-Bit [0-65535] using I2C interface)
* RPi
* esp32 (8 channels, GPIOs 32-39, 12-Bit [0-4095])
* Analog components (I used 2-axis joystick and ntc thermistor for testing)
​​
### Pi0/PCA9685 Software Requirements​
In raspi-config make sure i2c is enabled (in the interface menu)  
`$ sudo apt install python-smbus`  
`$ sudo apt install i2c-tools`  
Once the ADS1115 is connected you can confirm the address is 0x48 (assuming address has not been changed) with i2cdetect command (searches /dev/i2c-1)  
`$ sudo i2cdetect -y 1`  
​Python packages are in requirements on github and include: setuptools, adafruit-blinka, adafruit-circuitpython-ads1x15

### Pi0/MCP3008 Software Requirements  
In raspi-config make sure spi is enabled (in the interface menu)
Python packages are in requirements on github and include: adafruit-circuitpython-mcp3xxx

**Adafruit_Blinka library provides the CircuitPython support in Python**

The voltage can be calculated from the raw ADC using the V reference (max Voltage the ADC can convert) and the ADC resolution (10, 12, 16 bit).   

Voltage measured = raw ADC X Vref/ADC resolution  
(note - the ADS1115 outputs a voltage and no conversion is needed)

So at 12bit and 3.3Vref  
a raw ADC value of 0:  0 x 3.3/4095 = 0V  
a raw ADC value of 4095: 4095 x 3.3/4095 = 3.3V  

An important consideration when using an ADC is if the voltage range you're measuring is within the allowable limits of the ADC/GPIO pins. If it is not within the limits a voltage divider is needed. (R2 = R1(1/(Vin/Vout-1))

The esp32 pins can only go up to 3.3V so you can not measure a signal greater than that. Projects measuring a 18650 battery (4.2V) require a voltage divider (R1=27k R2=100k) to bring the max voltage to 3.3V

>A function I use a lot for converting from one unit/range to another unit range is value mapping.
>Example with a 12 bit adc [0-4095] and 3.3 Vref [0-3.3]  
>value = raw value read from ADC  
>istart = 0        ostart = 0  
>istop = 4095  ostop = 3.3  
`def valmap(self, value, istart, istop, ostart, ostop):`  
    `return ostart + (ostop - ostart) * ((value - istart) / (istop - istart))`

# ADC

ADC involves converting a continuous time/amplitude analog signal to a discrete time/amplitude digital signal. Sampling rate and resolution are two important factors.

Sampling rate for ADS1115 ranges from 8 to 860 samples/second. MCP3008 is in the ksps. For simple STEM projects, reading a joystick, monitoring a battery, I have not had issues with sampling rates. When working with audio the sampling rate is critical (CD quality is 44.1ksps)

Resolution for the different ADC in this projects are listed below. Again, more than enough resolution for simple STEM projects.
MCP3008 (5Vref)= 10 bit or 1024 resolution (4.9mV steps)
esp32 (3.3Vref) = 12 bit or 4096 resolution (0.8mV steps)
ADS1115  = 16 bit or 65536 resolution

In the example below the Y-axis scale would be resolution (10 bit would have 1024 marks)
And the X-scale (time) would represent sampling. (# of samples per second)  
![ADC](images/Pcm.svg#250sq-5rad)  
[CC BY-SA 3.0](https://commons.wikimedia.org/w/index.php?curid=635225)

ADC converts an analog signal to digital. Its compliment is a DAC which converts the digital signal to analog (audio is another good example for this)  
![ADC](images/Conversion_AD_DA.png#300y)  
[By Megodenas - Own work, Public Domain](https://commons.wikimedia.org/w/index.php?curid=36972702)

>​In $ sudo raspi-config make sure SPI and/or I2C is enabled in the interface.  
Can confirm in $ sudo nano /boot/config.txt  
dtparam=i2c=on  
dtparam=spi=on  
## Rpi/MCP3008
SPI0 uses 4 pins, MOSI(Din), MISO(Dout), CLK and a CS (chip select) pin. For the CS the github code allows GPIO7 or 8. You can use either pin and pass it when creating the SPI object.

Initially I used 5V to power, Vdd, the MCP3008 and for Vref but you need to use a voltage divider on the MISO(Dout) to convert from 5V to 3.3V logic (RPi GPIO pin has 3.3V limit).
### If using the Joystick Button (switch) you will need to connect the switch (SW) to a GPIO pin. You have two options
1. Leave Vref at 5V and use another voltage divider to convert the switch down to 3.3V
2. Move Vref from 5V to 3.3V and connect the switch directly to a GPIO pin. (this is what I did). ** Don't forget to update the code to 3.3V for Vref when you create the mcp3008 object.  
![ADC](images/RPi-MCP3008-Joystick-Vdivider.png#300x-200y-5rad)
![ADC](images/RPi-MCP3008-Pin-Diagram.png#250x-200y-5rad)
#5rad)

## RPi/ADS1115  
The ADS1115 uses I2C interface so only 2 wires are required for the communication. Data (GPIO2) and Clock (GPIO3). The ADS1115 can run on the 3.3V or 5V (I confirmed the data/clock voltage is the same regardless if you use 3.3V or 5V). There is a gain setting that changes what voltage range you can measure.  
![ADC](images/RPI-ADS1115-Thermistor-Breadboard.png#250x-200y-5rad)

## esp32
For esp32 GPIO32-39 can be used for ADC. (max voltage you can measure is 3.3V)  
![ADC](images/ADC-joystick-ESP32.png#300x-200y-5rad)

You load the upython scripts /main.py, /boot.py, /adc.py, /umqttsimply.py on to the esp32.  [Directions using Thonny](https://stemjust4u.com/esp32-esp8266)

### MQTT Explorer  
MQTT Explorer is a great tool for watching messages between your clients and broker. You can also manually enter a topic and send a msg to test your code. This is useful for first setting up your code and trouble shooting.

# Code
​​The external ADC require python packages installed with pip3.  
MCP3008: adafruit-circuitpython-mcp3xxx  
ADS1115: adafruit-circuitpython-ads1x15  
(and these require adafruit-blinka)    

MQTT is used to communicate readings to a node-red server.
A max time delay is used to force a reading.

RPi
/ADCmqtt.py (uncomment which ADC you're using, MCP3008 or ADS1115)  
|-/adc  
|    |-MadcADS1115_4CH.py (ads1115 module)  
|    |-MadcMCP3008_8CH.py (mcp3008 module)  

/ADCmqtt_Joystick.py  (uses MCP3008 to read joystick movement including button)
![ADC](images/mqtt-joystick.png#300x-200y-5rad)  
For mcp3008: adc = mcp3008(2, 5, 400, 1, 8) # numOfChannels, vref, noiseThreshold, max time interval, chip select 

/ADCmqtt_ntcThermistor.py  (uses ADS1115 to output Temp from ntc thermistor)
![ADC](images/mqtt-thermistor.png#300x-200y-5rad)  

For ads1115: adc = ads1115(1, 0.001, 1, 1) # numOfChannels, noiseThreshold, max time interval, Gain  

Gain options. Set the gain to capture the voltage range being measured.  
|PGA setting |FS (V)|  
|------------|-------|
|2/3 |+/- 6.144  |
|1 |+/- 4.096  |
|2 |+/- 2.048  |
|4 |+/- 1.024  |
|8 |+/- 0.512  |
|16 |+/- 0.256  |
 

For esp32  
/upython/main.py (and adc, boot, umqttsimple files)  

adc = espADC(2, 3.3, 40, 1) # Create adc object. Pass numOfChannels, vref, noiseThreshold=35, max Interval = 1  

The GPIO pins used for ADC have to be updated in the init of /adc.py module.

**A function was added to monitor a joystick button press on pin 4**

# Node Red
[Link to General MQTT-Node-Red Setup](https://stemjust4u.com/mqtt-influxdb-nodered-grafana)  

Node red flow is in github or at bottom of project web site.  
[ADC Project Web Site](https://stemjust4u.com/adc)

![Node Red](images/nodered-realtime-graphs.gif#200x-150y-5rad) 
![Node Red](images/nodered-ntc.gif#100x-150y-5rad) 

Grafana Charts  
![Node Red](images/grafana-js-ntc.png#500x-150y)  

![Node Red](images/nodered-ADC-plotter.png#500x-150y)  

import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
from machine import Pin
from time import sleep
import ujson
from adc import espADC
esp.osdebug(None)
import gc
gc.collect()

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('woke from a deep sleep')

with open("stem", "rb") as f:
  user_info = f.read().splitlines()

MQTT_SERVER = '10.0.0.115'
MQTT_USER = user_info[0] 
MQTT_PASSWORD = user_info[1] 
MQTT_SUB_TOPIC1 = b'espJoystick/motion/all'
MQTT_PUB_TOPIC1 = b'espJoystick/motion/XY'
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
WIFI_SSID = user_info[2]
WIFI_PASSWORD = user_info[3]

buttonpressed = False
outgoingD, incomingD = {}, {}
newmsg = True

#=== HARDWARE SETUP =====#
# ADC is on pins 4,12-15,25-27,32-35,36,39
pinlist = [34, 35]
adc = espADC(pinlist, 3.3, 40, 1)    # Create adc object. Pass numOfChannels, vref, noiseThreshold=35, max Interval = 1
buttonpin = 4 
button = Pin(buttonpin, Pin.IN, Pin.PULL_UP)  # Create button
def handle_interrupt(pin):    # Create handle interrupt function to update when button pressed
    global buttonpressed
    buttonpressed = True
button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=handle_interrupt) # link interrupt handler to function for pin falling or rising

station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(WIFI_SSID, WIFI_PASSWORD)

while station.isconnected() == False:
  pass

print('Connection successful')
print(station.ifconfig())

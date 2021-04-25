import micropython
import gc
from umqttsimple import MQTTClient
import network
import ujson
import ubinascii
from time import sleep
import time
from machine import Pin
import machine
from lib.adc import espADC
gc.collect()
micropython.alloc_emergency_exception_buf(100)

if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('woke from a deep sleep')

with open("stem", "rb") as f:
  user_info = f.read().splitlines()

MQTT_SERVER = '10.0.0.115'
MQTT_USER = user_info[0] 
MQTT_PASSWORD = user_info[1] 
MQTT_SUB_TOPIC1 = b'nred2esp/motion/all'

MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())

MQTT_PUB_TOPIC1 = b'esp2nred/adc/esp23'

WIFI_SSID = user_info[2]
WIFI_PASSWORD = user_info[3]

buttonpressed = False
outgoingD, incomingD = {}, {}
newmsg = True

#=== HARDWARE SETUP =====#
# ADC is on pins 4,12-15,25-27,32-35,36,39
pinlist = [34]
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

def on_message(topic, msg):
    #print("Topic %s msg %s ESP Subscribed to %s" % (topic, msg, MQTT_SUB_TOPIC1))
    global newmsg, incomingD
    if topic == MQTT_SUB_TOPIC1:
        incomingD = ujson.loads(msg.decode("utf-8", "ignore")) # decode json data to dictionary
        newmsg = True
        #Uncomment prints for debugging. Will print the JSON incoming payload and unpack the converted dictionary
        #print("Received topic(tag): {0}".format(topic))
        #print("JSON payload: {0}".format(msg.decode("utf-8", "ignore")))
        #print("Unpacked dictionary (converted JSON>dictionary)")
        #for key, value in incomingD.items():
        #  print("{0}:{1}".format(key, value))
      
def connect_and_subscribe():
    global MQTT_CLIENT_ID, MQTT_SERVER, MQTT_SUB_TOPIC1
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASSWORD)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(MQTT_SUB_TOPIC1)
    print('Connected to %s MQTT broker, subscribed to %s topic' % (MQTT_SERVER, MQTT_SUB_TOPIC1))
    return client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    sleep(10)
    machine.reset()

try:
    mqtt_client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()
  
#=== MAIN LOOP =======#
# MQTT setup is successful. Publish generic status confirmation easily seen on MQTT Explorer
# and blink led
mqtt_client.publish(b"status", b"esp32 connected, entering main loop")
pin = 2
led = Pin(pin, Pin.OUT) #2 is the internal LED
led.value(1)
sleep(1)
led.value(0)  # flash led to know main loop starting

while True:
  try:
    mqtt_client.check_msg()
    if newmsg:                 # Place holder if wanting to receive message/instructions
      newmsg = False
    voltage = adc.getValue()
    if buttonpressed or voltage is not None:         # Update if button pressed or voltage changed or time limit hit
      if voltage is not None:
        for i,pin in enumerate(voltage):
          outgoingD['a' + str(i) + 'f'] = str(voltage[i])             # Get the voltage of each channel
      outgoingD['buttoni'] = str(button.value())
      buttonpressed = False
      mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))  # Convert to JSON and publish voltage of each channel
      #Uncomment prints for debugging. 
      #print(ujson.dumps(outgoingD))
      #print("JSON payload: {0}\n".format(ujson.dumps(outgoingD)))
  except OSError as e:
    restart_and_reconnect()

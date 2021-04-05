#!/usr/bin/env python3
# This MCP3008 adc is multi channel.  If any channel has a delta (current-previous) that is above the
# noise threshold then the voltage from all channels will be returned.
# MQTT version has a publish section in the main code to test MQTT ability stand alone
import os, busio, digitalio, board, sys, re, json
from time import time, sleep
import paho.mqtt.client as mqtt
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from os import path
from pathlib import Path

class ads1115:
  def __init__(self, numOfChannels, vref, sampleInterval=1, noiseThreshold=0.001, numOfSamples= 10):
    self.vref = vref
    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)
    # Create the ADC object using the I2C bus
    ads = ADS.ADS1115(i2c)
    #ads.gain = 2/3
    self.numOfChannels = numOfChannels
    self.chan = [AnalogIn(ads, ADS.P0), # create analog input channel on pins
                 AnalogIn(ads, ADS.P1),
                 AnalogIn(ads, ADS.P2),
                 AnalogIn(ads, ADS.P3)]
    self.noiseThreshold = noiseThreshold
    self.sensorChanged = False
    self.numOfSamples = numOfSamples
    self.sensorAve = [x for x in range(self.numOfChannels)]
    self.sensorLastRead = [x for x in range(self.numOfChannels)]
    for x in range(self.numOfChannels): # initialize the first read for comparison later
      self.sensorLastRead[x] = self.chan[x].value
    self.adcValue = [x for x in range(self.numOfChannels)]
    self.sensor = [[x for x in range(0, self.numOfSamples)] for x in range(0, self.numOfChannels)]
    self.sampleInterval = sampleInterval  # interval in seconds to check for update
    self.time0 = time()   # time 0
    
  def valmap(self, value, istart, istop, ostart, ostop):
    return ostart + (ostop - ostart) * ((value - istart) / (istop - istart))

  def getValue(self):
    if time() - self.time0 > self.sampleInterval:
      self.time0 = time()
      for x in range(self.numOfChannels):
        for i in range(self.numOfSamples):  # get samples points from analog pin and average
          self.sensor[x][i] = self.chan[x].voltage
        self.sensorAve[x] = sum(self.sensor[x])/len(self.sensor[x])
        if abs(self.sensorAve[x] - self.sensorLastRead[x]) > self.noiseThreshold:
          self.sensorChanged = True
        self.sensorLastRead[x] = self.sensorAve[x]
        self.adcValue[x] = self.sensorAve[x]
        #print('chan: {0} value: {1:1.2f}'.format(x, self.adcValue[x]))
      if self.sensorChanged:
        self.adcValue = ["%.2f"%pin for pin in self.adcValue] #format and send final adc results
        self.sensorChanged = False
        return self.adcValue
      
if __name__ == "__main__":
    #=======   SETUP MQTT =================#
    # Import mqtt and wifi info. Remove if hard coding in python file
    home = str(Path.home())
    with open(path.join(home, "stem"),"r") as f:
        stem = f.read().splitlines()

    #=======   SETUP MQTT =================#
    MQTT_SERVER = '10.0.0.115'                    # Replace with IP address of device running mqtt server/broker
    MQTT_USER = stem[0]                           # Replace with your mqtt user ID
    MQTT_PASSWORD = stem[1]                       # Replace with your mqtt password
    MQTT_CLIENT_ID = 'RPi'
    MQTT_PUB_TOPIC1 = 'RPi/ads1115/all'

    def on_connect(client, userdata, flags, rc):
        """ on connect callback verifies a connection established and subscribe to TOPICs"""
        print("attempting on_connect")
        if rc==0:
            mqtt_client.connected = True          # If rc = 0 then successful connection
            client.subscribe(MQTT_SUB_TOPIC1)      # Subscribe to topic
            print("Successful Connection: {0}".format(str(rc)))
            print("Subscribed to: {0}\n".format(MQTT_SUB_TOPIC1))
        else:
            mqtt_client.failed_connection = True  # If rc != 0 then failed to connect. Set flag to stop mqtt loop
            print("Unsuccessful Connection - Code {0}".format(str(rc)))

    def on_message(client, userdata, msg):
        """on message callback will receive messages from the server/broker. Must be subscribed to the topic in on_connect"""
        global newmsg, incomingD
        if msg.topic == MQTT_SUB_TOPIC1:
            incomingD = json.loads(str(msg.payload.decode("utf-8", "ignore")))  # decode the json msg and convert to python dictionary
            newmsg = True
            #Uncomment prints for debugging. Will print the JSON incoming payload and unpack the converted dictionary
            #print("Receive: msg on subscribed topic: {0} with payload: {1}".format(msg.topic, str(msg.payload))) 
            #print("Incoming msg converted (JSON->Dictionary) and unpacking")
            #for key, value in incomingD.items():
            #    print("{0}:{1}".format(key, value))

    def on_publish(client, userdata, mid):
        """on publish will send data to client"""
        #Uncomment prints for debugging. Will unpack the dictionary and then the converted JSON payload
        #print("msg ID: " + str(mid)) 
        #print("Publish: Unpack outgoing dictionary (Will convert dictionary->JSON)")
        #for key, value in outgoingD.items():
        #    print("{0}:{1}".format(key, value))
        #print("Converted msg published on topic: {0} with JSON payload: {1}\n".format(MQTT_PUB_TOPIC1, json.dumps(outgoingD))) # Uncomment for debugging. Will print the JSON incoming msg
        pass # DO NOT COMMENT OUT

    def on_disconnect(client, userdata,rc=0):
        logging.debug("DisConnected result code "+str(rc))
        mqtt_client.loop_stop()

    #==== start/bind mqtt functions ===========#
    # Create a couple flags to handle a failed attempt at connecting. If user/password is wrong we want to stop the loop.
    mqtt.Client.connected = False          # Flag for initial connection (different than mqtt.Client.is_connected)
    mqtt.Client.failed_connection = False  # Flag for failed initial connection
    # Create our mqtt_client object and bind/link to our callback functions
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID) # Create mqtt_client object
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD) # Need user/password to connect to broker
    mqtt_client.on_connect = on_connect    # Bind on connect
    mqtt_client.on_message = on_message    # Bind on message
    mqtt_client.on_publish = on_publish    # Bind on publish
    print("Connecting to: {0}".format(MQTT_SERVER))
    mqtt_client.connect(MQTT_SERVER, 1883) # Connect to mqtt broker. This is a blocking function. Script will stop while connecting.
    mqtt_client.loop_start()               # Start monitoring loop as asynchronous. Starts a new thread and will process incoming/outgoing messages.
    # Monitor if we're in process of connecting or if the connection failed
    while not mqtt_client.connected and not mqtt_client.failed_connection:
        print("Waiting")
        sleep(1)
    if mqtt_client.failed_connection:      # If connection failed then stop the loop and main program. Use the rc code to trouble shoot
        mqtt_client.loop_stop()
        sys.exit()

    # MQTT setup is successful. Initialize dictionaries and start the main loop.

    adc = ads1115(2, 5, 0.1, 0.001) # numOfChannels, vref, delay, noiseThreshold
    outgoingD = {}
    incomingD = {}
    newmsg = True
    while True:
      voltage = adc.getValue() # returns a list with the voltage for each pin that was passed in ads1115
      if voltage is not None:
        i = 0
        for pin in voltage:                               # create dictionary with voltage from each pin
          outgoingD['a' + str(i) + 'f'] = str(voltage[i])  # key=pin:value=voltage 
          i += 1                                          # will convert dict-to-json for easy MQTT publish of all pin at once
        mqtt_client.publish(MQTT_PUB_TOPIC1, json.dumps(outgoingD))       # publish voltage values

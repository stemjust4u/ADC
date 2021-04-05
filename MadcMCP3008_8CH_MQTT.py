#!/usr/bin/env python3
# This MCP3008 adc is multi channel.  If any channel has a delta (current-previous) that is above the
# noise threshold then the voltage from all channels will be returned.
# MQTT version has a publish section in the main code to test MQTT ability stand alone

import os, busio, digitalio, board, sys, re, json
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
from time import time
import paho.mqtt.client as mqtt

class mcp3008:
  def __init__(self, numOfChannels, vref, sampleInterval=1, noiseThreshold=350, numOfSamples= 10):
    self.vref = vref
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI) # create the spi bus
    cs = digitalio.DigitalInOut(board.D22) # create the cs (chip select)
    mcp = MCP.MCP3008(spi, cs) # create the mcp object
    self.numOfChannels = numOfChannels
    self.chan = [AnalogIn(mcp, MCP.P0), # create analog input channel on pins
                 AnalogIn(mcp, MCP.P1),
                 AnalogIn(mcp, MCP.P2),
                 AnalogIn(mcp, MCP.P3),
                 AnalogIn(mcp, MCP.P4),
                 AnalogIn(mcp, MCP.P5),
                 AnalogIn(mcp, MCP.P6),
                 AnalogIn(mcp, MCP.P7)]
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
          self.sensor[x][i] = self.chan[x].value
        self.sensorAve[x] = sum(self.sensor[x])/len(self.sensor[x])
        if abs(self.sensorAve[x] - self.sensorLastRead[x]) > self.noiseThreshold:
          self.sensorChanged = True
        self.sensorLastRead[x] = self.sensorAve[x]
        self.adcValue[x] = self.valmap(self.sensorAve[x], 0, 65535, 0, self.vref) # 4mV change is approx 500
        #print('chan: {0} value: {1:1.2f}'.format(x, self.adcValue[x]))
      if self.sensorChanged:
        self.adcValue = ["%.2f"%pin for pin in self.adcValue] #format and send final adc results
        self.sensorChanged = False
        return self.adcValue
      
if __name__ == "__main__":
    #=======   SETUP MQTT =================#
    MQTT_ADDRESS = '10.0.0.22'
    MQTT_TOPIC = 'countchocula/mcp3008/+'  # + means one or more occurrence
    MQTT_REGEX = 'countchocula/([^/]+)/([^/]+)'  #regular expression.  ^ means start with
    MQTT_CLIENT_ID = 'countchocula'
    topic_pub = 'countchocula/mcp3008/all'

    # create call back functions and then link them to the mqtt callback below in main program
    def on_connect(client, userdata, flags, rc):
        """ The callback for when the client receives a CONNACK response from the server."""
        print('Connected with result code ' + str(rc))  #str() returns the nicely printable representation of a given object.
        client.subscribe(MQTT_TOPIC)

    #on message will receive data from client 
    def on_message(client, userdata, msg):
        """The callback for when a PUBLISH message is received from the server."""
        print(msg.topic + ' ' + str(msg.payload))

    #on publish will send data to client
    def on_publish(client, userdata, mid):
        print("mid: "+str(mid))

    #==== start mqtt functions ===========#
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
    # mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect  #bind call back function
    mqtt_client.on_message = on_message  #bind function to be used when PUBLISH messages are found
    mqtt_client.on_publish = on_publish  #bind function for publishing
    mqtt_client.connect(MQTT_ADDRESS, 1883)  # connect to the mqtt
    mqtt_client.loop_start()   # other option is client.loop_forever() but it is blocking

    adc = mcp3008(2, 5, 0.1, 350) # numOfChannels, vref, delay, noiseThreshold
    mcp3008D = {}
    while True:
      voltage = adc.getValue() # returns a list with the voltage for each pin that was passed in mcp3008
      if voltage is not None:
        i = 0
        for pin in voltage:                               # create dictionary with voltage from each pin
          mcp3008D['a' + str(i) + 'f'] = str(voltage[i])  # key=pin:value=voltage 
          i += 1                                          # will convert dict-to-json for easy MQTT publish of all pin at once
        mcp3008MQTT = json.dumps(mcp3008D)                # convert dictionary to json
        mqtt_client.publish(topic_pub, mcp3008MQTT)       # publish voltage values

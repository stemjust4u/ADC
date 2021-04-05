#!/usr/bin/env python3
''' This MCP3008 adc is multi channel.  If any channel has a delta (current-previous) that is above the
noise threshold then the voltage from all channels will be returned.
'''

import os, busio, digitalio, board, sys, re, json
from time import time, sleep
import paho.mqtt.client as mqtt
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from os import path
from pathlib import Path

class ads1115wTime:
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
    
    adc = ads1115wTime(1, 5, 1, 0.001) # numOfChannels, vref, noiseThreshold
    outgoingD = {}
    while True:
        voltage = adc.getValue() # returns a list with the voltage for each pin that was passed in ads1115
        if voltage is not None:
        i = 0
        for pin in voltage:                               # create dictionary with voltage from each pin
            outgoingD['a' + str(i) + 'f'] = str(voltage[i])  # key=pin:value=voltage 
            i += 1
        print(outgoingD)

#!/usr/bin/env python3
''' This MCP3008 adc is multi channel.  If any channel has a delta (current-previous) that is above the
noise threshold then the voltage from all channels will be returned.
'''

import busio, board, logging
from time import sleep
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

class ads1115:
    ''' ADC using ADS1115 (I2C). Returns a list with voltge values '''
    def __init__(self, numOfChannels, vref, noiseThreshold=0.001, numOfSamples= 10):
        self.vref = vref
        i2c = busio.I2C(board.SCL, board.SDA)  # Create the I2C bus
        ads = ADS.ADS1115(i2c)   # Create the ADC object using the I2C bus
        #ads.gain = 2/3
        self.numOfChannels = numOfChannels
        self.chan = [AnalogIn(ads, ADS.P0), # create analog input channel on pins
                     AnalogIn(ads, ADS.P1),
                     AnalogIn(ads, ADS.P2),
                     AnalogIn(ads, ADS.P3)]
        self.noiseThreshold = noiseThreshold
        self.numOfSamples = 10        # Number of samples to average
        # Initialize lists
        self.sensorAve = [x for x in range(self.numOfChannels)]
        self.sensorLastRead = [x for x in range(self.numOfChannels)]
        self.adcValue = [x for x in range(self.numOfChannels)]
        self.sensor = [[x for x in range(0, self.numOfSamples)] for x in range(0, self.numOfChannels)]
        for x in range(self.numOfChannels): # initialize the first read for comparison later
            self.sensorLastRead[x] = self.chan[x].value

    def getValue(self):
        sensorChanged = False
        for x in range(self.numOfChannels):
            for i in range(self.numOfSamples):  # get samples points from analog pin and average
                self.sensor[x][i] = self.chan[x].voltage
            self.sensorAve[x] = sum(self.sensor[x])/len(self.sensor[x])
            if abs(self.sensorAve[x] - self.sensorLastRead[x]) > self.noiseThreshold:
                sensorChanged = True
                logging.debug('changed: {0} chan: {1} value: {2:1.2f} previously: {3:1.2f}'.format(sensorChanged, x, self.sensorAve[x], self.sensorLastRead[x]))
            self.adcValue[x] = self.sensorAve[x]            
            self.sensorLastRead[x] = self.sensorAve[x]
            #logging.debug('chan: {0} value: {1:1.2f}'.format(x, self.adcValue[x]))
        if sensorChanged:
            self.adcValue = ["%.2f"%pin for pin in self.adcValue] #format and send final adc results
            return self.adcValue
        else:
            pass
      
if __name__ == "__main__":
    
    adc = ads1115(1, 5, 0.001) # numOfChannels, vref, noiseThreshold
    outgoingD = {}
    while True:
        voltage = adc.getValue() # returns a list with the voltage for each pin that was passed in ads1115
        if voltage is not None:
            i = 0
            for pin in voltage:                               # create dictionary with voltage from each pin
                outgoingD['a' + str(i) + 'f'] = str(voltage[i])  # key=pin:value=voltage 
                i += 1
            print(outgoingD)
            sleep(.05)

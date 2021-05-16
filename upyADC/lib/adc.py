''' esp32 ADC.  If any channel has a delta (current-previous) that is above the
noise threshold or if the max Time interval exceeded then the 
voltage from all initialized channels will be returned.
 When creating object, pass: pins, Vref, noise threshold, and max time interval
 Will return a list with the voltage value for each channel.

To find the noise threshold set noise threshold low and max time interval low.
Noise is in raw ADC

Max time interval is used to catch drift/creep that is below the noise threshold.

'''

from machine import Pin, ADC
import utime, ulogging
from timer import TimerFunc

class espADC:
    def __init__(self, pinlist, vref=3.3, noiseThreshold=35, maxInterval=1000, logger=None):
        self.vref = vref
        self.numOfChannels = len(pinlist)
        if logger is not None:                         # Use logger passed as argument
            self.logger = logger
        else:                                          # Root logger already exists and no custom logger passed
            self.logger = ulogging.getLogger(__name__) # Create from root logger
        self.logger.info("ADC setting up {0} channels. Vref:{1} NoiseTh:{2} MaxIntvl:{3}sec".format(self.numOfChannels, vref, noiseThreshold, maxInterval/1000))
        self.chan = []
        for i, pin in enumerate(pinlist):
            self.chan.append(ADC(Pin(pin)))
            self.chan[i].atten(ADC.ATTN_11DB) # Full range: 0-3.3V
        self.logger.info("ADC setup:{0}".format(self.chan))   
        self.noiseThreshold = noiseThreshold
        self.numOfSamples = 3
        self.sensorAve = [x for x in range(self.numOfChannels)]
        self.sensorLastRead = [x for x in range(self.numOfChannels)]
        for x in range(self.numOfChannels): # initialize the first read for comparison later
            self.sensorLastRead[x] = self.chan[x].read()
        self.voltage = {}
        self.sensor = [[x for x in range(0, self.numOfSamples)] for x in range(0, self.numOfChannels)]
        self.maxInterval = maxInterval # interval in ms to check for update
        self.time0 = utime.ticks_ms()   # time 0
    
    def _valmap(self, value, istart, istop, ostart, ostop):
        return ostart + (ostop - ostart) * ((value - istart) / (istop - istart))

    #@TimerFunc  # Can uncomment to see how long it takes to get readings
    def getdata(self):
        sensorChanged = False
        timelimit = False
        if utime.ticks_diff(utime.ticks_ms(), self.time0) > self.maxInterval:
            timelimit = True
        for x in range(self.numOfChannels):
            for i in range(self.numOfSamples):  # get samples points from analog pin and average
                self.sensor[x][i] = self.chan[x].read()
                #self.logger.debug("chan:{0} raw:{1}".format(x, self.sensor[x][i]))
            self.sensorAve[x] = sum(self.sensor[x])/len(self.sensor[x])
            if abs(self.sensorAve[x] - self.sensorLastRead[x]) > self.noiseThreshold:
                sensorChanged = True
            #self.logger.debug("delta from last read: {0}".format(self.sensorAve[x] - self.sensorLastRead[x]))
            self.sensorLastRead[x] = self.sensorAve[x]
            self.voltage['a' + str(x) + 'f'] = self._valmap(self.sensorAve[x], 0, 4095, 0, self.vref) # 4mV change is approx 500
            #self.logger.debug("chan:{0} V:{1}".format(x, self.voltage))
        if sensorChanged or timelimit:
            self.time0 = utime.ticks_ms()
            return self.voltage

if __name__ == "__main__":
    import time
    # Run main loop
    pinlist = [34, 35]
    adc = espADC(pinlist, 3.3, 40, 10000, setupinfo=True, debuginfo=True)
    while True:
        print(adc.getdata())
        time.sleep(1)
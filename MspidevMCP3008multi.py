''' Uses spidev to output ADC values for multi channels 
  Just pass number of channels measuring 

'''

import spidev
from time import sleep, time

spi = spidev.SpiDev()
spi.open(0, 0)  # bus 0, the second 0 can be 0 or 1 for CS0 or CS1.. can have multiple devices
spi.max_speed_hz = 1000000

class mcp3008:
    def __init__(self, numOfChannels):
      self.numOfChannels = numOfChannels
      self.r = [x for x in range(self.numOfChannels)]
      self.adcOut = [x for x in range(self.numOfChannels)]
      
    def readValue(self):
      for channel in range(self.numOfChannels):
        self.r[channel] = spi.xfer([1, (8+channel) << 4, 0])
        self.adcOut[channel] = ((self.r[channel][1]&3) << 8) + self.r[channel][2]
        #percent = int(round(adcOut/10.24))
      return self.adcOut

if __name__ == "__main__":
    checkInterval = 0.1
    time0 = time()
    joystick = mcp3008(2)
    while True:
      if time() - time0 > checkInterval:
        print(joystick.readValue())
        time0 = time()

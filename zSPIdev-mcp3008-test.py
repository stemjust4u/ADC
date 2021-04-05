''' Quick routine using spidev to plot ADC values '''

import spidev
from time import sleep

spi = spidev.SpiDev()
spi.open(0, 0)  # bus 0, the second 0 can be 0 or 1 for CS0 or CS1.. can have multiple devices
spi.max_speed_hz = 1000000

def getADC(channel0, channel1):
  r0 = spi.xfer([1, (8+channel0) << 4, 0])
  adcOut0 = ((r0[1]&3) << 8) + r0[2]
  r1 = spi.xfer([1, (8+channel1) << 4, 0])
  adcOut1 = ((r1[1]&3) << 8) + r1[2]
  #percent = int(round(adcOut/10.24))
  print("channel 0 {0:4d} channel 1 {1:4d}".format (adcOut0,adcOut1))
  sleep(0.1)
  
while True:
  getADC(0, 1)

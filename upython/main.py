from machine import Pin, ADC
from time import sleep
import utime, ujson

class espADC:
  def __init__(self, numOfChannels, vref, sampleInterval=0.1, noiseThreshold=35, numOfSamples= 10):
    self.vref = vref
    self.numOfChannels = numOfChannels
    self.chan = [x for x in range(self.numOfChannels)]
    self.chan[0] = ADC(Pin(35))
    self.chan[1] = ADC(Pin(34))
    self.chan[0].atten(ADC.ATTN_11DB) # Full range: 0-3.3V
    self.chan[1].atten(ADC.ATTN_11DB) # Full range: 0-3.3V   
    self.noiseThreshold = noiseThreshold
    self.sensorChanged = False
    self.numOfSamples = numOfSamples
    self.sensorAve = [x for x in range(self.numOfChannels)]
    self.sensorLastRead = [x for x in range(self.numOfChannels)]
    for x in range(self.numOfChannels): # initialize the first read for comparison later
      self.sensorLastRead[x] = self.chan[x].read()
    self.adcValue = [x for x in range(self.numOfChannels)]
    self.sensor = [[x for x in range(0, self.numOfSamples)] for x in range(0, self.numOfChannels)]
    self.sampleInterval = sampleInterval * 1000000  # interval in seconds to check for update
    self.time0 = utime.ticks_us()   # time 0
    
  def valmap(self, value, istart, istop, ostart, ostop):
    return ostart + (ostop - ostart) * ((value - istart) / (istop - istart))

  def getValue(self):
    if utime.ticks_us() - self.time0 > self.sampleInterval:
      self.time0 = utime.ticks_us()
      for x in range(self.numOfChannels):
        for i in range(self.numOfSamples):  # get samples points from analog pin and average
          self.sensor[x][i] = self.chan[x].read()
        self.sensorAve[x] = sum(self.sensor[x])/len(self.sensor[x])
        #print(abs(self.sensorAve[x] - self.sensorLastRead[x]))
        if abs(self.sensorAve[x] - self.sensorLastRead[x]) > self.noiseThreshold:
          self.sensorChanged = True
          #print(self.sensorAve[x] - self.sensorLastRead[x])
        self.sensorLastRead[x] = self.sensorAve[x]
        self.adcValue[x] = self.valmap(self.sensorAve[x], 0, 4095, 0, self.vref) # 4mV change is approx 500
        #print('chan: {0} value: {1:1.2f}'.format(x, self.adcValue[x]))
      if self.sensorChanged:
        self.adcValue = ["%.2f"%pin for pin in self.adcValue] #format and send final adc results
        self.sensorChanged = False
        return self.adcValue

if __name__ == "__main__":
    
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

  # MQTT setup is successful.
  # Publish generic status confirmation easily seen on MQTT Explorer
  # Initialize dictionaries and start the main loop.
  mqtt_client.publish(b"status", b"esp32 connected, entering main loop")
  pin = 2
  led = Pin(pin, Pin.OUT) #2 is the internal LED
  led.value(1)
  sleep(1)
  led.value(0)  # flash led to know main loop starting
  outgoingD = {}
  incomingD = {}
  newmsg = True
  adc = espADC(2, 3.3, 0.1, 40)    # Create adc object. Pass numOfChannels, vref, sampleInterval=0.1, noiseThreshold=35, numOfSamples= 10
  while True:
      try:
        mqtt_client.check_msg()
        if newmsg:                 # Place holder if wanting to receive message/instructions
          newmsg = False
        voltage = adc.getValue()
        if voltage is not None:                                         # Only update if voltage has changed (ie if joystick moved or battery voltage changed)
          i = 0
          for pin in voltage:
            outgoingD['a' + str(i) + 'f'] = str(voltage[i])             # Get the voltage of each channel
            i += 1
          mqtt_client.publish(MQTT_PUB_TOPIC1, ujson.dumps(outgoingD))  # Convert to JSON and publish voltage of each channel
          #Uncomment prints for debugging. 
          #print(ujson.dumps(outgoingD))
          #print("JSON payload: {0}\n".format(ujson.dumps(outgoingD)))
      except OSError as e:
        restart_and_reconnect()

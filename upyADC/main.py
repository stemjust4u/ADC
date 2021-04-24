micropython.alloc_emergency_exception_buf(100)

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

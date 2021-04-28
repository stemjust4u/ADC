import utime, ubinascii, micropython, network, re, ujson
from lib.umqttsimple import MQTTClient
from machine import Pin, PWM
import gc
gc.collect()
micropython.alloc_emergency_exception_buf(100)

def connect_wifi(WIFI_SSID, WIFI_PASSWORD):
    station = network.WLAN(network.STA_IF)

    station.active(True)
    station.connect(WIFI_SSID, WIFI_PASSWORD)

    while station.isconnected() == False:
        pass

    print('Connection successful')
    print(station.ifconfig())

def mqtt_setup(IPaddress):
    global MQTT_CLIENT_ID, MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, MQTT_SUB_TOPIC, MQTT_REGEX
    with open("stem", "rb") as f:    # Remove and over-ride MQTT/WIFI login info below
      stem = f.read().splitlines()
    MQTT_SERVER = IPaddress   # Over ride with MQTT/WIFI info
    MQTT_USER = stem[0]         
    MQTT_PASSWORD = stem[1]
    WIFI_SSID = stem[2]
    WIFI_PASSWORD = stem[3]
    MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
    MQTT_SUB_TOPIC = []
    # Specific MQTT_SUB_TOPICS for ADC, servo, stepper are .appended below
    MQTT_REGEX = rb'nred2esp/([^/]+)/([^/]+)' # b'txt' is binary format. Required for umqttsimple to save memory
                                              # r'txt' is raw format for easier reg ex matching
                                              # 'nred2esp/+' would also work but would not return groups
                                              # () group capture. Useful for getting topic lvls in on_message
                                              # [^/] match a char except /. Needed to get topic lvl2, lvl3 groups
                                              # + will match one or more. Requiring at least 1 match forces a lvl1/lvl2/lvl3 topic structure
                                              # * could also be used for last group and then a lvl1/lvl2 topic would also be matched

def mqtt_connect_subscribe():
    global MQTT_CLIENT_ID, MQTT_SERVER, MQTT_SUB_TOPIC, MQTT_USER, MQTT_PASSWORD
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER, user=MQTT_USER, password=MQTT_PASSWORD)
    client.set_callback(mqtt_on_message)
    client.connect()
    print('(CONNACK) Connected to {0} MQTT broker'.format(MQTT_SERVER))
    for topics in MQTT_SUB_TOPIC:
        client.subscribe(topics)
        print('Subscribed to {0}'.format(topics)) 
    return client

def mqtt_on_message(topic, msg):
    print("on_message Received - topic:{0} payload:{1}".format(topic, msg.decode("utf-8", "ignore")))

def mqtt_reset():
    print('Failed to connect to MQTT broker. Reconnecting...')
    utime.sleep_ms(5000)
    machine.reset()

def create_adc(pinlist, switch, switchON=False):
    global MQTT_SUB_TOPIC, device, outgoingD, buttonADC_pressed, buttonADC
    from adc import espADC
    MQTT_SUB_TOPIC.append(b'nred2esp/adcZCMD/+')
    device.append(b'adc')
    outgoingD[b'adc'] = {}
    outgoingD[b'adc']['data'] = {}
    outgoingD[b'adc']['send_always'] = False
    outgoingD[b'adc']['send'] = False         # Used to flag when to send results
    buttonADC_pressed = False
    if switchON:
        buttonADC = Pin(switch, Pin.IN, Pin.PULL_UP)  # Create button
        def _buttonADC_ISR(pin):    # Create handle interrupt function to update when button pressed
            global buttonADC_pressed
            buttonADC_pressed = False
        buttonADC.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=_buttonADC_ISR) # link interrupt handler to function for pin falling or rising
        print('Button(ADC):{0}'.format(buttonADC))
    for pin in pinlist:
        pinsummary.append(pin)
    if switch is not None: pinsummary.append(switch)          # For adc noise, th is raw data, 1mV = 1.25 raw
    return espADC(pinlist, 3.3, 35, 5000, setupinfo=True, debuginfo=False)    # Create adc object. Pass numOfChannels, vref, noiseThreshold=35, max Interval (ms)

def main():
    global pinsummary
    global device, outgoingD                          # Containers setup in 'create' functions and used for Publishing mqtt
    global buttonADC_pressed, buttonADC               # Button specific for ADC (ie joystick setup) 
    
    #===== SETUP VARIABLES ============#
    # Setup mqtt variables (topics and data containers) used in on_message, main loop, and publishing
    # Further setup of variables is completed in specific 'create_device' functions
    mqtt_setup('10.0.0.115')
    device = []    # mqtt lvl2 topic category and '.appended' in create functions
    outgoingD = {} # container used for publishing mqtt data
        
    # umqttsimple requires topics to be byte format. For string.join to work on topics, all items must be the same, bytes.
    ESPID = b'/esp32A'  # Specific MQTT_PUB_TOPICS created at time of publishing using string.join (specifically lvl2.join)
    MQTT_PUB_TOPIC = [b'esp2nred/', ESPID]
  
    # Used to stagger timers for checking msgs, getting data, and publishing msgs
    on_msgtimer_delay_ms = 250
    # Period or frequency to check msgs, get data, publish msgs
    on_msg_timer_ms = 500     # Takes ~ 2ms to check for msg
    getdata_sndmsg_timer_ms = 100   # Can take > 7ms to publish msgs

    #=== SETUP DEVICES ===#
    # Boot fails if pin 12 is pulled high
    # Pins 34-39 are input only and do not have internal pull-up resistors. Good for ADC
    # Items that are sent as part of mqtt topic will be binary (b'item)
    pinsummary = []
    

    switchON = False          # Optional button (ie joystick)
    adcpins = [34, 35]
    switch = 25
    adc = create_adc(adcpins, switch, switchON)
    
    print('Pins in use:{0}'.format(sorted(pinsummary)))
    #==========#
    # Connect and create the client
    try:
        mqtt_client = mqtt_connect_subscribe()
    except OSError as e:
        mqtt_reset()
    # MQTT setup is successful, publish status msg and flash on-board led
    mqtt_client.publish(b'status'.join(MQTT_PUB_TOPIC), b'esp32 connected, entering main loop')
    # Initialize flags and timers
    checkmsgs = False
    get_data = False
    sendmsgs = False    
    t0onmsg_ms = utime.ticks_ms()
    utime.sleep_ms(on_msgtimer_delay_ms)
    t0_datapub_ms = utime.ticks_ms()
    t0loop_us = utime.ticks_us()
    
    while True:
        try:
            if utime.ticks_diff(utime.ticks_ms(), t0onmsg_ms) > on_msg_timer_ms:
                checkmsgs = True
                t0onmsg_ms = utime.ticks_ms()
            if utime.ticks_diff(utime.ticks_ms(), t0_datapub_ms) > getdata_sndmsg_timer_ms:
                get_data = True
                sendmsgs = True
                t0_datapub_ms = utime.ticks_ms()
            
            if checkmsgs:
                mqtt_client.check_msg()
                checkmsgs = False
            
            if get_data:            
                adcdata = adc.getValue()
                if buttonADC_pressed or adcdata is not None:         # Update if button pressed or voltage changed or time limit hit
                    outgoingD[b'adc']['send'] = True
                    if adcdata is not None:
                        for i,pin in enumerate(adcdata):
                            outgoingD[b'adc']['data']['a' + str(i) + 'f'] = str(adcdata[i])  # Get the voltage of each channel    
                    if switchON: outgoingD[b'adc']['data']['buttoni'] = str(buttonADC.value())
                    buttonADC_pressed = False
                get_data = False

            if sendmsgs:   # Send messages for all devices setup
                for item in device:
                    if outgoingD[item]['send']:
                        mqtt_client.publish(item.join(MQTT_PUB_TOPIC), ujson.dumps(outgoingD[item]['data']))
                        outgoingD[item]['send'] = False
                sendmsgs = False
                
        except OSError as e:
            mqtt_reset()

if __name__ == "__main__":
    # Run main loop            
    main()

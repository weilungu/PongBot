#
# https://randomnerdtutorials.com/micropython-mqtt-esp32-esp8266/
#
import machine
from machine import Pin
from machine import I2C 
import ssd1306

import dht
import time
import network

from umqtt.robust import MQTTClient

# import randomint

# Wifi AP
# WIFI_SSID = 'aron'
# WIFI_PASS = '00000000'

WIFI_SSID = 'shepherd'
WIFI_PASS = 'Good@11255'


MQTT_BROKER = 'broker.hivemq.com'

mqtt_user='pongBot'
mqtt_password='00000000' # 8 個 0
client_id = 'pongBot'


# the TOPICs for publish
# A bytes array ! ( NOT String object)

topic_power= b'pongBot/power'
topic_mode= b'pongBot/mode'


#######################################################
# NodeMCU/ESP8266  D0, D1, D2, D3, D4, D5, D6, D7, D8 ]
#                 [ -1, 5,  4, -1,  2, 14, 12, 13, 15 ]
#######################################################


###
mqttReady = False
NTP_DELTA = 8*60*60  # GMT+8
wifi = network.WLAN(network.STA_IF)
###

def publishMessage(timerX):
    if not mqttReady:
        return
    
    tm = time.localtime(time.time() + NTP_DELTA) # (year, month, month-day, hour, min, second, weekday, year-day)
    
    power_on = 1
    power_off = 0

    global mqttClient
    mqttClient.publish(topic_power, str(power_on))
    # mqttClient.publish(topic_mode, str(tempH))


# Action as Wifi Station Mode (Client)

print("Connecting to WiFi...", WIFI_SSID)
if not wifi.isconnected():
    wifi.active(True)
    
    wifi.connect(WIFI_SSID, WIFI_PASS)
    while not wifi.isconnected():
        print(".", end="_")
        time.sleep(1)
    
print('\nWifi connected, IP:', wifi.ifconfig()[0])
time.sleep(3)



### https://bhave.sh/micropython-ntp/
### RTC+NTP

from machine import RTC
import ntptime


try:
    rtc = RTC()
    ntptime.settime()    # this queries the time from an NTP server
    #tm = rtc.datetime() # ( y, m, s, w, h, mi, s, ss)
    # NTP_DELTA = 8*60*60  # GMT+8
    tm = time.localtime(time.time() + NTP_DELTA) # (year, month, month-day, hour, min, second, weekday, year-day)
    print(tm)
    # showOledMessage("NTP Server", "Ready!")
except OSError as ex:
    print(ex)
    print("Fail to connect with NTP Server?")

time.sleep(3)



## 定時發布 MQTT 訊息 
from machine import Timer
tim1=Timer(1)
# tim1.init(mode=Timer.PERIODIC, callback=publishMessage)
tim1.init(period=3000, mode=Timer.PERIODIC, callback=publishMessage)

# define a callback method for MQTT
def mqtt_callback(topic, payload):
    # decode from byte-array to be string object
    topic = topic.decode('utf-8').lower()
    msg = payload.decode('utf-8')
    print(f"接收到 mqtt: {msg}")



while wifi.isconnected():
    try:
        # led01.on() # RED ON
        print("Try to connect with MQTT Broker...")
        # showOledMessage("Try to connect", "MQTT Broker...", MQTT_BROKER)
        mqttClient = MQTTClient(client_id=client_id, keepalive=5, server=MQTT_BROKER, port=1883, ssl=False)
        # mqttClient = MQTTClient(client_id=client_id, server=MQTT_BROKER, user=mqtt_user, password=mqtt_password, ssl=False)
        mqttClient.connect()
        

        mqttReady = True
        print("Connected with MQTT Broker... Ready!")

        # showOledMessage("Connected with MQTT:", MQTT_BROKER)
        
        time.sleep(1)
        # led01.off() # RED OFF
        


        mqttClient.set_callback(mqtt_callback)

        # mqttClient.subscribe(b'pongBot/gpio/#')
        mqttClient.subscribe(b'pongBot/power')
        # mqttClient.subscribe(b'pongBot/humi')
        
        
        while True:
            # check the incoming message --> invoke the callback
            mqttClient.check_msg()
            

            time.sleep(0.5)
        #
    except Exception as e:
        print(e)
        
    finally:
        mqttReady = False
        mqttClient.disconnect()
        pass

# reboot after 5 seconds.
# showOledMessage("WiFi is losed!?", "Restart after 5 sec.")
time.sleep(5)
machine.reset()

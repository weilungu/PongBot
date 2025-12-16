import network
import time
from umqtt.simple import MQTTClient
from machine import Pin

# WiFi 設定
WIFI_SSID = 'shepherd'
WIFI_PASS = 'Good@11255'

# MQTT 設定
MQTT_BROKER = 'broker.hivemq.com'
mqtt_user = 'pongBot'
mqtt_password = '00000000'
client_id = 'pongBot'
topic_power = b'pongBot/power'

# 狀態變數
power_status = False

# 連接 WiFi
def connect_wifi():
    print('正在連接 WiFi...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(1)
            print('.', end='')
    
    print('\nWiFi 連接成功！')
    print('IP 地址:', wlan.ifconfig()[0])
    return wlan

# MQTT 訊息回調函數
def mqtt_callback(topic, msg):
    global power_status
    print(f'收到訊息 - Topic: {topic.decode()}, Message: {msg.decode()}')
    
    if topic == topic_power:
        if msg == b'1' or msg.lower() == b'on':
            power_status = True
            print('電源開啟')
            # 在這裡加入開啟發球機的代碼
            
        elif msg == b'0' or msg.lower() == b'off':
            power_status = False
            print('電源關閉')
            # 在這裡加入關閉發球機的代碼

# 連接 MQTT
def connect_mqtt():
    print('正在連接 MQTT Broker...')
    client = MQTTClient(
        client_id=client_id,
        server=MQTT_BROKER,
        user=mqtt_user,
        password=mqtt_password,
        keepalive=60
    )
    
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(topic_power)
    
    print('MQTT 連接成功！')
    print(f'已訂閱 Topic: {topic_power.decode()}')
    return client

# 主程式
def main():
    # 連接 WiFi
    wlan = connect_wifi()
    
    # 連接 MQTT
    client = connect_mqtt()
    
    print('系統運行中，等待 MQTT 訊息...')
    print('請在 IoT MQTT Panel 控制 pongBot/power switch')
    
    # 主迴圈
    try:
        while True:
            client.check_msg()  # 檢查是否有新訊息
            time.sleep(0.1)     # 短暫延遲避免過度佔用 CPU
            
    except KeyboardInterrupt:
        print('\n程式中斷')
        client.disconnect()
    except Exception as e:
        print(f'錯誤: {e}')
        client.disconnect()

# 執行主程式
if __name__ == '__main__':
    main()

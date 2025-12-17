"""
ESP8266 Blynk 連接程式
用於發球機控制
"""

import network
import time
import BlynkLib

import machine
from machine import Pin

# ==================== 設定區域 ====================
# WiFi 設定
WIFI_SSID = "aron"      # 請更改為您的 WiFi 名稱
WIFI_PASSWORD = "00000000"   # 請更改為您的 WiFi 密碼: 8 個 0

# Blynk 設定
#define BLYNK_TEMPLATE_ID "TMPL6ehjjbB9a"
#define BLYNK_TEMPLATE_NAME "pongBot"
#define BLYNK_AUTH_TOKEN "O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"

BLYNK_AUTH = "O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"

# Pin 設定
BALL_MACHINE_PIN = 5  # GPIO5 控制發球機

# ===================================================

def connect_wifi():
    """連接 WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("正在連接 WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # 等待連接，最多等待 20 秒
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            print(".", end="")
            time.sleep(1)
            timeout -= 1
        
        if wlan.isconnected():
            print("\nWiFi 連接成功!")
            print("IP 地址:", wlan.ifconfig()[0])
        else:
            print("\nWiFi 連接失敗!")
            return False
    else:
        print("WiFi 已連接")
        print("IP 地址:", wlan.ifconfig()[0])
    
    return True

def main():
    """主程式"""
    # 連接 WiFi
    if not connect_wifi():
        print("無法連接 WiFi，程式結束")
        return
    
    # 連接 Blynk (使用非 SSL 連接，因為 ESP8266 不支援完整 SSL)
    print("正在連接 Blynk...")
    blynk = BlynkLib.Blynk(BLYNK_AUTH, insecure=True)
    print("Blynk 連接成功!")
    
    # ==================== Blynk 虛擬腳位處理 ====================
    
    # 虛擬腳位 V0 - 範例：控制發球機開關
    @blynk.on("V0")
    def v0_handler(value):
        print("V0 收到:", value[0])
        # 在這裡添加發球機開關控制邏輯
        if value[0] == "1":
            Pin(5, Pin.OUT).on() # GPIO5

            print("發球機啟動")
            # TODO: 啟動發球機
        else:
            Pin(5, Pin.OUT).off() # GPIO5
            print("發球機停止")
            # TODO: 停止發球機
    
    # 虛擬腳位 V1 - 範例：控制發球速度
    @blynk.on("V1")
    def v1_handler(value):
        speed = int(value[0])
        print("發球速度設定為:", speed)
        # TODO: 設定發球速度
    
    # 虛擬腳位 V2 - 範例：控制發球角度
    @blynk.on("V2")
    def v2_handler(value):
        angle = int(value[0])
        print("發球角度設定為:", angle)
        # TODO: 設定發球角度
    
    # 連接事件
    @blynk.on("connected")
    def blynk_connected():
        print("已連接到 Blynk 伺服器")
    
    # 斷線事件
    @blynk.on("disconnected")
    def blynk_disconnected():
        print("與 Blynk 伺服器斷開連接")
    
    # ==================== 主迴圈 ====================
    print("開始執行主迴圈...")
    while True:
        blynk.run()
        time.sleep(0.1)

# 執行主程式
if __name__ == "__main__":
    main()

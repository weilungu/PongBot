"""
ESP8266 360度伺服馬達 + Blynk 控制
用於發球機旋轉控制
"""

from machine import Pin, PWM
import network
import time
import BlynkLib

# ==================== 設定區域 ====================
# WiFi 設定
WIFI_SSID = "aron"
WIFI_PASSWORD = "00000000"

# Blynk 設定
BLYNK_AUTH = "O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"

# 伺服馬達設定
SERVO_PIN = 14  # GPIO14 (D5)
ROTATION_SPEED = 100  # 順時針旋轉速度 (100 = 全速)

# ===================================================

# 初始化伺服馬達
servo_pin = PWM(Pin(SERVO_PIN, Pin.OUT), freq=50, duty=0)

# 全域變數
motor_running = False  # 馬達運行狀態
motor_speed = 100  # 馬達速度 (0-100)

def set_servo_speed(speed):
    """
    設定伺服馬達速度和方向
    speed: -100 到 +100
    -100 = 最快反向旋轉
    0 = 停止
    +100 = 最快正向旋轉
    """
    pulse_width = 1.5 + (speed / 100) * 1.0  # 0.5ms ~ 2.5ms
    duty = int(1024 * pulse_width / 20)
    servo_pin.duty(duty)

def connect_wifi():
    """連接 WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("正在連接 WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
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
    # 初始化：馬達停止
    set_servo_speed(0)
    
    # 連接 WiFi
    if not connect_wifi():
        print("無法連接 WiFi，程式結束")
        return
    
    # 連接 Blynk
    print("正在連接 Blynk...")
    blynk = BlynkLib.Blynk(BLYNK_AUTH, insecure=True)
    print("Blynk 連接成功!")
    
    # ==================== Blynk 虛擬腳位處理 ====================
    
    # 虛擬腳位 V0 - 控制伺服馬達開關
    @blynk.on("V0")
    def v0_handler(value):
        global motor_running
        print("V0 收到:", value[0])
        if value[0] == "1":
            motor_running = True
            print(f"伺服馬達啟動 - 順時針旋轉 (速度: {motor_speed}%)")
            set_servo_speed(motor_speed)  # 使用目前設定的速度
        else:
            motor_running = False
            print("伺服馬達停止")
            set_servo_speed(0)  # 停止
    
    # 虛擬腳位 V1 - 控制伺服馬達速度 (0-100%)
    @blynk.on("V1")
    def v1_handler(value):
        global motor_speed
        motor_speed = int(value[0])
        print(f"速度設定為: {motor_speed}%")
        
        # 如果馬達正在運行，立即更新速度
        if motor_running:
            set_servo_speed(motor_speed)
            print(f"馬達速度已更新為: {motor_speed}%")


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
    print("等待 Blynk 指令...")
    while True:
        blynk.run()
        time.sleep(0.1)

# 執行主程式
if __name__ == "__main__":
    main()
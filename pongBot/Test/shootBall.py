"""
ESP8266 發球機控制程式
使用 Blynk 進行遠端控制
包含 DC 馬達控制功能
"""

import network
import time
import BlynkLib
from machine import Pin, PWM

# ==================== 設定區域 ====================
# WiFi 設定
WIFI_SSID = "aron"      # 請更改為您的 WiFi 名稱
WIFI_PASSWORD = "00000000"   # 請更改為您的 WiFi 密碼

# Blynk 設定
BLYNK_AUTH = "O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"

# DC 馬達 Pin 設定 (TB6612FNG 雙馬達)
MOTOR_A_IN1_PIN = 5    # GPIO5 - AIN1
MOTOR_A_IN2_PIN = 4    # GPIO4 - AIN2
MOTOR_A_PWM_PIN = 14   # GPIO14 - PWMA

MOTOR_B_IN1_PIN = 12   # GPIO12 - BIN1
MOTOR_B_IN2_PIN = 13   # GPIO13 - BIN2
MOTOR_B_PWM_PIN = 15   # GPIO15 - PWMB
# MOTOR_STBY_PIN = None  # 如果需要可啟用

# ===================================================


class DCMotor:
    """DC 馬達控制類別 (TB6612FNG)"""
    
    def __init__(self, in1_pin, in2_pin, pwm_pin, freq=1000):
        """
        初始化 DC 馬達
        
        參數:
            in1_pin: 控制腳位 1
            in2_pin: 控制腳位 2
            pwm_pin: PWM 速度控制腳位
            freq: PWM 頻率 (預設 1000Hz)
        """
        self.in1 = Pin(in1_pin, Pin.OUT)
        self.in2 = Pin(in2_pin, Pin.OUT)
        self.pwm = PWM(Pin(pwm_pin))
        self.pwm.freq(freq)
        self.is_running = False
        self.current_speed = 0
        self.stop()
    
    def forward(self, speed=100):
        """
        正轉 (順時針)
        
        參數:
            speed: 速度 0-100 (百分比)
        """
        speed = max(0, min(100, speed))  # 限制在 0-100 之間
        duty = int(speed * 1023 / 100)  # ESP8266 使用 10 位元 PWM (0-1023)
        
        self.in1.value(1)
        self.in2.value(0)
        self.pwm.duty(duty)
        self.is_running = True
        self.current_speed = speed
        print(f"馬達正轉，速度: {speed}%")
    
    def backward(self, speed=100):
        """
        反轉 (逆時針)
        
        參數:
            speed: 速度 0-100 (百分比)
        """
        speed = max(0, min(100, speed))
        duty = int(speed * 1023 / 100)
        
        self.in1.value(0)
        self.in2.value(1)
        self.pwm.duty(duty)
        self.is_running = True
        self.current_speed = speed
        print(f"馬達反轉，速度: {speed}%")
    
    def stop(self):
        """停止馬達"""
        self.in1.value(0)
        self.in2.value(0)
        self.pwm.duty(0)
        self.is_running = False
        self.current_speed = 0
        print("馬達停止")
    
    def set_speed(self, speed):
        """
        設定速度 (保持當前方向)
        
        參數:
            speed: 速度 0-100 (百分比)
        """
        if self.is_running:
            speed = max(0, min(100, speed))
            duty = int(speed * 1023 / 100)
            self.pwm.duty(duty)
            self.current_speed = speed
            print(f"馬達速度設定為: {speed}%")


class DualMotor:
    """雙馬達控制類別 (TB6612FNG 雙通道)"""
    
    def __init__(self, ain1_pin, ain2_pin, pwma_pin,
                 bin1_pin, bin2_pin, pwmb_pin, freq=1000):
        """
        初始化雙馬達控制
        
        參數:
            ain1_pin: 馬達A控制腳位1 (AIN1)
            ain2_pin: 馬達A控制腳位2 (AIN2)
            pwma_pin: 馬達A PWM腳位 (PWMA)
            bin1_pin: 馬達B控制腳位1 (BIN1)
            bin2_pin: 馬達B控制腳位2 (BIN2)
            pwmb_pin: 馬達B PWM腳位 (PWMB)
            freq: PWM 頻率 (預設 1000Hz)
        """
        # 建立兩個馬達實例
        self.motor_a = DCMotor(ain1_pin, ain2_pin, pwma_pin, freq)
        self.motor_b = DCMotor(bin1_pin, bin2_pin, pwmb_pin, freq)
        self.is_running = False
        self.current_speed = 0
    
    def forward(self, speed=100):
        """兩個馬達同時正轉"""
        self.motor_a.forward(speed)
        self.motor_b.forward(speed)
        self.is_running = True
        self.current_speed = speed
        print(f"雙馬達正轉，速度: {speed}%")
    
    def backward(self, speed=100):
        """兩個馬達同時反轉"""
        self.motor_a.backward(speed)
        self.motor_b.backward(speed)
        self.is_running = True
        self.current_speed = speed
        print(f"雙馬達反轉，速度: {speed}%")
    
    def stop(self):
        """停止所有馬達"""
        self.motor_a.stop()
        self.motor_b.stop()
        self.is_running = False
        self.current_speed = 0
        print("雙馬達停止")
    
    def set_speed(self, speed):
        """設定兩個馬達的速度 (保持當前方向)"""
        if self.is_running:
            self.motor_a.set_speed(speed)
            self.motor_b.set_speed(speed)
            self.current_speed = speed
            print(f"雙馬達速度設定為: {speed}%")


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


def setup_blynk_handlers(blynk, motor):
    """設定 Blynk 虛擬腳位處理器"""
    
    # # 虛擬腳位 V0 - 發球機控制 (範例保留)
    # @blynk.on("V0")
    # def v0_handler(value):
    #     print("V0 收到:", value[0])
    #     if value[0] == "1":
    #         print("發球機啟動")
    #         # TODO: 啟動發球機
    #     else:
    #         print("發球機停止")
    #         # TODO: 停止發球機
    
    # # 虛擬腳位 V1 - 發球速度 (範例保留)
    # @blynk.on("V1")
    # def v1_handler(value):
    #     speed = int(value[0])
    #     print("發球速度設定為:", speed)
    #     # TODO: 設定發球速度
    
    # 虛擬腳位 V2 - DC 馬達開關控制
    @blynk.on("V2")
    def v2_handler(value):
        print("V2 (DC馬達開關) 收到:", value[0])
        if value[0] == "1":
            # 開啟馬達，使用當前速度或預設速度
            speed = motor.current_speed if motor.current_speed > 0 else 50
            motor.forward(speed)
        else:
            # 關閉馬達
            motor.stop()
    
    # 虛擬腳位 V3 - DC 馬達速度控制 (1-10 對應 10%-100%)
    @blynk.on("V3")
    def v3_handler(value):
        slider_value = int(value[0])
        print("V3 (DC馬達速度) 收到:", slider_value)
        
        # 將 1-10 的滑桿值轉換為 10%-100% 的速度
        speed_percent = slider_value * 10
        
        # 如果馬達正在運轉，更新速度
        if motor.is_running:
            motor.set_speed(speed_percent)
        else:
            # 如果馬達未運轉，只記錄速度值
            motor.current_speed = speed_percent
            print(f"速度已設定為 {speed_percent}% (馬達未啟動)")


def connect_blynk():
    """連接 Blynk，失敗時返回 None"""
    try:
        print("正在連接 Blynk...")
        blynk = BlynkLib.Blynk(BLYNK_AUTH, insecure=True)
        print("Blynk 連接成功!")
        return blynk
    except Exception as e:
        print(f"Blynk 連接失敗: {e}")
        return None


def main():
    """主程式"""
    # 連接 WiFi
    if not connect_wifi():
        print("無法連接 WiFi，程式結束")
        return
    
    # 初始化雙 DC 馬達
    motor = DualMotor(
        MOTOR_A_IN1_PIN, MOTOR_A_IN2_PIN, MOTOR_A_PWM_PIN,
        MOTOR_B_IN1_PIN, MOTOR_B_IN2_PIN, MOTOR_B_PWM_PIN
    )
    print("雙 DC 馬達初始化完成")
    
    # 連接 Blynk (初始連線失敗會持續嘗試)
    blynk = None
    while blynk is None:
        blynk = connect_blynk()
        if blynk is None:
            print("Blynk 連接失敗，5秒後重試...")
            time.sleep(5)
            # 確認 WiFi 仍然連接
            if not connect_wifi():
                print("WiFi 已斷線，重新連接...")
    
    # 設定 Blynk 處理器
    setup_blynk_handlers(blynk, motor)
    
    # ==================== 主迴圈 ====================
    print("\n發球機系統已啟動，等待 Blynk 指令...")
    print("=" * 50)
    print("V2: DC 馬達開關")
    print("V3: DC 馬達速度 (1-10 → 10%-100%)")
    print("=" * 50)
    
    # 連接事件
    @blynk.on("connected")
    def blynk_connected():
        print("已連接到 Blynk 伺服器")
    
    # 斷線事件
    @blynk.on("disconnected")
    def blynk_disconnected():
        print("與 Blynk 伺服器斷開連接")
    
    try:
        while True:
            blynk.run()
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n程式中斷")
        motor.stop()
    except Exception as e:
        print(f"發生錯誤: {e}")
        motor.stop()


if __name__ == "__main__":
    main()

"""
MicroPython DC 小馬達控制程式
適用於 Raspberry Pi Pico 或其他 MicroPython 板子
使用 TB6612FNG 馬達驅動模組
"""

from machine import Pin, PWM
import time


class DCMotor:
    """DC 馬達控制類別 (TB6612FNG)"""
    
    def __init__(self, in1_pin, in2_pin, pwm_pin, stby_pin=None, freq=1000):
        """
        初始化 DC 馬達 (TB6612FNG)
        
        參數:
            in1_pin: 控制腳位 1 (AIN1/BIN1)
            in2_pin: 控制腳位 2 (AIN2/BIN2)
            pwm_pin: PWM 速度控制腳位 (PWMA/PWMB)
            stby_pin: 待機控制腳位 (可選，None 表示 STBY 接到 VCC)
            freq: PWM 頻率 (預設 1000Hz)
        """
        self.in1 = Pin(in1_pin, Pin.OUT)
        self.in2 = Pin(in2_pin, Pin.OUT)
        self.pwm = PWM(Pin(pwm_pin))
        self.pwm.freq(freq)
        
        # STBY 腳位控制 (如果有連接到 GPIO)
        if stby_pin is not None:
            self.stby = Pin(stby_pin, Pin.OUT)
            self.stby.value(1)  # 啟用馬達驅動器
        else:
            self.stby = None
        
        self.stop()
    
    def forward(self, speed=100):
        """
        正轉 (順時針)
        
        參數:
            speed: 速度 0-100 (百分比)
        """
        if self.stby is not None:
            self.stby.value(1)  # 確保驅動器啟用
        
        speed = max(0, min(100, speed))  # 限制在 0-100 之間
        duty = int(speed * 65535 / 100)  # 轉換為 16 位元值 (0-65535)
        
        self.in1.value(1)
        self.in2.value(0)
        self.pwm.duty_u16(duty)
    
    def backward(self, speed=100):
        """
        反轉 (逆時針)
        
        參數:
            speed: 速度 0-100 (百分比)
        """
        if self.stby is not None:
            self.stby.value(1)  # 確保驅動器啟用
        
        speed = max(0, min(100, speed))
        duty = int(speed * 65535 / 100)
        
        self.in1.value(0)
        self.in2.value(1)
        self.pwm.duty_u16(duty)
    
    def stop(self):
        """停止馬達"""
        self.in1.value(0)
        self.in2.value(0)
        self.pwm.duty_u16(0)
    
    def brake(self):
        """短路煞車 (兩個腳位都設為高電位)"""
        if self.stby is not None:
            self.stby.value(1)
        self.in1.value(1)
        self.in2.value(1)
        self.pwm.duty_u16(65535)
    
    def standby(self):
        """進入待機模式 (低功耗)"""
        if self.stby is not None:
            self.stby.value(0)
        else:
            self.stop()
    
    def set_speed(self, speed):
        """
        設定速度 (不改變方向)
        
        參數:
            speed: 速度 0-100 (百分比)
        """
        speed = max(0, min(100, speed))
        duty = int(speed * 65535 / 100)
        self.pwm.duty_u16(duty)


def demo():
    """示範程式"""
    print("DC 馬達控制示範 (TB6612FNG)")
    print("AIN1=GPIO5, AIN2=GPIO4, PWMA=GPIO14")
    
    # 建立馬達實例 (TB6612FNG 接線)
    # AIN1→GPIO5, AIN2→GPIO4, PWMA→GPIO14
    # STBY→3.3V (常態啟用，所以不需要 GPIO 控制)
    motor = DCMotor(in1_pin=5, in2_pin=4, pwm_pin=14)
    
    try:
        # 正轉測試
        print("正轉 - 速度 50%")
        motor.forward(50)
        time.sleep(2)
        
        print("正轉 - 速度 100%")
        motor.forward(100)
        time.sleep(2)
        
        # 停止
        print("停止")
        motor.stop()
        time.sleep(1)
        
        # 反轉測試
        print("反轉 - 速度 50%")
        motor.backward(50)
        time.sleep(2)
        
        print("反轉 - 速度 100%")
        motor.backward(100)
        time.sleep(2)
        
        # 煞車
        print("煞車")
        motor.brake()
        time.sleep(1)
        
        # 速度變化測試
        print("速度漸增")
        motor.forward(0)
        for speed in range(0, 101, 10):
            motor.set_speed(speed)
            print(f"速度: {speed}%")
            time.sleep(0.5)
        
        print("速度漸減")
        for speed in range(100, -1, -10):
            motor.set_speed(speed)
            print(f"速度: {speed}%")
            time.sleep(0.5)
        
    except KeyboardInterrupt:
        print("\n程式中斷")
    finally:
        motor.stop()
        print("馬達已停止")


if __name__ == "__main__":
    demo()

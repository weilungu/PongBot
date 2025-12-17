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


class DualMotor:
    """雙馬達控制類別 (TB6612FNG 雙通道)"""
    
    def __init__(self, ain1_pin, ain2_pin, pwma_pin,
                 bin1_pin, bin2_pin, pwmb_pin,
                 stby_pin=None, freq=1000):
        """
        初始化雙馬達控制 (TB6612FNG)
        
        參數:
            ain1_pin: 馬達A控制腳位1 (AIN1)
            ain2_pin: 馬達A控制腳位2 (AIN2)
            pwma_pin: 馬達A PWM腳位 (PWMA)
            bin1_pin: 馬達B控制腳位1 (BIN1)
            bin2_pin: 馬達B控制腳位2 (BIN2)
            pwmb_pin: 馬達B PWM腳位 (PWMB)
            stby_pin: 待機控制腳位 (可選，None 表示 STBY 接到 VCC)
            freq: PWM 頻率 (預設 1000Hz)
        """
        # 共用 STBY 控制
        if stby_pin is not None:
            self.stby = Pin(stby_pin, Pin.OUT)
            self.stby.value(1)  # 啟用馬達驅動器
        else:
            self.stby = None
        
        # 建立兩個馬達實例
        self.motor_a = DCMotor(ain1_pin, ain2_pin, pwma_pin, stby_pin=None, freq=freq)
        self.motor_b = DCMotor(bin1_pin, bin2_pin, pwmb_pin, stby_pin=None, freq=freq)
    
    def forward(self, speed_a=100, speed_b=100):
        """兩個馬達同時正轉"""
        if self.stby is not None:
            self.stby.value(1)
        self.motor_a.forward(speed_a)
        self.motor_b.forward(speed_b)
    
    def backward(self, speed_a=100, speed_b=100):
        """兩個馬達同時反轉"""
        if self.stby is not None:
            self.stby.value(1)
        self.motor_a.backward(speed_a)
        self.motor_b.backward(speed_b)
    
    def turn_left(self, speed=100):
        """左轉 (馬達A反轉，馬達B正轉)"""
        if self.stby is not None:
            self.stby.value(1)
        self.motor_a.backward(speed)
        self.motor_b.forward(speed)
    
    def turn_right(self, speed=100):
        """右轉 (馬達A正轉，馬達B反轉)"""
        if self.stby is not None:
            self.stby.value(1)
        self.motor_a.forward(speed)
        self.motor_b.backward(speed)
    
    def stop(self):
        """停止所有馬達"""
        self.motor_a.stop()
        self.motor_b.stop()
    
    def brake(self):
        """煞車所有馬達"""
        if self.stby is not None:
            self.stby.value(1)
        self.motor_a.brake()
        self.motor_b.brake()
    
    def standby(self):
        """進入待機模式"""
        if self.stby is not None:
            self.stby.value(0)
        else:
            self.stop()
    
    def set_speed(self, speed_a, speed_b):
        """設定兩個馬達的速度"""
        self.motor_a.set_speed(speed_a)
        self.motor_b.set_speed(speed_b)


def demo():
    """示範程式 - 單馬達控制"""
    print("=== 單馬達控制示範 ===")
    print("馬達A: AIN1=GPIO5, AIN2=GPIO4, PWMA=GPIO14")
    
    motor = DCMotor(in1_pin=5, in2_pin=4, pwm_pin=14)
    
    try:
        print("\n正轉 50%")
        motor.forward(50)
        time.sleep(2)
        
        print("停止")
        motor.stop()
        time.sleep(1)
        
        print("反轉 50%")
        motor.backward(50)
        time.sleep(2)
        
        motor.stop()
        
    except KeyboardInterrupt:
        print("\n程式中斷")
    finally:
        motor.stop()
        print("馬達已停止")


def demo_dual():
    """示範程式 - 雙馬達控制"""
    print("\n=== 雙馬達控制示範 (TB6612FNG) ===")
    print("馬達A: AIN1=GPIO5, AIN2=GPIO4, PWMA=GPIO14")
    print("馬達B: BIN1=GPIO?, BIN2=GPIO?, PWMB=GPIO?")
    print("註: 請根據實際接線修改 GPIO 腳位\n")
    
    # 建立雙馬達實例
    # 請根據您的實際接線修改以下 GPIO 腳位
    # 範例: BIN1=GPIO12, BIN2=GPIO13, PWMB=GPIO27
    motors = DualMotor(
        ain1_pin=5,   # AIN1 D1
        ain2_pin=4,   # AIN2 D2
        pwma_pin=14,  # PWMA D5
        bin1_pin=12,  # BIN1 D6
        bin2_pin=13,  # BIN2 D7
        pwmb_pin=15   # PWMB D8
    )
    
    try:
        # 同時正轉
        print("兩個馬達同時正轉 (70%)")
        motors.forward(70, 70)
        time.sleep(2)
        
        # 停止
        print("停止")
        motors.stop()
        time.sleep(1)
        
        # 同時反轉
        print("兩個馬達同時反轉 (70%)")
        motors.backward(70, 70)
        time.sleep(2)
        
        motors.stop()
        time.sleep(1)
        
        # 左轉
        print("左轉 (A反轉, B正轉)")
        motors.turn_left(60)
        time.sleep(2)
        
        motors.stop()
        time.sleep(1)
        
        # 右轉
        print("右轉 (A正轉, B反轉)")
        motors.turn_right(60)
        time.sleep(2)
        
        motors.stop()
        time.sleep(1)
        
        # 不同速度測試
        print("馬達A 50%, 馬達B 80%")
        motors.forward(50, 80)
        time.sleep(2)
        
        # 煞車
        print("煞車")
        motors.brake()
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n程式中斷")
    finally:
        motors.stop()
        print("所有馬達已停止")


if __name__ == "__main__":
    # 執行單馬達示範
    # demo()
    
    # 取消註解以執行雙馬達示範
    demo_dual()

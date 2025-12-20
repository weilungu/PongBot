"""
ESP8266 發球機整合控制程式
整合功能：
- Blynk 遠端控制
- 長按計時發球機制
- DC 馬達控制（雙馬達發球）
- 360度伺服馬達控制（旋轉）
"""

import network
import time
import BlynkLib
from machine import Pin, PWM

# ==================== WiFi 設定 ====================
WIFI_SSID = "aron"
WIFI_PASSWORD = "00000000"

# ==================== Blynk 設定 ====================
BLYNK_AUTH = "O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"

# ==================== Pin 設定 ====================
# 基本發球機控制
BALL_MACHINE_PIN = 5  # GPIO5

# DC 馬達設定 (TB6612FNG)
MOTOR_A_IN1 = 5     # GPIO5 - AIN1  (D1)
MOTOR_A_IN2 = 4     # GPIO4 - AIN2  (D2)
MOTOR_A_PWM = 14    # GPIO14 - PWMA (D5)
MOTOR_B_IN1 = 12    # GPIO12 - BIN1 (D6)
MOTOR_B_IN2 = 13    # GPIO13 - BIN2 (D7)
MOTOR_B_PWM = 15    # GPIO15 - PWMB (D8)

# 360度伺服馬達設定
SERVO_PIN = 0      # GPIO0 (D3) (可與 MOTOR_A_PWM 共用或分開)

# ==================== 計時參數 ====================
LONG_PRESS_TIME = 3000      # 長按觸發時間（毫秒）
HOLD_TIME = 3000            # 發球後保持時間（毫秒）
GAUGE_UPDATE_INTERVAL = 30  # 計量表更新間隔（毫秒）

# ==================== 速度映射設定 ====================
# V1 伺服馬達速度映射 (1-5 → 30%, 50%, 70%, 90%, 100%)
SERVO_SPEED_MAP = [0, 30, 50, 70, 90, 100]  # 索引 0 不使用，1-5 對應速度

# ==================== 全域變數 ====================
# V10/V11 按鈕狀態
press_start_v10 = None
is_pressing_v10 = False
is_triggered_v10 = False
trigger_end_v10 = None

# V12/V13 按鈕狀態
press_start_v12 = None
is_pressing_v12 = False
is_triggered_v12 = False
trigger_end_v12 = None

blynk = None
dual_motor = None
servo_pwm = None
servo_running = False
servo_speed = 0  # 初始值為0，避免未調整V1時顯示錯誤速度

# ==================== DC 馬達類別 ====================
class DCMotor:
    """DC 馬達控制"""
    def __init__(self, in1_pin, in2_pin, pwm_pin, freq=1000):
        self.in1 = Pin(in1_pin, Pin.OUT)
        self.in2 = Pin(in2_pin, Pin.OUT)
        self.pwm = PWM(Pin(pwm_pin))
        self.pwm.freq(freq)
        self.is_running = False
        self.current_speed = 0
        self.stop()
    
    def forward(self, speed=100):
        speed = max(0, min(100, speed))
        duty = int(speed * 1023 / 100)
        self.in1.value(1)
        self.in2.value(0)
        self.pwm.duty(duty)
        self.is_running = True
        self.current_speed = speed
    
    def stop(self):
        self.in1.value(0)
        self.in2.value(0)
        self.pwm.duty(0)
        self.is_running = False
        self.current_speed = 0
    
    def set_speed(self, speed):
        speed = max(0, min(100, speed))
        duty = int(speed * 1023 / 100)
        if self.is_running:
            self.pwm.duty(duty)
        self.current_speed = speed

class DualMotor:
    """雙馬達控制"""
    def __init__(self, ain1, ain2, pwma, bin1, bin2, pwmb, freq=1000):
        self.motor_a = DCMotor(ain1, ain2, pwma, freq)
        self.motor_b = DCMotor(bin1, bin2, pwmb, freq)
        self.is_running = False
        self.current_speed = 0
    
    def forward(self, speed=100):
        self.motor_a.forward(speed)
        self.motor_b.forward(speed)
        self.is_running = True
        self.current_speed = speed
    
    def stop(self):
        self.motor_a.stop()
        self.motor_b.stop()
        self.is_running = False
        self.current_speed = 0
    
    def set_speed(self, speed):
        if self.is_running:
            self.motor_a.set_speed(speed)
            self.motor_b.set_speed(speed)
            self.current_speed = speed

# ==================== 360度伺服馬達函數 ====================
def init_servo():
    """初始化伺服馬達"""
    global servo_pwm
    servo_pwm = PWM(Pin(SERVO_PIN, Pin.OUT), freq=50, duty=0)

def set_servo_speed(speed):
    """設定伺服馬達速度 -100 到 +100"""
    pulse_width = 1.5 + (speed / 100) * 1.0
    duty = int(1024 * pulse_width / 20)
    servo_pwm.duty(duty)

# ==================== WiFi 連接 ====================
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
            print("IP:", wlan.ifconfig()[0])
            return True
        else:
            print("\nWiFi 連接失敗!")
            return False
    else:
        print("WiFi 已連接")
        print("IP:", wlan.ifconfig()[0])
        return True

# ==================== 長按機制輔助函數 ====================
def get_time_ms():
    """取得目前時間（毫秒）"""
    try:
        return time.ticks_ms()
    except:
        return int(time.time() * 1000)

def calc_gauge(elapsed_ms):
    """計算計量表值 0-100"""
    return min(100, int((elapsed_ms / LONG_PRESS_TIME) * 100))

def update_gauge(pin, value):
    """更新計量表"""
    if blynk:
        blynk.virtual_write(pin, value)

def trigger_ball(button_pin, label_pin, is_trig):
    """觸發發球機並更新狀態 Label"""
    if not is_trig:
        Pin(BALL_MACHINE_PIN, Pin.OUT).on()
        print(f"[V{button_pin}] 發球機已觸發！")
        if blynk:
            blynk.virtual_write(button_pin, 1)
            # 當按鈕觸發時，對應的 Label 設為 True
            blynk.virtual_write(label_pin, "True")
        return True, get_time_ms()
    return is_trig, None

def reset_button(button_pin, gauge_pin):
    """重置按鈕狀態"""
    Pin(BALL_MACHINE_PIN, Pin.OUT).off()
    print(f"[V{button_pin}] 發球機已停止")
    if blynk:
        blynk.virtual_write(gauge_pin, 0)
        blynk.virtual_write(button_pin, 0)
    return False, None, False, None

def process_button(btn_pin, gauge_pin, label_pin, is_press, press_start, is_trig, trig_end):
    """處理單個按鈕邏輯"""
    now = get_time_ms()
    
    if is_press and press_start is not None:
        elapsed = now - press_start
        
        if elapsed % GAUGE_UPDATE_INTERVAL < 30:
            update_gauge(gauge_pin, calc_gauge(elapsed))
        
        if elapsed >= LONG_PRESS_TIME and not is_trig:
            is_trig, trig_end = trigger_ball(btn_pin, label_pin, is_trig)
    
    if is_trig and trig_end is not None:
        if now - trig_end >= HOLD_TIME:
            is_press, press_start, is_trig, trig_end = reset_button(btn_pin, gauge_pin)
    
    return is_press, press_start, is_trig, trig_end

def process_all_buttons():
    """處理所有按鈕邏輯"""
    global press_start_v10, is_pressing_v10, is_triggered_v10, trigger_end_v10
    global press_start_v12, is_pressing_v12, is_triggered_v12, trigger_end_v12
    
    # V10/V11 對應 V14 Label
    is_pressing_v10, press_start_v10, is_triggered_v10, trigger_end_v10 = \
        process_button(10, 11, 14, is_pressing_v10, press_start_v10, is_triggered_v10, trigger_end_v10)
    
    # V12/V13 對應 V15 Label
    is_pressing_v12, press_start_v12, is_triggered_v12, trigger_end_v12 = \
        process_button(12, 13, 15, is_pressing_v12, press_start_v12, is_triggered_v12, trigger_end_v12)

# ==================== Blynk 處理器設定 ====================
def setup_handlers():
    """設定 Blynk 虛擬腳位處理器"""
    global blynk, dual_motor
    global is_pressing_v10, press_start_v10, is_triggered_v10
    global is_pressing_v12, press_start_v12, is_triggered_v12
    global servo_running, servo_speed
    
    # V0 - 伺服馬達開關
    @blynk.on("V0")
    def v0_handler(value):
        global servo_running
        if value[0] == "1":
            servo_running = True
            set_servo_speed(servo_speed)
            print(f"伺服馬達啟動 (速度: {servo_speed}%)")
        else:
            servo_running = False
            set_servo_speed(0)
            print("伺服馬達停止")
        # 調整 V0~V4 時，V14、V15 設為 False
        blynk.virtual_write(14, "False")
        blynk.virtual_write(15, "False")
    
    # V1 - 伺服馬達速度 (1-5 → 30%, 50%, 70%, 90%, 100%)
    @blynk.on("V1")
    def v1_handler(value):
        global servo_speed
        level = int(value[0])  # 1-5
        if 1 <= level <= 5:
            servo_speed = SERVO_SPEED_MAP[level]
            if servo_running:
                set_servo_speed(servo_speed)
            print(f"伺服速度: 等級 {level} -> {servo_speed}%")
        else:
            print(f"錯誤：伺服速度等級應為 1-5，收到: {level}")
        # 調整 V0~V4 時，V14、V15 設為 False
        blynk.virtual_write(14, "False")
        blynk.virtual_write(15, "False")
    
    # V2 - DC 馬達開關
    @blynk.on("V2")
    def v2_handler(value):
        if value[0] == "1":
            # 使用各自馬達已設定的速度，如果沒有設定則使用預設值
            speed_a = dual_motor.motor_a.current_speed if dual_motor.motor_a.current_speed > 0 else 25
            speed_b = dual_motor.motor_b.current_speed if dual_motor.motor_b.current_speed > 0 else 25
            dual_motor.motor_a.forward(speed_a)
            dual_motor.motor_b.forward(speed_b)
            print(f"DC 馬達啟動 - Motor A: {speed_a}%, Motor B: {speed_b}%")
        else:
            dual_motor.stop()
            print("DC 馬達停止")
        # 調整 V0~V4 時，V14、V15 設為 False
        blynk.virtual_write(14, "False")
        blynk.virtual_write(15, "False")
    
    # V3 - Motor_Speed_A (1-100 → 0.5%-50%)
    @blynk.on("V3")
    def v3_handler(value):
        panel_value = int(value[0])  # 1-100
        if 1 <= panel_value <= 100:
            speed = panel_value / 2  # 實際速度為 Panel 值的一半
            dual_motor.motor_a.set_speed(speed)
            print(f"Motor A 速度: Panel {panel_value} -> {speed}%")
        else:
            print(f"錯誤：Motor A 速度應為 1-100，收到: {panel_value}")
        # 調整 V0~V4 時，V14、V15 設為 False
        blynk.virtual_write(14, "False")
        blynk.virtual_write(15, "False")
    
    # V4 - Motor_Speed_B (1-100 → 0.5%-50%)
    @blynk.on("V4")
    def v4_handler(value):
        panel_value = int(value[0])  # 1-100
        if 1 <= panel_value <= 100:
            speed = panel_value / 2  # 實際速度為 Panel 值的一半
            dual_motor.motor_b.set_speed(speed)
            print(f"Motor B 速度: Panel {panel_value} -> {speed}%")
        else:
            print(f"錯誤：Motor B 速度應為 1-100，收到: {panel_value}")
        # 調整 V0~V4 時，V14、V15 設為 False
        blynk.virtual_write(14, "False")
        blynk.virtual_write(15, "False")
    
    # V10 - 長按按鈕 1
    @blynk.on("V10")
    def v10_handler(value):
        global is_pressing_v10, press_start_v10, is_triggered_v10
        if value[0] == "1":
            if not is_pressing_v10:
                is_pressing_v10 = True
                press_start_v10 = get_time_ms()
                update_gauge(11, 0)
                blynk.virtual_write(10, 0)
        else:
            if is_pressing_v10 and not is_triggered_v10:
                is_pressing_v10 = False
                press_start_v10 = None
                blynk.virtual_write(11, 0)
            elif is_triggered_v10:
                is_pressing_v10 = False
                blynk.virtual_write(10, 1)
    
    # V12 - 長按按鈕 2
    @blynk.on("V12")
    def v12_handler(value):
        global is_pressing_v12, press_start_v12, is_triggered_v12
        if value[0] == "1":
            if not is_pressing_v12:
                is_pressing_v12 = True
                press_start_v12 = get_time_ms()
                update_gauge(13, 0)
                blynk.virtual_write(12, 0)
        else:
            if is_pressing_v12 and not is_triggered_v12:
                is_pressing_v12 = False
                press_start_v12 = None
                blynk.virtual_write(13, 0)
            elif is_triggered_v12:
                is_pressing_v12 = False
                blynk.virtual_write(12, 1)
    
    # 連接事件
    @blynk.on("connected")
    def connected():
        print("✓ Blynk 已連接")
        # 初始化所有虛擬腳位歸零
        for pin in [0, 1, 2, 3, 4, 10, 11, 12, 13]:
            blynk.virtual_write(pin, 0)
        # 初始化 V14、V15 Label 為 False
        blynk.virtual_write(14, "False")
        blynk.virtual_write(15, "False")
        print("所有 Panel 已初始化歸零")
    
    @blynk.on("disconnected")
    def disconnected():
        print("✗ Blynk 斷線")

# ==================== 主程式 ====================
def main():
    """主程式"""
    global blynk, dual_motor
    
    print("=" * 50)
    print("發球機整合控制系統")
    print("=" * 50)
    
    # 連接 WiFi（持續重試直到成功）
    while not connect_wifi():
        print("WiFi 連接失敗，5 秒後重試...")
        time.sleep(5)
    
    # 初始化硬體
    print("初始化硬體...")
    dual_motor = DualMotor(MOTOR_A_IN1, MOTOR_A_IN2, MOTOR_A_PWM,
                           MOTOR_B_IN1, MOTOR_B_IN2, MOTOR_B_PWM)
    init_servo()
    print("硬體初始化完成")
    
    # 連接 Blynk
    print("正在連接 Blynk...")
    try:
        blynk = BlynkLib.Blynk(BLYNK_AUTH, insecure=True)
        print("Blynk 連接成功!")
    except Exception as e:
        print(f"Blynk 連接失敗: {e}")
        return
    
    # 設定處理器
    setup_handlers()
    
    print("=" * 50)
    print("系統已啟動，等待指令...")
    print("V0/V1: 伺服馬達 | V2: DC馬達開關")
    print("V3: Motor A速度 | V4: Motor B速度")
    print("V10/V11: 長按按鈕1 | V12/V13: 長按按鈕2")
    print("=" * 50)
    
    # 主迴圈
    try:
        while True:
            blynk.run()
            process_all_buttons()
            time.sleep(0.01)  # 10ms 間隔
    except KeyboardInterrupt:
        print("\n程式中斷")
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        # 清理資源
        dual_motor.stop()
        set_servo_speed(0)
        print("程式已結束")

# ==================== 程式進入點 ====================
if __name__ == "__main__":
    main()

"""
ESP8266 360度伺服馬達測試程式
單純測試伺服馬達旋轉功能（無 WiFi/Blynk）
"""

from machine import Pin, PWM
import time

# ==================== 設定區域 ====================
# 伺服馬達設定
SERVO_PIN = 14  # GPIO14 (D5)

# ===================================================

# 初始化伺服馬達
servo_pin = PWM(Pin(SERVO_PIN, Pin.OUT), freq=50, duty=0)

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

# ==================== 主程式 ====================
print("360度伺服馬達互動控制")
print("======================")
print("輸入速度: -100 到 +100")
print("  正數 = 順時針旋轉")
print("  負數 = 逆時針旋轉")
print("  0 = 停止")
print("輸入 'q' 或 'quit' 結束程式")
print("======================\n")

# 初始化：馬達停止
set_servo_speed(0)

try:
    while True:
        # 取得使用者輸入
        user_input = input("請輸入速度 (-100 到 100): ")
        
        # 檢查是否要退出
        if user_input.lower() in ['q', 'quit', 'exit']:
            print("退出程式...")
            break
        
        try:
            # 轉換為整數
            speed = int(user_input)
            
            # 限制範圍
            if speed < -100 or speed > 100:
                print("錯誤: 速度必須在 -100 到 100 之間")
                continue
            
            # 設定馬達速度
            set_servo_speed(speed)
            
            # 顯示狀態
            if speed > 0:
                print(f"✓ 順時針旋轉 (速度: {speed}%)")
            elif speed < 0:
                print(f"✓ 逆時針旋轉 (速度: {abs(speed)}%)")
            else:
                print("✓ 馬達停止")
            
        except ValueError:
            print("錯誤: 請輸入有效的數字\n")

except KeyboardInterrupt:
    print("\n\n程式被中斷...")

finally:
    # 清理：停止馬達
    print("停止馬達...")
    set_servo_speed(0)
    servo_pin.deinit()
    print("程式結束")

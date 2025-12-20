"""
Blynk 發球機控制 - 長按計時機制
用於實現 Image Button (V10) 長按三秒觸發發球機
"""

import network
import time
import BlynkLib
import machine
from machine import Pin

# ==================== 設定區域 ====================
# WiFi 設定
WIFI_SSID = "aron"
WIFI_PASSWORD = "00000000"

# Blynk 設定
BLYNK_AUTH = "O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"

# Pin 設定
BALL_MACHINE_PIN = 5  # GPIO5 控制發球機

# ==================== 計時參數 ====================
LONG_PRESS_TIME = 3000      # 長按觸發時間（毫秒）：3秒
HOLD_TIME = 3000            # 發球後保持時間（毫秒）：3秒
GAUGE_UPDATE_INTERVAL = 30  # 計量表更新間隔（毫秒）

# ==================== 全域狀態變數 ====================
# V10/V11 狀態
press_start_time_v10 = None          # V10 按下開始時間
is_pressing_v10 = False              # V10 是否正在按下
is_triggered_v10 = False             # V10 是否已觸發發球
trigger_end_time_v10 = None          # V10 發球結束時間

# V12/V13 狀態
press_start_time_v12 = None          # V12 按下開始時間
is_pressing_v12 = False              # V12 是否正在按下
is_triggered_v12 = False             # V12 是否已觸發發球
trigger_end_time_v12 = None          # V12 發球結束時間

blynk_instance = None            # Blynk 實例參考

# ==================== 輔助函數 ====================

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
            return True
        else:
            print("\nWiFi 連接失敗!")
            return False
    else:
        print("WiFi 已連接")
        print("IP 地址:", wlan.ifconfig()[0])
        return True

def get_current_time_ms():
    """取得目前時間（毫秒）"""
    try:
        return time.ticks_ms()
    except:
        return int(time.time() * 1000)

def calculate_gauge_value(elapsed_ms):
    """
    根據經過時間計算計量表值（0-100）
    
    Args:
        elapsed_ms: 經過時間（毫秒）
    
    Returns:
        計量表值（0-100）
    """
    gauge_value = int((elapsed_ms / LONG_PRESS_TIME) * 100)
    return min(100, gauge_value)  # 最大值為 100

def update_gauge(gauge_pin, gauge_value):
    """
    更新計量表
    
    Args:
        gauge_pin: 計量表虛擬引腳號 (11 或 13)
        gauge_value: 計量表值（0-100）
    """
    if blynk_instance:
        blynk_instance.virtual_write(gauge_pin, gauge_value)
        print(f"[V{gauge_pin}] 計量表更新: {gauge_value}")

def trigger_ball_machine(button_pin, is_triggered):
    """觸發發球機"""
    if not is_triggered:
        trigger_end_time = get_current_time_ms()
        
        # 發球機啟動
        Pin(BALL_MACHINE_PIN, Pin.OUT).on()
        print(f"[V{button_pin}] 發球機已觸發！")
        
        # 按鈕設為 1（此時計量表已經是 100）
        if blynk_instance:
            blynk_instance.virtual_write(button_pin, 1)  # 按鈕設為 1（Image Button 切換圖片 + LED 亮起）
        
        return True, trigger_end_time
    return is_triggered, None

def reset_button(button_pin, gauge_pin):
    """重置按鈕狀態"""
    # 關閉發球機
    Pin(BALL_MACHINE_PIN, Pin.OUT).off()
    print(f"[V{button_pin}] 發球機已停止")
    
    # 更新 Blynk：先歸零計量表，再將按鈕設為 0
    if blynk_instance:
        blynk_instance.virtual_write(gauge_pin, 0)  # 計量表先設為 0
        blynk_instance.virtual_write(button_pin, 0)  # 按鈕最後設為 0（Image Button 恢復原圖片）
    
    # 返回重置後的狀態
    return False, None, False, None  # is_pressing, press_start_time, is_triggered, trigger_end_time

def process_single_button_logic(button_pin, gauge_pin, is_pressing, press_start_time, is_triggered, trigger_end_time):
    """
    處理單個按鈕邏輯
    
    Returns:
        tuple: (is_pressing, press_start_time, is_triggered, trigger_end_time)
    """
    current_time = get_current_time_ms()
    
    # 1. 如果正在按下，計算經過時間
    if is_pressing and press_start_time is not None:
        elapsed_time = current_time - press_start_time
        
        # 更新計量表
        if elapsed_time % GAUGE_UPDATE_INTERVAL < 30:  # 定期更新
            gauge_value = calculate_gauge_value(elapsed_time)
            update_gauge(gauge_pin, gauge_value)
        
        # 檢查是否達到長按時間
        if elapsed_time >= LONG_PRESS_TIME and not is_triggered:
            is_triggered, trigger_end_time = trigger_ball_machine(button_pin, is_triggered)
    
    # 2. 如果已觸發，檢查是否需要復位
    if is_triggered and trigger_end_time is not None:
        hold_elapsed_time = current_time - trigger_end_time
        
        # 在 HOLD_TIME 毫秒後重置
        if hold_elapsed_time >= HOLD_TIME:
            is_pressing, press_start_time, is_triggered, trigger_end_time = reset_button(button_pin, gauge_pin)
    
    return is_pressing, press_start_time, is_triggered, trigger_end_time

def process_button_logic():
    """
    處理所有按鈕邏輯
    應該在主迴圈中定期調用
    """
    global press_start_time_v10, is_pressing_v10, is_triggered_v10, trigger_end_time_v10
    global press_start_time_v12, is_pressing_v12, is_triggered_v12, trigger_end_time_v12
    
    # 處理 V10/V11
    is_pressing_v10, press_start_time_v10, is_triggered_v10, trigger_end_time_v10 = \
        process_single_button_logic(10, 11, is_pressing_v10, press_start_time_v10, is_triggered_v10, trigger_end_time_v10)
    
    # 處理 V12/V13
    is_pressing_v12, press_start_time_v12, is_triggered_v12, trigger_end_time_v12 = \
        process_single_button_logic(12, 13, is_pressing_v12, press_start_time_v12, is_triggered_v12, trigger_end_time_v12)

def main():
    """主程式"""
    global blynk_instance
    global is_pressing_v10, press_start_time_v10, is_triggered_v10
    global is_pressing_v12, press_start_time_v12, is_triggered_v12
    
    # 連接 WiFi
    if not connect_wifi():
        print("無法連接 WiFi，程式結束")
        return
    
    # 連接 Blynk
    print("正在連接 Blynk...")
    try:
        blynk_instance = BlynkLib.Blynk(BLYNK_AUTH, insecure=True)
        print("Blynk 連接成功!")
    except Exception as e:
        print(f"Blynk 連接失敗: {e}")
        return
    
    # ==================== Blynk 虛擬腳位處理 ====================
    
    # V10 - Image Button (Push Mode - 持續按住)
    @blynk_instance.on("V10")
    def v10_handler(value):
        global is_pressing_v10, press_start_time_v10, is_triggered_v10
        
        button_value = value[0]
        print(f"[V10] 收到按鈕狀態: {button_value}")
        
        if button_value == "1":  # 按下
            if not is_pressing_v10:
                is_pressing_v10 = True
                press_start_time_v10 = get_current_time_ms()
                print("[V10] 按鈕按下 - 開始計時")
                update_gauge(11, 0)  # 重置計量表為 0
                # 立即將 V10 設為 0（Push 時會自動變 1，我們需要控制它）
                if blynk_instance:
                    blynk_instance.virtual_write(10, 0)
        else:  # 鬆開
            if is_pressing_v10 and not is_triggered_v10:
                print("[V10] 按鈕鬆開 - 未達到觸發時間")
                is_pressing_v10 = False
                press_start_time_v10 = None
                # 只有在未觸發的情況下才歸零 V11
                if blynk_instance:
                    blynk_instance.virtual_write(11, 0)
            elif is_triggered_v10:
                # 已觸發時，保持 V10 為 1（放開手指後三秒內仍保持觸發狀態）
                is_pressing_v10 = False
                print("[V10] 按鈕鬆開 - 已觸發，保持 V10 = 1")
                if blynk_instance:
                    blynk_instance.virtual_write(10, 1)  # 重新設為 1 以保持觸發狀態
    
    # V11 - Radial Gauge (只讀，由程式更新)
    @blynk_instance.on("V11")
    def v11_handler(value):
        # 這個回調通常不會被觸發（因為 V11 只由程式寫入）
        print(f"[V11] 計量表值: {value[0]}")
    
    # V12 - Image Button (Push Mode - 持續按住)
    @blynk_instance.on("V12")
    def v12_handler(value):
        global is_pressing_v12, press_start_time_v12, is_triggered_v12
        
        button_value = value[0]
        print(f"[V12] 收到按鈕狀態: {button_value}")
        
        if button_value == "1":  # 按下
            if not is_pressing_v12:
                is_pressing_v12 = True
                press_start_time_v12 = get_current_time_ms()
                print("[V12] 按鈕按下 - 開始計時")
                update_gauge(13, 0)  # 重置計量表為 0
                # 立即將 V12 設為 0（Push 時會自動變 1，我們需要控制它）
                if blynk_instance:
                    blynk_instance.virtual_write(12, 0)
        else:  # 鬆開
            if is_pressing_v12 and not is_triggered_v12:
                print("[V12] 按鈕鬆開 - 未達到觸發時間")
                is_pressing_v12 = False
                press_start_time_v12 = None
                # 只有在未觸發的情況下才歸零 V13
                if blynk_instance:
                    blynk_instance.virtual_write(13, 0)
            elif is_triggered_v12:
                # 已觸發時，保持 V12 為 1（放開手指後三秒內仍保持觸發狀態）
                is_pressing_v12 = False
                print("[V12] 按鈕鬆開 - 已觸發，保持 V12 = 1")
                if blynk_instance:
                    blynk_instance.virtual_write(12, 1)  # 重新設為 1 以保持觸發狀態
    
    # V13 - Radial Gauge (只讀，由程式更新)
    @blynk_instance.on("V13")
    def v13_handler(value):
        # 這個回調通常不會被觸發（因為 V13 只由程式寫入）
        print(f"[V13] 計量表值: {value[0]}")
    
    # 連接事件
    @blynk_instance.on("connected")
    def blynk_connected():
        print("✓ 已連接到 Blynk 伺服器")
        # 初始化虛擬腳位
        if blynk_instance:
            blynk_instance.virtual_write(10, 0)
            blynk_instance.virtual_write(11, 0)
            blynk_instance.virtual_write(12, 0)
            blynk_instance.virtual_write(13, 0)
    
    # 斷線事件
    @blynk_instance.on("disconnected")
    def blynk_disconnected():
        print("✗ 與 Blynk 伺服器斷開連接")
    
    # ==================== 主迴圈 ====================
    print("=" * 50)
    print("發球機長按控制系統啟動")
    print(f"長按觸發時間: {LONG_PRESS_TIME}ms")
    print(f"發球保持時間: {HOLD_TIME}ms")
    print("=" * 50)
    print("等待按鈕輸入...")
    
    try:
        while True:
            # Blynk 通信
            blynk_instance.run()
            
            # 處理按鈕邏輯
            process_button_logic()
            
            time.sleep(0.01)  # 10ms 的迴圈間隔
            
    except KeyboardInterrupt:
        print("\n程式被中止")
    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        # 清理資源
        reset_button()
        print("程式已結束")

# ==================== 程式進入點 ====================
if __name__ == "__main__":
    main()

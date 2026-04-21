from hm10_esp32 import HM10ESP32Bridge
import time
import sys
import threading

def get_connected_bridge(port, expected_name):
    """
    連線核心邏輯：處理改名、重位與狀態檢查。
    成功則回傳 bridge 物件，失敗回傳 None。
    """
    try:
        bridge = HM10ESP32Bridge(port=port)
        
        # 1. 檢查模組名稱
        current_name = bridge.get_hm10_name()
        if current_name != expected_name:
            print(f"[BT] 名稱不符 (目前: {current_name})，正在更新為: {expected_name}...")
            if bridge.set_hm10_name(expected_name):
                print("✅ 名稱更新成功，正在重置模組...")
                bridge.reset()
                time.sleep(2) # 給硬體時間重啟
                bridge.ser.close() # 關閉 Port 以便重新初始化
                bridge = HM10ESP32Bridge(port=port)
            else:
                print("❌ 無法變更名稱。")
                return None

        # 2. 檢查連線狀態
        print("[BT] 正在檢查連線狀態...")
        status = bridge.get_status()
        if status != "CONNECTED":
            print(f"⚠️ 狀態：{status}。請確認車車電源已開啟且紅燈停止閃爍。")
            return None
        
        return bridge
    except Exception as e:
        print(f"❌ 連線發生例外錯誤: {e}")
        return None

def background_listener(bridge):
    """背景監聽執行緒"""
    while True:
        msg = bridge.listen()
        if msg:
            print(f"\r[HM10]: {msg.strip()}")
            print("You: ", end="", flush=True)
        time.sleep(0.1)

# --- 測試區塊：直接執行此檔案時才會跑 ---
if __name__ == "__main__":
    TEST_PORT = 'COM3' # 記得確認你的 Port
    TEST_NAME = 'carcar'
    
    print(f"--- 啟動藍牙測試模式 (Port: {TEST_PORT}) ---")
    bridge_obj = get_connected_bridge(TEST_PORT, TEST_NAME)
    
    if bridge_obj:
        print(f"✨ 連線成功！已連接至 {TEST_NAME}")
        # 開啟背景監聽
        t = threading.Thread(target=background_listener, args=(bridge_obj,), daemon=True)
        t.start()

        try:
            while True:
                user_msg = input("You: ")
                if user_msg.lower() in ['exit', 'quit']: break
                if user_msg: bridge_obj.send(user_msg)
        except KeyboardInterrupt:
            pass
        print("\n測試結束。")
    else:
        print("連線失敗，請檢查硬體。")
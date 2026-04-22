#define DEBUG  // debug flag

#include <MFRC522.h>
#include <SPI.h>

/*===========================定義腳位================================*/
// 馬達腳位 (依照你們原本的 AIN, BIN 設定)
#define MotorR_I1 8     // BIN1
#define MotorR_I2 9     // BIN2
#define MotorR_PWMR 11  // PWMB
#define MotorL_I3 7     // AIN1
#define MotorL_I4 6     // AIN2
#define MotorL_PWML 10  // PWMA

// 循線模組腳位
#define IRpin_LL A7     // L3
#define IRpin_L  A6     // L2
#define IRpin_M  A5     // M
#define IRpin_R  A4     // R2
#define IRpin_RR A3     // R3

// RFID 腳位
#define RST_PIN 3       
#define SS_PIN 2        
MFRC522 mfrc522(SS_PIN, RST_PIN);

#define CUSTOM_NAME "carcar"

/*===========================全域變數===========================*/
int _Tp = 125;           
bool state = false;       // 車子狀態 (true: 可動, false: 停止)
int l3 = 0, l2 = 0, m = 0, r2 = 0, r3 = 0; // 感測器讀值狀態

/*=====引入自定義標頭檔 (順序很重要) =====*/
#include "bluetooth.h"
#include "track.h"
#include "node.h"
#include "RFID.h"

/*============setup============*/
void setup() {
    Serial.begin(115200);
    Serial3.begin(9600); // 假設 HM-10 已經透過原本的腳本設定好 9600

    SPI.begin();
    mfrc522.PCD_Init();

    pinMode(MotorR_I1, OUTPUT); pinMode(MotorR_I2, OUTPUT); pinMode(MotorR_PWMR, OUTPUT);
    pinMode(MotorL_I3, OUTPUT); pinMode(MotorL_I4, OUTPUT); pinMode(MotorL_PWML, OUTPUT);
    pinMode(IRpin_LL, INPUT); pinMode(IRpin_L, INPUT); pinMode(IRpin_M, INPUT);
    pinMode(IRpin_R, INPUT); pinMode(IRpin_RR, INPUT);

    Serial.println("System Ready!");
    Serial.println("Waiting for Bluetooth Connection...");
    clear();
    
}

/*===========================主迴圈===========================*/
void loop() {
    BT_Process(); // 處理藍芽與 RFID
    
    if (!state) {
        MotorWriting(0, 0);
    } else {
        Search();
    }
}

// 整合藍芽收發與 RFID 的邏輯

void BT_Process() {
    // 1. 接收藍芽指令並放入 Queue
    BT_CMD cmd = ask_BT();
    if (cmd == CMD_W) in(STRAIGHT);
    else if (cmd == CMD_A) in(LEFT);
    else if (cmd == CMD_S) in(BACK);
    else if (cmd == CMD_D) in(RIGHT);
    else if (cmd == CMD_START) {state = true;  clear();}
    else if (cmd == CMD_STOP) in(STOP);
    // 2. 處理 RFID
    byte idSize;
    byte* id = rfid(idSize);
    if (id != 0) {
        send_byte(id, idSize); // 讀到卡片就傳給藍芽
    }
}

void Search() {
    if (!isEmpty()) {
        bool onNode = false;
        while (!onNode) {
            BT_Process(); // 移動中也要能收指令跟讀卡
            tracking(_Tp);
            // Serial.println("tracking9");
            // Serial3.println("tracking9");
            if ((l3 + l2 + m + r2 + r3) == 5) {
                onNode = true;
            }
        }
        Turn(out()); // 到達節點，執行佇列中的轉向
        Serial.println("node");
        Serial3.println("node");
        Serial3.print('\n');
        // print_queue();
    } else {
        MotorWriting(0, 0); // 沒有指令時停下 (或可改成原地循線)
    }
}
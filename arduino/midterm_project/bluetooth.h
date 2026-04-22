#ifndef BLUETOOTH_H
#define BLUETOOTH_H

enum BT_CMD {
    NOTHING,
    CMD_W,
    CMD_A,
    CMD_S,
    CMD_D,
    CMD_START,
    CMD_STOP
};

BT_CMD ask_BT() {
    BT_CMD message = NOTHING;
    if (Serial3.available()) {
        char cmd = Serial3.read();
        if (cmd == 'F' || cmd == 'f') message = CMD_W;
        else if (cmd == 'L' || cmd == 'l') message = CMD_A;
        else if (cmd == 'B' || cmd == 'b') message = CMD_S;
        else if (cmd == 'R' || cmd == 'r') message = CMD_D;
        else if (cmd == 'S' || cmd == 's') message = CMD_START;
        else if (cmd == 'C' || cmd == 'c') message = CMD_STOP;

#ifdef DEBUG
        Serial.print("cmd : "); Serial.println(cmd);
#endif
    }
    return message;
}

// send UID back through Serial3
void send_byte(byte* id, byte idSize) {
    String uidStr = "UID:";
    for (byte i = 0; i < idSize; i++) {
        uidStr += (id[i] < 0x10 ? " 0" : " ");
        uidStr += String(id[i], HEX);
    }
    uidStr.toUpperCase();
    
    Serial3.println(uidStr); // 傳給手機
    Serial.println(uidStr);  // 顯示在電腦
}

#endif
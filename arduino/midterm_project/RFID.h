#ifndef RFID_H
#define RFID_H

extern MFRC522 mfrc522; // 從主程式引用

byte* rfid(byte& idSize) {
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
        byte* id = mfrc522.uid.uidByte;  
        idSize = mfrc522.uid.size;       

#ifdef DEBUG
        Serial.print("UID Size: ");
        Serial.println(idSize);
        for (byte i = 0; i < idSize; i++) { 
            Serial.print(id[i] < 0x10 ? " 0" : " ");
            Serial.print(id[i], HEX); 
        }
        Serial.println();
#endif
        mfrc522.PICC_HaltA();  
        mfrc522.PCD_StopCrypto1(); // 停止加密通訊
        return id;
    }
    return 0;
}

#endif
#ifndef TRACK_H
#define TRACK_H

extern int _Tp;
extern int l3, l2, m, r2, r3;

double lastError = 0, error, sum;
double Kd = 10;
int Kp = 25; double w2 = 1; double w3 = 3;
bool firstrun = true;

void MotorWriting(double vL, double vR) {
    if (vL > 0) {
        digitalWrite(MotorL_I3, LOW);
        digitalWrite(MotorL_I4, HIGH);
    } else {
        vL *= -1;
        digitalWrite(MotorL_I3, HIGH);
        digitalWrite(MotorL_I4, LOW);
    }
    
    if (vR > 0) {
        digitalWrite(MotorR_I1, LOW);
        digitalWrite(MotorR_I2, HIGH);
    } else {
        vR *= -1;
        digitalWrite(MotorR_I1, HIGH);
        digitalWrite(MotorR_I2, LOW);
    }
    
    analogWrite(MotorL_PWML, vL);
    analogWrite(MotorR_PWMR, vR);
}

void read_sensors() {
    int l3_ = analogRead(IRpin_LL);
    int l2_ = analogRead(IRpin_L);
    int m_  = analogRead(IRpin_M);
    int r2_ = analogRead(IRpin_R);
    int r3_ = analogRead(IRpin_RR);

    l3 = (l3_ > 100) ? 1 : 0;
    l2 = (l2_ > 100) ? 1 : 0;
    m  = (m_ > 100) ? 1 : 0;
    r2 = (r2_ > 100) ? 1 : 0;
    r3 = (r3_ > 200) ? 1 : 0;

    // Serial3.print(l3_); // 將數值印出來
    // Serial3.print("  ");
    // Serial3.print(l2_); // 將數值印出來
    // Serial3.print("  ");
    // Serial3.print(m_); // 將數值印出來
    // Serial3.print("  ");
    // Serial3.print(r2_); // 將數值印出來
    // Serial3.print("  ");
    // Serial3.println(r3_); // 將數值印出來
    // Serial3.println('\n');
}

void tracking(int Tp) {
    read_sensors();
    sum = l3 + l2 + m + r2 + r3;
    
    if (sum == 0) {
        error = lastError; 
    } else {
        error = double(l3 * (-w3) + l2 * (-w2) + r2 * w2 + r3 * w3) / sum;
    }
    
    if (firstrun) {
        lastError = error;
        firstrun = false;
    }
    
    double dError = error - lastError;
    double powerCorrection = (Kp * error + Kd * dError);
    lastError = error;
    
    int vR = Tp - powerCorrection;
    int vL = Tp + powerCorrection;  
    
    if (vR > 255) vR = 255; else if (vR < -255) vR = -255;
    if (vL > 255) vL = 255; else if (vL < -255) vL = -255;
    // if (vL > vR) Serial3.println("RRR");
    // else if (vR > vL) Serial3.println("LLL");
    MotorWriting(vL, vR); 

    lastError = 0;
    firstrun = true;
}

void back_tracking(int Tp) {
    Tp *= -1;
    read_sensors();
    sum = l3 + l2 + m + r2 + r3;
    
    if (sum == 0) {
        error = lastError; 
    } else {
        error = double(l3 * (-w3) + l2 * (-w2) + r2 * w2 + r3 * w3) / sum;
    }
    
    if (firstrun) {
        lastError = error;
        firstrun = false;
    }
    
    double dError = error - lastError;
    double powerCorrection = (Kp * error + Kd * dError);
    lastError = error;
    
    int vR = Tp + powerCorrection;
    int vL = Tp - powerCorrection;  
    
    if (vR > 255) vR = 255; else if (vR < -255) vR = -255;
    if (vL > 255) vL = 255; else if (vL < -255) vL = -255;
    // if (vL > vR) Serial3.println("RRR");
    // else if (vR > vL) Serial3.println("LLL");
    MotorWriting(vL, vR); 

    lastError = 0;
    firstrun = true;
}
#endif
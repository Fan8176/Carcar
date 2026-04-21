#ifndef NODE_H
#define NODE_H

extern int _Tp;
extern int m;
extern void MotorWriting(double vL, double vR);
extern void read_sensors();

enum Turn_t {LEFT, RIGHT, BACK, STRAIGHT};

#define MAX_Q 20
Turn_t queue[MAX_Q];
int head = 0;        
int tail = 0;        
int qCount = 0;      

bool isFull() { return qCount >= MAX_Q; }
bool isEmpty() { return qCount == 0; }

void in(Turn_t move) {
    if (!isFull()) {
        queue[tail] = move;
        tail = (tail + 1) % MAX_Q;
        qCount++;
    }
}

Turn_t out() {
    if (!isEmpty()) {
        Turn_t move = queue[head];
        head = (head + 1) % MAX_Q;
        qCount--;
        // if (move == STRAIGHT){ 
        //     Serial.println("straight9");
        //     Serial3.println("straight9");
        // }
        // else if (move == BACK){ 
        //     Serial.println("back9");
        //     Serial3.println("back9");
        // }
        // else if (move == RIGHT){ 
        //     Serial.println("right");
        //     Serial3.println("right");
        // }
        // else if (move == LEFT){ 
        //     Serial.println("left9");
        //     Serial3.println("left9");
        // }        
        return move;
    }
    return STRAIGHT; 
}

void Turn(Turn_t targetDir) {
    // if (targetDir == STRAIGHT) {
    //     MotorWriting(_Tp, _Tp); delay(500); //待測
    // }
    // else{
        if (targetDir == BACK) {
            MotorWriting(75, -75); delay(770); 
            MotorWriting(62, -62); 
        } else {
            MotorWriting(_Tp, _Tp); delay(325); // 先置中
            if (targetDir == LEFT) {
                MotorWriting(-75, 75); delay(385); 
                MotorWriting(-62, 62); 
            } else if (targetDir == RIGHT) {
                MotorWriting(75, -75); delay(385); 
                MotorWriting(62, -62); 
            }
        }
    // }
    m = 0;
    while (m == 0) {
        read_sensors(); 
    }
    MotorWriting(0, 0);
}

#endif
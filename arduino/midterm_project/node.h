#ifndef NODE_H
#define NODE_H

extern int _Tp;
extern int m;
extern void MotorWriting(double vL, double vR);
extern void read_sensors();

enum Turn_t {LEFT, RIGHT, BACK, STRAIGHT,STOP};

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


void clear() {
    head = 0;
    tail = 0;
    qCount = 0;
    Serial3.println("queue cleared");
}

Turn_t out() {
    if (!isEmpty()) {
        Turn_t move = queue[head];
        head = (head + 1) % MAX_Q;
        qCount--;

        // if (move == STRAIGHT) Serial3.println('W');
        // else if (move == RIGHT) Serial3.println('D');
        // else if (move == LEFT) Serial3.println('A');
        // else if (move == BACK) Serial3.println('S');
        /*else*/ if (move == STOP) {
            MotorWriting(0,0);
            delay(5000);
            clear();
        }
        return move;
    }
    return STRAIGHT; 
}

// char queue_buff[MAX_Q];
// void print_queue() {
//     for (int i = 0 ; i < qCount ; i++){
//         if (queue[i] == STRAIGHT) queue_buff[i] = 'f';
//         else if (queue[i] == BACK) queue_buff[i] = 'b';
//         else if (queue[i] == RIGHT) queue_buff[i] = 'r';
//         else if (queue[i] == LEFT) queue_buff[i] = 'l';
//     }
    
//     Serial3.println("pq:");
//     Serial3.println('\n');
//     for (int i = 0 ; i < qCount ; i++){
//         Serial3.print(queue_buff[i]);
//     }
// }

int Tcs; // time constant
int RTcs; // rotating time constant
int Rcs; // rotating constant 


void Turn(Turn_t targetDir){
  
  if(targetDir == BACK){
    MotorWriting(75,-75); delay(750);
    MotorWriting(60,-60); 
  } else {
    MotorWriting(_Tp,_Tp); delay(325); // 先置中
    // MotorWriting(0,0); delay(100);
    if(targetDir == LEFT){
      MotorWriting(-75,75); delay(375); // 旋轉
      MotorWriting(-60,60); 
    }else if(targetDir == RIGHT){
      MotorWriting(75,-75); delay(375); // 旋轉
      MotorWriting(60,-60); 
    }
  }
  m = 0;
  while(m == 0){
    read_sensors(); 
  }

  MotorWriting(0,0);
}


#endif
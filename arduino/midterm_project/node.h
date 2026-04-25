#ifndef NODE_H
#define NODE_H

extern int _Tp;
extern int m;
extern void MotorWriting(double vL, double vR);
extern void read_sensors();
extern bool backing;
extern int mode;
extern float rate;

enum Turn_t {LEFT, RIGHT, BACK, BACKT, STRAIGHT, STOP};

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
  
  // if(targetDir == BACKT){
  //   if (mode == 0){
  //     MotorWriting(-_Tp,-_Tp); delay(600/rate); // 先置中
  //     read_sensors();
  //     if (m == 0){
  //       if (r2 + r3 >= 1) MotorWriting(-75,75);
  //       else if (l2 + l3 >= 1) MotorWriting(75,-75);
  //     }
  //   }
  //   else if (mode == 1){
  //     MotorWriting(-_Tp,-_Tp-15); delay(600/rate);
  //     // MotorWriting(0,0); delay(5000);
  //   }
  //   if (mode == -1){
  //     MotorWriting(-_Tp-15,-_Tp); delay(600/rate);
  //     // MotorWriting(0,0); delay(5000);
  //   }
    
  //   backing = true;
  // }
  // else backing = false;

  // if (backing)
  if(targetDir == BACK){
    MotorWriting(125,-125); delay(400);
    MotorWriting(100,-100); delay (150);
    MotorWriting(60,-60);
  }

  else if(targetDir == STRAIGHT){
    if (mode == 0){
      MotorWriting(_Tp,_Tp); delay(325/rate);
      read_sensors();
      if (m == 0){
        if (r2 + r3 >= 1) MotorWriting(75,-75);
        else if (l2 + l3 >= 1) MotorWriting(-75,75);
      }
    }
    else if (mode == 1){
      MotorWriting(_Tp+14.5*rate,_Tp); delay(325/rate);
      read_sensors();
      if (m == 0){
        if (r2 + r3 >= 1) MotorWriting(75,-75);
        else if (l2 + l3 >= 1) MotorWriting(-75,75);
      }
      // MotorWriting(0,0); delay(5000);
    }
    if (mode == -1){
      MotorWriting(_Tp,_Tp+14.5*rate); delay(325/rate);
      read_sensors();
      if (m == 0){
        if (r2 + r3 >= 1) MotorWriting(75,-75);
        else if (l2 + l3 >= 1) MotorWriting(-75,75);
      }
      // MotorWriting(0,0); delay(5000);
    }
  }

  // else {
  //   MotorWriting(_Tp,_Tp); delay(325); // 先置中
  //   // MotorWriting(0,0); delay(100);
  //   if(targetDir == LEFT){
  //     MotorWriting(-75,75); delay(375); // 旋轉
  //     MotorWriting(-60,60); 
  //   }else if(targetDir == RIGHT){
  //     MotorWriting(75,-75); delay(375); // 旋轉
  //     MotorWriting(60,-60); 
  //   }
  // }

  else {
    if(targetDir == LEFT){
      MotorWriting(35,175); delay(350); // 旋轉 
    }
    else if(targetDir == RIGHT){
      MotorWriting(175,35); delay(350); // 旋轉
    }
  }

  m = 0;
  while(m == 0){
    read_sensors(); 
  }
  MotorWriting(50,50);
}


#endif
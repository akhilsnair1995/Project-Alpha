/*
 * Project Alpha: Wall-E Autonomous Companion Rover
 * Spinal Cord Microcontroller Firmware (Arduino Uno / Nano)
 * 
 * Hardware Responsibilities:
 * - Deterministic, jitter-free 50Hz PWM for Pan & Tilt servos (MG90S)
 * - 8-bit Phase-correct PWM for DRV8833 Dual H-Bridge crawler tracks
 * - Hardware safety watchdog timer (cuts motors if Pi freezes > 300ms)
 * - Microsecond cliff sensor interrupts (TCRT5000 active LOW table edge reflex)
 * 
 * Pinout Mappings:
 * - Pin 9:  Pan Servo (MG90S)
 * - Pin 10: Tilt Servo (MG90S)
 * - Pin 3:  DRV8833 IN1 (Left Motor Forward, PWM)
 * - Pin 5:  DRV8833 IN2 (Left Motor Reverse, PWM)
 * - Pin 6:  DRV8833 IN3 (Right Motor Forward, PWM)
 * - Pin 11: DRV8833 IN4 (Right Motor Reverse, PWM)
 * - Pin 2:  TCRT5000 Left Cliff Sensor (Interrupt INT0, Active LOW)
 * - Pin 4:  TCRT5000 Right Cliff Sensor (Active LOW)
 * - Pin 7:  TTP223 Head Pet Touch Sensor (Active HIGH)
 * - Pin 8:  Dock Charging Contact Sensor (Active HIGH)
 * - Pin 13: Built-in LED (Heartbeat / Watchdog Indicator)
 */

#include <Servo.h>

// Actuator Pins
const int PIN_SERVO_PAN    = 9;
const int PIN_SERVO_TILT   = 10;
const int PIN_M_L_FWD      = 3;
const int PIN_M_L_REV      = 5;
const int PIN_M_R_FWD      = 6;
const int PIN_M_R_REV      = 11;

// Sensor Pins
const int PIN_CLIFF_LEFT   = 2;
const int PIN_CLIFF_RIGHT  = 4;
const int PIN_TOUCH_HEAD   = 7;
const int PIN_DOCK_CHARGE  = 8;
const int PIN_LED_WATCHDOG = 13;

// Servos
Servo servoPan;
Servo servoTilt;

// State Variables
float currentPan = 0.0;
float currentTilt = 0.0;
int motorLeftSpeed = 0;   // -255 to 255
int motorRightSpeed = 0;  // -255 to 255

// Safety & Watchdog
unsigned long lastCommandTime = 0;
const unsigned long WATCHDOG_TIMEOUT_MS = 300;
bool watchdogTriggered = false;
volatile bool cliffInterruptTriggered = false;

// Serial Buffer
char serialBuffer[64];
byte bufferIdx = 0;

// Cliff interrupt handler
void onCliffDetected() {
  // Microsecond instant hardware reflex! Cut motor power immediately
  analogWrite(PIN_M_L_FWD, 0);
  analogWrite(PIN_M_L_REV, 0);
  analogWrite(PIN_M_R_FWD, 0);
  analogWrite(PIN_M_R_REV, 0);
  motorLeftSpeed = 0;
  motorRightSpeed = 0;
  cliffInterruptTriggered = true;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; } // Wait for serial port

  pinMode(PIN_LED_WATCHDOG, OUTPUT);
  digitalWrite(PIN_LED_WATCHDOG, HIGH);

  // Motor outputs
  pinMode(PIN_M_L_FWD, OUTPUT);
  pinMode(PIN_M_L_REV, OUTPUT);
  pinMode(PIN_M_R_FWD, OUTPUT);
  pinMode(PIN_M_R_REV, OUTPUT);
  stopMotors();

  // Attach Servos
  servoPan.attach(PIN_SERVO_PAN, 600, 2400);
  servoTilt.attach(PIN_SERVO_TILT, 800, 2200);
  setHeadPose(0.0, 0.0);

  // Sensor inputs
  pinMode(PIN_CLIFF_LEFT, INPUT_PULLUP);
  pinMode(PIN_CLIFF_RIGHT, INPUT_PULLUP);
  pinMode(PIN_TOUCH_HEAD, INPUT);
  pinMode(PIN_DOCK_CHARGE, INPUT);

  // Attach instant interrupt to left cliff sensor
  attachInterrupt(digitalPinToInterrupt(PIN_CLIFF_LEFT), onCliffDetected, FALLING);

  lastCommandTime = millis();
  Serial.println(F("ALPHA_SPINAL_CORE_READY v1.0"));
}

void setHeadPose(float pan, float tilt) {
  currentPan = constrain(pan, -85.0, 85.0);
  currentTilt = constrain(tilt, -25.0, 35.0);

  // Map -90..+90 to 0..180 servo degrees
  int panAngle = map((int)currentPan, -90, 90, 0, 180);
  int tiltAngle = map((int)currentTilt, -90, 90, 0, 180);

  servoPan.write(panAngle);
  servoTilt.write(tiltAngle);
}

void applyMotorPwm(int fwdPin, int revPin, int speed) {
  speed = constrain(speed, -255, 255);
  if (speed > 0) {
    analogWrite(fwdPin, speed);
    analogWrite(revPin, 0);
  } else if (speed < 0) {
    analogWrite(fwdPin, 0);
    analogWrite(revPin, abs(speed));
  } else {
    analogWrite(fwdPin, 0);
    analogWrite(revPin, 0);
  }
}

void stopMotors() {
  applyMotorPwm(PIN_M_L_FWD, PIN_M_L_REV, 0);
  applyMotorPwm(PIN_M_R_FWD, PIN_M_R_REV, 0);
  motorLeftSpeed = 0;
  motorRightSpeed = 0;
}

void parseSerialCommand(char* cmd) {
  lastCommandTime = millis();
  watchdogTriggered = false;
  digitalWrite(PIN_LED_WATCHDOG, HIGH);

  if (cmd[0] == 'H' || cmd[0] == 'h') {
    // Head command: H <pan> <tilt>
    float p = 0, t = 0;
    if (sscanf(cmd + 1, "%f %f", &p, &t) == 2) {
      setHeadPose(p, t);
      Serial.print(F("OK H "));
      Serial.print(p, 1);
      Serial.print(F(" "));
      Serial.println(t, 1);
    }
  } else if (cmd[0] == 'M' || cmd[0] == 'm') {
    // Motor command: M <left> <right>
    int l = 0, r = 0;
    if (sscanf(cmd + 1, "%d %d", &l, &r) == 2) {
      // Check cliff sensors before driving forward
      bool cliffRight = (digitalRead(PIN_CLIFF_RIGHT) == LOW);
      if ((l > 0 || r > 0) && (cliffInterruptTriggered || cliffRight)) {
        stopMotors();
        Serial.println(F("ERR CLIFF_INTERLOCK"));
        return;
      }
      cliffInterruptTriggered = false;
      motorLeftSpeed = l;
      motorRightSpeed = r;
      applyMotorPwm(PIN_M_L_FWD, PIN_M_L_REV, motorLeftSpeed);
      applyMotorPwm(PIN_M_R_FWD, PIN_M_R_REV, motorRightSpeed);
      Serial.print(F("OK M "));
      Serial.print(l);
      Serial.print(F(" "));
      Serial.println(r);
    }
  } else if (strcasecmp(cmd, "STOP") == 0) {
    stopMotors();
    Serial.println(F("OK STOP"));
  } else if (strcasecmp(cmd, "PING") == 0) {
    Serial.println(F("PONG"));
  } else if (strcasecmp(cmd, "STATUS") == 0) {
    Serial.print(F("STATUS PAN:"));
    Serial.print(currentPan, 1);
    Serial.print(F(" TILT:"));
    Serial.print(currentTilt, 1);
    Serial.print(F(" ML:"));
    Serial.print(motorLeftSpeed);
    Serial.print(F(" MR:"));
    Serial.println(motorRightSpeed);
  } else {
    Serial.println(F("ERR UNKNOWN_CMD"));
  }
}

void loop() {
  unsigned long now = millis();

  // 1. Process incoming Serial bytes from Pi
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufferIdx > 0) {
        serialBuffer[bufferIdx] = '\0';
        parseSerialCommand(serialBuffer);
        bufferIdx = 0;
      }
    } else {
      if (bufferIdx < sizeof(serialBuffer) - 1) {
        serialBuffer[bufferIdx++] = c;
      }
    }
  }

  // 2. Watchdog Check: Auto-stop if no serial heartbeat in 300ms
  if (!watchdogTriggered && (now - lastCommandTime > WATCHDOG_TIMEOUT_MS)) {
    if (motorLeftSpeed != 0 || motorRightSpeed != 0) {
      stopMotors();
      watchdogTriggered = true;
      digitalWrite(PIN_LED_WATCHDOG, LOW); // Flash LED off to indicate watchdog trip
      Serial.println(F("ALERT:WATCHDOG_TIMEOUT"));
    }
  }

  // 3. Periodic Sensor Polling (Touch & Cliff Right)
  static unsigned long lastSensorPoll = 0;
  if (now - lastSensorPoll > 50) { // 20Hz polling
    lastSensorPoll = now;

    if (digitalRead(PIN_CLIFF_RIGHT) == LOW && (motorLeftSpeed > 0 || motorRightSpeed > 0)) {
      stopMotors();
      cliffInterruptTriggered = true;
      Serial.println(F("EVENT:CLIFF"));
    }

    static bool lastTouch = false;
    bool touch = digitalRead(PIN_TOUCH_HEAD) == HIGH;
    if (touch && !lastTouch) {
      Serial.println(F("EVENT:TOUCH"));
    }
    lastTouch = touch;
  }
}

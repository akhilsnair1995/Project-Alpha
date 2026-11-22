/*
 * Project Alpha: Wall-E Autonomous Desktop Rover
 * ESP32-S3 Mini Real-Time Motor, Servo & Cliff Controller Firmware
 *
 * Responsibilities:
 * - 20 kHz Ultrasonic / Silent PWM for DRV8833 Dual H-Bridge (N20 crawler motors)
 * - Jitter-free 50 Hz Hardware PWM for MG90S Pan/Tilt servos with angle clamping
 * - >= 200 Hz Hardware Cliff Safety Interlock (TCRT5000 IR, Active LOW on table drop)
 * - 500 ms Dead-Man's Switch Watchdog (auto-zero motor outputs on Pi freeze/disconnect)
 * - Documented PCNT (Pulse Counter) hooks for wheel odometry encoders
 * - 115200 Baud Newline-Terminated ASCII Command & Telemetry Protocol
 */

#include <Arduino.h>

// ============================================================================
// Pinout Definitions (Carefully chosen to avoid strapping & flash pins)
// ============================================================================
// Strapping pins AVOIDED: GPIO 0, 3, 45, 46
// Internal SPI Flash/PSRAM AVOIDED: GPIO 33-37

// DRV8833 Dual H-Bridge Motor Driver (20 kHz PWM)
constexpr int PIN_M_L_FWD = 4;   // Left Motor Forward (IN1)
constexpr int PIN_M_L_REV = 5;   // Left Motor Reverse (IN2)
constexpr int PIN_M_R_FWD = 6;   // Right Motor Forward (IN3)
constexpr int PIN_M_R_REV = 7;   // Right Motor Reverse (IN4)

// MG90S Pan/Tilt Servos (50 Hz PWM)
constexpr int PIN_SERVO_PAN  = 8;  // Neck Pan (Left/Right)
constexpr int PIN_SERVO_TILT = 9;  // Neck Tilt (Up/Down)

// TCRT5000 Optical Cliff Sensors (3.3V Logic, Active LOW on drop)
constexpr int PIN_CLIFF_LEFT  = 10;
constexpr int PIN_CLIFF_RIGHT = 11;

// Optional Wheel Encoders (PCNT Peripheral Hooks)
constexpr int PIN_ENC_L_A = 12;
constexpr int PIN_ENC_L_B = 13;
constexpr int PIN_ENC_R_A = 14;
constexpr int PIN_ENC_R_B = 15;

// Status LED (Heartbeat / Watchdog Indicator)
constexpr int PIN_STATUS_LED = 2;

// ============================================================================
// PWM Channels & Configuration (Compatible with ESP32 Core 2.x and 3.x)
// ============================================================================
constexpr uint32_t MOTOR_PWM_FREQ = 20000;  // 20 kHz silent PWM
constexpr uint8_t  MOTOR_PWM_RES  = 8;      // 8-bit (0-255)

constexpr uint32_t SERVO_PWM_FREQ = 50;     // 50 Hz standard servo frame
constexpr uint8_t  SERVO_PWM_RES  = 16;     // 16-bit (0-65535)

// LEDC Channels (Core 2.x)
constexpr int CH_M_L_FWD   = 0;
constexpr int CH_M_L_REV   = 1;
constexpr int CH_M_R_FWD   = 2;
constexpr int CH_M_R_REV   = 3;
constexpr int CH_SERVO_PAN = 4;
constexpr int CH_SERVO_TILT= 5;

// Safety & Watchdog Thresholds
constexpr unsigned long WATCHDOG_TIMEOUT_MS = 500;  // 500 ms dead-man switch
constexpr unsigned long TELEM_INTERVAL_MS   = 100;  // 10 Hz periodic telemetry
constexpr unsigned long CLIFF_POLL_INTERVAL_US = 2500; // 400 Hz cliff polling
constexpr bool ENABLE_SAFE_RECOIL = true;

// State Variables
float cmdLeftNorm = 0.0f;
float cmdRightNorm = 0.0f;
float currentPanDeg = 0.0f;
float currentTiltDeg = 0.0f;

bool cliffLeftDetected = false;
bool cliffRightDetected = false;
bool lastCliffLeft = false;
bool lastCliffRight = false;
bool watchdogTriggered = false;

unsigned long lastCommandTime = 0;
unsigned long lastTelemTime = 0;
unsigned long lastCliffPollUs = 0;

// Serial Buffer
char rxBuffer[128];
size_t rxIndex = 0;

// Encoder Variables (PCNT Hooks)
volatile int32_t encLeftTicks = 0;
volatile int32_t encRightTicks = 0;

// ============================================================================
// Hardware PWM Helper Functions
// ============================================================================

void pwmWriteMotor(int pin, int channel, uint32_t duty) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcWrite(pin, duty);
#else
    ledcWrite(channel, duty);
#endif
}

void pwmWriteServo(int pin, int channel, uint32_t duty) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcWrite(pin, duty);
#else
    ledcWrite(channel, duty);
#endif
}

void initPWM() {
    // Motor PWM Setup (20 kHz, 8-bit)
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcAttach(PIN_M_L_FWD, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcAttach(PIN_M_L_REV, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcAttach(PIN_M_R_FWD, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcAttach(PIN_M_R_REV, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcAttach(PIN_SERVO_PAN, SERVO_PWM_FREQ, SERVO_PWM_RES);
    ledcAttach(PIN_SERVO_TILT, SERVO_PWM_FREQ, SERVO_PWM_RES);
#else
    ledcSetup(CH_M_L_FWD, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcSetup(CH_M_L_REV, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcSetup(CH_M_R_FWD, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcSetup(CH_M_R_REV, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcAttachPin(PIN_M_L_FWD, CH_M_L_FWD);
    ledcAttachPin(PIN_M_L_REV, CH_M_L_REV);
    ledcAttachPin(PIN_M_R_FWD, CH_M_R_FWD);
    ledcAttachPin(PIN_M_R_REV, CH_M_R_REV);

    ledcSetup(CH_SERVO_PAN, SERVO_PWM_FREQ, SERVO_PWM_RES);
    ledcSetup(CH_SERVO_TILT, SERVO_PWM_FREQ, SERVO_PWM_RES);
    ledcAttachPin(PIN_SERVO_PAN, CH_SERVO_PAN);
    ledcAttachPin(PIN_SERVO_TILT, CH_SERVO_TILT);
#endif

    // Zero motor outputs
    pwmWriteMotor(PIN_M_L_FWD, CH_M_L_FWD, 0);
    pwmWriteMotor(PIN_M_L_REV, CH_M_L_REV, 0);
    pwmWriteMotor(PIN_M_R_FWD, CH_M_R_FWD, 0);
    pwmWriteMotor(PIN_M_R_REV, CH_M_R_REV, 0);
}

// ============================================================================
// Actuator Control Functions
// ============================================================================

void applyMotors(float left, float right) {
    cmdLeftNorm = constrain(left, -1.0f, 1.0f);
    cmdRightNorm = constrain(right, -1.0f, 1.0f);

    // Left Motor IN1 / IN2
    if (cmdLeftNorm > 0.01f) {
        uint32_t duty = (uint32_t)(cmdLeftNorm * 255.0f);
        pwmWriteMotor(PIN_M_L_FWD, CH_M_L_FWD, duty);
        pwmWriteMotor(PIN_M_L_REV, CH_M_L_REV, 0);
    } else if (cmdLeftNorm < -0.01f) {
        uint32_t duty = (uint32_t)(-cmdLeftNorm * 255.0f);
        pwmWriteMotor(PIN_M_L_FWD, CH_M_L_FWD, 0);
        pwmWriteMotor(PIN_M_L_REV, CH_M_L_REV, duty);
    } else {
        pwmWriteMotor(PIN_M_L_FWD, CH_M_L_FWD, 0);
        pwmWriteMotor(PIN_M_L_REV, CH_M_L_REV, 0);
    }

    // Right Motor IN3 / IN4
    if (cmdRightNorm > 0.01f) {
        uint32_t duty = (uint32_t)(cmdRightNorm * 255.0f);
        pwmWriteMotor(PIN_M_R_FWD, CH_M_R_FWD, duty);
        pwmWriteMotor(PIN_M_R_REV, CH_M_R_REV, 0);
    } else if (cmdRightNorm < -0.01f) {
        uint32_t duty = (uint32_t)(-cmdRightNorm * 255.0f);
        pwmWriteMotor(PIN_M_R_FWD, CH_M_R_FWD, 0);
        pwmWriteMotor(PIN_M_R_REV, CH_M_R_REV, duty);
    } else {
        pwmWriteMotor(PIN_M_R_FWD, CH_M_R_FWD, 0);
        pwmWriteMotor(PIN_M_R_REV, CH_M_R_REV, 0);
    }
}

void applyServos(float panDeg, float tiltDeg) {
    // Clamp to physical mechanics
    currentPanDeg  = constrain(panDeg, -85.0f, 85.0f);
    currentTiltDeg = constrain(tiltDeg, -25.0f, 35.0f);

    // 50 Hz PWM period = 20,000 us.
    // 16-bit timer: 65535 ticks = 20,000 us -> 1 us = 3.27675 ticks.
    // -90 deg = 600 us, 0 deg = 1500 us, +90 deg = 2400 us.
    float panUs  = 1500.0f + (currentPanDeg / 90.0f) * 900.0f;
    float tiltUs = 1500.0f + (currentTiltDeg / 90.0f) * 900.0f;

    uint32_t panDuty  = (uint32_t)(panUs * 3.27675f);
    uint32_t tiltDuty = (uint32_t)(tiltUs * 3.27675f);

    pwmWriteServo(PIN_SERVO_PAN, CH_SERVO_PAN, panDuty);
    pwmWriteServo(PIN_SERVO_TILT, CH_SERVO_TILT, tiltDuty);
}

void emergencyStop() {
    applyMotors(0.0f, 0.0f);
}

// ============================================================================
// Cliff Safety Interlock (>= 200 Hz fast hardware protection)
// ============================================================================

void sendTelemetryFrame() {
    Serial.printf("TELEM cliff_l=%d cliff_r=%d wd=%d\n",
        cliffLeftDetected ? 1 : 0,
        cliffRightDetected ? 1 : 0,
        watchdogTriggered ? 1 : 0
    );
}

void checkCliffSensors() {
    // TCRT5000 output is LOW when reflection lost (table edge/cliff drop)
    cliffLeftDetected  = (digitalRead(PIN_CLIFF_LEFT) == LOW);
    cliffRightDetected = (digitalRead(PIN_CLIFF_RIGHT) == LOW);

    // Fast hardware-level reflex: If moving forward and cliff drops, brake IMMEDIATELY
    if ((cliffLeftDetected || cliffRightDetected) && (cmdLeftNorm > 0.0f || cmdRightNorm > 0.0f)) {
        emergencyStop();

        // Optional short recoil away from edge (e.g. reverse slightly)
        if (ENABLE_SAFE_RECOIL) {
            applyMotors(-0.4f, -0.4f);
            delay(80);
            emergencyStop();
        }

        // Emit immediate telemetry alert to Pi 5
        sendTelemetryFrame();
    }

    // Trigger immediate telemetry if cliff status changes
    if (cliffLeftDetected != lastCliffLeft || cliffRightDetected != lastCliffRight) {
        sendTelemetryFrame();
        lastCliffLeft = cliffLeftDetected;
        lastCliffRight = cliffRightDetected;
    }
}

// ============================================================================
// Documented PCNT (Hardware Pulse Counter) Hooks for Wheel Encoders
// ============================================================================

void setupEncoders() {
    pinMode(PIN_ENC_L_A, INPUT_PULLUP);
    pinMode(PIN_ENC_L_B, INPUT_PULLUP);
    pinMode(PIN_ENC_R_A, INPUT_PULLUP);
    pinMode(PIN_ENC_R_B, INPUT_PULLUP);

    // Simple interrupt hooks for encoder ticks (can be upgraded to ESP-IDF PCNT driver)
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_L_A), []() {
        if (digitalRead(PIN_ENC_L_B) == HIGH) encLeftTicks++;
        else encLeftTicks--;
    }, RISING);

    attachInterrupt(digitalPinToInterrupt(PIN_ENC_R_A), []() {
        if (digitalRead(PIN_ENC_R_B) == HIGH) encRightTicks++;
        else encRightTicks--;
    }, RISING);
}

void getEncoderCounts(int32_t &leftTicks, int32_t &rightTicks) {
    noInterrupts();
    leftTicks = encLeftTicks;
    rightTicks = encRightTicks;
    interrupts();
}

// ============================================================================
// Command Parser
// ============================================================================

void processCommandLine(const char* line) {
    if (!line || strlen(line) == 0) return;

    char cmd = line[0];

    if (cmd == 'M' || cmd == 'm') {
        // M <left> <right>
        float l = 0.0f, r = 0.0f;
        if (sscanf(line + 1, "%f %f", &l, &r) == 2) {
            lastCommandTime = millis();
            watchdogTriggered = false;

            // Prevent driving forward if cliff is currently tripped
            if ((l > 0.0f || r > 0.0f) && (cliffLeftDetected || cliffRightDetected)) {
                emergencyStop();
                Serial.println("ACK M CLIFF_BLOCKED");
            } else {
                applyMotors(l, r);
                Serial.println("ACK M");
            }
        }
    } else if (cmd == 'H' || cmd == 'h') {
        // H <pan_deg> <tilt_deg>
        float p = 0.0f, t = 0.0f;
        if (sscanf(line + 1, "%f %f", &p, &t) == 2) {
            applyServos(p, t);
            Serial.println("ACK H");
        }
    } else if (cmd == 'S' || cmd == 's') {
        // Immediate Emergency Stop
        emergencyStop();
        lastCommandTime = millis();
        watchdogTriggered = false;
        Serial.println("ACK S");
    } else if (cmd == 'P' || cmd == 'p') {
        // Heartbeat Ping
        lastCommandTime = millis();
        watchdogTriggered = false;
        Serial.println("ACK P");
    }
}

// ============================================================================
// Setup & Main Loop
// ============================================================================

void setup() {
    Serial.begin(115200);

    // Initialize Cliff Sensors
    pinMode(PIN_CLIFF_LEFT, INPUT_PULLUP);
    pinMode(PIN_CLIFF_RIGHT, INPUT_PULLUP);

    // Status LED
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, HIGH);

    // Initialize Actuator PWM
    initPWM();
    applyServos(0.0f, 0.0f);
    emergencyStop();

    // Initialize Encoders
    setupEncoders();

    lastCommandTime = millis();
    lastTelemTime = millis();
    lastCliffPollUs = micros();

    // Initial Telemetry Frame
    sendTelemetryFrame();
}

void loop() {
    unsigned long now = millis();
    unsigned long nowUs = micros();

    // 1. High-frequency cliff sensor polling (400 Hz / every 2500 us)
    if (nowUs - lastCliffPollUs >= CLIFF_POLL_INTERVAL_US) {
        lastCliffPollUs = nowUs;
        checkCliffSensors();
    }

    // 2. Dead-Man's Switch Watchdog: Cut motors if Pi 5 freezes > 500 ms
    if (now - lastCommandTime > WATCHDOG_TIMEOUT_MS) {
        if (!watchdogTriggered && (cmdLeftNorm != 0.0f || cmdRightNorm != 0.0f)) {
            emergencyStop();
            watchdogTriggered = true;
            digitalWrite(PIN_STATUS_LED, LOW);
            sendTelemetryFrame();
        }
    } else {
        digitalWrite(PIN_STATUS_LED, HIGH);
    }

    // 3. Periodic 10 Hz Telemetry Frame
    if (now - lastTelemTime >= TELEM_INTERVAL_MS) {
        lastTelemTime = now;
        sendTelemetryFrame();
    }

    // 4. Non-blocking serial packet reading
    while (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (rxIndex > 0) {
                rxBuffer[rxIndex] = '\0';
                processCommandLine(rxBuffer);
                rxIndex = 0;
            }
        } else if (rxIndex < sizeof(rxBuffer) - 1) {
            rxBuffer[rxIndex++] = c;
        }
    }
}

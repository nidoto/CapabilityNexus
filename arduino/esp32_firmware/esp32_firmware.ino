/*
 * UMI-ESP32 — ESP32-S3 + BNO085 Motion Sensor
 *
 * 专为 UniversalMotionInput 设计的固件
 *
 * 硬件: ESP32-S3 + BNO085 (I2C) + 按钮
 * 接线:
 *   SDA→GPIO13, SCL→GPIO12
 *   按钮→GPIO40 (三脚按钮, 按钮另一端接GND, 内部上拉)
 *   (可选) 内置LED → GPIO 48 (部分开发板可用)
 *
 * 输出格式 (UMI SerialParser 兼容):
 *   FRAME=1
 *   X=12.50
 *   Y=-3.20
 *   R=0.10
 *
 * 校准信号:
 *   长按按钮3秒 → 校准1秒 → 输出 "CALIBRATION_DONE"
 *
 * 通道映射:
 *   YAW  → X   (gyro.x → 右摇杆水平)
 *   PITCH → Y  (gyro.y → 右摇杆垂直)
 *   ROLL  → R  (gyro.r → 保留通道)
 *
 * 输出频率: ~100Hz (delay 10ms)
 */

#include <Wire.h>
#include <Adafruit_BNO08x.h>

// ---------- I2C ----------
#define BNO_SDA 13
#define BNO_SCL 12

// ---------- 校准按钮 ----------
#define CAL_BUTTON 40      // 三脚按钮, 另一端接GND
#define CAL_DURATION_MS 3000  // 按下后3秒内完成采样+校准

Adafruit_BNO08x bno08x(-1);
sh2_SensorValue_t sensorValue;

// ---------- 校准偏移 ----------
float yawOffset   = 0;
float pitchOffset = 0;
float rollOffset  = 0;

// ---------- 按钮状态 (老代码的简单逻辑) ----------
bool lastButtonState = HIGH;      // 上次按钮状态 (HIGH=未按下)
unsigned long pressTime = 0;      // 按钮按下的时间
bool longPressTriggered = false;  // 是否已触发长按

// ---------- 帧计数器 ----------
unsigned long frameCounter = 0;

// ---------- 校准中标志 ----------
bool calibrating = false;

// ---------- 四元数 → 欧拉角 ----------
void quaternionToEuler(
  float qw, float qx, float qy, float qz,
  float &roll,  float &pitch, float &yaw
) {
  roll = atan2f(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy));

  float sinp = 2 * (qw * qy - qz * qx);
  if (fabs(sinp) >= 1.0f)
    pitch = copysignf(PI / 2, sinp);
  else
    pitch = asinf(sinp);

  yaw = atan2f(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz));
}

// ---------- 校准 (3秒完成：长按触发后，采样+校准+输出总计不超过3秒) ----------
void calibrate() {
  calibrating = true;

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);

  // 采样时长：取总校准窗口的 80%，剩余 20% 留给计算和输出
  unsigned long sampleMs = (CAL_DURATION_MS * 8) / 10;  // 2400ms
  unsigned long deadline = millis() + CAL_DURATION_MS;

  Serial.println("CALIBRATING...");

  float sy = 0, sp = 0, sr = 0;
  int count = 0;
  unsigned long sampleStart = millis();

  while (millis() - sampleStart < sampleMs) {
    if (bno08x.getSensorEvent(&sensorValue)) {
      if (sensorValue.sensorId == SH2_ROTATION_VECTOR) {
        float r, p, y;
        quaternionToEuler(
          sensorValue.un.rotationVector.real,
          sensorValue.un.rotationVector.i,
          sensorValue.un.rotationVector.j,
          sensorValue.un.rotationVector.k,
          r, p, y
        );
        sr += r;  sp += p;  sy += y;
        count++;
      }
    }
    delay(5);
  }

  if (count > 0) {
    rollOffset  = sr / count;
    pitchOffset = sp / count;
    yawOffset   = sy / count;
  }

  frameCounter = 0;

  // 确保总计不超过 CAL_DURATION_MS
  while (millis() < deadline) { delay(1); }

  // 发送校准完成信号
  Serial.println("CALIBRATION_DONE");

  digitalWrite(LED_BUILTIN, LOW);
  calibrating = false;
}

// ---------- BNO085 初始化 ----------
bool initBNO() {
  Wire.begin(BNO_SDA, BNO_SCL);
  delay(200);

  if (!bno08x.begin_I2C(0x4A, &Wire)) {
    if (!bno08x.begin_I2C(0x4B, &Wire)) {
      return false;
    }
  }

  bno08x.enableReport(SH2_ROTATION_VECTOR, 4000);
  return true;
}

// ---------- setup ----------
void setup() {
  pinMode(CAL_BUTTON, INPUT_PULLUP);  // 内部上拉，按钮接GND，按下=低电平
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.begin(115200);
  delay(1000);

  Serial.println("UMI-ESP32 BNO085 STARTED");

  if (!initBNO()) {
    // 初始化失败：LED快闪报错
    while (1) {
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
      delay(200);
    }
  }

  Serial.println("BNO085 READY");

  // 开机自动校准一次
  Serial.println("INITIAL AUTO-CALIBRATION...");
  calibrate();
}

// ---------- loop ----------
void loop() {
  // ──── 1. 按键检测 (来自老代码的简单可靠逻辑) ────
  bool currentState = digitalRead(CAL_BUTTON);
  
  // 检测按钮状态变化 (下降沿: 按下)
  if (currentState == LOW && lastButtonState == HIGH) {
    pressTime = millis();           // 记录按下时间
    longPressTriggered = false;     // 重置长按触发标志
  }
  
  // 检测按钮状态变化 (上升沿: 释放)
  if (currentState == HIGH && lastButtonState == LOW) {
    // 如果释放时还没触发长按，重置计时器
    if (!longPressTriggered) {
      pressTime = 0;
    }
  }
  
  // 如果按钮按下且未触发长按，检查是否达到长按时间
  if (currentState == LOW && !longPressTriggered) {
    if (millis() - pressTime >= CAL_DURATION_MS) {
      longPressTriggered = true;    // 标记已触发
      pressTime = 0;               // 重置时间
      
      // 只有在非校准状态下才执行校准
      if (!calibrating) {
        Serial.println("[BUTTON] Long press detected! Triggering calibration...");
        calibrate();
      }
    }
  }
  
  // 更新上次状态
  lastButtonState = currentState;

  // ──── 2. 校准期间暂停数据输出 ────
  if (calibrating) {
    delay(5);
    return;
  }

  // ──── 3. 读取传感器数据 ────
  static float lastRoll  = 0;
  static float lastPitch = 0;
  static float lastYaw   = 0;

  if (bno08x.getSensorEvent(&sensorValue)) {
    if (sensorValue.sensorId == SH2_ROTATION_VECTOR) {
      float roll, pitch, yaw;

      quaternionToEuler(
        sensorValue.un.rotationVector.real,
        sensorValue.un.rotationVector.i,
        sensorValue.un.rotationVector.j,
        sensorValue.un.rotationVector.k,
        roll, pitch, yaw
      );

      // 去偏移 + 弧度转角度
      lastRoll  = (roll  - rollOffset)  * 57.2958f;
      lastPitch = (pitch - pitchOffset) * 57.2958f;
      lastYaw   = (yaw   - yawOffset)   * 57.2958f;
    }
  }

  // ──── 4. UMI 格式输出 ────
  frameCounter++;

  Serial.printf("FRAME=%lu\n", frameCounter);
  Serial.printf("X=%.2f\n", lastYaw);
  Serial.printf("Y=%.2f\n", lastPitch);
  Serial.printf("R=%.2f\n", lastRoll);

  delay(10);
}
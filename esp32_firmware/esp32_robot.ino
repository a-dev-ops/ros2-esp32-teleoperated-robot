#include <WiFi.h>

// ── WiFi ──────────────────────────────────────────────────────
const char* ssid     = "ESP_ROBOT";
const char* password = "12345678";

WiFiServer server(8080);
WiFiClient client;

// ── Motor pins ────────────────────────────────────────────────
//   Motor A (LEFT)  pin1/pin2 — wired INVERTED (see move())
//   Motor B (RIGHT) pin3/pin4 — wired NORMAL
const int pin1 = 14, pin2 = 27;   // Motor A
const int pin3 = 32, pin4 = 19;   // Motor B
const int en1  = 12, en2  = 33;   // PWM enables

const int PWM_FREQ       = 1000;
const int PWM_RESOLUTION = 8;

int currentPWM = 127;

// ── Retrace stack ─────────────────────────────────────────────
#define MAX_MOVES 100

struct Move {
  char          cmd;
  unsigned long duration;
};

Move          stack[MAX_MOVES];
int           stackSize        = 0;
char          currentCmd       = 'S';
unsigned long lastTime         = 0;

bool          isRetracing      = false;
int           retraceIndex     = 0;
unsigned long retraceStepStart = 0;

// ── Motor helpers ─────────────────────────────────────────────
void motorStop() {
  digitalWrite(pin1, LOW); digitalWrite(pin2, LOW);
  digitalWrite(pin3, LOW); digitalWrite(pin4, LOW);
}

void applySpeed(int pwm) {
  ledcWrite(en1, pwm);
  ledcWrite(en2, pwm);
}

void move(char cmd) {
  applySpeed(currentPWM);

  // Motor A (LEFT)  pin1/pin2: inverted — LOW/HIGH = forward physically
  // Motor B (RIGHT) pin3/pin4: normal  — HIGH/LOW = forward physically
  switch (cmd) {
    case 'F':
      digitalWrite(pin1, LOW);  digitalWrite(pin2, HIGH);   // A inverted → fwd
      digitalWrite(pin3, HIGH); digitalWrite(pin4, LOW);    // B normal   → fwd
      break;
    case 'B':
      digitalWrite(pin1, HIGH); digitalWrite(pin2, LOW);    // A inverted → bwd
      digitalWrite(pin3, LOW);  digitalWrite(pin4, HIGH);   // B normal   → bwd
      break;
    case 'L':   // spin left: A backward, B forward
      digitalWrite(pin1, HIGH); digitalWrite(pin2, LOW);    // A inverted → bwd
      digitalWrite(pin3, HIGH); digitalWrite(pin4, LOW);    // B normal   → fwd
      break;
    case 'R':   // spin right: A forward, B backward
      digitalWrite(pin1, LOW);  digitalWrite(pin2, HIGH);   // A inverted → fwd
      digitalWrite(pin3, LOW);  digitalWrite(pin4, HIGH);   // B normal   → bwd
      break;
    default:
      motorStop();
      break;
  }
}

char reverseCmd(char cmd) {
  switch (cmd) {
    case 'F': return 'B';
    case 'B': return 'F';
    case 'L': return 'R';
    case 'R': return 'L';
    default:  return 'S';
  }
}

char getCmd(float lin, float ang) {
  if (lin > 0) return 'F';
  if (lin < 0) return 'B';
  if (ang > 0) return 'L';
  if (ang < 0) return 'R';
  return 'S';
}

// ── Retrace helpers ───────────────────────────────────────────
void pushCurrentMove() {
  if (stackSize >= MAX_MOVES)  return;
  if (currentCmd == 'S')       return;
  unsigned long elapsed = millis() - lastTime;
  if (elapsed == 0)            return;

  stack[stackSize].cmd      = currentCmd;
  stack[stackSize].duration = elapsed;
  stackSize++;
  Serial.printf("Pushed %c for %lums\n", currentCmd, elapsed);
}

void startRetrace() {
  pushCurrentMove();
  if (stackSize == 0) {
    Serial.println("Nothing to retrace!");
    return;
  }
  Serial.printf("=== RETRACE START | %d steps ===\n", stackSize);
  isRetracing      = true;
  retraceIndex     = stackSize - 1;
  retraceStepStart = millis();
  move(reverseCmd(stack[retraceIndex].cmd));
  Serial.printf("Step %d: %c\n", retraceIndex, reverseCmd(stack[retraceIndex].cmd));
}

void updateRetrace() {
  if (millis() - retraceStepStart < stack[retraceIndex].duration) return;

  retraceIndex--;
  if (retraceIndex < 0) {
    motorStop();
    stackSize   = 0;
    isRetracing = false;
    Serial.println("=== RETRACE DONE ===");
    return;
  }
  retraceStepStart = millis();
  move(reverseCmd(stack[retraceIndex].cmd));
  Serial.printf("Step %d: %c\n", retraceIndex, reverseCmd(stack[retraceIndex].cmd));
}

void interruptRetrace(char newCmd) {
  Serial.println("=== RETRACE INTERRUPTED ===");
  stackSize   = 0;
  isRetracing = false;
  currentCmd  = newCmd;
  lastTime    = millis();
  (newCmd == 'S') ? motorStop() : move(newCmd);
}

// ── Setup ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(pin1, OUTPUT); pinMode(pin2, OUTPUT);
  pinMode(pin3, OUTPUT); pinMode(pin4, OUTPUT);

  ledcAttach(en1, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(en2, PWM_FREQ, PWM_RESOLUTION);
  applySpeed(0);

  WiFi.softAP(ssid, password);
  server.begin();
  lastTime = millis();

  Serial.printf("AP IP: %s\nESP32 Robot Ready\n",
                WiFi.softAPIP().toString().c_str());
  Serial.println("Packet format: lin,ang,speed,flag");
}

// ── Main loop ─────────────────────────────────────────────────
void loop() {

  // ── Client connection management
  if (!client || !client.connected()) {
    if (currentCmd != 'S') {
      motorStop();
      currentCmd = 'S';
      Serial.println("Client disconnected — motors stopped.");
    }
    client = server.available();
    if (client) {
      client.setTimeout(100);
      lastTime = millis();
      Serial.println("Client connected.");
    }
    return;
  }

  // ── Parse incoming packet: "lin,ang,speed,flag\n"
  if (client.available()) {
    String data = client.readStringUntil('\n');
    data.trim();
    Serial.print("RX: "); Serial.println(data);

    int c1 = data.indexOf(',');
    int c2 = data.indexOf(',', c1 + 1);
    int c3 = data.indexOf(',', c2 + 1);

    if (c1 < 0 || c2 <= c1 || c3 <= c2) {
      Serial.println("Parse error — need 4 comma-separated fields.");
      return;
    }

    float  lin   = data.substring(0,      c1).toFloat();
    float  ang   = data.substring(c1 + 1, c2).toFloat();
    float  spd   = data.substring(c2 + 1, c3).toFloat();
    String flag  = data.substring(c3 + 1);
    flag.trim();

    // Update PWM from speed level (0-8 → 0-255)
    currentPWM = (int)map((long)spd, 0, 8, 0, 255);
    Serial.printf("CMD=%s  PWM=%d\n", flag.length() ? flag.c_str() : String(getCmd(lin, ang)).c_str(), currentPWM);

    // ── Retrace trigger
    if (flag == "RETRACE") {
      if (!isRetracing) startRetrace();
      else Serial.println("Already retracing!");
      return;
    }

    char cmd = getCmd(lin, ang);

    // ── Interrupt retrace on any motion command
    if (isRetracing) {
      interruptRetrace(cmd);
      return;
    }

    // ── Normal motion
    if (cmd != currentCmd) {
      pushCurrentMove();
      currentCmd = cmd;
      lastTime   = millis();
    }
    move(cmd);
  }

  if (isRetracing) updateRetrace();
}

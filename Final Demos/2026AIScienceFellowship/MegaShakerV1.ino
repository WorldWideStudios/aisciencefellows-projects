/*
  ============================================================================
  SHAKER CONTROL - SINGLE ARDUINO MEGA 2560, BOTH SHIELDS STACKED
  ============================================================================
  Stack: Mega 2560 -> Seeed Motor Shield V2.0 -> Seeed TFT Touch Shield V2.4.

  WHY THIS WORKS ON MEGA (NOT ON UNO) WITHOUT MULTIPLEXING
  ----------------------------------------------------------------------------
  The TFT shield's SPI is physically wired ONLY to the 6-pin ICSP header
  (confirmed: Seeed forum + Adafruit compatibility notes). On an Uno, ICSP
  maps to the same silicon pins as D11/D12/D13, so it collides with the
  motor shield's coil drive on those same pins. On a MEGA, ICSP maps to
  pins 50/51/52 instead - completely separate from D11/D12/D13. Result:
  the motor shield's D8/D9/D10/D11/D12/D13 are plain GPIO on a Mega, no
  SPI role, so there is NO conflict. Motor runs continuously; draws can
  happen anytime; no bus-sharing tricks needed.

  REQUIRED: the ICSP signals must physically reach the TFT through the
  motor shield's stacking headers. If the motor shield has an ICSP 2x3
  passthrough (most Seeed Uno-shape shields do), this just works when
  stacked. If display stays white, that passthrough is the first thing
  to check.

  ----------------------------------------------------------------------------
  POWER - READ BEFORE RUNNING
  ----------------------------------------------------------------------------
  This build is powered from USB only (no external 6-15V supply on the
  motor shield's screw terminals). USB ports typically supply 500mA-900mA
  (up to ~2A on some high-power USB3/PD ports, but do not assume that).
  A stepper motor pulling up to 2A ALONE can exceed what USB provides,
  before the Mega and TFT backlight draw their own share.

  CONSEQUENCES if the stepper demands more current than the USB port can
  give: brownout resets, corrupted touch readings, TFT glitching, or the
  port shutting down output. This is a HARDWARE limit - no code change
  fixes it. Symptoms to watch for during testing:
    - Mega resets/reboots when motor starts stepping
    - Serial Monitor disconnects/reconnects
    - TFT flickers or garbles when motor turns on

  IF you see any of the above: stop, connect proper external 6-15V power
  to the motor shield's screw terminals, and remove or bridge MB_EN per
  your supply configuration (previously discussed). This sketch keeps
  DEFAULT_MAX_RPM conservative and boots with the motor OFF so you can
  verify the display/touch on USB power alone before spinning the motor.

  ----------------------------------------------------------------------------
  PIN MAP (Mega, both shields stacked)
  ----------------------------------------------------------------------------
    TFT_CS = D5, TFT_DC = D6, no reset pin, backlight hardwired on
    TFT SPI = ICSP header -> Mega hardware SPI (50/51/52), automatic
    Touch = A0-A3 (SeeedTouchScreen driver, solved calibration below)
    Motor coils I1-I4 = D8, D11, D12, D13 (plain GPIO on Mega - no conflict)
    Motor enables EA/EB = D9, D10
    SD_CS (unused) = D4

  DEBUG: hardware Serial 115200. DEBUG / TOUCH_DIAG flags below.
  ============================================================================
*/

#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <SeeedTouchScreen.h>
#include <SPI.h>

// ---------------------------------------------------------------------------
// DEBUG FLAGS
// ---------------------------------------------------------------------------
#define DEBUG 1
#define TOUCH_DIAG 0   // 1 = red dot at each validated tap + verbose serial
#if DEBUG
  #define DBG(x)   Serial.print(x)
  #define DBGLN(x) Serial.println(x)
#else
  #define DBG(x)
  #define DBGLN(x)
#endif

// ---------------------------------------------------------------------------
// TFT - hardware SPI via ICSP (automatic on Mega, no pin config needed)
// ---------------------------------------------------------------------------
#define TFT_CS 5
#define TFT_DC 6
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, -1);

// ---------------------------------------------------------------------------
// Touch - SeeedTouchScreen driver, solved linear calibration (this panel)
// ---------------------------------------------------------------------------
#define YP A2
#define XM A1
#define YM A0
#define XP A3
TouchScreen ts = TouchScreen(XP, YP, XM, YM);

#define CAL_AX  0.180124
#define CAL_BX  -23.11
#define CAL_AY  -0.141721
#define CAL_BY  263.70
#define TS_MINPRESSURE 200
#define TS_AGREE_TOL 120

#define SCREEN_W 320
#define SCREEN_H 240

// ---------------------------------------------------------------------------
// Motor Shield V2.0 pins (official Seeed wiki mapping - plain GPIO on Mega)
// ---------------------------------------------------------------------------
#define COIL_I1 8    // L298P IN1
#define COIL_I2 11   // L298P IN2
#define COIL_I3 12   // L298P IN3
#define COIL_I4 13   // L298P IN4
#define ENABLE_A 9   // EA - HIGH enables bridge A
#define ENABLE_B 10  // EB - HIGH enables bridge B

const uint8_t STEP_SEQUENCE[4][4] = {
  {1, 0, 0, 1},
  {1, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 1}
};
uint8_t stepIndex = 0;

#define STEPS_PER_REV 200        // 1.8 deg/step default - verify vs your motor
#define RPM_INCREMENT 5
#define MAXRPM_INCREMENT 10
#define MIN_RPM 0
#define DEFAULT_MAX_RPM 100      // conservative default while on USB power - raise once on external supply

bool motorOn = false;             // boots OFF - verify display/touch on USB before spinning
int currentRPM = 0;
int maxRPM = DEFAULT_MAX_RPM;
unsigned long lastStepMicros = 0;
unsigned long stepIntervalMicros = 0;

// ---------------------------------------------------------------------------
// UI state
// ---------------------------------------------------------------------------
enum Screen { SCREEN_MAIN, SCREEN_OPTIONS };
Screen currentScreen = SCREEN_MAIN;
unsigned long lastTouchMillis = 0;
#define TOUCH_DEBOUNCE_MS 220

const int BTN_ONOFF_X = 20,  BTN_ONOFF_Y = 20,  BTN_ONOFF_W = 110, BTN_ONOFF_H = 60;
const int BTN_MINUS_X = 20,  BTN_MINUS_Y = 100, BTN_MINUS_W = 50,  BTN_MINUS_H = 60;
const int BTN_PLUS_X  = 90,  BTN_PLUS_Y  = 100, BTN_PLUS_W  = 50,  BTN_PLUS_H  = 60;
const int BTN_OPTS_X  = 20,  BTN_OPTS_Y  = 180, BTN_OPTS_W  = 130, BTN_OPTS_H  = 40;
const int BAR_X = 250, BAR_Y = 20, BAR_W = 40, BAR_H = 200;
const int OPT_MINUS_X = 40,  OPT_MINUS_Y = 100, OPT_MINUS_W = 60, OPT_MINUS_H = 60;
const int OPT_PLUS_X  = 220, OPT_PLUS_Y  = 100, OPT_PLUS_W  = 60, OPT_PLUS_H  = 60;
const int OPT_SAVE_X  = 100, OPT_SAVE_Y  = 180, OPT_SAVE_W  = 120, OPT_SAVE_H = 40;

// ===========================================================================
void setup() {
#if DEBUG
  Serial.begin(115200);
  DBGLN("Shaker control (Mega, single board) booting...");
  DBGLN("POWER MODE: USB only. Watch for resets/glitches when motor starts.");
#endif

  pinMode(COIL_I1, OUTPUT);
  pinMode(COIL_I2, OUTPUT);
  pinMode(COIL_I3, OUTPUT);
  pinMode(COIL_I4, OUTPUT);
  pinMode(ENABLE_A, OUTPUT);
  pinMode(ENABLE_B, OUTPUT);
  digitalWrite(ENABLE_A, LOW); // motor starts OFF
  digitalWrite(ENABLE_B, LOW);
  allCoilsOff();

  tft.begin();
  tft.setRotation(1);
  drawMainScreen();

  DBGLN("Setup complete. Motor OFF - verify display/touch before enabling.");
}

void loop() {
  handleTouch();
  stepMotorNonBlocking();
}

// ===========================================================================
// STEPPER - non-blocking, runs continuously and independently of drawing
// (no bus sharing needed on Mega - see header notes)
// ===========================================================================
void allCoilsOff() {
  digitalWrite(COIL_I1, LOW);
  digitalWrite(COIL_I2, LOW);
  digitalWrite(COIL_I3, LOW);
  digitalWrite(COIL_I4, LOW);
}

void recalcStepInterval() {
  if (currentRPM <= 0) { stepIntervalMicros = 0; return; }
  float stepsPerSec = (currentRPM * (float)STEPS_PER_REV) / 60.0;
  stepIntervalMicros = (unsigned long)(1000000.0 / stepsPerSec);
  DBG("RPM="); DBG(currentRPM);
  DBG(" -> step interval us="); DBGLN(stepIntervalMicros);
}

void stepMotorNonBlocking() {
  if (!motorOn || currentRPM <= 0 || stepIntervalMicros == 0) return;
  unsigned long now = micros();
  if (now - lastStepMicros >= stepIntervalMicros) {
    lastStepMicros = now;
    digitalWrite(COIL_I1, STEP_SEQUENCE[stepIndex][0]);
    digitalWrite(COIL_I2, STEP_SEQUENCE[stepIndex][1]);
    digitalWrite(COIL_I3, STEP_SEQUENCE[stepIndex][2]);
    digitalWrite(COIL_I4, STEP_SEQUENCE[stepIndex][3]);
    stepIndex = (stepIndex + 1) % 4;
  }
}

void setMotorOn(bool on) {
  motorOn = on;
  if (on) {
    digitalWrite(ENABLE_A, HIGH);
    digitalWrite(ENABLE_B, HIGH);
    DBGLN("Motor ON - watch Serial/display for USB brownout symptoms");
  } else {
    digitalWrite(ENABLE_A, LOW);
    digitalWrite(ENABLE_B, LOW);
    allCoilsOff();
    DBGLN("Motor OFF");
  }
}

// ===========================================================================
// TOUCH - A0-A3, no bus conflict, safe to poll continuously
// ===========================================================================
bool inRect(int px, int py, int rx, int ry, int rw, int rh) {
  return (px >= rx && px <= rx + rw && py >= ry && py <= ry + rh);
}

void handleTouch() {
  Point p1 = ts.getPoint();
  if (p1.z < TS_MINPRESSURE) return;

  delay(5);
  Point p2 = ts.getPoint();
  if (abs(p1.x - p2.x) > TS_AGREE_TOL || abs(p1.y - p2.y) > TS_AGREE_TOL) {
#if TOUCH_DIAG
    Serial.println("REJECT agree");
#endif
    return;
  }
  if (millis() - lastTouchMillis < TOUCH_DEBOUNCE_MS) return;

  long rx = ((long)p1.x + p2.x) / 2;
  long ry = ((long)p1.y + p2.y) / 2;
  int screenX = (int)(CAL_AX * ry + CAL_BX);
  int screenY = (int)(CAL_AY * rx + CAL_BY);
  screenX = constrain(screenX, 0, SCREEN_W);
  screenY = constrain(screenY, 0, SCREEN_H);

#if TOUCH_DIAG
  Serial.print("PRESS raw x="); Serial.print(rx);
  Serial.print(" y="); Serial.print(ry);
  Serial.print(" -> screen x="); Serial.print(screenX);
  Serial.print(" y="); Serial.println(screenY);
  tft.fillCircle(screenX, screenY, 3, ILI9341_RED);
#endif
  DBG("Touch x="); DBG(screenX); DBG(" y="); DBGLN(screenY);

  lastTouchMillis = millis();

  if (currentScreen == SCREEN_MAIN) handleTouchMain(screenX, screenY);
  else handleTouchOptions(screenX, screenY);
}

void handleTouchMain(int x, int y) {
  if (inRect(x, y, BTN_ONOFF_X, BTN_ONOFF_Y, BTN_ONOFF_W, BTN_ONOFF_H)) {
    setMotorOn(!motorOn);
    drawOnOffButton();
    return;
  }
  if (inRect(x, y, BTN_MINUS_X, BTN_MINUS_Y, BTN_MINUS_W, BTN_MINUS_H)) {
    currentRPM = max(MIN_RPM, currentRPM - RPM_INCREMENT);
    recalcStepInterval();
    drawRPMText(); drawRPMBar();
    return;
  }
  if (inRect(x, y, BTN_PLUS_X, BTN_PLUS_Y, BTN_PLUS_W, BTN_PLUS_H)) {
    currentRPM = min(maxRPM, currentRPM + RPM_INCREMENT);
    recalcStepInterval();
    drawRPMText(); drawRPMBar();
    return;
  }
  if (inRect(x, y, BTN_OPTS_X, BTN_OPTS_Y, BTN_OPTS_W, BTN_OPTS_H)) {
    DBGLN("Entering OPTIONS screen");
    currentScreen = SCREEN_OPTIONS;
    drawOptionsScreen();
    return;
  }
#if TOUCH_DIAG
  Serial.println("MISS: tap hit no button");
#endif
}

void handleTouchOptions(int x, int y) {
  if (inRect(x, y, OPT_MINUS_X, OPT_MINUS_Y, OPT_MINUS_W, OPT_MINUS_H)) {
    maxRPM = max(MAXRPM_INCREMENT, maxRPM - MAXRPM_INCREMENT);
    drawMaxRPMText();
    return;
  }
  if (inRect(x, y, OPT_PLUS_X, OPT_PLUS_Y, OPT_PLUS_W, OPT_PLUS_H)) {
    maxRPM += MAXRPM_INCREMENT;
    drawMaxRPMText();
    return;
  }
  if (inRect(x, y, OPT_SAVE_X, OPT_SAVE_Y, OPT_SAVE_W, OPT_SAVE_H)) {
    if (currentRPM > maxRPM) { currentRPM = maxRPM; recalcStepInterval(); }
    DBGLN("Options saved");
    currentScreen = SCREEN_MAIN;
    drawMainScreen();
    return;
  }
}

// ===========================================================================
// DRAWING
// ===========================================================================
void drawMainScreen() {
  tft.fillScreen(ILI9341_BLACK);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(2);
  tft.setCursor(20, 0);
  tft.print("SHAKER CONTROL");
  drawOnOffButton();
  drawSpeedButtons();
  drawOptionsButton();
  drawRPMBarFrame();
  drawRPMBar();
  drawRPMText();
}

void drawOnOffButton() {
  uint16_t color = motorOn ? ILI9341_GREEN : ILI9341_RED;
  tft.fillRect(BTN_ONOFF_X, BTN_ONOFF_Y, BTN_ONOFF_W, BTN_ONOFF_H, color);
  tft.drawRect(BTN_ONOFF_X, BTN_ONOFF_Y, BTN_ONOFF_W, BTN_ONOFF_H, ILI9341_WHITE);
  tft.setTextColor(ILI9341_BLACK);
  tft.setTextSize(2);
  tft.setCursor(BTN_ONOFF_X + 15, BTN_ONOFF_Y + 22);
  tft.print(motorOn ? "ON" : "OFF");
}

void drawSpeedButtons() {
  tft.fillRect(BTN_MINUS_X, BTN_MINUS_Y, BTN_MINUS_W, BTN_MINUS_H, ILI9341_BLUE);
  tft.drawRect(BTN_MINUS_X, BTN_MINUS_Y, BTN_MINUS_W, BTN_MINUS_H, ILI9341_WHITE);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(3);
  tft.setCursor(BTN_MINUS_X + 15, BTN_MINUS_Y + 15);
  tft.print("-");
  tft.fillRect(BTN_PLUS_X, BTN_PLUS_Y, BTN_PLUS_W, BTN_PLUS_H, ILI9341_BLUE);
  tft.drawRect(BTN_PLUS_X, BTN_PLUS_Y, BTN_PLUS_W, BTN_PLUS_H, ILI9341_WHITE);
  tft.setCursor(BTN_PLUS_X + 15, BTN_PLUS_Y + 15);
  tft.print("+");
}

void drawOptionsButton() {
  tft.fillRect(BTN_OPTS_X, BTN_OPTS_Y, BTN_OPTS_W, BTN_OPTS_H, ILI9341_ORANGE);
  tft.drawRect(BTN_OPTS_X, BTN_OPTS_Y, BTN_OPTS_W, BTN_OPTS_H, ILI9341_WHITE);
  tft.setTextColor(ILI9341_BLACK);
  tft.setTextSize(2);
  tft.setCursor(BTN_OPTS_X + 10, BTN_OPTS_Y + 10);
  tft.print("OPTIONS");
}

void drawRPMBarFrame() {
  tft.drawRect(BAR_X - 2, BAR_Y - 2, BAR_W + 4, BAR_H + 4, ILI9341_WHITE);
}

void drawRPMBar() {
  int pct = (maxRPM > 0) ? (currentRPM * 100L / maxRPM) : 0;
  pct = constrain(pct, 0, 100);
  int fillH = map(pct, 0, 100, 0, BAR_H);
  tft.fillRect(BAR_X, BAR_Y, BAR_W, BAR_H, ILI9341_BLACK);
  tft.fillRect(BAR_X, BAR_Y + (BAR_H - fillH), BAR_W, fillH, ILI9341_GREEN);
}

void drawRPMText() {
  tft.fillRect(180, 60, 60, 60, ILI9341_BLACK);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(3);
  tft.setCursor(180, 60);
  tft.print(currentRPM);
  tft.setTextSize(1);
  tft.setCursor(180, 95);
  tft.print("RPM");
  tft.setCursor(180, 110);
  tft.print("max ");
  tft.print(maxRPM);
}

void drawOptionsScreen() {
  tft.fillScreen(ILI9341_BLACK);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(2);
  tft.setCursor(20, 0);
  tft.print("OPTIONS - MAX RPM");
  tft.fillRect(OPT_MINUS_X, OPT_MINUS_Y, OPT_MINUS_W, OPT_MINUS_H, ILI9341_BLUE);
  tft.drawRect(OPT_MINUS_X, OPT_MINUS_Y, OPT_MINUS_W, OPT_MINUS_H, ILI9341_WHITE);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(3);
  tft.setCursor(OPT_MINUS_X + 20, OPT_MINUS_Y + 15);
  tft.print("-");
  tft.fillRect(OPT_PLUS_X, OPT_PLUS_Y, OPT_PLUS_W, OPT_PLUS_H, ILI9341_BLUE);
  tft.drawRect(OPT_PLUS_X, OPT_PLUS_Y, OPT_PLUS_W, OPT_PLUS_H, ILI9341_WHITE);
  tft.setCursor(OPT_PLUS_X + 20, OPT_PLUS_Y + 15);
  tft.print("+");
  tft.fillRect(OPT_SAVE_X, OPT_SAVE_Y, OPT_SAVE_W, OPT_SAVE_H, ILI9341_GREEN);
  tft.drawRect(OPT_SAVE_X, OPT_SAVE_Y, OPT_SAVE_W, OPT_SAVE_H, ILI9341_WHITE);
  tft.setTextColor(ILI9341_BLACK);
  tft.setTextSize(2);
  tft.setCursor(OPT_SAVE_X + 15, OPT_SAVE_Y + 10);
  tft.print("SAVE");
  drawMaxRPMText();
}

void drawMaxRPMText() {
  tft.fillRect(100, 100, 120, 60, ILI9341_BLACK);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(4);
  tft.setCursor(105, 110);
  tft.print(maxRPM);
}

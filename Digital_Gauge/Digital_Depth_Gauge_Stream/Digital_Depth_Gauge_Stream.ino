// Pin Definitions for ESP32
const int CLOCK_PIN = 18; 
const int DATA_PIN = 19;

// Volatile variables modified inside the Interrupt Service Routine (ISR)
volatile unsigned long lastClockMicros = 0;
volatile int bitCount = 0;
volatile uint32_t currentPacket = 0;
volatile uint32_t completedPacket = 0;
volatile bool isPacketReady = false;

// Interrupt Service Routine (ISR) - Triggered by the Clock line
void IRAM_ATTR handleClockInterrupt() {
  unsigned long now = micros();
  unsigned long timeSinceLastClock = now - lastClockMicros;
  lastClockMicros = now;

  // Frame sync handling for inverted clock (idle state is LOW)
  if (timeSinceLastClock > 3000) {
    bitCount = 0;
    currentPacket = 0;
  }

  if (bitCount < 24) {
    // Transistor logic inversion: LOW input = binary 1, HIGH input = binary 0
    uint32_t bitVal = (digitalRead(DATA_PIN) == LOW) ? 1 : 0;
    
    // Store bit into our 24-bit variable (LSB first storage)
    currentPacket |= (bitVal << bitCount);
    bitCount++;

    // Lock frame when exactly 24 bits are received
    if (bitCount == 24) {
      completedPacket = currentPacket;
      isPacketReady = true;
    }
  }
}

void setup() {
  // Initialize Serial at high speed for smooth output streams
  Serial.begin(115200);
  delay(500);
  
  pinMode(CLOCK_PIN, INPUT);
  pinMode(DATA_PIN, INPUT);

  // Monitor the FALLING edge to account for transistor signal inversion
  attachInterrupt(digitalPinToInterrupt(CLOCK_PIN), handleClockInterrupt, FALLING);
}

void loop() {
  // Process and print data immediately as new packets land
  if (isPacketReady) {
    noInterrupts();
    uint32_t rawPacket = completedPacket;
    isPacketReady = false;
    interrupts();

    // Isolate the core 20-bit numeric reading
    int32_t numericValue = rawPacket & 0xFFFFF;

    // Check the native 21st bit (index 20) for the negative sign flag
    bool isNegative = (rawPacket >> 20) & 1;

    // Scale to a standard metric float value
    float distanceMm = (float)numericValue / 100.0;
    if (isNegative) {
      distanceMm = -distanceMm;
    }

    // Direct, uncluttered data stream to the serial port
    Serial.println(distanceMm, 2);
  }
}





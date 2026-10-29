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

  // With inverted logic, the idle state is LOW. 
  // A gap of more than 3ms between transmissions indicates the start of a brand new frame.
  if (timeSinceLastClock > 3000) {
    bitCount = 0;
    currentPacket = 0;
  }

  if (bitCount < 24) {
    // Read the Data pin. 
    // Transistor logic inversion: LOW input = binary 1, HIGH input = binary 0
    uint32_t bitVal = (digitalRead(DATA_PIN) == LOW) ? 1 : 0;
    
    // Store bit into our 24-bit variable (LSB first storage)
    currentPacket |= (bitVal << bitCount);
    bitCount++;

    // Once we hit exactly 24 bits, lock the packet and signal the main loop
    if (bitCount == 24) {
      completedPacket = currentPacket;
      isPacketReady = true;
    }
  }
}

void setup() {
  // Initialize Serial at high speed for clean debugging
  Serial.begin(115200);
  delay(1000);
  
  pinMode(CLOCK_PIN, INPUT);
  pinMode(DATA_PIN, INPUT);

  // Due to transistor inversion, we look for the FALLING edge 
  // to sample data on the correct side of the original clock pulse.
  attachInterrupt(digitalPinToInterrupt(CLOCK_PIN), handleClockInterrupt, FALLING);

  Serial.println("==============================================");
  Serial.println("   ESP32 Fully Inverted Caliper Reader        ");
  Serial.println("==============================================");
}

void loop() {
  // Check if the background hardware interrupt has delivered a complete 24-bit frame
  if (isPacketReady) {
    // Disable interrupts momentarily to safely copy the volatile variable
    noInterrupts();
    uint32_t rawPacket = completedPacket;
    isPacketReady = false;
    interrupts();

    // 1. Isolate the first 20 bits directly for the value
    int32_t numericValue = rawPacket & 0xFFFFF;

    // 2. Extract the native negative sign flag (Bit 21, which sits at index 20)
    bool isNegative = (rawPacket >> 20) & 1;

    // 3. Convert the native integer value to standard millimeter format (divided by 100)
    float distanceMm = (float)numericValue / 100.0;
    if (isNegative) {
      distanceMm = -distanceMm;
    }

    // 4. Output the correct measurements cleanly
    Serial.print("Processed Measurement: ");
    Serial.print(distanceMm, 2);
    Serial.print(" mm");

    // Keep raw print active for tracking bit flips
    Serial.print("  [Raw Bits: ");
    for (int i = 23; i >= 0; i--) {
      Serial.print((rawPacket >> i) & 1);
    }
    Serial.println("]");
  }
}




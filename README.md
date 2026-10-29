# ESP32 Digital Tyre Tread Depth Gauge Interface & Data Logger

An ESP32-based hardware interface and Python data logging pipeline for digital tyre tread depth gauges (and standard digital calipers using the 24-bit protocol). 

This project taps into the raw serial output lines of a battery-powered gauge, uses transistor-based level shifting and logic inversion to feed the signals safely into an ESP32, decodes the synchronous stream via high-speed interrupts, and provides real-time desktop visualisation with CSV export capabilities.

---

## Features

- **Hardware Level Shifting & Logic Inversion**: Converts 1.5V clock and data signals from the gauge to 3.3V logic for the ESP32 while inverting collector output.
- **Interrupt-Driven Decoding**: Uses ESP32 hardware interrupts (`IRAM_ATTR`) on clock falling edges to decode the 24-bit measurement packet with frame-synchronisation detection.
- **Real-Time Data Streaming**: Outputs cleaned, scaled measurement values (in mm) over USB Serial at 115200 baud.
- **Python Desktop Dashboard**: Includes a Tkinter + Matplotlib GUI application (`Digital_Gauge_Dash.py`) for live scrolling plotting, auto-ranging viewport, auto-detection of COM ports, and CSV dataset export.
- **Repeatability & Accuracy Analysis**: Designed for statistical analysis, tyre wear tracking, and measurement variance studies.

---

## Hardware Architecture & Setup

### Logic & Level Shifting

Digital calipers and tread depth gauges natively operate on a single 1.5V button cell (`LR44` / `SR44`). Their data (`DATA`) and clock (`CLK`) signals operate at 1.5V CMOS levels, which cannot reliably trigger ESP32 digital inputs (minimum $V_{IH} \approx 2.4\text{V}$).

To solve this, two NPN transistors (e.g., `2N2222` or `BC547`) are arranged in common-emitter configuration:
1. When the gauge signal is **HIGH** (1.5V), the transistor turns on, pulling the ESP32 GPIO pin to **LOW** (0V).
2. When the gauge signal is **LOW** (0V), the transistor turns off, allowing the internal/external pull-up resistor to pull the ESP32 GPIO pin to **HIGH** (3.3V).

> **Note**: This circuit inverts the signal logic. Consequently, the firmware handles bit reading with inverted logic (`LOW` = Binary 1, `HIGH` = Binary 0) and triggers interrupts on the `FALLING` edge.

Digital Gauge (1.5V Logic)                       ESP32 (3.3V Logic)
   +------------------------+                       +-----------------+
   |                        |                       |                 |
   |  CLK Signal  ----------+---> [Transistor 1] ---> GPIO 18 (Interrupt)
   |                        |                       |                 |
   |  DATA Signal ----------+---> [Transistor 2] ---> GPIO 19         |
   |                        |                       |                 |
   |  GND ------------------+-----------------------> GND             |
   +------------------------+                       +-----------------+
   
### Pin Map

| ESP32 Pin | Function | Description |
|---|---|---|
| **GPIO 18** | `CLOCK_PIN` | Serial clock input (Interrupt attached, falling edge) |
| **GPIO 19** | `DATA_PIN` | Serial data input (Sampled on clock pulse) |
| **GND** | Ground | Common ground reference with interface board |

### Hardware Assembly 

<img src="Digital_Gauge/IMG20261029143447.jpg" alt="Digital Tyre Tread Depth Gauge Hardware Interface Setup" width="300">
*Figure 1: Hardware prototype showing the digital gauge wired via the transistor-based level shifter interface board to the ESP32 microcontroller.*

---

## Data Protocol Specification

The digital depth gauge transmits data as a continuous stream of 24-bit packets:

1. **Frame Synchronisation**: A clock idle time exceeding ~3ms indicates a new packet boundary.
2. **Bit Structure**:
   - **Bits 0–19**: Core measurement value in units of $0.01\text{ mm}$ (LSB transmitted first).
   - **Bit 20**: Sign bit (`0` = positive, `1` = negative).
   - **Bits 21–23**: Reserved/Units flags.
3. **Conversion**:
   $$\text{Distance (mm)} = \frac{\text{Raw 20-bit Integer}}{100.0} \times (\text{Sign Bit} ? -1 : 1)$$

---

## Software Setup & Usage

### 1. ESP32 Firmware

1. Open `Digital_Depth_Gauge_Stream.ino` in the Arduino IDE or PlatformIO.
2. Ensure the ESP32 board support package is installed.
3. Select your ESP32 target board and COM port.
4. Upload the code.
5. Open the Serial Monitor at **115200 baud** to verify live measurement output.

### 2. Python Visualisation Dashboard

https://github.com/user-attachments/assets/Recording%202026-10-29%20143327.mp4

*Figure 2: Real-time demonstration of the Python dashboard capturing digital gauge measurements live over serial.*

#### Dependencies
Install the required packages using pip:
```bash
pip install pyserial matplotlib

https://www.ipsilondev.com/maker/en/digital-gauge-arduino.php

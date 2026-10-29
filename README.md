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


https://www.ipsilondev.com/maker/en/digital-gauge-arduino.php

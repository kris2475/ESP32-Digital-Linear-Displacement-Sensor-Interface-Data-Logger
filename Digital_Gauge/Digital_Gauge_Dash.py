import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import time
import csv

class CaliperPlotterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Caliper Live Data Plotter")
        self.root.geometry("850x600")

        # Serial Connection Variables
        self.serial_port = None
        self.is_running = False
        
        # Data Storage (Holds the last 200 data points for moving view)
        self.max_points = 200
        self.time_data = collections.deque(maxlen=self.max_points)
        self.value_data = collections.deque(maxlen=self.max_points)
        
        # Comprehensive Session Storage (For Saving All Data)
        self.all_time_stamps = []
        self.all_values = []
        self.start_time = None

        # Build User Interface
        self.create_widgets()
        
        # Setup Matplotlib Plot
        self.setup_plot()

        # Handle window closure cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # --- Top Control Panel ---
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # COM Port Dropdown Label
        ttk.Label(control_frame, text="Select COM Port:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        # COM Port Combo Box
        self.port_combobox = ttk.Combobox(control_frame, width=15, state="readonly")
        self.port_combobox.pack(side=tk.LEFT, padx=5)
        self.refresh_ports()

        # Refresh Ports Button
        self.refresh_btn = ttk.Button(control_frame, text="🔄 Refresh", command=self.refresh_ports)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        # Connect / Disconnect Button
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=15)

        # Save Data Button (Initially disabled until data exists)
        self.save_btn = ttk.Button(control_frame, text="💾 Save Data to CSV", command=self.save_data, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=5)

    def setup_plot(self):
        # Create Matplotlib Figure & Axis
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.ax.set_title("Live Depth Gauge Readings", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time elapsed (seconds)", fontsize=10)
        self.ax.set_ylabel("Measurement (mm)", fontsize=10)
        self.ax.grid(True, linestyle="--", alpha=0.6)
        
        # Create empty plot line
        self.line, = self.ax.plot([], [], color="#007acc", lw=2, label="Depth (mm)")
        self.ax.legend(loc="upper right")

        # Embed Matplotlib Figure inside Tkinter layout
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

    def refresh_ports(self):
        """Scans the system for active serial COM ports and updates the dropdown menu."""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combobox['values'] = port_list
        if port_list:
            self.port_combobox.current(0)
        else:
            self.port_combobox.set("No Ports Found")

    def toggle_connection(self):
        if not self.is_running:
            self.start_serial()
        else:
            self.stop_serial()

    def start_serial(self):
        selected_port = self.port_combobox.get()
        if not selected_port or selected_port == "No Ports Found":
            messagebox.showerror("Error", "Please select a valid COM port first.")
            return

        try:
            # Initialize connection matching the 115200 baud rate in the ESP32 code
            self.serial_port = serial.Serial(selected_port, 115200, timeout=0.1)
            self.is_running = True
            self.connect_btn.config(text="Disconnect", style="Accent.TButton")
            self.port_combobox.config(state="disabled")
            self.refresh_btn.config(state="disabled")
            self.save_btn.config(state="disabled") # Lock saving during active acquisition
            
            # Reset timeline baselines
            self.start_time = time.time()
            self.time_data.clear()
            self.value_data.clear()
            self.all_time_stamps.clear()
            self.all_values.clear()

            # Begin continuous readout cycle
            self.read_serial_stream()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not open port {selected_port}:\n{str(e)}")
            self.stop_serial()

    def stop_serial(self):
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.connect_btn.config(text="Connect")
        self.port_combobox.config(state="readonly")
        self.refresh_btn.config(state="normal")
        
        # If data was captured during the session, unlock the save features
        if self.all_values:
            self.save_btn.config(state="normal")

    def read_serial_stream(self):
        if not self.is_running:
            return

        # Process all available incoming lines in the serial buffer
        while self.serial_port and self.serial_port.in_waiting > 0:
            try:
                raw_line = self.serial_port.readline()
                clean_line = raw_line.decode('utf-8').strip()
                
                if clean_line:
                    # Parse numerical float value out of raw text stream
                    val = float(clean_line)
                    elapsed_time = time.time() - self.start_time
                    
                    # Add to shifting real-time plot window
                    self.time_data.append(elapsed_time)
                    self.value_data.append(val)
                    
                    # Add to session master historical logs
                    self.all_time_stamps.append(round(elapsed_time, 3))
                    self.all_values.append(val)
                    
            except ValueError:
                # Discard garbage characters or broken line splits on startup
                pass
            except Exception:
                self.stop_serial()
                return

        # Dynamically refresh layout scales to fit the viewport data limits
        if self.time_data:
            self.line.set_data(list(self.time_data), list(self.value_data))
            self.ax.set_xlim(min(self.time_data), max(self.time_data) + 0.5)
            
            # Pad Y axis constraints slightly above and below minimums/maximums
            y_min, y_max = min(self.value_data), max(self.value_data)
            padding = max(1.0, (y_max - y_min) * 0.1)
            self.ax.set_ylim(y_min - padding, y_max + padding)
            
            # Redraw canvas context
            self.canvas.draw_idle()

        # Reschedule check cycle using Tkinter's main event handler clock (every 15ms)
        if self.is_running:
            self.root.after(15, self.read_serial_stream)

    def save_data(self):
        if not self.all_values:
            messagebox.showwarning("Warning", "No session logs recorded to save.")
            return

        # Prompt user for export path location via file manager save prompt
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Caliper Log Asset"
        )
        
        if file_path:
            try:
                with open(file_path, mode='w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    # Headers
                    writer.writerow(["Relative Time (s)", "Measurement (mm)"])
                    # Combine timestamps and measurements structurally line by line
                    for t, v in zip(self.all_time_stamps, self.all_values):
                        writer.writerow([t, v])
                messagebox.showinfo("Success", f"Session dataset successfully saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to save structural file output:\n{str(e)}")

    def on_closing(self):
        self.stop_serial()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CaliperPlotterApp(root)
    root.mainloop()

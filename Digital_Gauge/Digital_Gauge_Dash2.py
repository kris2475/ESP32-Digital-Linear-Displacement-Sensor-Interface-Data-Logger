import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import time
import csv
import numpy as np

class CaliperPlotterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Displacement Sensor Live Analytics & Stroke Logger")
        self.root.geometry("950x850")

        # Serial Connection & State Variables
        self.serial_port = None
        self.is_running = False
        
        # Tolerance Limits
        self.upper_limit = 25.0
        self.lower_limit = 0.0
        self.tolerance_active = False

        # Data Storage (Holds the last 250 points for real-time scrolling view)
        self.max_points = 250
        self.time_data = collections.deque(maxlen=self.max_points)
        self.value_data = collections.deque(maxlen=self.max_points)
        
        # Comprehensive Session Storage (For Saving All Data)
        self.all_time_stamps = []
        self.all_values = []
        self.start_time = None

        # Build User Interface
        self.create_widgets()
        
        # Setup Matplotlib Plots (Displacement and Velocity)
        self.setup_plots()

        # Handle window closure cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # --- Top Control Panel ---
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # COM Port Dropdown Label
        ttk.Label(control_frame, text="Select COM Port:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        # COM Port Combo Box
        self.port_combobox = ttk.Combobox(control_frame, width=12, state="readonly")
        self.port_combobox.pack(side=tk.LEFT, padx=5)
        self.refresh_ports()

        # Refresh Ports Button
        self.refresh_btn = ttk.Button(control_frame, text="🔄", width=3, command=self.refresh_ports)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        # Connect / Disconnect Button
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=10)

        # Save Data Button
        self.save_btn = ttk.Button(control_frame, text="💾 Save CSV", command=self.save_data, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=5)

        # --- Digital Readout, Stroke Analytics & Tolerance Panel ---
        display_frame = ttk.LabelFrame(self.root, text=" Live Digital Readout & Stroke Metrics ", padding="10")
        display_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Top row inside display frame: LCD & Stroke Stats side by side
        readout_container = ttk.Frame(display_frame)
        readout_container.pack(side=tk.TOP, fill=tk.X, pady=2)

        # LCD Display Label
        self.lcd_label = ttk.Label(readout_container, text="0.00 mm", font=("Consolas", 32, "bold"), foreground="#007acc")
        self.lcd_label.pack(side=tk.LEFT, padx=20)

        # Stroke / Extrema Stats Label Frame
        stats_frame = ttk.Frame(readout_container)
        stats_frame.pack(side=tk.LEFT, padx=20)

        self.stroke_label = ttk.Label(stats_frame, text="Stroke (Peak-to-Peak): 0.00 mm", font=("Arial", 10))
        self.stroke_label.pack(anchor=tk.W)
        self.max_label = ttk.Label(stats_frame, text="Max Extension: 0.00 mm", font=("Arial", 9), foreground="gray")
        self.max_label.pack(anchor=tk.W)
        self.min_label = ttk.Label(stats_frame, text="Min Retraction: 0.00 mm", font=("Arial", 9), foreground="gray")
        self.min_label.pack(anchor=tk.W)

        # Status indicator for Pass/Fail tolerance
        self.status_label = ttk.Label(display_frame, text="IDLE", font=("Arial", 10, "bold"), foreground="gray")
        self.status_label.pack(side=tk.TOP, pady=2)

        # --- Tolerance Configuration Sub-panel ---
        tol_frame = ttk.Frame(display_frame)
        tol_frame.pack(side=tk.TOP, pady=5)

        self.tol_var = tk.BooleanVar(value=False)
        self.tol_check = ttk.Checkbutton(tol_frame, text="Enable Tolerance Limits", variable=self.tol_var, command=self.toggle_tolerance)
        self.tol_check.pack(side=tk.LEFT, padx=5)

        ttk.Label(tol_frame, text="Min (mm):").pack(side=tk.LEFT, padx=2)
        self.min_entry = ttk.Entry(tol_frame, width=6)
        self.min_entry.insert(0, "0.0")
        self.min_entry.pack(side=tk.LEFT, padx=2)

        ttk.Label(tol_frame, text="Max (mm):").pack(side=tk.LEFT, padx=2)
        self.max_entry = ttk.Entry(tol_frame, width=6)
        self.max_entry.insert(0, "25.0")
        self.max_entry.pack(side=tk.LEFT, padx=2)

    def setup_plots(self):
        # Create Matplotlib Figure with 2 Subplots (Displacement and Velocity)
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6), dpi=100)
        
        # Subplot 1: Displacement
        self.ax1.set_title("Live Displacement Readings", fontsize=10, fontweight='bold')
        self.ax1.set_ylabel("Travel (mm)", fontsize=8)
        self.ax1.grid(True, linestyle="--", alpha=0.6)
        self.line1, = self.ax1.plot([], [], color="#007acc", lw=2, label="Displacement")
        self.ax1.legend(loc="upper right", fontsize=7)

        # Subplot 2: Velocity
        self.ax2.set_title("Sensor Velocity (First Derivative)", fontsize=10, fontweight='bold')
        self.ax2.set_xlabel("Time elapsed (seconds)", fontsize=8)
        self.ax2.set_ylabel("Speed (mm/s)", fontsize=8)
        self.ax2.grid(True, linestyle="--", alpha=0.6)
        self.line_vel, = self.ax2.plot([], [], color="#28a745", lw=1.5, label="Velocity")
        self.ax2.legend(loc="upper right", fontsize=7)

        self.fig.tight_layout()

        # Embed Matplotlib Figure inside Tkinter layout
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh_ports(self):
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
            self.serial_port = serial.Serial(selected_port, 115200, timeout=0.1)
            self.is_running = True
            self.connect_btn.config(text="Disconnect")
            self.port_combobox.config(state="disabled")
            self.refresh_btn.config(state="disabled")
            self.save_btn.config(state="disabled")
            
            # Reset session parameters
            self.start_time = time.time()
            self.time_data.clear()
            self.value_data.clear()
            self.all_time_stamps.clear()
            self.all_values.clear()

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
        self.status_label.config(text="IDLE", foreground="gray")
        
        if self.all_values:
            self.save_btn.config(state="normal")

    def toggle_tolerance(self):
        self.tolerance_active = self.tol_var.get()
        if self.tolerance_active:
            try:
                self.lower_limit = float(self.min_entry.get())
                self.upper_limit = float(self.max_entry.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values for tolerance boundaries.")
                self.tol_var.set(False)
                self.tolerance_active = False

    def read_serial_stream(self):
        if not self.is_running:
            return

        latest_display_val = None

        while self.serial_port and self.serial_port.in_waiting > 0:
            try:
                raw_line = self.serial_port.readline()
                clean_line = raw_line.decode('utf-8').strip()
                
                if clean_line:
                    val = float(clean_line)
                    latest_display_val = val
                    elapsed_time = time.time() - self.start_time
                    
                    self.time_data.append(elapsed_time)
                    self.value_data.append(val)
                    
                    self.all_time_stamps.append(round(elapsed_time, 3))
                    self.all_values.append(round(val, 3))
                    
            except ValueError:
                pass
            except Exception:
                self.stop_serial()
                return

        # Update Digital Screen, Stroke Metrics, and Quality Control Status
        if latest_display_val is not None:
            self.lcd_label.config(text=f"{latest_display_val:.2f} mm")
            
            if self.all_values:
                session_max = max(self.all_values)
                session_min = min(self.all_values)
                stroke_range = session_max - session_min
                
                self.stroke_label.config(text=f"Stroke (Peak-to-Peak): {stroke_range:.2f} mm")
                self.max_label.config(text=f"Max Extension: {session_max:.2f} mm")
                self.min_label.config(text=f"Min Retraction: {session_min:.2f} mm")

            if self.tolerance_active:
                if self.lower_limit <= latest_display_val <= self.upper_limit:
                    self.status_label.config(text="PASS (Within Specification)", foreground="#28a745")
                else:
                    self.status_label.config(text="FAIL (Out of Bounds)", foreground="#dc3545")
            else:
                self.status_label.config(text="LOGGING ACTIVE", foreground="#007acc")

        # Refresh Plots and Kinematics
        if len(self.time_data) > 2:
            t_arr = np.array(self.time_data)
            v_arr = np.array(self.value_data)
            
            velocity = np.gradient(v_arr, t_arr)

            # Update Plot 1 (Displacement)
            self.line1.set_data(t_arr, v_arr)
            self.ax1.set_xlim(t_arr[0], t_arr[-1] + 0.5)
            y_min, y_max = np.min(v_arr), np.max(v_arr)
            padding = max(1.0, (y_max - y_min) * 0.1)
            self.ax1.set_ylim(y_min - padding, y_max + padding)

            # Update Plot 2 (Velocity)
            self.line_vel.set_data(t_arr, velocity)
            self.ax2.set_xlim(t_arr[0], t_arr[-1] + 0.5)
            v_min, v_max = np.min(velocity), np.max(velocity)
            v_pad = max(0.5, (v_max - v_min) * 0.1)
            self.ax2.set_ylim(v_min - v_pad, v_max + v_pad)
            
            self.canvas.draw_idle()

        if self.is_running:
            self.root.after(15, self.read_serial_stream)

    def save_data(self):
        if not self.all_values:
            messagebox.showwarning("Warning", "No session logs recorded to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Displacement Log Asset"
        )
        
        if file_path:
            try:
                with open(file_path, mode='w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(["Relative Time (s)", "Displacement (mm)"])
                    for t, v in zip(self.all_time_stamps, self.all_values):
                        writer.writerow([t, v])
                messagebox.showinfo("Success", f"Dataset successfully saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to save structural file output:\n{str(e)}")

    def on_closing(self):
        self.stop_serial()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CaliperPlotterApp(root)
    root.mainloop()

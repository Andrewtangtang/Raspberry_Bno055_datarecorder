# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_bno055
import serial
import csv
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
import os
from upload_togoogle import GoogleDriveUploader


i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_bno055.BNO055_I2C(i2c)
google_uploader = GoogleDriveUploader()
last_val = 0xFFFF

# CSV file settings
csv_dir = "sensor_data/"
csv_filename = ""
csv_header = ["Packet number", "Gyroscope X (deg/s)", "Gyroscope Y (deg/s)", "Gyroscope Z (deg/s)", 
            "Accelerometer X (g)", "Accelerometer Y (g)", "Accelerometer Z (g)","Magnetometer X (microteslas)","Magnetometer Y (microteslas)","Magnetometer Z (microteslas)","Timestamp"]

# Global variables for UI updates and thread communication
FREQUENCY = 50
packet_counter = 0
running = True
ui_active = False
collecting_data = False  # Flag to indicate if data collection is active

# These variables will be used to communicate between threads
latest_gyro = None
latest_accel = None
latest_mag = None
latest_timestamp = None
latest_timestamp_str = None
latest_error = None

# Create UI management class
class SensorUI:
    def __init__(self):
        self.root = None
        self.stop_button = None
        self.exit_button = None
        self.packet_label = None
        self.time_label = None
        self.gyro_label = None
        self.accel_label = None
        self.mag_label = None
        self.error_label = None
        self.status_label = None
        self.upload_label = None

    def setup_ui(self):
        # Create the GUI
        self.root = tk.Tk()
        self.root.title("I2C Data Recorder")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)

        # Create a frame for content with some padding
        frame = ttk.Frame(self.root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # Create labels for displaying data
        title_label = ttk.Label(frame, text="I2C Sensor Data Recorder", font=("Arial", 16, "bold"))
        title_label.pack(pady=5)

        self.status_label = ttk.Label(frame, text="Status: Ready", foreground="blue", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=2)

        self.packet_label = ttk.Label(frame, text="Data Count: 0")
        self.packet_label.pack(pady=2)

        self.time_label = ttk.Label(frame, text="Timestamp: --")
        self.time_label.pack(pady=2)

        self.gyro_label = ttk.Label(frame, text="Gyroscope (rad/s): --")
        self.gyro_label.pack(pady=2)

        self.accel_label = ttk.Label(frame, text="Accelerometer (m/s^2): --")
        self.accel_label.pack(pady=2)
        
        self.mag_label = ttk.Label(frame, text="Magnetometer (microteslas): --")
        self.mag_label.pack(pady=2)

        self.error_label = ttk.Label(frame, text="", foreground="red")
        self.error_label.pack(pady=2)
        
        self.upload_label = ttk.Label(frame, text="", foreground="blue")
        self.upload_label.pack(pady=2)

        # Create buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Recording", command=self.start_collection)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop Recording", command=self.stop_collection, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.exit_button = ttk.Button(button_frame, text="Exit", command=self.exit_application)
        self.exit_button.pack(side=tk.LEFT, padx=5)
        
        # Start UI updates
        self.update_ui()
        
    def start_collection(self):
        global collecting_data
        collecting_data = True
        self.status_label.config(text="Status: Running", foreground="green")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.exit_button.config(state="disabled")
        print("Data collection started")

    def update_ui(self):
        global packet_counter, latest_gyro, latest_accel, latest_mag, latest_timestamp_str, latest_error, ui_active
        
        if not ui_active:
            return
            
        if running:
            # Update data display
            self.packet_label.config(text=f"Data Count: {packet_counter}")
            
            if latest_timestamp_str:
                self.time_label.config(text=f"Timestamp: {latest_timestamp_str}")
            
            if latest_gyro:
                self.gyro_label.config(text=f"Gyroscope (rad/s): {latest_gyro}")
            
            if latest_accel:
                self.accel_label.config(text=f"Accelerometer (m/s^2): {latest_accel}")
                
            if latest_mag:
                self.mag_label.config(text=f"Magnetometer (microteslas): {latest_mag}")
            
            if latest_error:
                self.error_label.config(text=f"Error: {latest_error}")
            
            # Schedule the next UI update (less frequent to not slow down data collection)
            self.root.after(100, self.update_ui)
        
    def stop_collection(self):
        global running, collecting_data
        collecting_data = False
        self.status_label.config(text="Status: Stopped", foreground="red")
        self.stop_button.config(state="disabled")
        self.start_button.config(state="normal")
        self.exit_button.config(state="normal")
        print("Data collection stopped")

    def exit_application(self):
        global ui_active, running, collecting_data, csv_filename
        
        # Don't exit immediately, just disable controls and show uploading status
        self.exit_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        
        # First stop data collection
        running = False  # Signal main loop to exit
        collecting_data = False
        
        # Show uploading status
        self.status_label.config(text="Status: Uploading to cloud", foreground="blue")
        
        # Upload the CSV file to Google Drive if it exists
        if csv_filename and os.path.exists(csv_filename):
            try:
                self.upload_label.config(text=f"Uploading {os.path.basename(csv_filename)} to Google Drive...")
                self.root.update()  # Force UI update
                
                print(f"Uploading {csv_filename} to Google Drive...")
                file_id = google_uploader.upload_file(csv_filename)
                
                if file_id:
                    success_msg = f"Successfully uploaded to Google Drive with ID: {file_id}"
                    self.upload_label.config(text=success_msg, foreground="green")
                    print(f"Successfully uploaded {csv_filename} to Google Drive with ID: {file_id}")
                    # Display the success message for 2 seconds before closing
                    self.root.update()
                    time.sleep(2)
                else:
                    fail_msg = f"Failed to upload to Google Drive"
                    self.upload_label.config(text=fail_msg, foreground="red")
                    print(f"Failed to upload {csv_filename} to Google Drive")
                    # Display the failure message for 3 seconds before closing
                    self.root.update()
                    time.sleep(3)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.upload_label.config(text=error_msg, foreground="red")
                self.root.update()
                print(f"Error uploading file to Google Drive: {e}")
                time.sleep(3)
        else:
            self.upload_label.config(text="No data file to upload", foreground="orange")
            self.root.update()
            time.sleep(2)
        
        # Now we can safely exit
        ui_active = False
        self.root.destroy()
        
    def run(self):
        global ui_active
        ui_active = True
        self.setup_ui()
        self.root.mainloop()
        print("UI thread terminated")

# Main data collection function - now runs in the main thread
def collect_data():
    global packet_counter, running, latest_gyro, latest_accel, latest_mag, latest_timestamp, latest_timestamp_str, latest_error, collecting_data
    
    print("Data collection function running in main thread")
    
    # Create a new CSV file with date and time in filename
    global csv_filename
    os.makedirs(csv_dir, exist_ok=True)
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = f"{csv_dir}{current_time}.csv"
    print(f"Creating new CSV file: {csv_filename}")
    
    # Initialize CSV file
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(csv_header)
    
    while running:
        if collecting_data:  # Only collect data when the start button has been pressed
            try:
                # Get sensor data - priority on speed and accuracy
                start_time = time.time()
                gyro = sensor.gyro
                accel = sensor.acceleration
                mag = sensor.magnetic
                timestamp = time.time()
                timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                # Write raw data to CSV file
                if csv_filename:
                    with open(csv_filename, 'a', newline='') as csvfile:
                        csv_writer = csv.writer(csvfile)
                        csv_writer.writerow([
                            packet_counter,
                            gyro[0], gyro[1], gyro[2],
                            accel[0], accel[1], accel[2],
                            mag[0], mag[1], mag[2],
                            timestamp
                        ])
                
                # Update shared variables for UI thread to use
                latest_gyro = gyro
                latest_accel = accel
                latest_mag = mag
                latest_timestamp = timestamp
                latest_timestamp_str = timestamp_str
                latest_error = None

                # Increment counter
                packet_counter += 1
                
                # Calculate sleep time to maintain desired frequency
                elapsed = time.time() - start_time
                sleep_time = max(0, 1/FREQUENCY - elapsed)  # Ensure we don't get negative sleep time
                time.sleep(sleep_time)
                
            except Exception as e:
                print("Error occurred:", e)
                latest_error = str(e)
                time.sleep(0.5)
        else:
            # If not collecting data, just sleep briefly to avoid consuming CPU
            time.sleep(0.1)

# Main function to start both threads
def main():
    # Create the UI object
    sensor_ui = SensorUI()
    
    # Start UI in a separate thread
    ui_thread = threading.Thread(target=sensor_ui.run)
    ui_thread.daemon = True  # Thread will close when main program exits
    ui_thread.start()
    
    # Start data collection in the main thread
    # It will wait for the start button press before actually collecting data
    collect_data()
    
    print("Data collection function exited")
    
    # Wait for UI thread to finish if it's still running
    if ui_active and ui_thread.is_alive():
        print("Waiting for UI thread to terminate...")
        ui_thread.join(timeout=3)
    
    print("Program finished")

# Run the main function if script is executed directly
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        running = False
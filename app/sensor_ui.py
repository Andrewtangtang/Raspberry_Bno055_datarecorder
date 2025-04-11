# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import tkinter as tk
from tkinter import ttk
import threading
import os
from datetime import datetime

# This class has been moved to a separate file for better organization
class SensorUI:
    def __init__(self, collect_data_function, global_vars):
        # Store the data collection function and global variables
        self.collect_data_function = collect_data_function
        self.globals = global_vars
        
        # Initialize UI components
        self.root = None
        self.stop_button = None
        self.upload_button = None
        self.exit_button = None
        self.packet_label = None
        self.time_label = None
        self.gyro_label = None
        self.accel_label = None
        self.mag_label = None
        self.error_label = None
        self.status_label = None
        self.upload_label = None
        self.data_thread = None

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

        self.upload_button = ttk.Button(button_frame, text="Upload", command=self.upload_to_drive, state="disabled")
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        self.exit_button = ttk.Button(button_frame, text="Exit", command=self.exit_application, state="disabled")
        self.exit_button.pack(side=tk.LEFT, padx=5)
        
        # Start UI updates
        self.update_ui()
        
    def start_collection(self):
        # Set global variables through the globals dictionary
        self.globals['collecting_data'] = True
        self.globals['running'] = True
        
        # Start data collection thread if not already running
        if self.data_thread is None or not self.data_thread.is_alive():
            self.data_thread = threading.Thread(target=self.collect_data_function)
            self.data_thread.daemon = True
            self.data_thread.start()
        
        self.status_label.config(text="Status: Running", foreground="green")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.upload_button.config(state="disabled")
        self.exit_button.config(state="disabled")
        print("Data collection started")

    def update_ui(self):
        # Get global variables from the globals dictionary
        packet_counter = self.globals['packet_counter']
        latest_gyro = self.globals['latest_gyro']
        latest_accel = self.globals['latest_accel']
        latest_mag = self.globals['latest_mag']
        latest_timestamp_str = self.globals['latest_timestamp_str']
        latest_error = self.globals['latest_error']
        running = self.globals['running']
        
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
        # Update global variables through the globals dictionary
        self.globals['collecting_data'] = False
        
        self.status_label.config(text="Status: Stopped", foreground="red")
        self.stop_button.config(state="disabled")
        self.start_button.config(state="normal")
        self.upload_button.config(state="normal")
        self.exit_button.config(state="normal")
        print("Data collection stopped")

    def upload_to_drive(self):
        # Get CSV filename from globals
        csv_filename = self.globals['csv_filename']
        google_uploader = self.globals['google_uploader']
        
        # Disable all buttons during upload
        self.upload_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.exit_button.config(state="disabled")
        
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
                    # Display the success message for 1 second per requirements
                    self.root.update()
                    time.sleep(1)
                else:
                    fail_msg = f"Failed to upload to Google Drive"
                    self.upload_label.config(text=fail_msg, foreground="red")
                    print(f"Failed to upload {csv_filename} to Google Drive")
                    # Display the failure message for 3 seconds per requirements
                    self.root.update()
                    time.sleep(3)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.upload_label.config(text=error_msg, foreground="red")
                self.root.update()
                print(f"Error uploading file to Google Drive: {e}")
                # Display the error message for 3 seconds per requirements
                time.sleep(3)
        else:
            self.upload_label.config(text="No data file to upload", foreground="orange")
            self.root.update()
            time.sleep(2)
        
        # After upload is complete, enable the exit button and start button
        self.start_button.config(state="normal")
        self.exit_button.config(state="normal")
    
    def exit_application(self):
        # Update global variables through the globals dictionary
        self.globals['ui_active'] = False
        self.globals['running'] = False  # Signal data collection thread to exit
        self.globals['collecting_data'] = False
        
        # Wait for data collection thread to finish if it's running
        if self.data_thread and self.data_thread.is_alive():
            print("Waiting for data collection thread to terminate...")
            self.data_thread.join(timeout=2)
        
        # Now we can safely exit
        self.root.destroy()
        
    def run(self):
        # Update global variable
        self.globals['ui_active'] = True
        
        self.setup_ui()
        self.root.mainloop()
        print("UI thread terminated")

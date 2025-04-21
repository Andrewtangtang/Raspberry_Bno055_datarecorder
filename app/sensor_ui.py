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
        self.root.geometry("500x350")  # Standard size to fit all elements
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)

        # Create a frame for content with some padding
        frame = ttk.Frame(self.root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # Create labels for displaying data
        title_label = ttk.Label(frame, text="I2C Sensor Data Recorder", font=("Arial", 16, "bold"))
        title_label.pack(pady=5)

        # Status label with larger, more prominent font
        self.status_label = ttk.Label(frame, text="Status: Ready", foreground="blue", font=("Arial", 14, "bold"))
        self.status_label.pack(pady=5)

        # Data and duration display in a more prominent style with border
        data_frame = ttk.Frame(frame, relief=tk.GROOVE, borderwidth=2)
        data_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Create a frame for data count and duration to display side by side with more space
        info_frame = ttk.Frame(data_frame)
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Data count with more prominent display
        self.packet_label = ttk.Label(info_frame, text="Data Count: 0", font=("Arial", 16, "bold"), foreground="#0066cc")
        self.packet_label.pack(side=tk.LEFT, padx=20)
        
        # Duration label to show elapsed time
        self.duration_label = ttk.Label(info_frame, text="Duration: 0 ms", font=("Arial", 16, "bold"), foreground="#006600")
        self.duration_label.pack(side=tk.RIGHT, padx=20)

        # Sensor value labels (initially blank - will be shown during recording)
        self.gyro_label = ttk.Label(data_frame, text="", font=("Arial", 12))
        self.accel_label = ttk.Label(data_frame, text="", font=("Arial", 12))

        # Add spacer with a horizontal line for better visual separation
        separator = ttk.Separator(frame, orient='horizontal')
        separator.pack(fill='x', pady=15, padx=10)

        self.error_label = ttk.Label(frame, text="", foreground="red")
        self.error_label.pack(pady=2)
        
        self.upload_label = ttk.Label(frame, text="", foreground="blue")
        self.upload_label.pack(pady=2)

        # Create buttons with simple standard layout
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=15, fill=tk.X)
        
        # Create buttons with standard styling
        self.start_button = ttk.Button(button_frame, text="Start Recording", command=self.start_collection)
        self.start_button.pack(side=tk.LEFT, padx=5, expand=True)

        self.stop_button = ttk.Button(button_frame, text="Stop Recording", command=self.stop_collection, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5, expand=True)

        self.upload_button = ttk.Button(button_frame, text="Upload", command=self.upload_to_drive, state="disabled")
        self.upload_button.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.exit_button = ttk.Button(button_frame, text="Exit", command=self.exit_application)
        self.exit_button.pack(side=tk.LEFT, padx=5, expand=True)
        

        
    def prompt_for_filename(self):
        # Create a dialog window for filename input
        dialog = tk.Toplevel(self.root)
        dialog.title("Enter File Name")
        dialog.geometry("400x150")
        dialog.transient(self.root)  # Make it a modal dialog
        dialog.grab_set()  # Modal behavior
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Current date/time for default filename
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = current_time
        
        # Instruction label
        ttk.Label(dialog, text="Enter a filename (without .csv extension):", font=("Arial", 10)).pack(pady=10)
        
        # Filename entry field
        filename_var = tk.StringVar(value=default_filename)
        entry = ttk.Entry(dialog, textvariable=filename_var, width=40)
        entry.pack(pady=5, padx=20)
        entry.select_range(0, 'end')  # Select all text by default
        entry.focus_set()  # Set focus to the entry
        
        # Store the result
        result = [None]
        
        def on_ok():
            result[0] = filename_var.get().strip()
            if not result[0]:
                result[0] = default_filename  # Use default if empty
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=10)
        
        # Make Enter key work as OK button
        dialog.bind("<Return>", lambda event: on_ok())
        dialog.bind("<Escape>", lambda event: on_cancel())
        
        # Wait for the dialog to be closed
        self.root.wait_window(dialog)
        
        return result[0]
    
    def start_collection(self):
        # Prompt user for filename
        filename = self.prompt_for_filename()
        
        # If user cancelled, don't start collection
        if filename is None:
            return
            
        # Update the filename in globals
        csv_dir = "sensor_data/"
        csv_filename = f"{csv_dir}{filename}.csv"
        self.globals['csv_filename'] = csv_filename
        self.globals['custom_filename_provided'] = True
        
        # Reset upload status for new recording
        self.globals['file_uploaded'] = False
        
        # Set global variables through the globals dictionary
        self.globals['running'] = True
        self.globals['collecting_data'] = True
        
        # Clear any previous upload messages
        self.upload_label.config(text="")

        
        
        # Start data collection thread if not already running
        if self.data_thread is None or not self.data_thread.is_alive(): 
            self.data_thread = threading.Thread(target=self.collect_data_function)
            self.data_thread.daemon = True
            self.data_thread.start()
            # Start UI updates
            self.update_ui()

            # Show sensor labels when recording starts
            self.gyro_label.pack(pady=2)
            self.accel_label.pack(pady=2)
        
        self.status_label.config(text="Status: RECORDING", foreground="green", font=("Arial", 14, "bold"))
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.upload_button.config(state="disabled")
        self.exit_button.config(state="disabled")
        print(f"Data collection started with filename: {csv_filename}")

    def update_ui(self):
        # Get global variables from the globals dictionary
        packet_counter = self.globals['packet_counter']
        latest_gyro = self.globals['latest_gyro']
        latest_accel = self.globals['latest_accel']
        latest_mag = self.globals['latest_mag']
        latest_timestamp_str = self.globals['latest_timestamp_str']
        latest_error = self.globals['latest_error']
        running = self.globals['running']
        elapsed_ms = self.globals.get('elapsed_ms', 0)  # Get elapsed time in milliseconds
        if running:
            # Update data display with more prominent formatting
            self.packet_label.config(text=f"Data Count: {packet_counter}")
            
            # Update duration display
            if elapsed_ms is not None:
                self.duration_label.config(text=f"Duration: {elapsed_ms} ms")
            
            if latest_error:
                self.error_label.config(text=f"Error: {latest_error}")
            # Wait for 100ms (less frequent to not slow down data collection)
            self.root.after(100, self.update_ui)
        else:
            # Stop the UI update loop
            self.root.after_cancel(self.update_ui)
        
        # Update sensor value displays
        if latest_gyro is not None:
            self.gyro_label.config(text=f"Gyro (deg/s): {latest_gyro[0]:.2f}, {latest_gyro[1]:.2f}, {latest_gyro[2]:.2f}")
        if latest_accel is not None:
            self.accel_label.config(text=f"Accel (g): {latest_accel[0]:.2f}, {latest_accel[1]:.2f}, {latest_accel[2]:.2f}")
    
    def stop_collection(self):
        # Update global variables through the globals dictionary
        self.globals['running'] = False
        self.globals['collecting_data'] = False
        
        self.status_label.config(text="Status: STOPPED", foreground="red", font=("Arial", 14, "bold"))
        self.stop_button.config(state="disabled")
        # Keep start button disabled as requested - only allow upload or exit after stopping
        self.start_button.config(state="disabled")
        self.upload_button.config(state="normal")
        self.exit_button.config(state="normal")
        self.data_thread = None
        print("Data collection stopped - can only upload or exit")

        # Hide sensor labels when recording stops
        self.gyro_label.pack_forget()
        self.accel_label.pack_forget()
    
    def upload_to_drive(self):
        # Get CSV filename from globals
        csv_filename = self.globals['csv_filename']
        google_uploader = self.globals['google_uploader']
        file_uploaded = self.globals.get('file_uploaded', False)
        
        # Disable all buttons during upload
        self.upload_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.exit_button.config(state="disabled")
        
        # Show uploading status with larger text
        self.status_label.config(text="Status: UPLOADING TO CLOUD", foreground="blue", font=("Arial", 14, "bold"))
        
        # Check if file already uploaded in this session
        if file_uploaded:
            self.upload_label.config(text="This file has already been uploaded", foreground="orange")
            self.root.update()
            time.sleep(2)
        # Upload the CSV file to Google Drive if it exists
        elif csv_filename and os.path.exists(csv_filename):
            try:
                self.upload_label.config(text=f"Uploading {os.path.basename(csv_filename)} to Google Drive...")
                self.root.update()  # Force UI update
                
                print(f"Uploading {csv_filename} to Google Drive...")
                file_id = google_uploader.upload_file(csv_filename)
                
                if file_id:
                    success_msg = f"Successfully uploaded to Google Drive with ID: {file_id}"
                    self.upload_label.config(text=success_msg, foreground="green")
                    print(f"Successfully uploaded {csv_filename} to Google Drive with ID: {file_id}")
                    # Reset file tracking for next recording cycle
                    self.globals['csv_filename'] = None
                    self.globals['custom_filename_provided'] = False
                    self.globals['file_uploaded'] = False
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
        
        # After upload is complete, enable both start and exit buttons
        # This allows starting a new recording cycle after uploading
        self.start_button.config(state="normal")
        self.exit_button.config(state="normal")
        
        # Reset key values for the next recording cycle
        self.globals['packet_counter'] = 0
        self.globals['elapsed_ms'] = 0
        self.globals['start_time'] = None
        
        # Update the UI to reflect reset values
        self.packet_label.config(text="Data Count: 0")
        self.duration_label.config(text="Duration: 0 ms")
        
        # Update status to ready for new recording
        self.status_label.config(text="Status: Ready", foreground="blue", font=("Arial", 14, "bold"))
    
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

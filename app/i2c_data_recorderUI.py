# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_bno055
import serial
import csv
import threading
import os
from datetime import datetime
from upload_togoogle import GoogleDriveUploader
# Import SensorUI from the separate file
from sensor_ui import SensorUI




i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_bno055.BNO055_I2C(i2c)
# Set calibration offsets
# update calibration offsets
calibration_data = {
    "accel_offset_x": -35,    
    "accel_offset_y": -43, 
    "accel_offset_z": -42,     
    "gyro_offset_x": 0,
    "gyro_offset_y": -1,
    "gyro_offset_z": 2,
    "mag_offset_x": -216,
    "mag_offset_y": -76,
    "mag_offset_z": 250,
    "accel_radius": 1000,  
    "mag_radius": 1000
}

sensor.offsets_accelerometer = (
    calibration_data["accel_offset_x"],
    calibration_data["accel_offset_y"],
    calibration_data["accel_offset_z"]
)
sensor.offsets_gyroscope = (
    calibration_data["gyro_offset_x"],
    calibration_data["gyro_offset_y"],
    calibration_data["gyro_offset_z"]
)
sensor.offsets_magnetometer = (
    calibration_data["mag_offset_x"],
    calibration_data["mag_offset_y"],
    calibration_data["mag_offset_z"]
)


google_uploader = GoogleDriveUploader()

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
start_time = None  # For tracking duration
elapsed_ms = 0  # Elapsed time in milliseconds

# Create a dictionary to hold global variables that need to be shared with the UI
global_vars = {
    'packet_counter': packet_counter,
    'running': running,
    'ui_active': ui_active,
    'collecting_data': collecting_data,
    'latest_gyro': latest_gyro,
    'latest_accel': latest_accel,
    'latest_mag': latest_mag,
    'latest_timestamp': latest_timestamp,
    'latest_timestamp_str': latest_timestamp_str,
    'latest_error': latest_error,
    'csv_filename': csv_filename,
    'google_uploader': google_uploader,
    'custom_filename_provided': False,  # Flag to indicate if user provided a custom filename
    'start_time': start_time,  # Time when recording started
    'elapsed_ms': elapsed_ms  # Elapsed time in milliseconds
}


# Data collection function - now runs in a separate thread
def collect_data():
    global packet_counter, running, latest_gyro, latest_accel, latest_mag, latest_timestamp, latest_timestamp_str, latest_error, collecting_data, csv_filename, global_vars
    
    print("Data collection function running in separate thread")
    
    # Check if a custom filename was provided by the user
    custom_filename_provided = global_vars.get('custom_filename_provided', False)
    
    if not custom_filename_provided:
        # No custom filename provided, create a new one with current date and time
        os.makedirs(csv_dir, exist_ok=True)
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_filename = f"{csv_dir}{current_time}.csv"
        global_vars['csv_filename'] = csv_filename  # Update in the global_vars dictionary
        print(f"Creating new CSV file with auto-generated name: {csv_filename}")
    else:
        # Use the custom filename already set in global_vars by SensorUI
        csv_filename = global_vars['csv_filename']
        os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
        print(f"Creating new CSV file with user-provided name: {csv_filename}")
    
    # Initialize CSV file
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(csv_header)
    
    # Initialize recording start time
    recording_start_time = None
    running = global_vars['running']
    
    while running:
        # Check global vars instead of directly accessing globals
        collecting_data = global_vars['collecting_data']  
        running = global_vars['running']
        
        if collecting_data:  # Only collect data when the start button has been pressed
            # Initialize start time when we first start collecting
            if recording_start_time is None:
                recording_start_time = time.time()
                global_vars['start_time'] = recording_start_time
            
            # Calculate elapsed time since recording started (in milliseconds)
            current_time = time.time()
            elapsed_ms = int((current_time - recording_start_time) * 1000)
            global_vars['elapsed_ms'] = elapsed_ms
            
            try:
                # Get sensor data - priority on speed and accuracy
                iteration_start_time = time.time()  # For timing this iteration
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
                
                # Update the global_vars dictionary
                global_vars['latest_gyro'] = gyro
                global_vars['latest_accel'] = accel
                global_vars['latest_mag'] = mag
                global_vars['latest_timestamp'] = timestamp
                global_vars['latest_timestamp_str'] = timestamp_str
                global_vars['latest_error'] = None

                # Increment counter
                packet_counter += 1
                global_vars['packet_counter'] = packet_counter
                
                # Calculate sleep time to maintain desired frequency
                iteration_elapsed = time.time() - iteration_start_time
                sleep_time = max(0, 1/FREQUENCY - iteration_elapsed)  # Ensure we don't get negative sleep time
                time.sleep(sleep_time)
                
            except Exception as e:
                print("Error occurred:", e)
                latest_error = str(e)
                global_vars['latest_error'] = str(e)
                time.sleep(0.5)
        else:
            # If not collecting data, reset time tracking
            recording_start_time = None
            global_vars['start_time'] = None
            global_vars['elapsed_ms'] = 0
            
            # Sleep briefly to avoid consuming CPU
            time.sleep(0.1)
    
    print("Data collection function exited")

# Main function to start the application
def main():
    global global_vars
    
    # Create the UI object with references to the data collection function and global variables
    sensor_ui = SensorUI(collect_data, global_vars)
    
    # Run the UI in the main thread
    sensor_ui.run()
    
    print("Program finished")

# Run the main function if script is executed directly
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        running = False
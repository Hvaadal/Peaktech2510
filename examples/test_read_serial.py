import csv
import argparse
import sys
import os
import queue
import threading
import time
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import matplotlib.pyplot as plt

sys.path.append(os.getcwd()+"\..\peaktech2510")
from PeakTech2510 import PeakTech2510

GET_DATA_FROM_FILE = True
TIMER_FONT = {'family':"Helvetica", 'size':40}
PLOT_X_AXIS_LIMITS = {'left':0, 'right':300}
PLOT_Y_AXIS_LIMITS = [[0, 1.2], [200, 400], [210, 250], [0.5, 2]]

running = False
start_time = 0
data_queue = queue.Queue()

def trigger_press():
    global running
    global toggle_button
    running = not running
    if running:
        # Set initial time for counter
        global start_time
        start_time = time.time()

        # Start threads
        threading.Thread(target=get_data, args=("COM3", 9600, 1, "output", GET_DATA_FROM_FILE), daemon=True).start()
        threading.Thread(target=update_timer).start()
        
        # Update plot is scheduled using tkinter.after(), but we need to kick it off by calling it the first time
        update_plot()

        # Button is now stop button
        toggle_button['text'] = "STOP + SAVE"
    else:
        # Clear the data in a sensible way
        global data_history
        data_history = [[] for _ in range(num_plots)]

        # Button is now start button
        toggle_button['text'] = "START"

def update_timer():
    global timer_label
    global start_time
    global running
    while running:
        print(timer_label.keys())
        timer_label['text'] = f'Test time: {(time.time() - start_time):.2f}s'

def get_data(serial_port, baudrate, timeout, csv_filename, input_from_file=False):
    instrument = PeakTech2510(serial_port, baudrate, timeout, input_from_file)
    
    # Clear the output csv files and write column headers
    for i in range(1,5):
        with open(csv_filename+str(i)+'.csv', 'w', newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=['Display_reading', 'Annunciator_for_Display', 'LCD_Display', 'Polarity'])
            # csv_writer.writeheader()
    
    # Continuously read from instrument and update csv files with data
    global running
    while running:
        # Insert a small delay when reading from file, to simulate more accurately the behaviour of actually connecting to an instrument
        if input_from_file:
            time.sleep(0.01)
        data = instrument.read_data()
        global q
        data_queue.put(data)
        print("put data in q")
        row = {}
        row['Display_reading']= data.get_display_reading()
        row['Annunciator_for_Display'] = data.get_annunciator_text_str()
        row['LCD_Display'] = data.get_display()
        row['Polarity'] = data.get_polarity()
        if data:
            with open(csv_filename+row['LCD_Display']+'.csv', 'a', newline='') as csv_file: 
                csv_writer = csv.DictWriter(csv_file, fieldnames=['Display_reading', 'Annunciator_for_Display', 'LCD_Display', 'Polarity'])
                csv_writer.writerow(row)

    instrument.close()

def update_plot():
    global data_history
    global q
    while not data_queue.empty():
        data=data_queue.get()
        print("got data from q", data.get_display_reading())
        data_history[int(data.get_display())-1].append(float(data.get_display_reading()))
    print(data_history[:][-10:])
    # Update each subplot
    for i, ax in enumerate(axs.flatten()):
        ax.clear()
        print("PLotting", i, " with data", data_history[i])
        ax.plot(data_history[i], linewidth=2)
        ax.set_title(titles[i])
        ax.set_xlabel(x_labels[i])
        ax.set_ylabel(y_labels[i])
        ax.set_ylim(bottom=PLOT_Y_AXIS_LIMITS[i][0], top=PLOT_Y_AXIS_LIMITS[i][1])
        ax.set_xlim(left=PLOT_X_AXIS_LIMITS['left'], right=PLOT_X_AXIS_LIMITS['right'])
        # ax.set_xlim(left=0, right=100)

    canvas.draw()

    if running:
        root.after(500, update_plot)



    # Show the plot
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read data from the RS-232 device and store it in a CSV file.")
    parser.add_argument('-p', '--port', type=str, required=True, help="Serial port name, e.g., COM3 or /dev/ttyS0.")
    parser.add_argument('-b', '--baudrate', type=int, default=9600, help="Baud rate. Default is 9600.")
    parser.add_argument('-t', '--timeout', type=float, default=1.0, help="Timeout for reading data in seconds. Default is 1 second.")
    parser.add_argument('-f', '--file', type=str, default='output', help="Output CSV filename. Default is 'output'.")
    
    args = parser.parse_args()
    
    # GUI setup
    root = tk.Tk()
    root.title("Hello world")
    toggle_button = tk.Button(root, text="START", command=trigger_press, font=tk.font.Font(family=TIMER_FONT['family'], size=TIMER_FONT['size']))
    toggle_button.pack()
    timer_label = tk.Label(root, text="Test time 0.00s", font=tk.font.Font(family=TIMER_FONT['family'], size=TIMER_FONT['size']))
    timer_label.pack()
    

    # Plot setup
    num_plots = 4
    data_history = [[] for _ in range(num_plots)]
    titles = ['Power factor', 'Power', 'Voltage', 'Current']
    x_labels = ['X1', 'X2', 'X3', 'X4']
    y_labels = ['Power factor', 'Watts', 'Volts', 'Ampere']

    fig, axs = plt.subplots(2, 2, figsize=(10, 10))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    root.mainloop()
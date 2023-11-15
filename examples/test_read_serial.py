import csv
import argparse
import datetime
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
PLOT_X_AXIS_SPAN = 30 # Number of seconds to show for each plot
PLOT_Y_AXIS_LIMITS = [[0, 1.2], [200, 400], [210, 250], [0.5, 2]]
NUM_PLOTS = 4
DATA_HISTORY_DEFAULT_VALUE = [[[] for _ in range(2)] for _ in range(NUM_PLOTS)]

running = False
start_time = 0
data_queue = queue.Queue()

def trigger_press():
    global running
    global data_history
    global data_queue
    global start_time
    running = not running
    if running:
        # Set initial time for counter
        start_time = time.time()

        # Clear the data in a sensible way
        data_history = DATA_HISTORY_DEFAULT_VALUE
        data_queue = queue.Queue()

        # Start threads
        threading.Thread(target=get_data, args=("COM3", 9600, 1, GET_DATA_FROM_FILE), daemon=True).start()
        threading.Thread(target=update_timer).start()
        
        # Update plot is scheduled using tkinter.after(), but we need to kick it off the first time
        update_plot()

        # Button is now stop button
        toggle_button['text'] = "STOP + SAVE"

    else:
        # Store data to csv files
        timestring = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
        # Clear the output csv files and write column headers
        for i in range(4):
            with open(timestring + '_' + titles[i] + '.csv', 'w', newline='') as csv_file:
                csv_writer = csv.DictWriter(csv_file, fieldnames=['Time', titles[i]])
                csv_writer.writeheader()
                for j, data in enumerate(data_history[i][0]):
                    if data is not None:
                        csv_writer.writerow({'Time':data_history[i][1][j], titles[i]:data_history[i][0][j]})

        # Store plot to png file
        canvas.print_png(timestring + "_plots.png")

        # Button is now start button
        toggle_button['text'] = "START"

def update_timer():
    while running:
        timer_label['text'] = f'Test time: {(time.time() - start_time):.2f}s'

def get_data(serial_port, baudrate, timeout, input_from_file=False):
    instrument = PeakTech2510(serial_port, baudrate, timeout, input_from_file)
    # Continuously read from instrument and update csv files with data
    while running:
        # Insert a small delay when reading from file, to simulate more accurately the behaviour of actually connecting to an instrument
        if input_from_file:
            time.sleep(0.1)
        data = instrument.read_data()    
        data_queue.put(data)
        # print("Put data in queue", data)
    instrument.close()

def update_plot():
    # Pop all data put into the queue since last call of the function
    while not data_queue.empty():
        data=data_queue.get()
        print("got data from q", data.get_display_reading())
        data_history[int(data.get_display())-1][0].append(float(data.get_display_reading()))
        data_history[int(data.get_display())-1][1].append(float(time.time()-start_time))
    print(data_history[:][0][:-10])
    
    # Update each subplot
    for i, ax in enumerate(axs.flatten()):
        ax.clear()
        # print("PLotting", i, " with data length", len(data_history[i][0]), "and", len(data_history[i][1]))
        ax.plot(data_history[i][1], data_history[i][0])
        ax.set_title(titles[i])
        ax.set_xlabel(x_labels[i])
        ax.set_ylabel(y_labels[i])
        ax.set_ylim(bottom=PLOT_Y_AXIS_LIMITS[i][0], top=PLOT_Y_AXIS_LIMITS[i][1])
        if len(data_history[i][1]) >= 1:
            left = 0 if (data_history[i][1][-1] < PLOT_X_AXIS_SPAN) else (data_history[i][1][-1] - PLOT_X_AXIS_SPAN)
            right = PLOT_X_AXIS_SPAN if (data_history[i][1][-1] < PLOT_X_AXIS_SPAN) else data_history[i][1][-1]
        else:
            left = 0
            right = PLOT_X_AXIS_SPAN
        ax.set_xlim(left=left, right=right)
    canvas.draw()

    # Schedule new update
    if running:
        root.after(500, update_plot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read data from the RS-232 device and store it in a CSV file.")
    parser.add_argument('-p', '--port', type=str, required=True, help="Serial port name, e.g., COM3 or /dev/ttyS0.")
    parser.add_argument('-b', '--baudrate', type=int, default=9600, help="Baud rate. Default is 9600.")
    parser.add_argument('-t', '--timeout', type=float, default=1.0, help="Timeout for reading data in seconds. Default is 1 second.")
    parser.add_argument('-f', '--file', type=str, default='output', help="Output CSV filename. Default is 'output'.")
    
    args = parser.parse_args()
    
    # GUI setup
    root = tk.Tk()
    root.title("PeakTech2510")
    toggle_button = tk.Button(root, text="START", command=trigger_press, font=tk.font.Font(family=TIMER_FONT['family'], size=TIMER_FONT['size']))
    toggle_button.pack()
    timer_label = tk.Label(root, text="Test time 0.00s", font=tk.font.Font(family=TIMER_FONT['family'], size=TIMER_FONT['size']))
    timer_label.pack()

    # Plot setup
    data_history = DATA_HISTORY_DEFAULT_VALUE
    titles = ['Power factor', 'Power', 'Voltage', 'Current']
    x_labels = ['X1', 'X2', 'X3', 'X4']
    y_labels = ['Power factor', 'Watts', 'Volts', 'Ampere']

    fig, axs = plt.subplots(2, 2, figsize=(10, 10))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    root.mainloop()
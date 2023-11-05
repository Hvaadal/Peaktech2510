import serial
import csv
import argparse
import sys
import os

import matplotlib.pyplot as plt

sys.path.append(os.getcwd()+"\..\peaktech2510")
from PeakTech2510 import PeakTech2510

def main(serial_port, baudrate, timeout, csv_filename):
    instrument = PeakTech2510(serial_port, baudrate, timeout)
    
    # Clear the output csv files and write column headers
    for i in range(1,5):
        with open(csv_filename+str(i)+'.csv', 'w', newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=['Display_reading', 'Annunciator_for_Display', 'LDC_Display', 'Polarity'])
            # csv_writer.writeheader()
    
    # Continuously read from instrument and update csv files with data
    try:
        while True:
            data = instrument.read_data()
            row = {}
            row['Display_reading']= data.get_display_reading()
            row['Annunciator_for_Display'] = data.get_annunciator_text_str()
            row['LDC_Display'] = data.get_display()
            row['Polarity'] = data.get_polarity()
            if data:
                with open(csv_filename+row['LDC_Display']+'.csv', 'a', newline='') as csv_file: 
                    csv_writer = csv.DictWriter(csv_file, fieldnames=['Display_reading', 'Annunciator_for_Display', 'LDC_Display', 'Polarity'])
                    csv_writer.writerow(row)
    except KeyboardInterrupt:
        pass
    except IndexError:
        # Reached the end of our input
        # Plot data
        plot_data()

    instrument.close()

def plot_data():
    # File paths for your CSV files
    csv_files = []
    for i in range(1,5):
        csv_files.append('output' + str(i) + '.csv')

    # Function to read the first column from a CSV file
    def read_first_column(filename):
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            return [float(row[0]) for row in reader if row]  # Extract the first column

    # Read data from CSV files
    datasets = []
    for csv_file in csv_files:
        datasets.append(read_first_column(csv_file))

    # Create 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(10, 10))

    # Titles and labels (you can configure these)
    titles = ['Power factor', 'Power', 'Voltage', 'Current']
    x_labels = ['X1', 'X2', 'X3', 'X4']
    y_labels = ['Power factor', 'Watts', 'Volts', 'Ampere']

    # Plotting data in each subplot
    # Assuming the data is sequential (1, 2, 3, ...)
    for i, data in enumerate(datasets):
        axs[i // 2, i % 2].plot(range(1, len(data) + 1), data)
        axs[i // 2, i % 2].set_title(titles[i])
        # axs[i // 2, i % 2].set_xlabel(x_labels[i])
        axs[i // 2, i % 2].set_ylabel(y_labels[i])
        axs[i // 2, i % 2].set_ylim(bottom=0)

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
    
    main(args.port, args.baudrate, args.timeout, args.file)
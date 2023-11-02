import serial
import csv
import argparse

def parse_data(data_stream):
    """
    Parses the 16-digit data stream from the device and returns a dictionary of the parsed values.
    """
    parsed_data = {
        'End_Word': data_stream[0],
        'Display_reading': int(data_stream[1:9], 2),
        'Decimal_Point': int(data_stream[9], 2),
        'Polarity': 'Positive' if data_stream[10] == '0' else 'Negative',
        'Annunciator_for_Display': int(data_stream[11:13], 2),
        'LDC_Display': int(data_stream[13], 2),
        'D14': data_stream[14],
        'Start_Word': data_stream[15]
    }
    return parsed_data

def main(serial_port, baudrate, timeout, csv_filename):
    # Open the serial connection
    with serial.Serial(serial_port, baudrate=baudrate, timeout=timeout) as ser:
        with open(csv_filename, 'w', newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=['End_Word', 'Display_reading', 'Decimal_Point', 'Polarity', 'Annunciator_for_Display', 'LDC_Display', 'D14', 'Start_Word'])
            csv_writer.writeheader()
            
            while True:
                try:
                    # Read data from serial port
                    data = ser.read(16)  # Read 16 bytes (assuming each digit corresponds to a byte)
                    print("Read: ", data)
                    if len(data) == 16:
                        parsed_data = parse_data(data)
                        csv_writer.writerow(parsed_data)
                except KeyboardInterrupt:
                    # Exit the loop if Ctrl+C is pressed
                    break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read data from the RS-232 device and store it in a CSV file.")
    parser.add_argument('-p', '--port', type=str, required=True, help="Serial port name, e.g., COM3 or /dev/ttyS0.")
    parser.add_argument('-b', '--baudrate', type=int, default=9600, help="Baud rate. Default is 9600.")
    parser.add_argument('-t', '--timeout', type=float, default=1.0, help="Timeout for reading data in seconds. Default is 1 second.")
    parser.add_argument('-f', '--file', type=str, default='output.csv', help="Output CSV filename. Default is 'output.csv'.")
    
    args = parser.parse_args()
    
    main(args.port, args.baudrate, args.timeout, args.file)
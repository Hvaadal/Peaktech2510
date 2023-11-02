import serial
import csv
import argparse
import io
import ast

class PeakTech2510:

    def __init__(self, serial_port, baudrate=9600, timeout=1.0):
        # self.ser = serial.Serial(serial_port, baudrate=baudrate, timeout=timeout)
        self.ser = io.open("input_test.txt")
        data = self.ser.read().split('b')[1:]
        print((data))
        # self.input = [ast.literal_eval('b' + byte_string) for byte_string in data]
        self.input = data

    def read_data(self):
        """Read data from the instrument and return parsed result."""
        data = []
        for i in range(16):
            byte = self.input.pop(0).replace('\'','')
            print(byte)
            data.append(byte)
        if len(data) == 16:
            return self.parse_data(data)
        return None

    @staticmethod
    def parse_data(data_stream):
        """Parses the 16-digit data stream from the device."""
        parsed_data = {
            'End_Word': data_stream[15],
            'Display_reading': data_stream[14:6:-1].reverse(),
            'Decimal_Point': data_stream[6],
            'Polarity': 'Positive' if data_stream[5] == '0' else 'Negative',
            'Annunciator_for_Display': data_stream[4:2:-1],
            'LDC_Display': data_stream[2],
            'D14': data_stream[1],
            'Start_Word': data_stream[0]
        }
        reading = data_stream[14:6:-1]
        reading.reverse()
        parsed_data['Display_reading'] = reading
        return parsed_data

    def close(self):
        """Close the serial connection."""
        self.ser.close()


def main(serial_port, baudrate, timeout, csv_filename):
    instrument = PeakTech2510(serial_port, baudrate, timeout)

    with open(csv_filename, 'w', newline='') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=['End_Word', 'Display_reading', 'Decimal_Point', 'Polarity', 'Annunciator_for_Display', 'LDC_Display', 'D14', 'Start_Word'])
        csv_writer.writeheader()

        try:
            while True:
                data = instrument.read_data()
                if data:
                    csv_writer.writerow(data)
        except KeyboardInterrupt:
            pass

        instrument.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read data from the RS-232 device and store it in a CSV file.")
    parser.add_argument('-p', '--port', type=str, required=True, help="Serial port name, e.g., COM3 or /dev/ttyS0.")
    parser.add_argument('-b', '--baudrate', type=int, default=9600, help="Baud rate. Default is 9600.")
    parser.add_argument('-t', '--timeout', type=float, default=1.0, help="Timeout for reading data in seconds. Default is 1 second.")
    parser.add_argument('-f', '--file', type=str, default='output.csv', help="Output CSV filename. Default is 'output.csv'.")
    
    args = parser.parse_args()
    main(args.port, args.baudrate, args.timeout, args.file)

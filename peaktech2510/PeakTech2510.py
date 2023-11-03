import serial
import csv
import argparse
import io
import ast

# Constants
DISPLAY_READING_LENGTH = 8
DECIMAL_POINT_ALLOWED_VALUES = ['0', '1', '2', '3']
POLARITY_ALLOWED_VALUES = ['Positive', 'Negative']
DISPLAY_ALLOWED_VALUES = ['1', '2', '3', '4']

class Annunciator:

    annunciator_dict = {
        "31": "HZ",
        "34": "DCV",
        "36": "DCA",
        "38": "OHM",
        "39": "KOHM",
        "47": "WATT",
        "48": "KWATT",
        "50": "ACV",
        "52": "ACA",
        "54": "POWER_FACTOR",
        "61": "HOUR",
        "62": "MINUTE",
        "63": "VA",
        "64": "KVA",
        "65": "KW/HR",
        "F2": "W/HR"
    }

    def __init__(self, annunciator:str):
        if annunciator in Annunciator.annunciator_dict:
            self.annunciator = annunciator
        else:
            raise ValueError("Unknown or uninitialized annunciator", annunciator)

    def get_str(self):
        return Annunciator.annunciator_dict[self.annunciator]
        

class PeakTech2510OutputData:
    
    def __init__(self, display_reading, decimal_point, polarity, annunciator, display):
        # Check data integrity
        if type(display_reading) != str or len(display_reading) != DISPLAY_READING_LENGTH:
            raise ValueError("Error when parsing display reading", display_reading)
        if decimal_point not in DECIMAL_POINT_ALLOWED_VALUES:
            raise ValueError("Got unallowed decimal_point value", decimal_point)
        if polarity not in POLARITY_ALLOWED_VALUES:
            raise ValueError("Got unallowed polarity value", polarity)
        if (type(annunciator) != Annunciator):
            raise ValueError("Annunciator is incorrect type", type(annunciator))
        if display not in DISPLAY_ALLOWED_VALUES:
            raise ValueError("Got unallowed display value", display)
        
        self.display_reading = display_reading
        self.decimal_point = decimal_point
        self.polarity = polarity
        self.annunciator = annunciator
        self.display = display

    def get_display_reading(self):
        if self.decimal_point == "0":
            # No decimal point
            return self.display_reading
        else:
            # Add decimal point
            return self.display_reading[:-int(self.decimal_point)] + ',' + self.display_reading[-int(self.decimal_point):]

    def get_display_reading_raw(self):
        return self.display_reading

    def get_decimal_point(self):
        return self.decimal_point
    
    def get_polarity(self):
        return self.polarity

    def get_annunciator_str(self):
        return self.annunciator.get_str()
    
    def get_display(self):
        return self.display
    

class PeakTech2510:

    def __init__(self, serial_port, baudrate=9600, timeout=1.0):
        # self.ser = serial.Serial(serial_port, baudrate=baudrate, timeout=timeout)
        self.ser = io.open("input_test.txt")
        data = self.ser.read().split('b')[1:]
        print((data))
        # self.input = [ast.literal_eval('b' + byte_string) for byte_string in data]
        self.input = data

    def read_data(self) -> PeakTech2510OutputData:
        """Read data from the instrument and return parsed result."""
        data = []
        for i in range(16):
            byte = self.input.pop(0).replace('\'','')
            print(byte)
            data.append(byte)
        if len(data) == 16:
            return self._parse_data(data)
        return None

    @staticmethod
    def _parse_data(data_stream):
        """Parses the 16-digit data stream from the device."""
        
        # Reverse the data stream, so it fits with the description from the user manual
        data_stream.reverse()
        parsed_data = {
        'End_Word': data_stream[0],
        'Display_reading': data_stream[1:9],
        'Decimal_Point': data_stream[9],
        'Polarity': 'Positive' if data_stream[10] == '0' else 'Negative',
        'Annunciator_for_Display': data_stream[11:13],
        'LDC_Display': data_stream[13],
        'D14': data_stream[14],
        'Start_Word': data_stream[15]
        }
        # ... and reverse the data sequences that are longer than a single byte aswell
        parsed_data['Display_reading'].reverse()
        parsed_data['Annunciator_for_Display'].reverse()

        # Create a data object
        output_data = None
        try:
            output_data = PeakTech2510OutputData(display_reading="".join(parsed_data['Display_reading']), \
                                                decimal_point=parsed_data['Decimal_Point'], \
                                                polarity=parsed_data['Polarity'], \
                                                annunciator=Annunciator("".join(parsed_data['Annunciator_for_Display'])), \
                                                display=parsed_data['LDC_Display'])
        except ValueError:
            # Print an error, just return an empty reading with all zeroes
            print("WARNING: Error when parsing output data")
            return PeakTech2510OutputData(display_reading=" " * DISPLAY_READING_LENGTH, \
                                                decimal_point='0', \
                                                polarity='Positive', \
                                                annunciator=Annunciator("31"), \
                                                display="1")
        return output_data

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

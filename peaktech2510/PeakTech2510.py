import serial
import csv
import argparse
import io

"""
Wrapper around the serial interface to the PeakTech 2510 Energy meter based on the product manual found on: https://www.peaktech.de/media/52/bd/50/1625732272/PeakTech_2510_07-2021_DE_EN.pdf (05.11.2023)

The PeakTech 2510 serial interface is output only, so the PeakTech2510 object simply reads from a serial connection, and parses the output data.
The user should ensure that read_data() is polled at a sufficient frequency, as no action is taken by the PeakTech2510 object between calls to this function.
"""

# Constants
DATA_FRAME_NUM_BYTES = 16
DATA_FRAME_START_WORD = b'\x02'
DATA_FRAME_END_WORD = b'\r'
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
            raise ValueError("Unknown annunciator", annunciator)

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

    def get_display_reading(self) -> str:
        """ Returns the display reading with the decimal point inserted and a '-' as the first character if it is negative """
        display_reading_with_polarity = self.display_reading
        if self.get_polarity() == 'Negative':
            display_reading_with_polarity = '-' + display_reading_with_polarity
        if self.decimal_point == "0":
            # No decimal point
            return display_reading_with_polarity
        else:
            # Add decimal point
            return display_reading_with_polarity[:-int(self.decimal_point)] + '.' + display_reading_with_polarity[-int(self.decimal_point):]

    def get_display_reading_raw(self) -> str:
        """ Returns the raw display reading as a string of length DISPLAY_READING_LENGTH """
        return self.display_reading

    def get_decimal_point(self) -> str:
        """ Returns the position of the decimal point, if any """
        return self.decimal_point
    
    def get_polarity(self) -> str:
        """ Returns the polarity of the display reading """
        return self.polarity

    def get_annunciator_text_str(self) -> str:
        """ Returns the annunciator text value """
        return self.annunciator.get_str()
    
    def get_annunciator_num_str(self) -> str:
        """ Returns the annunciator numerical value as a str """
        return self.annunciator.get_num()
    
    def get_display(self) -> str:
        """ Returns the display ID """
        return self.display
    

class PeakTech2510:

    def __init__(self, serial_port, baudrate=9600, timeout=1.0, input_from_file=False):
        self.input_from_file = input_from_file
        if self.input_from_file:
            self.input_file = io.open("input_test_2.txt")
            self.input = self.input_file.read().split('b')[1:]
        else:
            self.input = serial.Serial(serial_port, baudrate=baudrate, timeout=timeout)

    def read_data(self, timeout_num_bytes=32) -> PeakTech2510OutputData:
        """Read data from the instrument and return parsed result. 
        Default value for timeout bytes is set to the length of two 16 byte data frames"""
        total_num_bytes = 0
        data = []
        current_byte = ''

        # Pop bytes until a start of data byte is found or we time out
        while total_num_bytes < timeout_num_bytes:
            current_byte = self._pop_byte()
            if current_byte == DATA_FRAME_START_WORD:
                break
            print(current_byte, "is not equal to", DATA_FRAME_START_WORD)
            total_num_bytes += 1
        
        # Did we find start of data byte?
        if not current_byte == DATA_FRAME_START_WORD:
            print("Timeout. Did not find start of data byte in the first", timeout_num_bytes, "bytes")
            return None
        print("Found start of data byte")

        # Append start of data byte to data frame
        data.append(current_byte.decode())

        # Expect multiple start of data bytes, the PeakTech2510 sometimes sends more of them for some reason...
        while total_num_bytes < timeout_num_bytes:
            current_byte = self._pop_byte()
            if current_byte != DATA_FRAME_START_WORD:
                data.append(current_byte.decode())
                break
            total_num_bytes += 1

        # Did we time out?
        if not total_num_bytes < timeout_num_bytes:
            print("Timeout. Did not find start of data byte in the first", timeout_num_bytes, "bytes")
            return None
        
        # Pop remaining bytes in the data frame
        current_data_frame_num_bytes = 1
        while current_data_frame_num_bytes < (DATA_FRAME_NUM_BYTES - 1):
            current_byte = self._pop_byte()
            data.append(current_byte.decode())
            current_data_frame_num_bytes += 1
        
        # _parse_data() will handle erroneous data within the frame. Our job is just to ensure correct length and presence of start
        # and end of data
        if len(data) != DATA_FRAME_NUM_BYTES or data[-1].encode() != DATA_FRAME_END_WORD:
            print("Wrong data frame size, did not find end word in expected place. Data frame was", data, "with length", len(data))
            return None

        print("Found full data frame", data)
        return self._parse_data(data)

    def _pop_byte(self) -> str:
        if self.input_from_file:
            # Handle start/stop characters separately
            current_char = self.input.pop(0).replace('\'','')
            if current_char.startswith('\\'):
                current_byte = bytes(current_char, "utf-8").decode("unicode_escape").encode("latin1")
            else:
                current_byte = bytes(current_char, "utf-8")
        else:
            current_byte = self.input.read(1)
        print("found byte", current_byte, "type", type(current_byte), current_byte.decode())
        return current_byte

    @staticmethod
    def _parse_data(data_frame) -> PeakTech2510OutputData:
        """Parses the 16-digit data frame from the device """
        
        # Reverse the data frame, so it fits with the description from the user manual
        data_frame.reverse()
        
        # Decode the data packet according to the user manual
        parsed_data = {
        'End_Word': data_frame[0],
        'Display_reading': data_frame[1:9],
        'Decimal_Point': data_frame[9],
        'Polarity': 'Positive' if data_frame[10] == '0' else 'Negative',
        'Annunciator_for_Display': data_frame[11:13],
        'LCD_Display': data_frame[13],
        'D14': data_frame[14],
        'Start_Word': data_frame[15]
        }
        # ... and reverse the order of data sequences that are longer than a single byte aswell
        parsed_data['Display_reading'].reverse()
        parsed_data['Annunciator_for_Display'].reverse()

        # Create a data object
        output_data = None
        try:
            output_data = PeakTech2510OutputData(display_reading="".join(parsed_data['Display_reading']), \
                                                decimal_point=parsed_data['Decimal_Point'], \
                                                polarity=parsed_data['Polarity'], \
                                                annunciator=Annunciator("".join(parsed_data['Annunciator_for_Display'])), \
                                                display=parsed_data['LCD_Display'])
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
        if not self.input_from_file:
            self.input.close()


def main(serial_port, baudrate, timeout, csv_filename):
    instrument = PeakTech2510(serial_port, baudrate, timeout)

    with open(csv_filename, 'w', newline='') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=['End_Word', 'Display_reading', 'Decimal_Point', 'Polarity', 'Annunciator_for_Display', 'LCD_Display', 'D14', 'Start_Word'])
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

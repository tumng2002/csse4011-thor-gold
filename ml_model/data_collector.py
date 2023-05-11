import time
import threading
import serial
import queue
import re
import json

to_database_queue = queue.Queue()



def get_base_data():

    ser = serial.Serial(port="/dev/ttyACM0") # depending on the device used. 
    while True:
        line = ser.readline().decode('utf-8') # assuming still passing through JSON format
        inc_sensor = re.findall('\{(.+?)\}', line)
        if not inc_sensor:
            continue
        for a in inc_sensor:
            data = json.loads("{" + a + "}") 
            to_database_queue.put(data)


def main():

    data_thread = threading.Thread(target=get_base_data, daemon=True)
    data_thread.start()

    while True:
        data = to_database_queue.get()
        # use the database from the collector and pass through model. the model takes frames of values. 
        # need to figure out how this actually works...

if __name__ == "__main__":
    main()
"""
You can run the following code using:
    $ bokeh serve --show new_ganglion_visualizer.py

    

"""
import asyncio
import math
import queue
import threading
import time

import aioconsole
import numpy as np
from bokeh.models import ColumnDataSource, DataRange1d, Range1d
from bokeh.plotting import curdoc, figure
from brainflow.data_filter import *
from paho.mqtt import client as mqtt_client

from bleak import BleakClient, BleakScanner

source = ColumnDataSource(dict(frequencies=[], magnitudes=[]))
filter = DataFilter()
input_value = 0

p = figure(title="Live Data Stream", sizing_mode="stretch_both")
p.x_range = Range1d(start=0, end=100)
p.y_range = Range1d(start=0, end=1000)
p.line(source=source, x="frequencies", y="magnitudes", line_width=2, alpha=0.85)


def binary_search(arr, target):
    if len(arr) <= 0:
        return -1

    low, high = 0, len(arr) - 1
    closest_index = low

    while low <= high:
        mid = (low + high) // 2

        if abs(arr[mid] - target) < abs(arr[closest_index] - target):
            closest_index = mid

        if arr[mid] < target:
            low = mid + 1
        elif arr[mid] > target:
            high = mid - 1
        else:
            return mid

    return closest_index


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


broker = "eduoracle.ugavel.com"
port = 1883
topic = "ganglion/data"
client_id = "rishab"
username = "giiuser"
password = "giipassword"
client = connect_mqtt()


def publish(client, message):
    result = client.publish(topic, message)
    # result: [0, 1]
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {topic}")


def update_data(new_frequencies, new_magnitudes):
    source.data = dict(frequencies=new_frequencies, magnitudes=new_magnitudes)


async def update():
    if freq_queue.empty():
        return

    new_frequencies, new_magnitudes = freq_queue.get()
    update_data(new_frequencies, new_magnitudes)


# Add periodic callback to update plot
curdoc().add_periodic_callback(
    update, 1
)  # Updates every millisecond - realistically, need to change the limit

address = ""
read_uuid = "2d30c082-f39f-4ce6-923f-3484ea480596"
write_uuid = "2d30c083-f39f-4ce6-923f-3484ea480596"
SCALE = 0.0001869917138805
num_fft_points = 50
freq_queue = queue.Queue()
nd_array_points = np.array([0.0])
start_index = 0
stop_index = 0
DRY_ELEC = 22  # 2.9

# TODO: TUNE
WET_ELEC = 3.68

# TODO: TUNE
wet = False


async def connect(address):
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name == "Ganglion-2b18" or d.name == "Simblee":
            address = d.address
            break

    if address == "":
        print("Ganglion not found.")
        return
    else:
        print("Ganglion connected.")

    async with BleakClient(address) as client:
        await client.start_notify(read_uuid, callback)

        print("Ganglion sending data...")

        await client.write_gatt_char(write_uuid, bytes("b", "ascii"))

        print("Data stream started.")

        while True:
            input_str = await aioconsole.ainput("Press 'q' to quit: \n")
            if input_str == "q":
                print("Data stream ending...")
                await client.write_gatt_char(write_uuid, bytes("s", "ascii"))
                await client.disconnect()
                print("Client disconnected.")
                quit()


def get_input(inp):
    # TODO: TUNE
    if wet:
        inp /= 10
        inp -= 0.6
    else:
        inp /= 10
        inp -= 0.6

    if inp < 0:
        return 0

    if inp >= 1:
        return 1

    return inp


async def callback(sender, data):
    global nd_array_points
    global nd_array_times
    global overlap
    global tick
    global start_index
    global stop_index

    # Add new data to the arrays
    if len(data) == 20 and data[19] != 0:
        full_int = int.from_bytes(data, "big")

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        extracted_bits *= SCALE

        if extracted_bits > 50 and (extracted_bits < 900 or extracted_bits > 1000):
            nd_array_points = np.insert(
                nd_array_points, nd_array_points.size - 1, [extracted_bits]
            )
            # 25 - 40
            # if tick > overlap:
            if len(nd_array_points) > num_fft_points:
                filter.remove_environmental_noise(
                    nd_array_points,  # data
                    200,  # sampling rate
                    NoiseTypes.FIFTY_AND_SIXTY,  # frequency
                )

                # filter.perform_rolling_filter(nd_array_points, 2, AggOperations.MEAN)
                """
                filter.perform_bandstop(
                    nd_array_points,  # data
                    200,  # sampling rate
                    22,  # start freq
                    25,  # stop freq
                    1,  # order
                    FilterTypes.BUTTERWORTH,
                    0,
                )
                """

                magnitudes = np.abs(np.fft.fft(nd_array_points))
                frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)

                half_index = len(frequencies) // 2

                # considers only positive half
                freq_queue.put((frequencies[:half_index], magnitudes[:half_index]))

                if len(frequencies) > 0:
                    start_index = binary_search(frequencies, 13)
                    stop_index = binary_search(frequencies, 40)

                    sum_of_values = 0
                    for i in range(start_index, stop_index):
                        if wet:
                            sum_of_values = abs(magnitudes[i] - WET_ELEC)
                        else:
                            sum_of_values = abs(magnitudes[i] - DRY_ELEC)

                    input_value = sum_of_values / (stop_index - start_index)

                publish(client, get_input(input_value))

                nd_array_points = nd_array_points[1:]

        extracted_bits = (full_int >> (num_bits - 103)) & mask  # skip 84 + 19
        extracted_bits *= SCALE

        if extracted_bits > 50 and (extracted_bits < 900 or extracted_bits > 1000):
            nd_array_points = np.insert(
                nd_array_points, nd_array_points.size - 1, [extracted_bits]
            )

            # if tick > overlap:
            if len(nd_array_points) > num_fft_points:
                filter.remove_environmental_noise(
                    nd_array_points,  # data
                    200,  # sampling rate
                    NoiseTypes.FIFTY_AND_SIXTY,  # frequency
                )

                # filter.perform_rolling_filter(nd_array_points, 2, AggOperations.MEAN)
                """
                filter.perform_bandstop(
                    nd_array_points,  # data
                    200,  # sampling rate
                    22,  # start freq
                    25,  # stop freq
                    1,  # order
                    FilterTypes.BUTTERWORTH,
                    0,
                )
                """

                magnitudes = np.abs(np.fft.fft(nd_array_points))
                frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)

                half_index = len(frequencies) // 2

                # considers only positive half
                freq_queue.put((frequencies[:half_index], magnitudes[:half_index]))

                if len(frequencies) > 0:
                    start_index = binary_search(frequencies, 13)
                    stop_index = binary_search(frequencies, 40)

                    if wet:
                        sum_of_values = abs(magnitudes[i] - WET_ELEC)
                    else:
                        sum_of_values = abs(magnitudes[i] - DRY_ELEC)

                    input_value = sum_of_values / (stop_index - start_index)

                publish(client, get_input(input_value))

                nd_array_points = nd_array_points[1:]


def run_async_connect():
    asyncio.run(connect(address))


curdoc().add_root(p)

# Start the async connection in a separate thread
connect_thread = threading.Thread(target=run_async_connect, args=())
connect_thread.start()

import asyncio
import queue
import threading

import aioconsole
import numpy as np
from bleak import BleakClient, BleakScanner
from bokeh.models import ColumnDataSource, DataRange1d, Range1d
from bokeh.plotting import curdoc, figure
from brainflow.data_filter import *
from paho.mqtt import client as mqtt_client


# Create MQTT connection
def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    # Create the MQTT connection and set the username and password
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


# Form BLE connection, subscribe to the read characteristic, and handle quitting
async def connect(address):
    # Search for the Ganglion
    devices = await BleakScanner.discover()
    for d in devices:
        # Depending on OS, this name may be different - consider both
        if d.name == "Ganglion-2b18" or d.name == "Simblee":
            address = d.address
            break

    if address == "":
        print("Ganglion not found.")
        return
    else:
        print("Ganglion connected.")

    async with BleakClient(address) as client:
        # Subscribe to the read characteristic and call 'callback' whenever data is received
        await client.start_notify(read_uuid, callback)

        print("Ganglion sending data...")

        # Send the character to start Ganglion data stream
        await client.write_gatt_char(write_uuid, bytes("b", "ascii"))

        print("Data stream started.")

        # Give the stream a way to safely quit to stop the Ganglion stream first
        while True:
            input_str = await aioconsole.ainput("Press 'q' to quit: \n")
            if input_str == "q":
                print("Data stream ending...")

                # Send the character to stop Ganglion data stream
                await client.write_gatt_char(write_uuid, bytes("s", "ascii"))
                await client.disconnect()
                print("Client disconnected.")
                quit()


# Wrapped for BLE connection to run asynchronously
def run_async_connect():
    asyncio.run(connect(address))


# Publish message to MQTT broker
def publish(client, message):
    # Publish data to broker
    result = client.publish(topic, message)
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {topic}")


SCALE = 0.0001869917138805


# Handle input value processing
def get_input(inp):
    # TODO: TUNE
    if wet:
        inp -= 4.5
        inp /= 9
    else:
        inp /= 10
        inp -= 0.6

    if inp < 0:
        return 0

    if inp >= 1:
        return 1

    return inp


# Binary search to find indices of exact or closest magnitudes
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


# Callback that is called every time Ganglion sends data
async def callback(sender, data):
    global nd_array_points
    global nd_array_times
    global start_index
    global stop_index

    # Add new data to the arrays
    if len(data) == 20 and data[19] != 0:
        full_int = int.from_bytes(data, "big")

        # Retreive the bits from the Ganglion's packet
        mask = (1 << 19) - 1
        num_bits = len(data) * 8
        extracted_bits = (full_int >> (num_bits - 27)) & mask
        extracted_bits *= SCALE

        # If bits are within the right range
        if extracted_bits > 50 and (extracted_bits < 900 or extracted_bits > 1000):
            # Add element to end
            nd_array_points = np.insert(
                nd_array_points, nd_array_points.size - 1, [extracted_bits]
            )

            if len(nd_array_points) > num_fft_points:
                # Remove AC noise
                filter.remove_environmental_noise(
                    nd_array_points,  # data
                    200,  # sampling rate
                    NoiseTypes.FIFTY_AND_SIXTY,  # frequency
                )

                # Perform FFT and calculate magnitudes and frequencies
                magnitudes = np.abs(np.fft.fft(nd_array_points))
                frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)

                # Get index of positive frequencies
                half_index = len(frequencies) // 2

                # Add the arrays to the queue
                freq_queue.put((frequencies[:half_index], magnitudes[:half_index]))

                if len(frequencies) > 0:
                    # Find the indeces we consider
                    start_index = binary_search(frequencies, 10)
                    stop_index = binary_search(frequencies, 40)

                    # Calculate the average change of magnitudes from the given mean values
                    sum_of_values = 0
                    for i in range(start_index, stop_index):
                        if wet:
                            sum_of_values = abs(magnitudes[i] - WET_ELEC)
                        else:
                            sum_of_values = abs(magnitudes[i] - DRY_ELEC)

                    input_value = sum_of_values / (stop_index - start_index)

                # Send this data to the broker
                print(get_input(input_value))
                publish(client, get_input(input_value))

                # Remove the oldest point
                nd_array_points = nd_array_points[1:]

        # Retreive the second set of bits from the Ganglion's packet
        extracted_bits = (full_int >> (num_bits - 103)) & mask  # skip 84 + 19
        extracted_bits *= SCALE

        # If bits are within the right range
        if extracted_bits > 50 and (extracted_bits < 900 or extracted_bits > 1000):
            # Add element to end
            nd_array_points = np.insert(
                nd_array_points, nd_array_points.size - 1, [extracted_bits]
            )

            if len(nd_array_points) > num_fft_points:
                # Remove AC noise
                filter.remove_environmental_noise(
                    nd_array_points,  # data
                    200,  # sampling rate
                    NoiseTypes.FIFTY_AND_SIXTY,  # frequency
                )

                # Perform FFT and calculate magnitudes and frequencies
                magnitudes = np.abs(np.fft.fft(nd_array_points))
                frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)

                # Get index of positive frequencies
                half_index = len(frequencies) // 2

                # Add the arrays to the queue
                freq_queue.put((frequencies[:half_index], magnitudes[:half_index]))

                if len(frequencies) > 0:
                    # Find the indeces we consider
                    start_index = binary_search(frequencies, 10)
                    stop_index = binary_search(frequencies, 40)

                    # Calculate the avergae change of magnitudes from the given mean values
                    for i in range(start_index, stop_index):
                        if wet:
                            sum_of_values = abs(magnitudes[i] - WET_ELEC)
                        else:
                            sum_of_values = abs(magnitudes[i] - DRY_ELEC)

                    input_value = sum_of_values / (stop_index - start_index)

                # Send this data to the broker
                print(get_input(input_value))
                publish(client, get_input(input_value))

                # Remove the oldest point
                nd_array_points = nd_array_points[1:]


# Send data to the plot
def update_data(new_frequencies, new_magnitudes):
    source.data = dict(frequencies=new_frequencies, magnitudes=new_magnitudes)


# Receive data from the queue
async def update():
    if freq_queue.empty():
        return

    # Take the value from the queue and send the data
    frequencies, magnitudes = freq_queue.get()
    update_data(frequencies, magnitudes)


# BLE variables
address = ""
read_uuid = "2d30c082-f39f-4ce6-923f-3484ea480596"
write_uuid = "2d30c083-f39f-4ce6-923f-3484ea480596"

# Data variables
filter = DataFilter()
input_value = 0
num_fft_points = 50
freq_queue = queue.Queue()
nd_array_points = np.array([0.0])
start_index = 0
stop_index = 0
DRY_ELEC = 22
# TODO: TUNE
WET_ELEC = 33
# TODO: TUNE
wet = True

# MQTT variables
broker = "eduoracle.ugavel.com"
port = 1883
topic = "ganglion/data"
client_id = "rishab"
username = "giiuser"
password = "giipassword"


# Create plot
source = ColumnDataSource(dict(frequencies=[], magnitudes=[]))
p = figure(title="Live Data Stream", sizing_mode="stretch_both")
p.x_range = Range1d(start=0, end=100)
p.y_range = Range1d(start=0, end=1000)
p.line(source=source, x="frequencies", y="magnitudes", line_width=2, alpha=0.85)

# Create MQTT client
client = connect_mqtt()

# Update plot every millisecond
curdoc().add_periodic_callback(update, 1)
curdoc().add_root(p)

# Start the async connection in a separate thread
connect_thread = threading.Thread(target=run_async_connect, args=())
connect_thread.start()

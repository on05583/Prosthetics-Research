"""
You can run the following code using:
    $ bokeh serve --show new_ganglion_visualizer.py

    

"""

import asyncio
import queue
import threading

import aioconsole
import numpy as np
from bokeh.models import ColumnDataSource, DataRange1d, Range1d
from bokeh.plotting import curdoc, figure

from bleak import BleakClient, BleakScanner

source = ColumnDataSource(dict(frequencies=[], magnitudes=[]))

p = figure(title="Live Data Stream", sizing_mode="stretch_both")
p.x_range = Range1d(start=0, end=100)
p.y_range = Range1d(start=0, end=10000)
p.line(source=source, x="frequencies", y="magnitudes", line_width=2, alpha=0.85)


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
SCALE = 0.001869917138805
num_fft_points = 200
freq_queue = queue.Queue()
nd_array_points = np.array([0.0])


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


async def callback(sender, data):
    global nd_array_points
    global nd_array_times
    global overlap
    global tick

    # Add new data to the arrays
    if len(data) == 20 and data[19] != 0:
        full_int = int.from_bytes(data, "big")

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        extracted_bits *= SCALE

        if extracted_bits < 900 or extracted_bits > 1000:
            nd_array_points = np.insert(
                nd_array_points, nd_array_points.size - 1, [extracted_bits]
            )

            # if tick > overlap:
            if len(nd_array_points) > num_fft_points:
                magnitudes = np.abs(np.fft.fft(nd_array_points))
                frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)

                """
                positive_frequencies = frequencies[:half_index]
                positive_magnitudes = magnitudes[:half_index]
                sorted_indices = np.argsort(positive_frequencies)
                sorted_frequencies = positive_frequencies[sorted_indices]
                sorted_magnitudes = positive_magnitudes[sorted_indices]

                freq_queue.put((sorted_frequencies, sorted_magnitudes))
                """
                half_index = len(frequencies) // 2

                # considers only positive half
                freq_queue.put((frequencies[:half_index], magnitudes[:half_index]))

                nd_array_points = nd_array_points[1:]

        extracted_bits = (full_int >> (num_bits - 103)) & mask  # skip 84 + 19
        extracted_bits *= SCALE

        if extracted_bits < 900 or extracted_bits > 1000:
            nd_array_points = np.insert(
                nd_array_points, nd_array_points.size - 1, [extracted_bits]
            )

            # if tick > overlap:
            if len(nd_array_points) > num_fft_points:
                magnitudes = np.abs(np.fft.fft(nd_array_points))
                frequencies = np.fft.fftfreq(len(nd_array_points), 1 / 200)

                """
                
                positive_frequencies = frequencies[:half_index]
                positive_magnitudes = magnitudes[:half_index]
                sorted_indices = np.argsort(positive_frequencies)
                sorted_frequencies = positive_frequencies[sorted_indices]
                sorted_magnitudes = positive_magnitudes[sorted_indices]

                freq_queue.put((sorted_frequencies, sorted_magnitudes))
                """

                half_index = len(frequencies) // 2

                # considers only positive half
                freq_queue.put((frequencies[:half_index], magnitudes[:half_index]))

                nd_array_points = nd_array_points[1:]


def run_async_connect():
    asyncio.run(connect(address))


curdoc().add_root(p)

# Start the async connection in a separate thread
connect_thread = threading.Thread(target=run_async_connect, args=())
connect_thread.start()

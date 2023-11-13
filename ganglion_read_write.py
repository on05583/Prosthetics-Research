'''
import asyncio

from bleak import BleakClient


async def main(address):
    async with BleakClient(address) as client:
        # Connect to the device
        connected = await client.is_connected()
        if connected:
            print(f"Connected to {address}")

            # Discover services and characteristics
            services = await client.get_services()
            for service in services:
                print(f"Service: {service.uuid}")
                for char in service.characteristics:
                    print(f"    Characteristic: {char.uuid}, Handle: {char.handle}")
                    if "write" in char.properties:
                        # Print additional info if this characteristic supports writing
                        print("    (This characteristic supports writing)")
        else:
            print(f"Failed to connect to {address}")

# Replace with your device's address
address = "DA:23:8D:D7:85:97"

loop = asyncio.get_event_loop()
loop.run_until_complete(main(address))
'''
import asyncio
import sys
import threading

import aioconsole
import keyboard

from bleak import BleakClient, BLEDevice

address = "DA:23:8D:D7:85:97"
read_uuid = "2d30c082-f39f-4ce6-923f-3484ea480596"
write_uuid = "2d30c083-f39f-4ce6-923f-3484ea480596"
# bleak.backends.scanning.BaseBleakScanner

# tester = BLEDevice(address=address)

async def callback(sender, data):
    if (len(data) == 20 and data[19] != 0):
        full_int = int.from_bytes(data, 'big')

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        // TODO: fix noise filtering below

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        if extracted_bits * 0.001869917138805 < 800 or extracted_bits * 0.001869917138805 > 1000:
            print(extracted_bits * 0.001869917138805)

        extracted_bits = (full_int >> (num_bits - 103)) & mask # skip 84 + 19
        if extracted_bits * 0.001869917138805 < 800 or extracted_bits * 0.001869917138805 > 1000:
            print(extracted_bits * 0.001869917138805)
    # print(extracted_bits * 0.001869917138805)
    #    print(data[0])

    '''
    for i in range(len(data)):
        if data[i] == 0xC9:
            if i + 2 < len(data):
                combined_bytes = data[i+1] << 16 | data[i+2] << 8 | data[i+3]
                channel_1_value = combined_bytes & 0x7FFFF
                print(f"Channel 1 Impedance Value (as int): {channel_1_value}")
                '''

async def main(address):
    async with BleakClient(address) as client:
        await client.start_notify(read_uuid, callback)

        await client.write_gatt_char(write_uuid,  bytes("b", "ascii")) 

        while True:
            input_str = await aioconsole.ainput("Press 'q' to quit: \n")
            if input_str == 'q':

                await client.write_gatt_char(write_uuid,  bytes("s", "ascii")) 
                await client.disconnect()
                break


loop = asyncio.get_event_loop()
loop.run_until_complete(main(address))

# DA:23:8D:D7:85:97: Ganglion-2b18

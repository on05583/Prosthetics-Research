import asyncio
import sys
import threading

import aioconsole
import keyboard

from bleak import BleakClient, BleakScanner, BLEDevice

address = ""
read_uuid = "2d30c082-f39f-4ce6-923f-3484ea480596"
write_uuid = "2d30c083-f39f-4ce6-923f-3484ea480596"
SCALE = 0.001869917138805

async def callback(sender, data):
    if (len(data) == 20 and data[19] != 0):
        full_int = int.from_bytes(data, 'big')

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        # TODO: fix noise filtering below

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        extracted_bits *= SCALE
        if extracted_bits < 800 or extracted_bits > 1000:
            print(extracted_bits)

        extracted_bits = (full_int >> (num_bits - 103)) & mask # skip 84 + 19
        extracted_bits *= SCALE
        if extracted_bits < 800 or extracted_bits > 1000:
            print(extracted_bits)

async def main(address):
    
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

        await client.write_gatt_char(write_uuid,  bytes("b", "ascii")) 

        print("Data stream started.")

        while True:
            input_str = await aioconsole.ainput("Press 'q' to quit: \n")
            if input_str == 'q':
                print("Data stream ending...")
                await client.write_gatt_char(write_uuid,  bytes("s", "ascii")) 
                await client.disconnect()
                print("Client disconnected.")
                break


loop = asyncio.get_event_loop()
loop.run_until_complete(main(address))

# DA:23:8D:D7:85:97: Ganglion-2b18

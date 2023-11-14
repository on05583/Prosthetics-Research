import asyncio
import sys
import threading

import aioconsole
import keyboard

from bleak import BleakClient, BLEDevice

address = "DA:23:8D:D7:85:97"
read_uuid = "2d30c082-f39f-4ce6-923f-3484ea480596"
write_uuid = "2d30c083-f39f-4ce6-923f-3484ea480596"

async def callback(sender, data):
    if (len(data) == 20 and data[19] != 0):
        full_int = int.from_bytes(data, 'big')

        mask = (1 << 19) - 1  # 19 bits mask
        num_bits = len(data) * 8

        # TODO: fix noise filtering below

        extracted_bits = (full_int >> (num_bits - 27)) & mask
        if extracted_bits * 0.001869917138805 < 800 or extracted_bits * 0.001869917138805 > 1000:
            print(extracted_bits * 0.001869917138805)

        extracted_bits = (full_int >> (num_bits - 103)) & mask # skip 84 + 19
        if extracted_bits * 0.001869917138805 < 800 or extracted_bits * 0.001869917138805 > 1000:
            print(extracted_bits * 0.001869917138805)

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

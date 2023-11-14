import asyncio

from bleak import BleakScanner, discover


async def main():
    devices = await BleakScanner.discover()
    for d in devices:
        print(d.name)


asyncio.run(main())
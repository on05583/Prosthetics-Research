import asyncio

from bleak import discover


async def main():
    devices = await discover()
    for d in devices:
        print(d)

asyncio.run(main())
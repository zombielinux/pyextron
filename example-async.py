#! /usr/local/bin/python3
#
# Running:
#   ./example-async.py --help
#   ./example-async.py --tty /dev/tty.usbserial-A501SGSZ

import time
import asyncio
import argparse
import serial
import logging
import sys

from pyextron import async_get_amp_controller

####----------------------------------------
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
LOG.addHandler(handler)
####----------------------------------------

parser = argparse.ArgumentParser(description='Xantech RS232 client example (asynchronous)')
parser.add_argument('--host', help='/dev/tty to use (e.g. /dev/tty.usbserial-A501SGSZ)', required=True)
parser.add_argument('--model', default='xantech8', help=f"model (e.g. xantech8, monoprice6)" )
args = parser.parse_args()

async def main():
    zone = 1

    amp = await async_get_amp_controller(args.model, args.host, asyncio.get_event_loop())
#    await amp.all_off()

#    print(f"Xantech amp version = {await amp.sendCommand('version')}")

    for zone in range(1, 8):
        
#        await asyncio.sleep(0.5)
#        await amp.set_power(zone, True)
        
#        await asyncio.sleep(0.5)
#        await amp.set_source(zone, 1)
#        await amp.set_mute(zone, False)

        status = await amp.zone_status(zone)
        print(f"Zone {zone} status: {status}")

    # ensure all zones are turned off
#    for zone in range(1, 8):
#        await amp.set_power(zone, False)
#    await amp.all_off()

    exit()

    # Valid zones are 11-16 for main xantech amplifier
    # zone_status = await amp.zone_status(zone)

    # Set balance for zone #11
    #amp.set_balance(zone, 3)

    # Restore zone #11 to it's original state
    # amp.restore_zone(zone_status.dict)

    
asyncio.run(main())


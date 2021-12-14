#!/usr/local/bin/python3
#
# Running:
#   ./example-async.py --help
#   ./example.py --tty /dev/tty.usbserial-A501SGSZ

import argparse                                                                                             
import time
from random import randrange
from pyextron import get_amp_controller

parser = argparse.ArgumentParser(description='Extron Telnet client example')
parser.add_argument('--host', help='/dev/tty to use (e.g. /dev/tty.usbserial-A501SGSZ)', required=True)
parser.add_argument('--model', default='mav88', help=f"model (e.g. mav88, mav44)" )
args = parser.parse_args()

zone = 1
amp = get_amp_controller(args.model, args.host)

# save the status for all zones before modifying
zone_status = {}
for zone in range(1, 9):
    zone_status[zone] = amp.zone_status(zone) # save current status for all zones
    print(f"Zone {zone} status: {zone_status[zone]}")
#amp.all_off()
exit

for zone in range(1, 9):
#    amp.set_power(zone, True)
    amp.set_mute(zone, True)
    print(f"Zone {zone} status: {amp.zone_status(zone)}")

for zone in range(1, 9):
#    amp.set_power(zone, True)
    amp.set_mute(zone, False)
    print(f"Zone {zone} status: {amp.zone_status(zone)}")

for zone in range(1, 9):
#    amp.set_power(zone, True)
    amp.set_source(zone, randrange(1,9))
    print(f"Zone {zone} status: {amp.zone_status(zone)}")

for zone in range(1, 9):
#    amp.set_power(zone, True)
    amp.set_volume(zone, randrange(1,65))
    print(f"Zone {zone} status: {amp.zone_status(zone)}")

#source = 1
#amp.set_source(1, source)

# restore zones back to their original states
#for zone in range(1, 9):
#    amp.restore_zone( zone_status[zone ])





#def knight_rider(amp, number_of_times):
#    for _ in range (1, number_of_times + 1):
#        for zone in range(1, 9):
#            amp.set_power(zone, True)
#            amp.set_power(zone, False)

#        for zone in range(-7, -1):
#            amp.set_power(-1 * zone, True)
#            amp.set_power(-1 * zone, False)
# knight_rider(amp, 2)

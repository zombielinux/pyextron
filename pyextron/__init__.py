import asyncio
import logging
import re
import time
import serial
from telnetlib import Telnet

from functools import wraps
from threading import RLock

from .config import (DEVICE_CONFIG, PROTOCOL_CONFIG, RS232_RESPONSE_PATTERNS, get_with_log, pattern_to_dictionary)
from .protocol import get_telnet_protocol, CONF_RESPONSE_EOL, CONF_COMMAND_EOL, CONF_COMMAND_SEPARATOR
from .protocol import async_get_telnet_protocol, CONF_RESPONSE_EOL, CONF_COMMAND_EOL, CONF_COMMAND_SEPARATOR

LOG = logging.getLogger(__name__)

SUPPORTED_AMP_TYPES = DEVICE_CONFIG.keys()

#CONF_SERIAL_CONFIG='rs232'

def get_device_config(amp_type, key):
#    print(amp_type, key)
    return get_with_log(amp_type, DEVICE_CONFIG[amp_type], key)

def get_protocol_config(amp_type, key):
    protocol = get_device_config(amp_type, 'protocol')
#    print(protocol, key, PROTOCOL_CONFIG[protocol].get(key))
    return PROTOCOL_CONFIG[protocol].get(key)

# FIXME: populate based on dictionary, not positional
class ZoneStatus(object):
    def __init__(self, status: dict):
        self.dict = status
        self.retype_bools(['mute', 'paged', 'linked', 'pa'])
        self.retype_ints(['zone', 'volume', 'source'])

    def retype_bools(self, keys):
        for key in keys:
            if key in self.dict:
                self.dict[key] = ((self.dict[key] == '1') or (self.dict[key] == '01'))

    def retype_ints(self, keys):
        for key in keys:
            if key in self.dict:
                self.dict[key] = int(self.dict[key])

    @classmethod
    def from_string(cls, amp_type: str, string: str):
        if not string:
            return None

        protocol_type = get_device_config(amp_type, 'protocol')
        pattern = RS232_RESPONSE_PATTERNS[protocol_type].get('zone_status')
        match = re.search(pattern, string)
        if not match:
            LOG.debug("Could not pattern match zone status '%s' with '%s'", string, pattern)
            return None

        return ZoneStatus(match.groupdict())

class AmpControlBase(object):
    """
    AmpliferControlBase amplifier interface
    """

    def zone_status(self, zone: int):
        """
        Get the structure representing the status of the zone
        :param zone: zone 11..16, 21..26, 31..36
        :return: status of the zone or None
        """
        raise NotImplemented()

    def set_mute(self, zone: int, mute: bool):
        """
        Mute zone on or off
        :param zone: zone 11..16, 21..26, 31..36
        :param mute: True to mute, False to unmute
        """
        raise NotImplemented()

    def set_volume(self, zone: int, volume: int):
        """
        Set volume for zone
        :param zone: zone 11..16, 21..26, 31..36
        :param volume: integer from 0 to 38 inclusive
        """
        raise NotImplemented()

    def set_source(self, zone: int, source: int):
        """
        Set source for zone
        :param zone: zone 11..16, 21..26, 31..36
        :param source: integer from 0 to 6 inclusive
        """
        raise NotImplemented()

    def restore_zone(self, status: ZoneStatus):
        """
        Restores zone to its previous state
        :param status: zone state to restore
        """
        raise NotImplemented()

def _command(amp_type: str, format_code: str, args = {}):
    cmd_eol = get_protocol_config(amp_type, CONF_COMMAND_EOL)
    cmd_separator = get_protocol_config(amp_type, CONF_COMMAND_SEPARATOR)

    rs232_commands = get_protocol_config(amp_type, 'commands')
    command = rs232_commands.get(format_code) + cmd_separator + cmd_eol
    
    return command.format(**args).encode('ascii')

def _zone_status_cmd(amp_type, zone: int) -> bytes:
    assert zone in get_device_config(amp_type, 'zones')
    return _command(amp_type, 'zone_status', args = { 'zone': zone })

def _set_mute_cmd(amp_type, zone: int, mute: bool) -> bytes:
    assert zone in get_device_config(amp_type, 'zones')
    if mute:
        LOG.info(f"Muting {amp_type} zone {zone}")
        return _command(amp_type, 'mute_on', { 'zone': zone })
    else:
        LOG.info(f"Turning off mute {amp_type} zone {zone}")
        return _command(amp_type, 'mute_off', { 'zone': zone })
    
def _set_volume_cmd(amp_type, zone: int, volume: int) -> bytes:
    assert zone in get_device_config(amp_type, 'zones')
    max_volume = get_device_config(amp_type, 'max_volume')
    volume = int(max(0, min(volume, max_volume)))
    LOG.info(f"Setting volume {amp_type} zone {zone} to {volume}")
    return _command(amp_type, 'set_volume', args = { 'zone': zone, 'volume': volume })

def _set_source_cmd(amp_type, zone: int, source: int) -> bytes:
    assert zone in get_device_config(amp_type, 'zones')
    assert source in get_device_config(amp_type, 'sources')
    LOG.info(f"Setting source {amp_type} zone {zone} to {source}")
    return _command(amp_type, 'set_source', args = { 'zone': zone, 'source': source })

def get_amp_controller(amp_type: str, port_url):
    """
    Return synchronous version of amplifier control interface
    :param port_url:  DNS name or IP address of the matrix device , i.e. 'extron.fqdn.tld'
    :return: synchronous implementation of amplifier control interface
    """

    # sanity check the provided amplifier type
    if amp_type not in SUPPORTED_AMP_TYPES:
        LOG.error("Unsupported amplifier type '%s'", amp_type)
        return None

    lock = RLock()

    def synchronized(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper


    class AmpControlSync(AmpControlBase):
        def __init__(self, amp_type, port_url):
            self._amp_type = amp_type
            config = DEVICE_CONFIG[amp_type]

            # allow overriding the default serial port configuration, in case the user has changed
            # settings on their amplifier (e.g. increased the default baudrate)

            self._port = Telnet(port_url)
            self._port.open(port_url)
            login_string='\r\n'
            self._port.write(login_string.encode('ascii'))
            #Done 3 times to clear out initial messages in telnet connection
            self._port.read_until(login_string.encode('ascii'))
            self._port.read_until(login_string.encode('ascii'))
            self._port.read_until(login_string.encode('ascii'))
            
        def _send_request(self, request, skip=0):
            """
            :param request: request that is sent to the xantech
            :param skip: number of bytes to skip for end of transmission decoding
            :return: ascii string returned by xantech
            """
            # clear
#            self._port.reset_output_buffer()
#            self._port.reset_input_buffer()

#            print(f"Sending:  {request}")
            LOG.debug(f"Sending:  {request}")

            # send
#            print(request.decode('ascii'))
            self._port.write(request)
#            self._port.flush()

            response_eol = get_protocol_config(amp_type, CONF_RESPONSE_EOL).encode('ascii')
            len_eol = len(response_eol)

            # receive
            result = bytearray()
            while True:
                login_string='64\r\n'
#               c = self._port.read_until(login_string.encode('ascii'))
                c = self._port.read_very_eager()
#                print(c)
                if not c:
                    ret = bytes(result)
                    LOG.info(result)
                    LOG.info("Connection Timed Out")
#                   raise serial.SerialTimeoutException(
#                        'Connection timed out! Last received bytes {}'.format([hex(a) for a in result]))
                result += c
                if len(result) > skip and result[-len_eol:] == response_eol:
                    break
                    
#            print(result)                    
#            ret = bytes(result)
            ret = result
            LOG.debug('Received "%s"', ret)
#            print(f"Received: {ret}")
            return ret.decode('ascii')


        @synchronized
        def _zone_status_manual(self, zone: int):
            status = {}
            responses = get_protocol_config(self._amp_type, 'responses')

            # send all the commands necessary to restore the various status settings to the amp
            for command in get_protocol_config(amp_type, 'zone_status_commands'):
                pattern = responses[command]
                result = self._send_request( _zone_status_cmd(self._amp_type, command) )

                # parse the result into status dictionary
                LOG.info(f"Received zone stats {result}, matching to {pattern}")
                match = re.search(pattern, result)
                if match:
                    status.copy(match.groupdict())
                else:
                    LOG.warning("Could not pattern match zone status '%s' with '%s'", result, pattern)
                time.sleep(0.1) # pause 100 ms

            return status

        @synchronized
        def zone_status(self, zone: int):
            # if there is a list of zone status commands, execute that (some don't have a single command for status)
            #if get_protocol_config(amp_type, 'zone_status_commands'):
            #    return self._zone_status_manual(zone)

            response = self._send_request(_zone_status_cmd(self._amp_type, zone))
            status = ZoneStatus.from_string(self._amp_type, response)
            LOG.debug("Status: %s (string: %s)", status, response)
            if status:
                return status.dict
            else:
                return None

        @synchronized
        def set_mute(self, zone: int, mute: bool):
            self._send_request(_set_mute_cmd(self._amp_type, zone, mute))
            
        @synchronized
        def set_volume(self, zone: int, volume: int):
            self._send_request(_set_volume_cmd(self._amp_type, zone, volume))

        @synchronized
        def set_source(self, zone: int, source: int):
            self._send_request(_set_source_cmd(self._amp_type, zone, source))

        @synchronized
        def all_off(self):
            self._send_request( _command(amp_type, 'all_zones_off') )

        @synchronized
        def restore_zone(self, status: dict):
            zone = status['zone']
            amp_type = self._amp_type
            success = get_protocol_config(amp_type, 'restore_success')
            #LOG.debug(f"Restoring amp {amp_type} zone {zone} from {status}")

            # FIXME: fetch current status first and only call those that changed

            # send all the commands necessary to restore the various status settings to the amp
            restore_commands = get_protocol_config(amp_type, 'restore_zone')
            for command in restore_commands:
                result = self._send_request( _command(amp_type, command, status) )
                if result != success:
                    LOG.warning(f"Failed restoring zone {zone} command {command}")
                time.sleep(0.1) # pause 100 ms

    return AmpControlSync(amp_type, port_url)



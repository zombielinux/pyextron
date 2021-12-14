import logging

import time
import asyncio
import functools
from ratelimit import limits

LOG = logging.getLogger(__name__)

CONF_COMMAND_EOL = 'command_eol'
CONF_RESPONSE_EOL = 'response_eol'
CONF_COMMAND_SEPARATOR = 'command_separator'

CONF_THROTTLE_RATE = 'min_time_between_commands'
DEFAULT_TIMEOUT = 1.0

MINUTES = 300

def get_telnet_protocol(fqdn, config, protocol_config, loop):

	LOG.debug('Got into get_telnet_protocol')	
	# check if connected, and abort calling provided method if no connection before timeout

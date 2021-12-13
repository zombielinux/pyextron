# Python Telnet API for Extron Media Switchers

Library for Telnet serial communication to Extron Media Switchers.
See below for exactly which amplifier models are supported.

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
#[![PyPi](https://img.shields.io/pypi/v/pyxantech.svg)](https://pypi.python.org/pypi/pyxantech)
[![MIT license](http://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT)

## Usage
```python
from pyextron import get_amp_controller

zone = 2
amp = get_amp_controller('MAV88', 'hostname.fqdn.tld')

amp.set_source(zone, 3) # select source 3
```

See also [example.py](example.py) for a more complete example.

## Usage with asyncio

With the `asyncio` flavor, all methods of the controller objects are coroutines:

```python
import asyncio
from pyxantech import async_get_amp_controller

async def main(loop):
    amp = await async)get_amp_controller('MAV88', 'hostname.fqdn.tld', loop)
    zone_status = await amp.zone_status(2)
    if zone_status.power:
        await amp.set_power(zone_status.zone, False)

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
```

## Supported Multi-Zone Amps

| Manufacturer | Model(s)                 | Zones | Supported  |   Series   | Notes                                            |
| ------------ | ------------------------ | :---: | :--------: | :--------: | ------------------------------------------------ |
| Extron       | MAV88                    |   8   |    YES     |  MAV88     | audio and composite video only                   |

# ds18b20_wrapper.py

from machine import Pin
from drivers.ds18b20 import DS18B20  # adjust module name if needed
from config import DS18B20_DATA_PIN
# Singleton instance holder
_DS18B20_BUS = None


def _get_bus():
    """
    Lazily create and return the singleton DS18B20 bus instance.
    Adjust the pin number to your wiring.
    """
    global _DS18B20_BUS

    if _DS18B20_BUS is None:
        # Example: DS18B20 data line on GPIO15 with 4.7k pull-up
        _DS18B20_BUS = DS18B20(DS18B20_DATA_PIN)

    return _DS18B20_BUS


def get_data():
    """
    Read all DS18B20 sensors on the bus via the singleton instance.

    Returns:
        dict with:
        {
            "temps": {rom_hex: temp_c, ...},  # all sensors
            "count": int,                     # number of sensors
            "roms": [rom_hex, ...],           # list of ROM hex strings
        }
    """
    bus = _get_bus()

    temps = bus.read_temps()  # {rom_hex: temp_c}
    roms = list(temps.keys())

    return {
        "temps": temps,
        "count": len(roms),
        "roms": roms,
    }

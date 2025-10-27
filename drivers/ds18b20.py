# DS18B20 driver for MicroPython on RP2040 (Raspberry Pi Pico)
# Works with the built-in 'onewire' module. No other deps.
# Supports multiple sensors on the same bus, CRC check, resolution config,
# blocking and non-blocking conversions.

import time
from machine import Pin
import onewire

_ROM_CMD_SEARCH = 0xF0
_ROM_CMD_READ = 0x33
_ROM_CMD_MATCH = 0x55
_ROM_CMD_SKIP = 0xCC

_FUNC_CONVERT_T = 0x44
_FUNC_READ_SCRATCH = 0xBE
_FUNC_WRITE_SCRATCH = 0x4E
_FUNC_COPY_SCRATCH = 0x48
_FUNC_RECALL_E2 = 0xB8
_FUNC_READ_PWR = 0xB4

# Conversion times by resolution (ms), per DS18B20 datasheet
_CONV_MS = {9: 94, 10: 188, 11: 375, 12: 750}


class DS18B20:
    def __init__(self, pin):
        """pin: int or machine.Pin for the 1-Wire data line (needs 4.7k pull-up)."""
        self.ow = onewire.OneWire(pin if isinstance(pin, Pin) else Pin(pin))
        # Cache device ROMs
        self.roms = self.scan()

    # ---------- Bus and ROM handling ----------

    def scan(self):
        """Return list of ROM bytes objects for devices on the bus."""
        roms = self.ow.scan()
        # Filter only DS18x20 family (0x28 is DS18B20)
        self.roms = [r for r in roms if r[0] == 0x28]
        return self.roms

    def _select(self, rom=None):
        self.ow.reset()
        if rom:
            self.ow.select_rom(rom)
        else:
            self.ow.writebyte(_ROM_CMD_SKIP)

    # ---------- Scratchpad ops ----------

    def read_scratch(self, rom):
        """Return 9-byte scratchpad. Raises ValueError on CRC fail."""
        self._select(rom)
        self.ow.writebyte(_FUNC_READ_SCRATCH)
        data = bytearray(9)
        self.ow.readinto(data)
        if onewire.crc8(data[:8]) != data[8]:
            raise ValueError("DS18B20 CRC mismatch")
        return data

    def write_scratch(self, rom, th=75, tl=70, resolution=12, copy_to_eeprom=False):
        """Write alarm TH/TL and resolution (9/10/11/12). Optionally persist to EEPROM."""
        if resolution not in (9, 10, 11, 12):
            raise ValueError("resolution must be 9,10,11,12")
        # Config register: bits R1 R0 in bits 6 and 5
        rbits = {9: 0b00, 10: 0b01, 11: 0b10, 12: 0b11}[resolution]
        cfg = 0b00011111 | (rbits << 5)  # lower 5 bits must be 1 per datasheet
        self._select(rom)
        self.ow.writebyte(_FUNC_WRITE_SCRATCH)
        self.ow.writebyte(th & 0xFF)
        self.ow.writebyte(tl & 0xFF)
        self.ow.writebyte(cfg)
        if copy_to_eeprom:
            self._select(rom)
            self.ow.writebyte(_FUNC_COPY_SCRATCH)
            # Datasheet: up to 10ms for internal write
            time.sleep_ms(12)

    def read_power_supply(self, rom=None):
        """Return True if externally powered, False if parasite-powered."""
        self._select(rom)
        self.ow.writebyte(_FUNC_READ_PWR)
        return bool(self.ow.readbyte())

    # ---------- Temperature conversion ----------

    def start_conversion(self, rom=None):
        """Kick off temperature conversion. Return expected ms duration based on configured resolution.

        If rom=None, broadcasts to all devices.
        """
        # We assume default 12-bit unless we can read an individual device config.
        if rom is not None:
            try:
                cfg = self.read_scratch(rom)[4]
                res_bits = (cfg >> 5) & 0b11
                resolution = {0b00: 9, 0b01: 10, 0b10: 11, 0b11: 12}[res_bits]
            except Exception:
                resolution = 12
        else:
            resolution = 12
        self._select(rom)
        self.ow.writebyte(_FUNC_CONVERT_T)
        # If parasite power, you should provide a strong pull-up here. Good luck if you don't.
        return _CONV_MS[resolution]

    def _raw_to_celsius(self, scratch):
        # scratch[0]=LSB, scratch[1]=MSB, sign-extended 16-bit
        raw = (scratch[1] << 8) | scratch[0]
        if raw & 0x8000:
            raw = -((raw ^ 0xFFFF) + 1)
        # Adjust lower resolution by zeroing undefined LSBs based on config
        cfg = scratch[4]
        res_bits = (cfg >> 5) & 0b11
        # 12-bit: 0.0625 C per LSB (raw/16). For lower res, mask out fractional bits.
        mask = {0b00: ~0x7,  # 9-bit -> keep bits >= 3
                0b01: ~0x3,  # 10-bit
                0b10: ~0x1,  # 11-bit
                0b11: ~0x0}[res_bits]
        raw &= mask
        return raw / 16.0

    def read_temp(self, rom):
        """Blocking read: start conversion, wait, then return temperature in Celsius."""
        delay = self.start_conversion(rom)
        time.sleep_ms(delay)
        scratch = self.read_scratch(rom)
        return self._raw_to_celsius(scratch)

    def read_temps(self):
        """Blocking read of all discovered sensors. Returns dict {rom_hex: temp_c}."""
        if not self.roms:
            self.scan()
        # Start broadcast conversion and wait max time (12-bit worst case)
        delay = self.start_conversion(None)
        time.sleep_ms(delay)
        out = {}
        for rom in self.roms:
            scratch = self.read_scratch(rom)
            out[self.rom_hex(rom)] = self._raw_to_celsius(scratch)
        return out

    # ---------- Helpers ----------

    @staticmethod
    def rom_hex(rom):
        return rom.hex()

    @staticmethod
    def parse_rom(hexstr):
        return bytes.fromhex(hexstr)

from drivers.ds18b20 import DS18B20

sensor = DS18B20(pin=16)  # GP16, change as needed
print("Found:", [sensor.rom_hex(r) for r in sensor.roms])
print(sensor.read_temps())  # {'28ff1a2b3c4d5e6f': 23.875}


for rom in sensor.roms:
    sensor.write_scratch(rom, resolution=12, copy_to_eeprom=True)

from drivers.d709 import *

def print_voltage_loop(adc, vcc=5.0, adc_bits=16, interval_ms=300):
    """
    Helper function mirroring the Arduino "offset sketch".

    Use it while you short the BNC inner and outer contacts and adjust
    the OFFSET pot so PO ≈ vcc/2 (e.g. 2.5 V for a 5 V board).
    """
    if not isinstance(adc, ADC):
        raise TypeError("adc must be a machine.ADC instance")

    adc_max = (1 << int(adc_bits)) - 1

    while True:
        raw = adc.read_u16()
        voltage = raw * vcc / adc_max
        print(voltage)
        utime.sleep_ms(interval_ms)

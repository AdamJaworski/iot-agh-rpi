# ph_sensor_wrapper.py

from machine import ADC, Pin
from drivers.d709 import PHSensor

# Singleton instance holder
_PH_SENSOR_INSTANCE = None

from config import D709_ADC_PIN, D709_DO_PIN

def _get_sensor():
    """
    Lazily create and return the singleton PHSensor instance.
    Adjust pins / vcc / calibration to your hardware.
    """
    global _PH_SENSOR_INSTANCE

    if _PH_SENSOR_INSTANCE is None:
        # Example wiring on RP2040 / Pico:
        #   PO -> ADC0 (GPIO26)
        #   DO -> GPIO16 (optional)
        #   TO not used by default
        adc_ph = ADC(D709_ADC_PIN)          # PO analog output
        do_pin = Pin(D709_DO_PIN, Pin.IN)  # DO digital output (optional, remove if not used)

        _PH_SENSOR_INSTANCE = PHSensor(
            adc_ph,
            vcc=5.0,
            calibration=0.0,
            slope=-5.70,
            samples=10,
            sample_delay_ms=30,
            adc_bits=16,
            do_pin=do_pin,
            temp_adc=None,        # add ADC(...) here if you actually wire TO
        )

    return _PH_SENSOR_INSTANCE


def get_data():
    """
    Read processed data from the pH sensor singleton.

    Returns:
        dict:
        {
            "ph": float,
            "voltage_v": float,
            "limit_raw": 0|1|None,
            "ph_above_limit": bool|None,
            "temp_raw": int|None,
            "temp_voltage_v": float|None,
        }
    """
    sensor = _get_sensor()

    ph_value = sensor.read_ph()
    voltage = sensor.read_voltage()
    limit_raw = sensor.limit_raw()
    ph_above_limit = sensor.ph_above_limit()
    temp_raw = sensor.read_temp_raw()
    temp_voltage = sensor.read_temp_voltage()

    return {
        "ph": ph_value,
        "voltage_v": voltage,
        "limit_raw": limit_raw,
        "ph_above_limit": ph_above_limit,
        "temp_raw": temp_raw,
        "temp_voltage_v": temp_voltage,
    }

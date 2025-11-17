# hx711_wrapper.py

from drivers.hx711 import HX711  # adjust module name if needed
from config import HX711_DO_PIN, HX711_SCK_PIN

# Singleton HX711 instance
_HX711_INSTANCE = None

# Simple linear calibration: weight = (avg_value - OFFSET) / SCALE
# You are expected to change these two constants after calibration.
_CALIB_OFFSET = 0       # raw units at zero load
_CALIB_SCALE = 1.0      # raw units per "weight unit" (e.g. per gram or kg)


def _get_device():
    """
    Lazily create and return the singleton HX711 instance.
    Adjust pins to match your wiring.
    """
    global _HX711_INSTANCE

    if _HX711_INSTANCE is None:
        _HX711_INSTANCE = HX711(d_out=HX711_DO_PIN, pd_sck=HX711_SCK_PIN)

    return _HX711_INSTANCE


def _read_average(samples=10):
    """
    Take multiple readings and return the average to reduce noise.
    """
    hx = _get_device()
    total = 0
    for _ in range(samples):
        total += hx.read()  # signed integer
    return total / samples


def get_data():
    """
    Read processed data from the HX711 singleton.

    Returns:
        dict:
        {
            "raw_avg": float,          # averaged raw ADC value (signed)
            "value_offset": float,     # raw_avg - CALIB_OFFSET
            "weight": float or None,   # (value_offset / CALIB_SCALE) or None if SCALE == 0
            "offset": int|float,       # calibration offset used
            "scale": float,            # calibration scale used
            "unit": str,               # label for weight units (you can change it)
        }
    """
    avg = _read_average(samples=10)
    value_offset = avg - _CALIB_OFFSET

    if _CALIB_SCALE != 0:
        weight = value_offset / _CALIB_SCALE
    else:
        weight = None

    return {
        "raw_avg": avg,
        "value_offset": value_offset,
        "weight": weight,
        "offset": _CALIB_OFFSET,
        "scale": _CALIB_SCALE,
        "unit": "unknown",  # change to "g", "kg", etc. after calibration
    }

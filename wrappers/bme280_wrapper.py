# bme280_wrapper.py

from machine import I2C, Pin
from drivers.bme280 import BME280  # adjust module name if needed

from config import BME280_SDA_PIN, BME280_SCL_PIN

# Singleton instance holder
_BME280_INSTANCE = None


def _get_sensor():
    """
    Lazily create and return the singleton BME280 instance.
    Adjust I2C bus / pins / freq to your hardware.
    """
    global _BME280_INSTANCE

    if _BME280_INSTANCE is None:
        # RP2040 / Pico typical I2C0 pins; change if you wired differently.
        i2c = I2C(0, sda=Pin(BME280_SDA_PIN), scl=Pin(BME280_SCL_PIN), freq=100_000)
        _BME280_INSTANCE = BME280(i2c=i2c)

    return _BME280_INSTANCE


def get_data():
    """
    Read processed data from the BME280 singleton and return it.

    Returns:
        dict with numeric values:
        {
            "temperature_c": float,
            "pressure_pa": float,
            "pressure_hpa": float,
            "humidity_percent": float,
            "altitude_m": float,
            "dew_point_c": float,
        }
    """
    sensor = _get_sensor()
    t, p, h = sensor.read_compensated_data()

    return {
        "temperature_c": t,
        "pressure_pa": p,
        "pressure_hpa": p / 100.0,
        "humidity_percent": h,
        "altitude_m": sensor.altitude,
        "dew_point_c": sensor.dew_point,
    }

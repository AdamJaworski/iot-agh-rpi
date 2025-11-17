# main.py
#
# Periodic telemetry sender for RP2040 (MicroPython).
# Uses:
#   - MQTTNumberDriver (mqtt_driver.py)
#   - bme280_wrapper.get_data()
#   - ph_sensor_wrapper.get_data()
#   - ds18b20_wrapper.get_data()
#   - hx711_wrapper.get_data()
#
# It:
#   - Tries to (re)connect to Wi-Fi + MQTT when needed
#   - Reads all devices, but isolates failures per device
#   - Packs data as JSON, sends via MQTTNumberDriver.sent(list[int])
#   - Never raises out of the main loop unless you hard-kill it

import time
import ujson

from drivers.mqtt import MQTTNumberDriver

from wrappers.bme280_wrapper import get_data as get_bme280_data
from wrappers.d709_wrapper import get_data as get_ph_data
from wrappers.ds18b20_wrapper import get_data as get_ds18b20_data
from wrappers.hx711_wrapper import get_data as get_hx711_data

from config import *


# ------------- MQTT SETUP -------------

mqtt_client = MQTTNumberDriver(
    WIFI_SSID,
    WIFI_PASSWORD,
    MQTT_HOST,
    port=MQTT_PORT,
    client_id=MQTT_CLIENT_ID,
    topic=MQTT_TOPIC,
)

_mqtt_connected = False


def _ensure_mqtt_connected():
    """
    Try to connect Wi-Fi + MQTT broker if not currently connected.
    This will raise on failure; caller decides whether to swallow it.
    """
    global _mqtt_connected

    if _mqtt_connected:
        return

    # MQTTNumberDriver.connect() already handles Wi-Fi connect + MQTT connect
    mqtt_client.connect()
    _mqtt_connected = True


# ------------- SENSOR READING -------------

def _safe_call(fn, name):
    """
    Call wrapper function fn() and return its result.
    On exception, return an error dict instead of raising.
    """
    try:
        return fn()
    except Exception as e:
        # Keep error short to avoid bloated payloads
        return {"error": "{}: {}".format(name, str(e)[:80])}


def build_payload():
    """
    Build the full telemetry payload as a dict.
    Reads all sensors but does not raise.
    """
    now = time.time()

    payload = {
        "ts": now,  # seconds since epoch (or since boot if RTC not set)
        "bme280": _safe_call(get_bme280_data, "bme280"),
        "ph": _safe_call(get_ph_data, "ph"),
        "ds18b20": _safe_call(get_ds18b20_data, "ds18b20"),
        "hx711": _safe_call(get_hx711_data, "hx711"),
    }

    return payload


def send_payload():
    """
    Build payload and push via MQTT. Handles most errors internally.
    """
    global _mqtt_connected

    # 1. Ensure connection
    try:
        _ensure_mqtt_connected()
    except Exception as e:
        # Connection failure: mark as disconnected and bail out for this cycle
        _mqtt_connected = False
        # Nothing else to do this round
        return

    # 2. Build payload
    payload_dict = build_payload()

    try:
        payload_bytes = ujson.dumps(payload_dict).encode("utf-8")
    except Exception as e:
        # If serialization somehow fails, there isn't much to do.
        # Drop this cycle.
        return

    # 3. Convert bytes -> list[int] for MQTTNumberDriver.sent()
    payload_list = [b for b in payload_bytes]

    # 4. Try to send
    try:
        mqtt_client.sent(payload_list)
    except Exception as e:
        # On any send error, force reconnect next time
        _mqtt_connected = False


# ------------- MAIN LOOP -------------

def main():
    last_send = 0

    while True:
        now = time.time()

        # basic "clocked" loop: run every SEND_INTERVAL_SECONDS
        if now - last_send >= SEND_INTERVAL_SECONDS:
            last_send = now
            try:
                send_payload()
            except Exception:
                # Absolutely do not die. If something slipped through, ignore it
                # and let the next iteration try again.
                pass

        # small sleep to avoid busy-waiting
        time.sleep(0.1)


# Auto-run if this is main script
if __name__ == "__main__":
    main()

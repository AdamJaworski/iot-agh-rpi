# mqtt_driver.py
import network
import time
from umqtt.simple import MQTTClient


class MQTTNumberDriver:
    def __init__(self, ssid, password, host, port=1883,
                 client_id="rp2040-client", topic=b"numbers"):
        self.ssid = ssid
        self.password = password
        self.host = host
        self.port = port
        self.client_id = client_id
        # topic must be bytes for MQTTClient
        self.topic = topic if isinstance(topic, bytes) else topic.encode()

        self._wlan = None
        self._client = None

    # ---------- Wi-Fi handling ----------

    def _connect_wifi(self, timeout_s=15):
        if self._wlan is None:
            self._wlan = network.WLAN(network.STA_IF)
            self._wlan.active(True)

        if self._wlan.isconnected():
            return

        self._wlan.connect(self.ssid, self.password)

        t0 = time.time()
        while not self._wlan.isconnected():
            if time.time() - t0 > timeout_s:
                raise RuntimeError("Wi-Fi connection timeout")
            time.sleep(0.2)

    # ---------- MQTT handling ----------

    def connect(self):
        """
        Connect to Wi-Fi and then to MQTT broker at host:port.
        """
        self._connect_wifi()

        self._client = MQTTClient(self.client_id,
                                  self.host,
                                  port=self.port)
        self._client.connect()

    def disconnect(self):
        """
        Disconnect from MQTT broker.
        """
        if self._client is not None:
            try:
                self._client.disconnect()
            except OSError:
                pass
            self._client = None

    # ---------- Public API ----------

    def sent(self, data):
        """
        Send list/tuple of numbers as raw bytes payload to MQTT topic.

        data: list/tuple of ints in range 0–255
        """
        if self._client is None:
            raise RuntimeError("MQTT client is not connected. Call connect() first.")

        if not isinstance(data, (list, tuple)):
            raise TypeError("data must be a list or tuple of ints")

        # validate and convert
        byte_list = []
        for v in data:
            if not isinstance(v, int):
                raise TypeError("all elements must be ints")
            if not 0 <= v <= 255:
                raise ValueError("all ints must be in range 0–255")
            byte_list.append(v)

        payload = bytes(byte_list)
        self._client.publish(self.topic, payload)

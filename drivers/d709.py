# ph_sensor.py
#
# MicroPython driver for the analog pH probe module described in:
# "How to use a PH probe and sensor" (offset pot + limit pot + PO/DO/TO pins).
#
# Usage example (RP2040 / Pico):
#
#   from machine import ADC, Pin
#   from ph_sensor import PHSensor
#
#   adc_ph = ADC(26)              # PO connected via proper level shifting
#   ph = PHSensor(adc_ph, vcc=5.0, calibration=0.0)
#
#   while True:
#       print("pH:", ph.read_ph())
#       utime.sleep(1)
#
# Calibrate once with buffer solution:
#
#   # put probe in buffer 6.86, wait ~2 min
#   ph.calibrate_to(6.86)
#
# After that, ph.read_ph() will be calibrated around that point.

from machine import ADC, Pin
import utime


class PHSensor:
    def __init__(
        self,
        adc,
        *,
        vcc=5.0,
        calibration=0.0,
        slope=-5.70,
        samples=10,
        sample_delay_ms=30,
        adc_bits=16,
        do_pin=None,
        temp_adc=None,
    ):
        """
        adc          : machine.ADC instance connected to PO (analog pH output)
        vcc          : supply voltage of the pH board (typically 5.0 V)
        calibration  : intercept term used in ph = slope * V + calibration
        slope        : default -5.70 from the original Arduino sketch
        samples      : number of ADC samples per reading
        sample_delay_ms : delay between samples
        adc_bits     : logical resolution of read_u16() (16 for MicroPython)
        do_pin       : optional digital pin number or Pin instance for DO
        temp_adc     : optional machine.ADC instance for TO (temperature out)
        """

        if not isinstance(adc, ADC):
            raise TypeError("adc must be a machine.ADC instance")

        self.adc = adc
        self.vcc = float(vcc)
        self.calibration = float(calibration)
        self.slope = float(slope)
        self.samples = int(samples)
        self.sample_delay_ms = int(sample_delay_ms)
        self.adc_max = (1 << int(adc_bits)) - 1

        # Optional digital limit pin (DO)
        if do_pin is None:
            self.do = None
        elif isinstance(do_pin, Pin):
            self.do = do_pin
        else:
            self.do = Pin(do_pin, Pin.IN)

        # Optional temperature ADC (TO)
        if temp_adc is not None and not isinstance(temp_adc, ADC):
            raise TypeError("temp_adc must be a machine.ADC instance or None")
        self.temp_adc = temp_adc

    # ---------- internal helpers ----------

    def _read_adc_filtered(self):
        """
        Read self.samples times, sort values, drop 2 lowest and 2 highest
        (like the Arduino example) and return the average of the middle ones.
        """
        buf = []
        for _ in range(self.samples):
            buf.append(self.adc.read_u16())
            utime.sleep_ms(self.sample_delay_ms)

        buf.sort()

        if self.samples >= 6:
            # drop 2 lowest and 2 highest, as in the PDF sketch
            trimmed = buf[2:-2]
        else:
            trimmed = buf

        return sum(trimmed) / len(trimmed)

    # ---------- main API ----------

    def read_voltage(self):
        """
        Return analog voltage at PO in volts, using board supply vcc.
        """
        avg_raw = self._read_adc_filtered()
        return avg_raw * self.vcc / self.adc_max

    def read_ph(self):
        """
        Return pH value using: pH = slope * V + calibration.
        """
        v = self.read_voltage()
        return self.slope * v + self.calibration

    def calibrate_to(self, buffer_ph):
        """
        One-point calibration.

        Put probe in a known buffer solution (e.g. 6.86),
        wait until stable, then call calibrate_to(buffer_ph).

        It adjusts 'calibration' so that read_ph() == buffer_ph
        at the current conditions and returns the new calibration.
        """
        measured = self.read_ph()
        self.calibration += (buffer_ph - measured)
        return self.calibration

    # ---------- limit output (DO) ----------

    def has_limit_pin(self):
        return self.do is not None

    def limit_raw(self):
        """
        Return raw digital state of DO (1 or 0), or None if not wired.

        Per the doc:
          - DO is normally ~3.3 V (logic 1).
          - When pH exceeds the set limit, DO goes to ~0 V (logic 0) and LED turns on.
        """
        if self.do is None:
            return None
        return self.do.value()

    def ph_above_limit(self):
        """
        True if DO indicates pH is higher than the limit set by the limit pot.

        Based on the board description: DO goes LOW when pH > threshold.
        """
        if self.do is None:
            return None
        return self.do.value() == 0

    # ---------- optional temperature channel (TO) ----------

    def read_temp_raw(self):
        """
        Return raw ADC value from TO, or None if temp_adc not configured.
        You can convert this to °C based on the temperature sensor used
        on your specific board (not defined in the original document).
        """
        if self.temp_adc is None:
            return None
        return self.temp_adc.read_u16()

    def read_temp_voltage(self):
        """
        Return voltage at TO in volts, or None if temp_adc not configured.
        """
        if self.temp_adc is None:
            return None
        raw = self.temp_adc.read_u16()
        return raw * self.vcc / self.adc_max



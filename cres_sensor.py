from .cres_req import CresRequest
import logging

_LOGGER = logging.getLogger(__name__)


class CresSensors:
    def __init__(self, reqAddr):
        self.req = CresRequest(reqAddr)
        self.sensors = []
        self.sensor_data = {}  # Store sensor data in a dictionary

    async def get_sensors(self):
        """Fetch the list of sensors."""
        sensor_data = await self.req._get_request("extension:get-all()")
        # Ensure sensor_ids is a clean list of sensor strings
        sensor_ids = sensor_data.strip("[]").replace('"', "").split(",")  # Split IDs

        self.sensors = sensor_ids if isinstance(sensor_ids, list) else [sensor_ids]

        return self.sensors

    async def update_sensor_data(self):
        """Update sensor data by fetching all relevant data in one pass."""
        self.sensor_data = {}  # Clear previous data

        for sensor_id in self.sensors:
            try:
                sensor_state = await self.fetch_all_sensor_data(sensor_id)
                self.sensor_data[sensor_id] = sensor_state

            except Exception as e:
                _LOGGER.error(
                    f"Fehler beim Abrufen oder Verarbeiten der Sensordaten für Sensor {sensor_id}: {e}"
                )

    async def fetch_all_sensor_data(self, sensor_id):
        """Fetch all data for a specific sensor in a single API request."""
        sensor_state = {}
        try:
            # Combine multiple requests into one to reduce the number of API calls
            response = await self.req._get_request(
                f"extension:{sensor_id}:humidity;extension:{sensor_id}:temperature;extension:{sensor_id}:vpd"
                + (f";extension:{sensor_id}:co2-concentration" if "co2" in sensor_id.lower() else "")
            )

            # Split the response and assign values
            values = response.split(";")
            humidity, temperature, vpd = values[0], values[1], values[2]

            if humidity:
                sensor_state["humidity"] = float(humidity)
            if temperature:
                sensor_state["temperature"] = float(temperature)
            if vpd:
                sensor_state["vpd"] = float(vpd)

            if "co2" in sensor_id.lower() and len(values) > 3:
                co2 = values[3]
                if co2:
                    sensor_state["co2"] = float(co2)

        except Exception as e:
            _LOGGER.error(
                f"Fehler beim Abrufen oder Verarbeiten der Sensordaten für Sensor {sensor_id}: {e}"
            )

        return sensor_state

    def __str__(self):
        """Provide a string representation of current sensor data."""
        return f"Sensors Status:\nSensor Data: {self.sensor_data}\n"

from custom_components.crescontrol.cres_req import CresRequest
import logging

_LOGGER = logging.getLogger(__name__)


class CresSensors:
    def __init__(self, reqAddr, session=None):
        self.req = CresRequest(reqAddr, session)
        self.sensors = []
        self.sensor_data = {} 

    async def get_sensors(self):
        """Fetch the list of sensors."""
        sensor_data = await self.req._get_request("extension:get-all()")

        sensor_ids = sensor_data.strip("[]").replace('"', "").split(",") 

        # Strip whitespace and filter out empty strings
        self.sensors = [sid.strip() for sid in sensor_ids if sid.strip()]

        return self.sensors

    async def update_sensor_data(self):
        """Update sensor data by fetching all relevant data in one pass.
        
        Failed sensors keep their previous data to avoid all entities going unavailable.
        """
        for sensor_id in self.sensors:
            try:
                sensor_state = await self.fetch_all_sensor_data(sensor_id)
                if sensor_state:
                    self.sensor_data[sensor_id] = sensor_state
                else:
                    _LOGGER.warning(
                        f"Sensor {sensor_id} returned no data, keeping previous values"
                    )

            except Exception as e:
                _LOGGER.warning(
                    f"Sensor {sensor_id} temporarily unavailable, keeping previous values: {e}"
                )

    async def fetch_all_sensor_data(self, sensor_id):
        """Fetch all data for a specific sensor in a single batched request.
        
        Returns empty dict on failure to allow graceful degradation.
        """
        sensor_state = {}
        try:
            # Build batched request for all parameters at once
            params = ["humidity", "temperature", "vpd"]
            if "co2" in sensor_id.lower():
                params.append("co2-concentration")

            request_parts = [f"extension:{sensor_id}:{param}" for param in params]
            request_string = ";".join(request_parts)

            response = await self.req._get_request(request_string)

            if response and response.strip():
                values = response.strip().split(";")
                for i, param in enumerate(params):
                    if i < len(values) and values[i].strip():
                        try:
                            sensor_state[param.replace("-concentration", "")] = float(values[i].strip())
                        except (ValueError, TypeError):
                            _LOGGER.debug(f"Could not parse {param} for sensor {sensor_id}: '{values[i]}'")

        except Exception as e:
            _LOGGER.warning(
                f"Sensor {sensor_id} fetch failed, returning empty state: {e}"
            )

        return sensor_state

    def __str__(self):
        """Provide a string representation of current sensor data."""
        return f"Sensors Status:\nSensor Data: {self.sensor_data}\n"

"""Constants for the Cre.Sience HA Integration"""

VERSION = "1.0.0"
DOMAIN = "crescontrol"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30

# Configuration keys
CONF_HOST = "host"
CONF_OUTPUTS = "outputs"
CONF_SWITCHES = "switches"
CONF_INPUTS = "inputs"
CONF_FAN = "fan"

# Entity types for outputs and switches
ENTITY_TYPE_NONE = "none"
ENTITY_TYPE_LIGHT = "light"
ENTITY_TYPE_SWITCH = "switch"
ENTITY_TYPE_FAN = "fan"
ENTITY_TYPE_NUMBER = "number"

# Entity type options for UI
ENTITY_TYPE_OPTIONS = {
    ENTITY_TYPE_NONE: "❌ Disabled",
    ENTITY_TYPE_LIGHT: "💡 Light (dimmable)",
    ENTITY_TYPE_SWITCH: "🔌 Switch (on/off)",
    ENTITY_TYPE_FAN: "🌀 Fan (speed control)",
    ENTITY_TYPE_NUMBER: "🔢 Number (manual)",
}

# Default hardware channels
OUTPUT_CHANNELS = ["a", "b", "c", "d", "e", "f"]
SWITCH_CHANNELS = ["12v", "24v-a", "24v-b"]
INPUT_CHANNELS = ["a", "b"]

# PWM capable outputs
PWM_OUTPUTS = ["a", "b"]

# Input sensor types
SENSOR_TYPE_NONE = "none"
SENSOR_TYPE_VOLTAGE = "voltage"
SENSOR_TYPE_TEMPERATURE = "temperature"
SENSOR_TYPE_HUMIDITY = "humidity"
SENSOR_TYPE_PRESSURE = "pressure"
SENSOR_TYPE_CO2 = "co2"
SENSOR_TYPE_EC = "ec"
SENSOR_TYPE_PH = "ph"

INPUT_SENSOR_OPTIONS = {
    SENSOR_TYPE_NONE: "❌ Disabled",
    SENSOR_TYPE_VOLTAGE: "⚡ Voltage (V)",
    SENSOR_TYPE_TEMPERATURE: "🌡️ Temperature (°C)",
    SENSOR_TYPE_HUMIDITY: "💧 Humidity (%)",
    SENSOR_TYPE_PRESSURE: "📊 Pressure (hPa)",
    SENSOR_TYPE_CO2: "🌬️ CO2 (ppm)",
    SENSOR_TYPE_EC: "🧪 EC (mS/cm)",
    SENSOR_TYPE_PH: "🔬 pH",
}

# Default names for channels
DEFAULT_OUTPUT_NAMES = {
    "a": "OutputA",
    "b": "OutputB",
    "c": "OutputC",
    "d": "OutputD",
    "e": "OutputE",
    "f": "OutputF",
}

DEFAULT_SWITCH_NAMES = {
    "12v": "Switch12V",
    "24v-a": "Switch24VA",
    "24v-b": "Switch24VB",
}

DEFAULT_INPUT_NAMES = {
    "a": "InputA",
    "b": "InputB",
}


def sanitize_sensor_id(sensor_id: str) -> str:
    """Transform sensor IDs from 'climate-14234' to 'sensor14234'.
    
    Extracts only digits from the sensor ID and prefixes with 'sensor'.
    Falls back to the original ID if no digits are found.
    """
    digits = "".join(char for char in sensor_id if char.isdigit())
    if digits:
        return f"sensor{digits}"
    return sensor_id

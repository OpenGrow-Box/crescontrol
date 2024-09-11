from .cres_req import CresRequest
import logging

_LOGGER = logging.getLogger(__name__)

class CresOutputs:
    def __init__(
        self,
        reqAddr,
        outputList=["a", "b", "c", "d", "e", "f"],
        pwm_devices=["a", "b"],
        
    ):
        self.req = CresRequest(reqAddr)
        self.outputList = outputList
        self.devices = outputList
        self.outputs_data = {}
        self.isPWM = pwm_devices
        for output_name in self.devices:
            self.outputs_data[output_name] = {
                "enabled": False,
                "voltage": 0,
                "calibOffset": 0,
                "calibFactor": 0,
                "pwmEnabled": False if output_name in self.isPWM else None,
                "pwmFrequency": 0 if output_name in self.isPWM else None,
                "threshold": 0,
            }

# Multi Deviec Request 
    async def getAllOutputsData(self):
        """Fetch all output data with a single request for all outputs."""
        # Kombinierter Request, um alle Output-Daten auf einmal abzurufen
        request_parts = []
        for output_name in self.outputList:
            request_parts.append(
                f"out-{output_name}:enabled;out-{output_name}:voltage;out-{output_name}:calib-offset;out-{output_name}:calib-factor;out-{output_name}:threshold"
            )
            if output_name in self.isPWM:
                request_parts.append(
                    f"out-{output_name}:pwm-enabled;out-{output_name}:pwm-frequency"
                )

        # Erzeuge den kombinierten Request-String
        request_string = ";".join(request_parts)

        # Sende den kombinierten Request
        response = await self.req._get_request(request_string)

        # Überprüfen, ob die Antwort gültig ist
        if response is None or "error" in response.lower():
            raise ValueError(f"Error fetching output data: {response}")

        # Aufteilen der Antworten
        try:
            split_response = response.split(";")
            index = 0
            for output_name in self.outputList:
                self.outputs_data[output_name]["enabled"] = str(split_response[index]).strip() == "1"
                self.outputs_data[output_name]["voltage"] = float(split_response[index + 1])
                self.outputs_data[output_name]["calibOffset"] = float(split_response[index + 2])
                self.outputs_data[output_name]["calibFactor"] = float(split_response[index + 3])
                self.outputs_data[output_name]["threshold"] = float(split_response[index + 4])
                index += 5
                
                # Falls PWM vorhanden ist, die zusätzlichen Werte verarbeiten
                if output_name in self.isPWM:
                    self.outputs_data[output_name]["pwmEnabled"] = str(split_response[index]).strip() == "1"
                    self.outputs_data[output_name]["pwmFrequency"] = float(split_response[index + 1])
                    index += 2

        except ValueError as e:
            # Fehler beim Parsen der Antwort
            raise ValueError(f"Error parsing output data: {response}") from e

        return self.outputs_data

## Single Device Request

    async def get_output_enabled(self, output_name):
        self.outputs_data[output_name]["enabled"] = (
            str(await self.req._get_request(f"out-{output_name}:enabled")).strip() == "1"
        )
        return self.outputs_data[output_name]["enabled"]

    async def set_output_enabled(self, output_name, enabled):
        """Sets the enabled state of the output."""
        value_str = "true" if enabled else "false"
        await self.req._get_request(f"out-{output_name}:enabled={value_str}")
        self.outputs_data[output_name]["enabled"] = enabled
        return enabled

    async def get_output_voltage(self, output_name):
        self.outputs_data[output_name]["voltage"] = await self.req._get_request(
            f"out-{output_name}:voltage"
        )
        return self.outputs_data[output_name]["voltage"]

    async def set_output_voltage(self, output_name, voltage_value):
        await self.req._get_request(f"out-{output_name}:voltage={voltage_value}")
        self.outputs_data[output_name]["voltage"] = voltage_value

    async def get_output_calib_offset(self, output_name):
        self.outputs_data[output_name]["calibOffset"] = await self.req._get_request(
            f"out-{output_name}:calib-offset"
        )
        return self.outputs_data[output_name]["calibOffset"]

    async def set_output_calib_offset(self, output_name, calib_offset_value):
        await self.req._get_request(
            f"out-{output_name}:calib-offset={calib_offset_value}"
        )
        self.outputs_data[output_name]["calibOffset"] = calib_offset_value

    async def get_output_calib_factor(self, output_name):
        self.outputs_data[output_name]["calibFactor"] = await self.req._get_request(
            f"out-{output_name}:calib-factor"
        )
        return self.outputs_data[output_name]["calibFactor"]

    async def set_output_calib_factor(self, output_name, calib_factor_value):
        await self.req._get_request(
            f"out-{output_name}:calib-factor={calib_factor_value}"
        )
        self.outputs_data[output_name]["calibFactor"] = calib_factor_value

    async def get_output_pwm_enabled(self, output_name):
        if output_name in self.isPWM:
            response = await self.req._get_request(f"out-{output_name}:pwm-enabled")
            self.outputs_data[output_name]["pwmEnabled"] = str(response).strip() == "1"
            return self.outputs_data[output_name]["pwmEnabled"]

    async def set_output_pwm_enabled(self, output_name, pwm_enabled_value):
        if output_name in self.isPWM:
            value_str = "true" if pwm_enabled_value else "false"
            await self.req._get_request(f"out-{output_name}:pwm-enabled={value_str}")
            self.outputs_data[output_name]["pwmEnabled"] = pwm_enabled_value

    async def get_output_pwm_frequency(self, output_name):
        if output_name in self.isPWM:
            self.outputs_data[output_name][
                "pwmFrequency"
            ] = await self.req._get_request(f"out-{output_name}:pwm-frequency")
            return self.outputs_data[output_name]["pwmFrequency"]

    async def set_output_pwm_frequency(self, output_name, pwm_frequency_value):
        if output_name in self.isPWM:
            await self.req._get_request(
                f"out-{output_name}:pwm-frequency={pwm_frequency_value}"
            )
            self.outputs_data[output_name]["pwmFrequency"] = pwm_frequency_value

    async def get_output_threshold(self, output_name):
        self.outputs_data[output_name]["threshold"] = await self.req._get_request(
            f"out-{output_name}:threshold"
        )
        return self.outputs_data[output_name]["threshold"]
    
    async def set_output_threshold(self, output_name,threshold):
        self.outputs_data[output_name]["threshold"] = await self.req._get_request(
            f"out-{output_name}:threshold={threshold}"
        )
        return self.outputs_data[output_name]["threshold"]

    async def update_output(self,output_name):
        await self.get_output_enabled(output_name)
        await self.get_output_voltage(output_name)
        await self.get_output_calib_offset(output_name)
        await self.get_output_calib_factor(output_name)
        await self.get_output_threshold(output_name)
        if output_name in self.isPWM:
            await self.get_output_pwm_enabled(output_name)
            await self.get_output_pwm_frequency(output_name)
            
        return self.outputs_data

    async def update_outputs(self):
        for output_name in self.outputList:
            await self.get_output_enabled(output_name)
            await self.get_output_voltage(output_name)
            await self.get_output_calib_offset(output_name)
            await self.get_output_calib_factor(output_name)
            await self.get_output_threshold(output_name)
            if output_name in self.isPWM:
                await self.get_output_pwm_enabled(output_name)
                await self.get_output_pwm_frequency(output_name)


        return self.outputs_data

from custom_components.crescontrol.cres_req import CresRequest
import logging

_LOGGER = logging.getLogger(__name__)

class CresSwitches:
    def __init__(self, reqAddr, switchList=None, session=None):
        self.req = CresRequest(reqAddr, session)
        self.switchList = switchList if switchList is not None else ["12v", "24v-a", "24v-b"]
        self.devices = self.switchList
        self.switch_data = {}
        
        for switch_name in self.devices:
            self.switch_data[switch_name] = {
                "enabled": False,
                "pwm-enabled": False, 
                "duty-cycle": 0.0,
                "pwm-frequency": 0.0,
            }

    ## Multi Device Request
    async def getAllSwitchData(self):
        """Fetch all switch data with a single request."""
        if not self.switchList:
            return self.switch_data

        request_parts = []
        for switch_name in self.switchList:
            request_parts.append(
                f"switch-{switch_name}:enabled;switch-{switch_name}:pwm-enabled;switch-{switch_name}:duty-cycle;switch-{switch_name}:pwm-frequency"
            )
        
        request_string = ";".join(request_parts)
        response = await self.req._get_request(request_string)

        if response is None or (isinstance(response, str) and "error" in response.lower()):
            raise ValueError(f"Error fetching switch data: {response}")

        try:
            split_response = response.split(";")
            index = 0
            for switch_name in self.switchList:
                self.switch_data[switch_name]["enabled"] = split_response[index].strip() == "1"
                self.switch_data[switch_name]["pwm-enabled"] = split_response[index + 1].strip() == "1"
                self.switch_data[switch_name]["duty-cycle"] = float(split_response[index + 2])
                self.switch_data[switch_name]["pwm-frequency"] = float(split_response[index + 3])
                index += 4

        except (ValueError, IndexError) as e:
            raise ValueError(f"Error parsing switch data: {response}") from e

        return self.switch_data

    ###  Single Device Requests 
    async def get_switch_enabled(self, switch_name):
        response = await self.req._get_request(f"switch-{switch_name}:enabled")
        self.switch_data[switch_name]["enabled"] = str(response).strip() == "1"
        return self.switch_data[switch_name]["enabled"]

    async def set_switch_enabled(self, switch_name, enabled):
        value_str = "true" if enabled else "false"
        response = await self.req._get_request(
            f"switch-{switch_name}:enabled={value_str}"
        )
        self.switch_data[switch_name]["enabled"] = enabled
        return response

    async def get_pwm_enabled(self, switch_name):
        response = await self.req._get_request(f"switch-{switch_name}:pwm-enabled")
        self.switch_data[switch_name]["pwm-enabled"] = str(response).strip() == "1"
        return self.switch_data[switch_name]["pwm-enabled"]

    async def set_pwm_enabled(self, switch_name, pwm_enabled):
        value_str = "true" if pwm_enabled else "false"
        response = await self.req._get_request(
            f"switch-{switch_name}:pwm-enabled={value_str}"
        )
        self.switch_data[switch_name]["pwm-enabled"] = pwm_enabled
        return response

    async def get_duty_cycle(self, switch_name):
        self.switch_data[switch_name]["duty-cycle"] = await self.req._get_request(
            f"switch-{switch_name}:duty-cycle"
        )
        return self.switch_data[switch_name]["duty-cycle"]

    async def set_duty_cycle(self, switch_name, duty_cycle):
        response = await self.req._get_request(
            f"switch-{switch_name}:duty-cycle={duty_cycle}"
        )
        self.switch_data[switch_name]["duty-cycle"] = duty_cycle
        return response

    async def get_pwm_frequency(self, switch_name):
        self.switch_data[switch_name]["pwm-frequency"] = await self.req._get_request(
            f"switch-{switch_name}:pwm-frequency"
        )
        return self.switch_data[switch_name]["pwm-frequency"]

    async def set_pwm_frequency(self, switch_name, frequency):
        response = await self.req._get_request(
            f"switch-{switch_name}:pwm-frequency={frequency}"
        )
        self.switch_data[switch_name]["pwm-frequency"] = frequency
        return response

    ### Update Methods
    async def update_switch(self, switch_name):
        """Update one switch data."""
        await self.get_switch_enabled(switch_name)
        await self.get_pwm_enabled(switch_name)
        await self.get_duty_cycle(switch_name)
        await self.get_pwm_frequency(switch_name)

    async def update_switches(self):
        """Update all switches data."""
        for switch_name in self.switch_data.keys():
            await self.update_switch(switch_name)

        return self.switch_data

    def __str__(self):
        """Provide a string representation of current switch data."""
        return f"Switches Status: {self.switch_data}"

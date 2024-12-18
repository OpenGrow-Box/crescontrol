from .cres_req import CresRequest
import logging

_LOGGER = logging.getLogger(__name__)

class CresSwitches:
    def __init__(self, reqAddr, switchList=["12v", "24v-a", "24v-b"]):
        self.req = CresRequest(reqAddr)
        self.switchList = switchList
        self.devices = switchList
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

        response = await self.req._get_request(
            "switch-12v:enabled;switch-12v:pwm-enabled;switch-12v:duty-cycle;switch-12v:pwm-frequency;"
            "switch-24v-a:enabled;switch-24v-a:pwm-enabled;switch-24v-a:duty-cycle;switch-24v-a:pwm-frequency;"
            "switch-24v-b:enabled;switch-24v-b:pwm-enabled;switch-24v-b:duty-cycle;switch-24v-b:pwm-frequency"
        )


        if response is None or "error" in response.lower():
            raise ValueError(f"Error fetching switch data: {response}")

 
        try:
            (
                enabled_12v, enabled_pwm_12v, duty_cycle_12v, pwm_frequency_12v,
                enabled_24v_a, enabled_pwm_24v_a, duty_cycle_24v_a, pwm_frequency_24v_a,
                enabled_24v_b, enabled_pwm_24v_b, duty_cycle_24v_b, pwm_frequency_24v_b
            ) = response.split(";")
            
           
            self.switch_data["12v"]["enabled"] = enabled_12v == "1"
            self.switch_data["12v"]["pwm-enabled"] = enabled_pwm_12v == "1"
            self.switch_data["12v"]["duty-cycle"] = float(duty_cycle_12v)
            self.switch_data["12v"]["pwm-frequency"] = float(pwm_frequency_12v)

           
            self.switch_data["24v-a"]["enabled"] = enabled_24v_a == "1"
            self.switch_data["24v-a"]["pwm-enabled"] = enabled_pwm_24v_a == "1"
            self.switch_data["24v-a"]["duty-cycle"] = float(duty_cycle_24v_a)
            self.switch_data["24v-a"]["pwm-frequency"] = float(pwm_frequency_24v_a)

           
            self.switch_data["24v-b"]["enabled"] = enabled_24v_b == "1"
            self.switch_data["24v-b"]["pwm-enabled"] = enabled_pwm_24v_b == "1"
            self.switch_data["24v-b"]["duty-cycle"] = float(duty_cycle_24v_b)
            self.switch_data["24v-b"]["pwm-frequency"] = float(pwm_frequency_24v_b)

        except ValueError as e:
            
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

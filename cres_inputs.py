from .cres_req import CresRequest


class CresInputs:
    def __init__(self, reqAddr, inputList=["a", "b"]):
        self.req = CresRequest(reqAddr)
        self.inputList = inputList
        self.inputs_data = {}
        self.devices = ["a", "b"]

        for input_name in self.inputList:
            self.inputs_data[input_name] = {
                "voltage": "",
                "calibOffset": "",
                "calibFactor": "",
            }

    def configureInputs(self, inputList):

        self.inputList = inputList
        for input_name in self.inputList:
            self.inputs_data[input_name] = {+                      
                "voltage": 0,
                "calibOffset": 0,
                "calibFactor": 0,
            }


## Multi Device Request
    async def getAllInputsData(self):
        """Fetch all input data with a single request for all inputs."""

        request_string = ";".join([f"in-{input_name}:voltage;in-{input_name}:calib-offset;in-{input_name}:calib-factor" for input_name in self.inputList])
        

        response = await self.req._get_request(request_string)

        if response is None or "error" in response.lower():
            raise ValueError(f"Error fetching input data: {response}")


        try:
            split_response = response.split(";")
            

            for i, input_name in enumerate(self.inputList):
                voltage = float(split_response[i * 3])
                calibOffset = float(split_response[i * 3 + 1])
                calibFactor = float(split_response[i * 3 + 2])


                self.inputs_data[input_name] = {
                    "voltage": voltage,
                    "calibOffset": calibOffset,
                    "calibFactor": calibFactor,
                }

        except ValueError as e:

            raise ValueError(f"Error parsing input data: {response}") from e

        return self.inputs_data


## Single Device Request

    async def get_input_voltage(self, input_name):
        self.inputs_data[input_name]["voltage"] = await self.req._get_request(
            f"in-{input_name}:voltage"
        )
        return self.inputs_data[input_name]["voltage"]

    async def get_input_calib_offset(self, input_name):
        self.inputs_data[input_name]["calibOffset"] = await self.req._get_request(
            f"in-{input_name}:calib-offset"
        )
        return self.inputs_data[input_name]["calibOffset"]

    async def set_input_calib_offset(self, input_name, offset):
        self.inputs_data[input_name]["calibOffset"] = await self.req._get_request(
            f"in-{input_name}:calib-offset={offset}"
        )
        return self.inputs_data[input_name]["calibOffset"]

    async def get_input_calib_factor(self, input_name):
        self.inputs_data[input_name]["calibFactor"] = await self.req._get_request(
            f"in-{input_name}:calib-factor"
        )
        return self.inputs_data[input_name]["calibFactor"]

    async def set_input_calib_factor(self, input_name, factor):
        self.inputs_data[input_name]["calibFactor"] = await self.req._get_request(
            f"in-{input_name}:calib-factor={factor}"
        )
        return self.inputs_data[input_name]["calibFactor"]

    async def update_input(self,input_name):

        await self.get_input_voltage(input_name)
        await self.get_input_calib_offset(input_name)
        await self.get_input_calib_factor(input_name)

    async def update_inputs(self):
        """Fetch all input data with a single request."""
        for input_name in self.inputList:

            response = await self.req._get_request(
                f"in-{input_name}:voltage;in-{input_name}:calib-offset;in-{input_name}:calib-factor"
            )


            voltage, calibOffset, calibFactor = response.split(";")


            self.inputs_data[input_name] = {
                "voltage": float(voltage),
                "calibOffset": float(calibOffset),
                "calibFactor": float(calibFactor),
            }

        return self.inputs_data
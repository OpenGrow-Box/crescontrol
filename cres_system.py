from .cres_req import CresRequest

import logging

_LOGGER = logging.getLogger(__name__)


class CresSystem:
    def __init__(self, reqAddr):
        self.req = CresRequest(reqAddr)
        self.cpuID = ""
        self.type = ""
        self.resetCause = ""
        self.debuggingEnabled = ""
        self.Frequency = ""
        self.RescueMode = ""
        self.heapSize = ""
        self.heapFree = ""
        self.largestBlock = ""
        self.watermark = ""
        self.serialEnabled = ""
        self.baudRate = ""
        self.system_info = {}
        self.reboot = ""

    async def getCpuID(self):
        self.cpuID = await self.req._get_request("system:cpu-id")
        return self.cpuID

    async def getResetCause(self):
        self.resetCause = await self.req._get_request("system:reset-cause")
        return self.resetCause

    async def getDebuggingEnabled(self):
        self.debuggingEnabled = await self.req._get_request("system:debugging-enabled")
        return self.debuggingEnabled

    async def getFrequency(self):
        self.Frequency = await self.req._get_request("system:frequency")
        return self.Frequency

    async def getRescueMode(self):
        self.RescueMode = await self.req._get_request("system:rescue-mode")
        return self.RescueMode

    async def getHeapSize(self):
        self.heapSize = await self.req._get_request("system:heap:size")
        return self.heapSize

    async def getHeapFree(self):
        self.heapFree = await self.req._get_request("system:heap:free")
        return self.heapFree

    async def getHeapLargestBlock(self):
        self.largestBlock = await self.req._get_request("system:heap:largest-block")
        return self.largestBlock

    async def getHeapWatermark(self):
        self.watermark = await self.req._get_request("system:heap:watermark")
        return self.watermark

    async def getSerialEnabled(self):
        self.serialEnabled = await self.req._get_request("system:serial:enabled")
        return self.serialEnabled

    async def getBaudrate(self):
        self.baudRate = await self.req._get_request("system:serial:baudrate")
        return self.baudRate

    async def getSystemInfo(self):
        try:
            self.type = await self.req._get_request("type")
            return self.type if self.type else None
        except Exception as e:
            _LOGGER.error(f"Kein Type Gefunden {e}")
            return None

    async def RebootSystem(self):
        self.reboot = await self.req._get_request("system:reboot")
        return self.reboot

    async def get_system_info(self):
        self.system_info = {
            # "cpuID": await self.getCpuID(),
            # "resetCause": await self.getResetCause(),
            # "debuggingEnabled": await self.getDebuggingEnabled(),
            # "Frequency": await self.getFrequency(),
            # "RescueMode": await self.getRescueMode(),
            # "heapSize": await self.getHeapSize(),
            # "heapFree": await self.getHeapFree(),
            # "largestBlock": await self.getHeapLargestBlock(),
            # "watermark": await self.getHeapWatermark(),
            # "serialEnabled": await self.getSerialEnabled(),
            # "baudRate": await self.getBaudrate(),
            "type": await self.getType(),
        }
        return self.system_info

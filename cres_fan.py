# CresFan Subclass with a new method updateFanData()
from .cres_req import CresRequest


class CresFan:
    def __init__(self, reqAddr):
        self.req = CresRequest(reqAddr)
        self.enabled: bool = False
        self.duty_cycle: float = 0.0  # Ändere zu float, da der Wert Dezimalstellen hat
        self.min_duty_cycle: float = 0.0  # Ändere zu float

## MULTI REQUESTS
    async def getAllFanData(self):
        """Fetch all Fan data with a single request."""
        # Kombinierter Request, um alle Fan-Daten auf einmal abzurufen
        response = await self.req._get_request(
            "fan:enabled;fan:duty-cycle;fan:duty-cycle-min"
        )

        # Überprüfen, ob die Antwort gültig ist
        if response is None or "error" in response.lower():
            raise ValueError(f"Error fetching fan data: {response}")

        # Antwort aufsplitten und die Werte zuweisen
        try:
            enabled, duty_cycle, min_duty_cycle = response.split(";")
            # Zuweisungen vornehmen
            self.enabled = enabled == "1"
            self.duty_cycle = float(duty_cycle)  # Konvertiere zu float
            self.min_duty_cycle = float(min_duty_cycle)  # Konvertiere zu float
        except ValueError as e:
            # Falls die Antwort unerwartet ist
            raise ValueError(f"Error parsing fan data: {response}") from e

        return {
            "enabled": self.enabled,
            "duty_cycle": self.duty_cycle,
            "min_duty_cycle": self.min_duty_cycle,
        }

    async def setAllFanData(self, enabled: bool, dutyCycle: float, dutyCycleMin: float):
        """Set all Fan data with a single request."""
        # Bereite den Request vor
        enabled_val = '1' if enabled else '0'
        
        # Ein einzelnes Request mit mehreren Kommandos kombinieren
        response = await self.req._get_request(
            f"fan:enabled={enabled_val};fan:duty-cycle={dutyCycle};fan:duty-cycle-min={dutyCycleMin}"
        )

        # Optional: Fehlerbehandlung hinzufügen, falls das Setzen der Werte fehlschlägt
        if response is None or "error" in response.lower():
            raise ValueError(f"Error setting fan data: {response}")
        
        # Da es sich um einen Set-Request handelt, sollte hier keine Antwort im Format "enabled;duty_cycle;min_duty_cycle" kommen
        # Wenn du sicherstellen möchtest, dass die Daten korrekt gesetzt wurden, kannst du danach die neuen Werte abrufen:
        await self.updateFanData()

        # Rückgabe der gesetzten Werte
        return {
            "enabled": self.enabled,
            "duty_cycle": self.duty_cycle,
            "min_duty_cycle": self.min_duty_cycle,
        }

## SINGLE REQUESTS 

    async def getFanEnabled(self):
        enabled = await self.req._get_request("fan:enabled")
        
        # Explizit überprüfen, ob der Rückgabewert "1" (an) oder "0" (aus) ist
        if enabled == "1" or enabled == 1:
            self.enabled = True
        else:
            self.enabled = False
            
        return self.enabled

    async def setFanEnabled(self, enabled: bool):
        """Enable or disable the fan. When disabling, set duty cycle to 0."""
        endpoint = f"fan:enabled={'1' if enabled else '0'}"  # Ensure it's '1' or '0' as true/false
        response = await self.req._get_request(endpoint)

        if response:
            self.enabled = enabled
            if not self.enabled:  # If fan is disabled, set duty cycle to 0
                await self.setFanDutyCycle(0)
        return response

    async def getFanDutyCycle(self):
        self.duty_cycle = float(await self.req._get_request("fan:duty-cycle"))  # Konvertiere zu float
        return self.duty_cycle

    async def setFanDutyCycle(self, duty_cycle: float):  # Erlaube float als Parameter
        self.duty_cycle = float(await self.req._get_request(f"fan:duty-cycle={duty_cycle}"))  # Konvertiere zu float
        return self.duty_cycle

    async def getFanDutyCycleMin(self):
        self.min_duty_cycle = float(await self.req._get_request("fan:duty-cycle-min"))  # Konvertiere zu float
        return self.min_duty_cycle

    async def setFanDutyCycleMin(self, min_duty_cycle: float):  # Erlaube float als Parameter
        await self.req._get_request(f"fan:duty-cycle-min={min_duty_cycle}")
        self.min_duty_cycle = min_duty_cycle
        
    def __str__(self):
        return (
            f"Fan Status:\n"
            f"Enabled: {self.enabled}\n"
            f"Duty Cycle: {self.duty_cycle}%\n"
            f"Minimum Duty Cycle: {self.min_duty_cycle}%\n"
        )

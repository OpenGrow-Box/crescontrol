import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)


class CresRequest:
    def __init__(self, reqAddr):
        self.reqAddr = reqAddr

    async def _get_request(self, endpoint):
        url = f"http://{self.reqAddr}/command?query={endpoint}"
        print(url)
        _LOGGER.debug(f"GET Request URL: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    content_type = response.headers.get("Content-Type")
                    if response.status == 200:
                        if content_type and "application/json" in content_type:
                            result = await response.json()
                            _LOGGER.debug(f"GET Response: {result}")
                            return result
                        elif content_type and "text/plain" in content_type:
                            content = await response.text()
                            _LOGGER.debug(f"GET Response (text/plain): {content}")
                            return content
                        else:
                            content = await response.text()
                            _LOGGER.error(
                                f"GET Request failed with unexpected content type: {content_type}. Response text: {content}"
                            )
                            raise ValueError(f"Unexpected content type: {content_type}")
                    else:
                        _LOGGER.error(
                            f"GET Request failed with status {response.status}"
                        )
                        response.raise_for_status()
        except Exception as e:
            _LOGGER.error(f"GET Request failed: {e}")
            raise

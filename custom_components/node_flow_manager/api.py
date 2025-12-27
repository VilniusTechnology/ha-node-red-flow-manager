import logging
import aiohttp
import async_timeout

from .const import DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

class NodeRedApiClient:
    def __init__(
        self, 
        host: str, 
        port: int = DEFAULT_PORT, 
        username: str = None, 
        password: str = None, 
        session: aiohttp.ClientSession = None,
        verify_ssl: bool = False,
        public_url: str = None
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._session = session
        self._verify_ssl = verify_ssl
        self._token = None
        self._public_url = public_url

    @property
    def base_url(self) -> str:
        protocol = "https" if self._verify_ssl else "http"
        return f"{protocol}://{self._host}:{self._port}"

    @property
    def configuration_base_url(self) -> str:
        """Return the base URL for configuration (browser access)."""
        if self._public_url:
            url = self._public_url.rstrip("/")
            if not url.startswith(("http://", "https://")):
                protocol = "https" if self._verify_ssl else "http"
                return f"{protocol}://{url}"
            return url
        return self.base_url

    async def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._token:
             headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def authenticate(self) -> bool:
        """Authenticate with Node-RED."""
        if not self._username or not self._password:
            return True

        url = f"{self.base_url}/auth/token"
        data = {
            "client_id": "node-red-editor",
            "grant_type": "password",
            "scope": "*",
            "username": self._username,
            "password": self._password,
        }
        
        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, json=data, verify_ssl=self._verify_ssl) as response:
                    if response.status != 200:
                        _LOGGER.error("Authentication failed: %s", await response.text())
                        return False
                    result = await response.json()
                    self._token = result.get("access_token")
                    return True
        except Exception as exception:
            _LOGGER.exception("Error authenticating with Node-RED: %s", exception)
            raise

    async def get_flows(self) -> list:
        """Get all flows from Node-RED."""
        url = f"{self.base_url}/flows"
        headers = await self._get_headers()
        
        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url, headers=headers, verify_ssl=self._verify_ssl) as response:
                    if response.status == 401 and self._username:
                        if await self.authenticate():
                             headers = await self._get_headers()
                             async with self._session.get(url, headers=headers, verify_ssl=self._verify_ssl) as response2:
                                 return await response2.json()
                    
                    response.raise_for_status()
                    return await response.json()
        except Exception as exception:
            _LOGGER.exception("Error fetching flows: %s", exception)
            raise

    async def get_flow(self, flow_id: str) -> dict:
        """Get a specific flow from Node-RED."""
        url = f"{self.base_url}/flow/{flow_id}"
        headers = await self._get_headers()
        
        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url, headers=headers, verify_ssl=self._verify_ssl) as response:
                    if response.status == 401 and self._username:
                        if await self.authenticate():
                             headers = await self._get_headers()
                             async with self._session.get(url, headers=headers, verify_ssl=self._verify_ssl) as response2:
                                 return await response2.json()
                    
                    response.raise_for_status()
                    return await response.json()
        except Exception as exception:
            _LOGGER.exception("Error fetching flow %s: %s", flow_id, exception)
            raise

    async def update_flow(self, flow_id: str, data: dict) -> bool:
        """Update a flow in Node-RED safely by fetching current state first."""
        # Fetch current flow state to avoid overwriting other properties
        current_flow = await self.get_flow(flow_id)
        
        # Resolve any nested properties like 'env'
        if "env" in data and "env" in current_flow:
            # Merge env variables
            new_env = {item["name"]: item for item in current_flow["env"]}
            for updated_item in data["env"]:
                new_env[updated_item["name"]] = updated_item
            current_flow["env"] = list(new_env.values())
            # Remove env from data so it doesn't overwrite the merged result
            update_data = {k: v for k, v in data.items() if k != "env"}
            current_flow.update(update_data)
        else:
            current_flow.update(data)

        url = f"{self.base_url}/flow/{flow_id}"
        headers = await self._get_headers()
        
        try:
            async with async_timeout.timeout(10):
                async with self._session.put(url, headers=headers, json=current_flow, verify_ssl=self._verify_ssl) as response:
                    if response.status == 401 and self._username:
                        if await self.authenticate():
                            headers = await self._get_headers()
                            async with self._session.put(url, headers=headers, json=current_flow, verify_ssl=self._verify_ssl) as response2:
                                return response2.status == 200

                    return response.status == 200
        except Exception as exception:
            _LOGGER.exception("Error updating flow %s: %s", flow_id, exception)
            raise

    async def listen_comms(self, callback) -> None:
        """Listen to the Node-RED comms WebSocket."""
        protocol = "wss" if self._verify_ssl else "ws"
        url = f"{protocol}://{self._host}:{self._port}/comms"
        
        # Add auth token if available. Re-auth if needed might be tricky in a loop.
        if self._token:
            url += f"?access_token={self._token}"
            
        _LOGGER.debug("Connecting to Node-RED comms at %s", url)
        
        try:
            async with self._session.ws_connect(url, verify_ssl=self._verify_ssl) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = msg.json()
                            await callback(data)
                        except Exception as e:
                            _LOGGER.error("Error parsing/handling WebSocket message: %s", e)
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        _LOGGER.warning("Node-RED comms WebSocket closed or error: %s", msg.data)
                        break
        except Exception as exception:
            _LOGGER.error("Error in Node-RED comms WebSocket connection: %s", exception)
            raise

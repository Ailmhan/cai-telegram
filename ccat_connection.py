import asyncio
import logging
import json
from cheshire_cat_api import CatClient, Config


class CCatConnection:

    def __init__(self, user_id, out_queue: asyncio.Queue, ccat_url: str = "https://cai-assistant.com", ccat_port: int = 443) -> None:
        self.user_id = user_id

        # Get event loop
        self._loop = asyncio.get_running_loop()

        # Queue of the messages to send on telegram
        self._out_queue = out_queue
        
        conf = Config(
            base_url=ccat_url,
            port=ccat_port,
            user_id=user_id,
        )

        # Instantiate the CAI client
        self.ccat = CatClient(
            config=conf,
            on_open=self._on_open,
            on_close=self._on_close,
            on_message=self._ccat_message_callback
        )

        # Easy access to send
        self.send = self.ccat.send

        # This event is not None if we are waiting for ws connection open
        self._stop_waiting_connection = None
       

    async def connect(self):

        if self._stop_waiting_connection is not None:
            logging.warning(f"Уже ожидает подключения через веб-сокету для пользователя {self.user_id}")
            return
        
        self.ccat.connect_ws()

        logging.info(f"Ожидание подключения веб-сокета {self.user_id}")

        # Create the event to stop waiting for connection
        self._stop_waiting_connection = asyncio.Event()

        # Wait connection
        await self._stop_waiting_connection.wait()
        self._stop_waiting_connection = None


    def _ccat_message_callback(self, message: str):
        # Websocket on_mesage callback

        message = json.loads(message)

        self._loop.call_soon_threadsafe(self._out_queue.put_nowait, (message, self.user_id))
    

    def _on_open(self):

        # Set the event to stop waiting for connection
        if self._stop_waiting_connection:
            self._stop_waiting_connection.set()


    def _on_close(self, status_code: int, msg: str):

        # on_close is called also if there is a connection error 
        # so the event is set if we are waiting for connection
        if self._stop_waiting_connection:
            self._stop_waiting_connection.set()

    @property
    def is_connected(self):
        return self.ccat.is_ws_connected
        
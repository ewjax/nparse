import json
import ssl
import time

from PyQt5.QtCore import QRunnable, pyqtSlot
from PyQt5.QtCore import QThreadPool
import websocket

from config import profile
from utils import logger
from utils.signals import SIGNALS

LOG = logger.get_logger(__name__)


RUN = True
THREADPOOL = QThreadPool()
_LSC = None


def get_location_service_connection():
    global _LSC
    if _LSC is None:
        _LSC = LocationServiceConnection()
    return _LSC


def start_location_service(update_func):
    try:
        SIGNALS.locs_recieved.disconnect()
    except TypeError:
        pass
    SIGNALS.locs_recieved.connect(update_func)
    SIGNALS.config_updated.connect(config_updated)
    config_updated()
    lsc = get_location_service_connection()
    THREADPOOL.start(lsc)


def stop_location_service():
    global RUN
    RUN = False
    lsc = get_location_service_connection()
    lsc.enabled = False
    lsc.configure_socket()


def config_updated():
    lsc = get_location_service_connection()
    lsc.enabled = profile.sharing.enabled
    lsc.host = profile.sharing.url
    lsc.reconnect_delay = profile.sharing.reconnect_delay
    lsc.configure_socket()


class LocationServiceConnection(QRunnable):
    _socket = None
    enabled = False
    host = None
    reconnect_delay = 5

    def __init__(self):
        super(LocationServiceConnection, self).__init__()
        try:
            SIGNALS.send_loc.disconnect()
        except TypeError:
            pass
        SIGNALS.send_loc.connect(self.send_loc)

    def configure_socket(self):
        if self._socket:
            LOG.info("Resetting socket, killing any open connection...")
            try:
                self._socket.close()
            except AttributeError:
                pass
            self._socket = None
        if self.host and self.enabled:
            LOG.info("Host set and sharing enabled, connecting...")
            self._socket = websocket.WebSocketApp(
                self.host, on_message=self._on_message,
                on_error=self._on_error, on_close=self._on_close,
                on_open=self._on_open)
        else:
            LOG.debug("Sharing disabled.")

    @pyqtSlot()
    def run(self):
        while RUN:
            try:
                self.configure_socket()
            except:
                LOG.exception("Failed to configure socket!")
            if self.enabled:
                LOG.info("Starting connection to sharing host...")
                try:
                    self._socket.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
                except:
                    LOG.warning("Socket connection broken, continuing...")
            if RUN:
                time.sleep(self.reconnect_delay)

    def send_loc(self, loc):
        if not self.enabled:
            return
        group_key = profile.sharing.group_key
        if profile.sharing.discord_channel:
            try:
                group_key = profile.discord.url.split('?')[0].split('/')[-1]
            except:
                LOG.warning("Failed to parse discord channel ID, "
                            "falling back to configured group_key.")

        message = {'type': "location",
                   'group_key': group_key,
                   'location': loc}
        try:
            self._socket.send(json.dumps(message))
        except:
            LOG.exception("Unable to send location to server.")

    def _on_message(self, ws, message):
        message = json.loads(message)
        if message['type'] == "state":
            LOG.debug("Message received: %s" % message)
            SIGNALS.locs_recieved.emit(message['locations'])

    def _on_error(self, ws, error):
        LOG.error("Connection error: %s" % error)

    def _on_open(self, ws):
        LOG.info("Connection opened.")

    def _on_close(self, ws):
        LOG.info("Connection closed.")

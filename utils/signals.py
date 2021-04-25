from PyQt5.QtCore import QObject, pyqtSignal


class LocationSignals(QObject):
    locs_recieved = pyqtSignal(dict)
    send_loc = pyqtSignal(dict)
    config_updated = pyqtSignal()


SIGNALS = LocationSignals()
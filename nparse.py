"""NomnsParse: Parsing tools for Project 1999."""
import os
import sys
import webbrowser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFontDatabase, QIcon
from PyQt5.QtWidgets import (QApplication, QFileDialog, QMenu, QMessageBox,
                             QSystemTrayIcon)

import parsers
from helpers import config, logreader, resource_path
from helpers.settings import SettingsWindow

config.load('nparse.config.yml')

os.environ['QT_SCALE_FACTOR'] = str(
    config.data['general']['qt_scale_factor'] / 100)


CURRENT_VERSION = 'v0.5-alpha'


class NomnsParse(QApplication):
    """Application Control."""

    def __init__(self, *args):
        super().__init__(*args)

        # validate settings file
        try:
            config.verify_settings()
        except ValueError:
            QMessageBox.critical(
                None,
                'Critical Error',
                'Config file nparse.config.yml contains errors.  Please obtain a valid settings file.',
                QMessageBox.Ok
            )
            sys.exit()

        # Updates
        self._toggled = False
        self._log_reader = None

        # Load Parsers
        self._load_parsers()
        self._settings = SettingsWindow()

        # Tray Icon
        self._system_tray = QSystemTrayIcon()
        self._system_tray.setIcon(QIcon(resource_path('data/ui/icon.png')))
        self._system_tray.setToolTip("nParse")
        # self._system_tray.setContextMenu(self._create_menu())
        self._system_tray.activated.connect(self._menu)
        self._system_tray.show()

        # Turn On
        self._toggle()

    def _load_parsers(self):
        self._parsers = [
            parsers.Maps(),
            parsers.Spells()
        ]
        for parser in self._parsers:
            if parser.name in config.data.keys() and 'geometry' in config.data[parser.name].keys():
                g = config.data[parser.name]['geometry']
                parser.setGeometry(g[0], g[1], g[2], g[3])
            if config.data[parser.name]['toggled']:
                parser.toggle()

    def _toggle(self):
        if not self._toggled:
            try:
                config.verify_paths()
            except ValueError as error:
                self._system_tray.showMessage(
                    error.args[0], error.args[1], msecs=3000)

            else:
                self._log_reader = logreader.LogReader(
                    config.data['general']['eq_log_dir'])
                self._log_reader.new_line.connect(self._parse)
                self._toggled = True
        else:
            if self._log_reader:
                self._log_reader.deleteLater()
                self._log_reader = None
            self._toggled = False

    def _parse(self, new_line):
        if new_line:
            timestamp, text = new_line  # (datetime, text)
            #  don't send parse to non toggled items, except maps.  always parse maps
            for parser in [parser for parser in self._parsers if config.data[parser.name]['toggled'] or parser.name == 'maps']:
                parser.parse(timestamp, text)

    def _menu(self, event):
        """Returns a new QMenu for system tray."""
        menu = QMenu()
        menu.setAttribute(Qt.WA_DeleteOnClose)
        check_version_action = menu.addAction(
            'Check For Update ({})'.format(CURRENT_VERSION))
        menu.addSeparator()
        get_eq_dir_action = menu.addAction('Select EQ Logs Directory')
        menu.addSeparator()

        parser_toggles = set()
        for parser in self._parsers:
            toggle = menu.addAction(parser.name.title())
            toggle.setCheckable(True)
            toggle.setChecked(config.data[parser.name]['toggled'])
            parser_toggles.add(toggle)

        menu.addSeparator()
        settings_action = menu.addAction('Settings')
        menu.addSeparator()
        quit_action = menu.addAction('Quit')

        action = menu.exec_(QCursor.pos())

        if action == check_version_action:
            webbrowser.open('https://github.com/nomns/nparse/releases')

        elif action == get_eq_dir_action:
            dir_path = str(QFileDialog.getExistingDirectory(
                None, 'Select Everquest Logs Directory'))
            if dir_path:
                config.data['general']['eq_log_dir'] = dir_path
                config.save()
                self._toggle()

        elif action == settings_action:
            if self._settings.exec_():
                # Update required settings
                for parser in self._parsers:
                    if parser.windowOpacity() != config.data['general']['parser_opacity']:
                        parser.setWindowOpacity(
                            config.data['general']['parser_opacity'] / 100)
                        parser.settings_updated()
            # some settings are saved within other settings automatically
            # force update
            for parser in self._parsers: 
                if parser.name == "spells":
                    parser.load_custom_timers()

        elif action == quit_action:
            if self._toggled:
                self._toggle()
            self._system_tray.setVisible(False)
            self.quit()

        elif action in parser_toggles:
            parser = [
                parser for parser in self._parsers if parser.name == action.text().lower()][0]
            parser.toggle()


if __name__ == "__main__":
    try:
        import ctypes
        APPID = 'nomns.nparse'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
    except:
        pass

    APP = NomnsParse(sys.argv)
    APP.setStyleSheet(open(resource_path('data/ui/_.css')).read())
    APP.setWindowIcon(QIcon(resource_path('data/ui/icon.png')))
    APP.setQuitOnLastWindowClosed(False)
    APP.setAttribute(Qt.AA_EnableHighDpiScaling)
    QFontDatabase.addApplicationFont(
        resource_path('data/fonts/NotoSans-Regular.ttf'))
    QFontDatabase.addApplicationFont(
        resource_path('data/fonts/NotoSans-Bold.ttf'))

    sys.exit(APP.exec())

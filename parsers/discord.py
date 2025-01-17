import functools

from PyQt6 import QtCore
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QScrollArea, QPushButton, QDialog, QGridLayout

from helpers import ParserWindow, config


JS_ADD_CSS_TEMPLATE = """(
function() {
    css = document.getElementById('%(name)s');
    if (css == null) {
        css = document.createElement('style');
        css.type='text/css'; css.id='%(name)s';
        document.head.appendChild(css);
    }
    css.innerText='%(new_css)s';
})()"""
CSS_SMALLER_AVATARS = (
    '.voice-container .voice-states .voice-state.small-avatar .avatar {'
    '    height: 20px !important;'
    '    width: 20px !important;'
    '}'
    '.voice-container .voice-states .voice-state.small-avatar .user {'
    '    padding-top: 0px !important;'
    '}'
    '.voice-container .voice-states .voice-state .user {'
    '    padding-top: 0px !important;'
    '}'
    '.voice-container .voice-states .voice-state.small-avatar {'
    '    height: 20px !important;'
    '}'
)
CSS_MENU = """
#ParserWindowMenu QPushButton:hover {{
    background: darkgreen;
}}
#ParserWindowMenu QPushButton:checked {{
    color: white;
}}
#ParserWindowMenu QPushButton {{
    color: rgba(255, 255, 255, {alpha});
}}
#ParserWindowMenuReal {{
    background-color:rgba({red},{green},{blue},{alpha})
}}
#ParserWindowMenuReal QPushButton {{
    background-color:rgba({red},{green},{blue},0)
}}
#ParserWindowMoveButton {{
    color: rgba(255,255,255,{alpha})
}}
#ParserWindowTitle {{
    color: rgba(200, 200, 200, {alpha})
}}"""
HTML_NO_CONFIG = """
<html><font color='lightgrey' size='5px'>
Hover this window and click the gear icon to configure your Discord overlay.
</font></html>"""


class Discord(ParserWindow):
    """Tracks spell casting, duration, and targets by name."""

    def __init__(self):
        super().__init__()
        self.name = 'discord'
        self.setWindowTitle(self.name.title())
        self.set_title(self.name.title())
        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumWidth(125)
        self.overlay = None
        self.settings_dialog = None
        self.url = config.data['discord']['url']
        self._setup_webview()

    def shutdown(self):
        if self.settings_dialog:
            self.settings_dialog.destroy()
        if self.overlay:
            self.overlay.destroy()

    def _applyTweaks(self):
        if self.overlay:
            # Make small avatars even smaller
            small_avatars = JS_ADD_CSS_TEMPLATE % {
                'name': 'smalleravatar', 'new_css': CSS_SMALLER_AVATARS}
            self.overlay.page().runJavaScript(small_avatars)

            # Fix background color/opacity to match settings
            self._fix_background()

    def _fix_background(self):
        bg_opacity = config.data[self.name]['bg_opacity'] / 100
        hexcolor = config.data[self.name]['color']
        intcolor = int(hexcolor.replace('#', '0x'), 16)
        qcolor = QColor(intcolor)
        bg_color_set = JS_ADD_CSS_TEMPLATE % {
            'name': 'bgcolor',
            'new_css': "body {{ background-color: rgba({red},{green},{blue},{alpha}) !important }}".format(
                red=qcolor.red(),
                green=qcolor.green(),
                blue=qcolor.blue(),
                alpha=bg_opacity
            )}
        self.overlay.page().runJavaScript(bg_color_set)

    def update_background_color(self):
        self._fix_background()
        opacity = config.data[self.name]['opacity'] / 100
        hexcolor = config.data[self.name]['color']
        intcolor = int(hexcolor.replace('#', '0x'), 16)
        qcolor = QColor(intcolor)
        self._menu.setStyleSheet(
            CSS_MENU.format(
                red=qcolor.red(),
                green=qcolor.green(),
                blue=qcolor.blue(),
                alpha=opacity
            ))

    def update_window_opacity(self):
        # This is special-cased as part of update_background_color for discord
        return

    def _setup_webview(self):
        setup_button = QPushButton('\u2699')
        setup_button.setObjectName('DiscordConfigButton')
        setup_button.setToolTip('Configure Discord')
        setup_button.clicked.connect(self.show_settings)
        self.menu_area.addWidget(setup_button)

        self.overlay = QWebEngineView()
        self.overlay.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.overlay.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.overlay.page().setBackgroundColor(QColor('transparent'))
        if self.url:
            self.overlay.loadFinished.connect(self._applyTweaks)
            self.overlay.load(QtCore.QUrl(self.url))
        else:
            self.overlay.setHtml(HTML_NO_CONFIG)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.overlay)
        scroll_area.setObjectName('DiscordScrollArea')
        scroll_area.setFrameStyle(0)
        self.content.addWidget(scroll_area, 1)

    def show_settings(self):
        if self.settings_dialog:
            self.settings_dialog.show()
            return

        self.settings_dialog = QDialog()
        self.settings_dialog.setWindowTitle('Configure Overlay')
        self.settings_dialog.setMinimumSize(1024, 800)
        self.settings_dialog.setContentsMargins(0, 0, 0, 0)
        settings_layout = QGridLayout()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_webview = QWebEngineView()
        settings_webview.loadFinished.connect(
            functools.partial(self._skip_stream_button, settings_webview))
        settings_webview.load(QtCore.QUrl(
            "https://streamkit.discord.com/overlay"))
        settings_layout.addWidget(settings_webview, 0, 0, 1, 2)

        ok_button = QPushButton('Save')
        ok_button.clicked.connect(
            functools.partial(self._save_settings,
                              settings_webview, self.settings_dialog))
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.settings_dialog.close)

        settings_layout.addWidget(ok_button, 1, 0)
        settings_layout.addWidget(cancel_button, 1, 1)
        self.settings_dialog.setLayout(settings_layout)
        self.settings_dialog.open()

    def _save_settings(self, webview, frame):
        get_url = "document.getElementsByClassName('source-url')[0].value;"
        webview.page().runJavaScript(get_url, self._on_get_url)
        frame.close()

    def _on_get_url(self, url):
        self.url = url.replace("true", "True")
        self.overlay.load(QtCore.QUrl(self.url))
        self._applyTweaks()
        config.data['discord']['url'] = self.url
        config.save()

    def _skip_stream_button(self, webview):
        skipIntro = (
            "buttons = document.getElementsByTagName('button');"
            "for(i=0;i<buttons.length;i++){"
            "   if(buttons[i].innerHTML=='Install for OBS'){"
            "       buttons[i].click()}}")
        resizeContents = (
            "document.getElementsByClassName('content')[0]"
            ".style.setProperty('top','0px');")
        hideHeader = (
            "document.getElementsByClassName('header')[0]"
            ".style.setProperty('display','none');")
        hidePreview = (
            "document.getElementsByClassName('config-link')[0]"
            ".style.setProperty('height','300px');"
            "document.getElementsByClassName('config-link')[0]"
            ".style.setProperty('overflow','hidden');")
        hideClose = (
            "document.getElementsByClassName('close')[0]"
            ".style.setProperty('display','none');")
        chooseVoice = (
            "document.querySelectorAll('button[value=voice]')[0].click();")
        toggleSmallAvatars = (
            "labels = document.getElementsByTagName('label');"
            "for(i=0;i<labels.length;i++){"
            "   if(labels[i].innerHTML=='Small Avatars'){"
            "       labels[i].parentElement.getElementsByClassName('switch')[0].click()}}")
        toggleSpeakingOnly = (
            "labels = document.getElementsByTagName('label');"
            "for(i=0;i<labels.length;i++){"
            "   if(labels[i].innerHTML=='Show Speaking Users Only'){"
            "       labels[i].parentElement.getElementsByClassName('switch')[0].click()}}")
        webview.page().runJavaScript(skipIntro)
        webview.page().runJavaScript(hideHeader)
        webview.page().runJavaScript(resizeContents)
        webview.page().runJavaScript(hidePreview)
        webview.page().runJavaScript(hideClose)
        webview.page().runJavaScript(chooseVoice)
        webview.page().runJavaScript(toggleSmallAvatars)
        webview.page().runJavaScript(toggleSpeakingOnly)

    def parse(self, timestamp, text):
        pass

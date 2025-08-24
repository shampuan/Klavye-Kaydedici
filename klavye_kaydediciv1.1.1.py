import sys
import os
import json
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLineEdit,
                             QTextEdit, QLabel, QSystemTrayIcon, QMenu,
                             QAction, QMainWindow, QGroupBox, QFileDialog, QMessageBox, QPushButton)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from pynput import keyboard

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Veri dosyası için yolu tanımla
data_file_path = os.path.join(os.path.expanduser("~"), ".klavye_kaydedici", "data.json")

# Dizin yoksa oluştur
os.makedirs(os.path.dirname(data_file_path), exist_ok=True)

# Mevcut verileri yükle veya yeni bir sözlük oluştur
key_counts = {}
if os.path.exists(data_file_path):
    try:
        with open(data_file_path, 'r', encoding='utf-8') as f:
            key_counts = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        key_counts = {}

# Ana pencere için global bir referans
app = None

# Klavye dinleyici iş parçacığından sinyal yaymak için yardımcı bir sınıf
class KeyboardSignalEmitter(QObject):
    key_pressed = pyqtSignal()

# Klavye dinleyici iş parçacığı
class QKeyboardListenerThread(QThread):
    def __init__(self, emitter):
        super().__init__()
        self.emitter = emitter
        self.listener = None

    def run(self):
        # pynput listener'ını başlat
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

        # Dinleyici iş parçacığının bitmesini bekle
        self.listener.join()

    def on_press(self, key):
        global key_counts
        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)

        key_counts.setdefault(key_str, 0)
        key_counts[key_str] += 1

        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(key_counts, f, indent=4, ensure_ascii=False)

        self.emitter.key_pressed.emit()

    def stop(self):
        # pynput listener'ını durdurmak için
        if self.listener and self.listener.running:
            self.listener.stop()
        # İş parçacığının sonlanmasını bekle
        self.wait()

def get_keyboard_model():
    try:
        lsusb_output = subprocess.check_output(['lsusb'], text=True)
        for line in lsusb_output.splitlines():
            if "Keyboard" in line or "keyboard" in line:
                return line.split('ID ')[1].split(' ', 1)[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        lshw_output = subprocess.check_output(['lshw', '-class', 'input'], text=True)
        for line in lshw_output.splitlines():
            if 'product:' in line:
                return line.split('product:')[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return "Marka-model bilgisi bulunamadı."


# Yeni grafik penceresi sınıfı
class GraphWindow(QMainWindow):
    def __init__(self, key_counts):
        super().__init__()
        self.setWindowTitle("Kullanım Grafiği")
        self.setGeometry(100, 100, 600, 600)

        self.key_counts = key_counts
        self.figure = Figure(facecolor='#212121')
        self.canvas = FigureCanvas(self.figure)

        self.setCentralWidget(self.canvas)

        self.plot_pie_chart()

    def plot_pie_chart(self):
        self.figure.clear()

        valid_keys = {k: v for k, v in self.key_counts.items() if (len(k) == 1 and (k.isalnum() or k.isspace() or k in ['.', ',', '!', '?', ';', ':', '(', ')', '[', ']', '{', '}']))}

        sorted_keys = sorted(valid_keys.items(), key=lambda item: item[1], reverse=True)

        # En çok kullanılan ilk 15 tuşu al
        top_keys = sorted_keys[:15]
        other_count = sum(item[1] for item in sorted_keys[15:])

        labels = [item[0] for item in top_keys]
        sizes = [item[1] for item in top_keys]

        if other_count > 0:
            labels.append("Diğer")
            sizes.append(other_count)

        ax = self.figure.add_subplot(111)
        patches, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'color': '#e0e0e0'})
        for text in texts:
            text.set_color('#e0e0e0')
        for autotext in autotexts:
            autotext.set_color('#424242')

        ax.axis('equal')  # Pasta grafiğinin yuvarlak olmasını sağlar
        ax.set_title("Tuş Kullanım Oranları", color='#e0e0e0')

        self.canvas.draw()


class KeyboardRecorder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.graph_window = None # Pencere referansını tutmak için
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Klavye Kaydedici v1.1.1")
        self.setGeometry(300, 300, 400, 500)

        # Tema ve yazı tipi ayarları
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #212121;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 10pt;
                padding: 0;
            }
            QLineEdit, QTextEdit {
                background-color: #424242;
                border: 1px solid #757575;
                padding: 5px;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #757575;
                margin-top: 10px;
            }
            QGroupBox::title {
                color: #e0e0e0;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                background-color: #212121;
            }
            QMenuBar {
                background-color: #212121;
                color: #e0e0e0;
            }
            QMenuBar::item {
                background-color: #212121;
            }
            QMenuBar::item:selected {
                background-color: #424242;
            }
            QMenu {
                background-color: #212121;
                border: 1px solid #757575;
            }
            QMenu::item {
                background-color: #212121;
                color: #e0e0e0;
            }
            QMenu::item:selected {
                background-color: #424242;
            }
            QPushButton {
                background-color: #007acc;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                font-size: 10pt;
                margin: 4px 2px;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        vbox = QVBoxLayout(central_widget)

        menubar = self.menuBar()

        file_menu = menubar.addMenu("Dosya")
        export_action = QAction("İstatistikleri Kaydet...", self)
        export_action.triggered.connect(self.export_stats_to_file)
        file_menu.addAction(export_action)

        help_menu = menubar.addMenu("Yardım")
        about_action = QAction("Hakkında...", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        klavye_label = QLabel("Klavye:")
        self.keyboard_info_display = QLineEdit(get_keyboard_model())
        self.keyboard_info_display.setReadOnly(True)

        vbox.addWidget(klavye_label)
        vbox.addWidget(self.keyboard_info_display)

        vbox.addSpacing(10)

        stats_group = QGroupBox("Kullanım İstatistikleri")
        stats_layout = QVBoxLayout()
        stats_group.setLayout(stats_layout)

        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        stats_layout.addWidget(self.stats_display)
        
        # Yeni butonları ekle
        self.export_button = QPushButton("İstatistikleri Kaydet")
        self.export_button.clicked.connect(self.export_stats_to_file)
        stats_layout.addWidget(self.export_button)

        self.graph_button = QPushButton("Grafik Oluştur")
        self.graph_button.clicked.connect(self.show_graph)
        stats_layout.addWidget(self.graph_button)

        vbox.addWidget(stats_group, 1)

        self.update_stats()

    def show_about_dialog(self):
        QMessageBox.about(self, "Hakkında",
            "<b>Klavye Kaydedici v1.1.1</b><br>"
            "Sürüm: 1.1.1<br>"
            "Lisans: GNU AGPLv3<br>"
            "Geliştirici: A. Serhat KILIÇOĞLU <br><br>"
            "Bu program, tuş vuruşlarını takip eder ve sayılarını gösterir."
            "Bu program hiçbir garanti getirmez."
        )

    def export_stats_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "İstatistikleri Kaydet", "klavye_istatistikleri.txt", "Text Files (*.txt);;All Files (*)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.stats_display.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Dosya kaydedilirken bir hata oluştu: {e}")

    def show_graph(self):
        self.graph_window = GraphWindow(key_counts)
        self.graph_window.show()

    def update_stats(self):
        valid_keys = {key: count for key, count in key_counts.items() if key is not None}
        sorted_keys = sorted(valid_keys.items(), key=lambda item: item[1], reverse=True)

        stats_text = ""
        for key, count in sorted_keys:
            if key and key.startswith('Key.'):
                key_name = key.replace('Key.', '')
                key_name = key_name.replace('\'', '')
                stats_text += f"[{key_name}]: {count}\n"
            else:
                stats_text += f"'{key}': {count}\n"

        self.stats_display.setPlainText(stats_text)

    def closeEvent(self, event):
        self.hide()
        event.ignore()

class SystemTrayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        # Matplotlib stil ayarını buraya taşıyarak sorunu çözüyoruz.
        plt.style.use('dark_background')
        plt.rcParams['text.color'] = '#e0e0e0'
        plt.rcParams['axes.labelcolor'] = '#e0e0e0'
        plt.rcParams['xtick.color'] = '#e0e0e0'
        plt.rcParams['ytick.color'] = '#e0e0e0'

        # Yazı tipini global olarak ayarla
        font = QFont("Nimbus Sans", 10)
        self.setFont(font)

        self.setQuitOnLastWindowClosed(False)
        self.main_window = KeyboardRecorder()

        self.signal_emitter = KeyboardSignalEmitter()
        self.signal_emitter.key_pressed.connect(self.main_window.update_stats)

        self.listener_thread = QKeyboardListenerThread(self.signal_emitter)
        self.listener_thread.start()

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if not os.path.exists(icon_path):
            print("Uyarı: 'icon.png' dosyası bulunamadı. Lütfen programın çalıştığı dizine bir simge dosyası oluşturun.")
            self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("input-keyboard"), self)
            if self.tray_icon.icon().isNull():
                 pixmap = QPixmap(22, 22)
                 pixmap.fill(Qt.transparent)
                 painter = QPainter(pixmap)
                 painter.setPen(Qt.white)
                 painter.drawText(0, 18, "K")
                 painter.end()
                 self.tray_icon.setIcon(QIcon(pixmap))
        else:
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)

        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        tray_menu = QMenu()
        show_action = QAction("Göster", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        exit_action = QAction("Çıkış", self)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.show_window()

    def show_window(self):
        self.main_window.show()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def quit_app(self):
        self.listener_thread.stop()
        self.quit()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.show_window()

if __name__ == '__main__':
    app = SystemTrayApp(sys.argv)
    sys.exit(app.exec_())

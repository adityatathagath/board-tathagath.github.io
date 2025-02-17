import sys
import os
import sqlite3
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QDateTimeEdit, QTextEdit,
    QMessageBox, QComboBox, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QGuiApplication

# Suppress PyQt warnings & Enable High-DPI Scaling
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# Barclays Colors
BARCLAYS_BLUE = "#00AEEF"
DARK_BLUE = "#00395D"
LIGHT_BLUE = "#0098DA"
WHITE = "#FFFFFF"
TEXT_COLOR = "#333333"

# Database setup
DB_FILE = "reminders.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        datetime TEXT,
                        note TEXT,
                        recurring TEXT
                      )''')
    conn.commit()
    conn.close()

# Multi-threaded Reminder Addition
class AddReminderThread(QThread):
    reminder_added = pyqtSignal()

    def __init__(self, datetime_value, note, recurring):
        super().__init__()
        self.datetime_value = datetime_value
        self.note = note
        self.recurring = recurring

    def run(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reminders (datetime, note, recurring) VALUES (?, ?, ?)",
                       (self.datetime_value, self.note, self.recurring))
        conn.commit()
        conn.close()
        self.reminder_added.emit()

# Multi-threaded Reminder Deletion
class DeleteReminderThread(QThread):
    reminder_deleted = pyqtSignal()

    def __init__(self, reminder_id):
        super().__init__()
        self.reminder_id = reminder_id

    def run(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (self.reminder_id,))
        conn.commit()
        conn.close()
        self.reminder_deleted.emit()

class ReminderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Barclays Reminder App")
        self.setGeometry(100, 100, 600, 550)

        # Apply Barclays Theme
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {WHITE};
                color: {TEXT_COLOR};
                font-family: Arial, sans-serif;
                font-size: 14px;
            }}
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {DARK_BLUE};
            }}
            QPushButton {{
                background-color: {BARCLAYS_BLUE};
                color: {WHITE};
                font-weight: bold;
                border-radius: 5px;
                padding: 6px;
            }}
            QPushButton:hover {{
                background-color: {LIGHT_BLUE};
            }}
            QTableWidget {{
                background-color: {WHITE};
                gridline-color: {DARK_BLUE};
                border: 1px solid {DARK_BLUE};
            }}
            QHeaderView::section {{
                background-color: {DARK_BLUE};
                color: {WHITE};
                font-weight: bold;
            }}
            QTextEdit, QDateTimeEdit, QComboBox {{
                border: 1px solid {BARCLAYS_BLUE};
                padding: 5px;
                border-radius: 3px;
            }}
        """)

        self.layout = QVBoxLayout()

        self.datetime_input = QDateTimeEdit(self)
        self.datetime_input.setCalendarPopup(True)
        self.datetime_input.setDateTime(datetime.datetime.now())

        self.note_input = QTextEdit(self)
        self.note_input.setPlaceholderText("Enter your reminder note here...")

        self.recurring_dropdown = QComboBox(self)
        self.recurring_dropdown.addItems(["None", "Daily", "Weekly", "Monthly", "Yearly"])

        self.add_button = QPushButton("Add Reminder", self)
        self.add_button.clicked.connect(self.add_reminder)

        self.refresh_button = QPushButton("Refresh Reminders", self)
        self.refresh_button.clicked.connect(self.load_reminders)

        self.reminder_table = QTableWidget(self)
        self.reminder_table.setColumnCount(4)
        self.reminder_table.setHorizontalHeaderLabels(["Date & Time", "Note", "Recurring", "Action"])
        self.reminder_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.layout.addWidget(QLabel("Set Reminder Date & Time:"))
        self.layout.addWidget(self.datetime_input)
        self.layout.addWidget(QLabel("Reminder Note:"))
        self.layout.addWidget(self.note_input)
        self.layout.addWidget(QLabel("Recurring Option:"))
        self.layout.addWidget(self.recurring_dropdown)
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.refresh_button)
        self.layout.addWidget(self.reminder_table)

        self.setLayout(self.layout)

        # Timer to check reminders every minute
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(60000)

        self.load_reminders()

    def add_reminder(self):
        datetime_value = self.datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        note = self.note_input.toPlainText()
        recurring = self.recurring_dropdown.currentText()

        if not note:
            QMessageBox.warning(self, "Warning", "Reminder note cannot be empty!")
            return

        self.add_thread = AddReminderThread(datetime_value, note, recurring)
        self.add_thread.reminder_added.connect(self.load_reminders)
        self.add_thread.start()

    def delete_reminder(self, reminder_id):
        self.delete_thread = DeleteReminderThread(reminder_id)
        self.delete_thread.reminder_deleted.connect(self.load_reminders)
        self.delete_thread.start()

    def load_reminders(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders ORDER BY datetime ASC")
        reminders = cursor.fetchall()
        conn.close()

        self.reminder_table.setRowCount(len(reminders))
        for row_idx, (reminder_id, datetime_value, note, recurring) in enumerate(reminders):
            self.reminder_table.setItem(row_idx, 0, QTableWidgetItem(datetime_value))
            self.reminder_table.setItem(row_idx, 1, QTableWidgetItem(note))
            self.reminder_table.setItem(row_idx, 2, QTableWidgetItem(recurring))

            delete_button = QPushButton("Delete")
            delete_button.setStyleSheet(f"background-color: {DARK_BLUE}; color: {WHITE}; padding: 5px; border-radius: 3px;")
            delete_button.clicked.connect(lambda _, rid=reminder_id: self.delete_reminder(rid))
            self.reminder_table.setCellWidget(row_idx, 3, delete_button)

    def check_reminders(self):
        now = datetime.datetime.now()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, datetime, note, recurring FROM reminders")
        reminders = cursor.fetchall()
        conn.close()

        for reminder_id, datetime_str, note, recurring in reminders:
            reminder_time = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            diff = (reminder_time - now).total_seconds()

            if 300 <= diff < 360:
                self.show_notification("Reminder in 5 minutes!", note)
            elif 900 <= diff < 960:
                self.show_notification("Reminder in 15 minutes!", note)

    def show_notification(self, title, message):
        QApplication.beep()
        self.setWindowState(Qt.WindowState.WindowActive)
        self.activateWindow()
        self.raise_()

        alert = QMessageBox(self)
        alert.setWindowTitle("Reminder Alert 🚀")
        alert.setText(f"{title}\n\n{message}")
        alert.setIcon(QMessageBox.Icon.Information)
        alert.setStandardButtons(QMessageBox.StandardButton.Ok)
        alert.exec()

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    window = ReminderApp()
    window.show()
    sys.exit(app.exec())
import sys
import sqlite3
import datetime
import time
import threading
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QDateTimeEdit, QTextEdit,
    QMessageBox, QSystemTrayIcon, QMenu, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from plyer import notification

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

class ReminderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reminder App")
        self.setGeometry(100, 100, 500, 500)

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

        self.reminder_table = QTableWidget(self)
        self.reminder_table.setColumnCount(4)
        self.reminder_table.setHorizontalHeaderLabels(["Date & Time", "Note", "Recurring", "Action"])
        self.reminder_table.setColumnWidth(0, 150)
        self.reminder_table.setColumnWidth(1, 200)
        self.reminder_table.setColumnWidth(2, 100)

        self.refresh_button = QPushButton("Refresh List", self)
        self.refresh_button.clicked.connect(self.load_reminders)

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

        # System Tray
        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_menu = QMenu(self)
        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.close)
        self.tray_menu.addAction(self.exit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

        self.load_reminders()
        self.start_reminder_checker()

    def add_reminder(self):
        datetime_value = self.datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        note = self.note_input.toPlainText()
        recurring = self.recurring_dropdown.currentText()

        if not note:
            QMessageBox.warning(self, "Warning", "Reminder note cannot be empty!")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reminders (datetime, note, recurring) VALUES (?, ?, ?)",
                       (datetime_value, note, recurring))
        conn.commit()
        conn.close()

        self.load_reminders()
        QMessageBox.information(self, "Success", "Reminder added successfully!")

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
            delete_button.clicked.connect(lambda _, rid=reminder_id: self.delete_reminder(rid))
            self.reminder_table.setCellWidget(row_idx, 3, delete_button)

    def delete_reminder(self, reminder_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()

        self.load_reminders()
        QMessageBox.information(self, "Deleted", "Reminder deleted successfully!")

    def start_reminder_checker(self):
        self.reminder_checker_thread = threading.Thread(target=self.check_reminders, daemon=True)
        self.reminder_checker_thread.start()

    def check_reminders(self):
        while True:
            now = datetime.datetime.now()
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT id, datetime, note, recurring FROM reminders")
            reminders = cursor.fetchall()
            conn.close()

            for reminder_id, datetime_str, note, recurring in reminders:
                reminder_time = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                diff = (reminder_time - now).total_seconds()

                if 300 <= diff < 315:  # 5 minutes before
                    self.show_notification(note, "Reminder in 5 minutes!")
                elif 900 <= diff < 915:  # 15 minutes before
                    self.show_notification(note, "Reminder in 15 minutes!")

                # Handle recurring reminders
                if diff < 0:  # Reminder time passed
                    if recurring == "Daily":
                        new_time = reminder_time + datetime.timedelta(days=1)
                    elif recurring == "Weekly":
                        new_time = reminder_time + datetime.timedelta(weeks=1)
                    elif recurring == "Monthly":
                        new_time = reminder_time.replace(month=(reminder_time.month % 12) + 1)
                    elif recurring == "Yearly":
                        new_time = reminder_time.replace(year=reminder_time.year + 1)
                    else:
                        continue

                    # Update reminder with new date
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE reminders SET datetime = ? WHERE id = ?", (new_time.strftime("%Y-%m-%d %H:%M:%S"), reminder_id))
                    conn.commit()
                    conn.close()

            time.sleep(60)

    def show_notification(self, title, message):
        notification.notify(
            title=title,
            message=message,
            app_name="Reminder App",
            timeout=10
        )

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    window = ReminderApp()
    window.show()
    sys.exit(app.exec())
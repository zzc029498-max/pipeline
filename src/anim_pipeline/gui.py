from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .models import Asset, Finding, Severity
from .service import PipelineService


class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class Task(QRunnable):
    def __init__(self, operation) -> None:
        super().__init__()
        self.operation = operation
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(self.operation())
        except Exception as exc:  # boundary: surface worker failures in the UI
            self.signals.failed.emit(str(exc))


class MainWindow(QMainWindow):
    COLORS = {Severity.ERROR: "#ff6b6b", Severity.WARNING: "#ffd166", Severity.INFO: "#70d6ff"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FrameForge · Asset Publisher")
        self.resize(820, 520)
        self.pool = QThreadPool.globalInstance()
        self.source = QLineEdit()
        self.project = QLineEdit("demo")
        self.kind = QLineEdit("asset")
        self.name = QLineEdit("dragon")
        self.root = QLineEdit(str(Path("published").resolve()))
        self.status = QLabel("Ready")
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Level", "Rule", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.validate_button = QPushButton("Validate")
        self.publish_button = QPushButton("Publish")
        self.publish_button.setEnabled(False)
        self._build_layout()
        self.validate_button.clicked.connect(self.validate)
        self.publish_button.clicked.connect(self.publish)

    def _build_layout(self) -> None:
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse)
        source_row = QHBoxLayout()
        source_row.addWidget(self.source)
        source_row.addWidget(browse)
        form = QFormLayout()
        form.addRow("Source folder", source_row)
        form.addRow("Project", self.project)
        form.addRow("Type", self.kind)
        form.addRow("Asset name", self.name)
        form.addRow("Publish root", self.root)
        actions = QHBoxLayout()
        actions.addWidget(self.status, 1)
        actions.addWidget(self.validate_button)
        actions.addWidget(self.publish_button)
        layout = QVBoxLayout()
        title = QLabel("FRAMEFORGE")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #70d6ff")
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.table, 1)
        layout.addLayout(actions)
        panel = QWidget()
        panel.setLayout(layout)
        self.setCentralWidget(panel)
        self.setStyleSheet("QWidget { background:#17202a; color:#eef2f3; } QLineEdit, QTableWidget { background:#22303c; padding:6px; } QPushButton { background:#386fa4; padding:8px 16px; border-radius:4px; }")

    def browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose asset source")
        if selected:
            self.source.setText(selected)

    def asset(self) -> Asset:
        return Asset(self.project.text(), self.kind.text(), self.name.text(), Path(self.source.text()))

    def run_task(self, operation, done) -> None:
        self.validate_button.setEnabled(False)
        self.publish_button.setEnabled(False)
        self.status.setText("Working…")
        task = Task(operation)
        task.signals.finished.connect(done)
        task.signals.failed.connect(self.failed)
        self.pool.start(task)

    def validate(self) -> None:
        asset = self.asset()
        service = PipelineService(Path(self.root.text()))
        self.run_task(lambda: service.inspect(asset), self.show_findings)

    def show_findings(self, findings: list[Finding]) -> None:
        self.table.setRowCount(len(findings))
        for row, finding in enumerate(findings):
            level = QTableWidgetItem(finding.severity.value.upper())
            level.setForeground(QColor(self.COLORS[finding.severity]))
            self.table.setItem(row, 0, level)
            self.table.setItem(row, 1, QTableWidgetItem(finding.rule))
            self.table.setItem(row, 2, QTableWidgetItem(finding.message))
        valid = all(f.severity != Severity.ERROR for f in findings)
        self.status.setText("Ready to publish" if valid else "Fix errors before publishing")
        self.validate_button.setEnabled(True)
        self.publish_button.setEnabled(valid)

    def publish(self) -> None:
        asset = self.asset()
        service = PipelineService(Path(self.root.text()))
        self.run_task(lambda: service.publish(asset), self.published)

    def published(self, result) -> None:
        self.validate_button.setEnabled(True)
        self.publish_button.setEnabled(True)
        self.status.setText(f"Published v{result.version:03d}")
        QMessageBox.information(self, "Published", f"Asset published to\n{result.directory}")

    def failed(self, message: str) -> None:
        self.validate_button.setEnabled(True)
        self.status.setText("Operation failed")
        QMessageBox.critical(self, "Error", message)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

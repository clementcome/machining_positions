from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QProgressBar,
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import sys
from machining_positions.process import main
from tqdm import tqdm


class TqdmSignal(QObject):
    update_progress = pyqtSignal(int)


def qt_tqdm_instance(signal: TqdmSignal) -> type(tqdm):
    class QtTqdm(tqdm):
        def update(self, n=1):
            super().update(n)
            signal.update_progress.emit(self.n / len(self) * 100)

    return QtTqdm


class Worker(QThread):
    finished = pyqtSignal()

    def __init__(self, input_path, output_folder, num_points, resolution, tqdm_signal):
        super().__init__()
        self.input_path = input_path
        self.output_folder = output_folder
        self.num_points = num_points
        self.resolution = resolution
        self.tqdm_signal = tqdm_signal

    def run(self):
        # Modify your main function to accept a tqdm instance
        main(
            self.input_path,
            self.output_folder,
            self.num_points,
            self.resolution,
            tqdm_instance=qt_tqdm_instance(self.tqdm_signal),
        )

        self.finished.emit()


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Input Path
        self.inputPathLabel = QLabel("Input SVG File:", self)
        layout.addWidget(self.inputPathLabel)

        self.inputPathEdit = QLineEdit(self)
        layout.addWidget(self.inputPathEdit)

        self.browseButton = QPushButton("Browse...", self)
        self.browseButton.clicked.connect(self.browseFile)
        layout.addWidget(self.browseButton)

        # Output Folder
        self.outputFolderLabel = QLabel("Output Folder:", self)
        layout.addWidget(self.outputFolderLabel)

        self.outputFolderEdit = QLineEdit(self)
        layout.addWidget(self.outputFolderEdit)

        self.browseFolderButton = QPushButton("Browse...", self)
        self.browseFolderButton.clicked.connect(self.browseFolder)
        layout.addWidget(self.browseFolderButton)

        # Num Points
        self.numPointsLabel = QLabel("Number of Points:", self)
        layout.addWidget(self.numPointsLabel)

        self.numPointsEdit = QLineEdit(self)
        layout.addWidget(self.numPointsEdit)

        # Resolution
        # TODO: Make it a float
        self.resolutionLabel = QLabel("Resolution:", self)
        layout.addWidget(self.resolutionLabel)

        self.resolutionEdit = QLineEdit(self)
        layout.addWidget(self.resolutionEdit)

        # Run Button
        self.runButton = QPushButton("Run", self)
        self.runButton.clicked.connect(self.runMain)
        layout.addWidget(self.runButton)

        self.setWindowTitle("SVG Machining Positions App")
        self.setGeometry(300, 300, 300, 150)

        # Progress Bar
        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)

        # Status Label
        self.statusLabel = QLabel("Status: Ready", self)
        layout.addWidget(self.statusLabel)

    def runMain(self):
        input_path = self.inputPathEdit.text()
        output_folder = self.outputFolderEdit.text()
        num_points = int(self.numPointsEdit.text())
        resolution = int(self.resolutionEdit.text())

        self.tqdm_signal = TqdmSignal()
        self.tqdm_signal.update_progress.connect(self.updateProgress)

        self.worker = Worker(input_path, output_folder, num_points, resolution, self.tqdm_signal)
        self.worker.finished.connect(self.onFinished)
        self.worker.start()

    def updateProgress(self, value):
        self.progressBar.setValue(value)

    def onFinished(self):
        self.statusLabel.setText("Status: Process Completed")

    def browseFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open file", "/home")
        if fname:
            self.inputPathEdit.setText(fname)

    def browseFolder(self):
        folder = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if folder:
            self.outputFolderEdit.setText(folder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())

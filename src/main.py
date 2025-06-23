import sys
from .gui import create_application, MainWindow


def main():
    app = create_application()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
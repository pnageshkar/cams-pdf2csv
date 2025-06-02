# CAMS CAS (CAMS + KFintech) PDF Statement Processor

A Python application to extract transaction data from CAMS (Computer Age Management Services) consolidated account statements in PDF format and convert it to CSV format.

## Features

- GUI interface built with CustomTkinter
- PDF password support
- Multi-threaded processing
- Extracts transaction details and generates the following:
  - Fund Name
  - Folio Number
  - Transaction Type
  - Date
  - Units
  - NAV
  - Amount
- Exports data to CSV format
- Generates unique filenames with timestamps

## Requirements

- Python 3.7+
- customtkinter
- pdfplumber
 

## Installation

1. Clone this repository
2. Create and activate a Python virtual environment:
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows cmd/ps
    ```
3. Install required packages:
```bash
pip install customtkinter pdfplumber
```

## Usage

1. Run the GUI application:
```bash
python gui_app.py
```

2. Use the interface to:
   - Browse and select your PDF statement
   - Enter password if the PDF is protected
   - Process the PDF
   - Get the resulting CSV file in the `generated_csvs` folder


## Building the Executable (using PyInstaller)

1.  Ensure all dependencies from `requirements.txt` are installed in your virtual environment.
2.  Install PyInstaller: `pip install pyinstaller`
3.  Run PyInstaller from the project root:
    ```bash
    pyinstaller --name "CAMS_Statement_Processor" --onefile --windowed --icon="app_icon.ico" gui_app.py 
    ```
    (Replace `app_icon.ico` if you have a different icon or omit if none.)
4.  The executable will be in the `dist/` folder.


## Note

This application is designed to work with CAMS (Computer Age Management Services) consolidated account statement (CAMS and Fintech) as on 02-Jun-2025. It may not work correctly with other PDF formats.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

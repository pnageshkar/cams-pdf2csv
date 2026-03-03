# CAMS CAS PDF Statement Processor

A Python application to extract mutual fund transaction data from **CAMS (Computer Age Management Services) Consolidated Account Statements (CAS)** in PDF format and convert it to CSV.

These statements are generated jointly by CAMS and KFintech and consolidate an investor's mutual fund holdings across multiple AMCs (Asset Management Companies).

## Features

- **GUI interface** built with CustomTkinter (dark theme)
- **PDF password support** for protected statements
- **Multi-threaded processing** (GUI remains responsive during extraction)
- **Robust ISIN extraction** using a three-layer strategy to handle PDF text garbling
- Extracts and exports the following fields per transaction:

| Column           | Description                                              |
|------------------|----------------------------------------------------------|
| Investor Name    | Full name of the investor (from PDF header)              |
| Folio Number     | The folio under which the fund is held                   |
| Fund Name        | Scheme code + fund name (e.g., `H02T-HDFC Flexi Cap...`)|
| ISIN             | 12-character ISIN code (e.g., `INF179K01UT0`)           |
| Transaction      | Description of the transaction                           |
| Transaction Type | `Purchase` or `Redemption` (derived from amount sign)    |
| Date             | Transaction date (`DD-Mon-YYYY`)                         |
| Units            | Number of units transacted                               |
| NAV              | Net Asset Value on the transaction date                  |
| Amount           | Transaction amount in INR (negative = redemption)        |

- Generates unique CSV filenames with timestamps
- Saves output to a `generated_csvs/` folder


## Architecture

The application has two main files:

```
cams_pdf2csv/
├── cams_parser.py    # Core PDF parsing + CSV conversion logic
├── gui_app.py        # CustomTkinter GUI wrapper
├── requirements.txt  # Python dependencies
└── generated_csvs/   # Output directory for CSV files
```

### `cams_parser.py` — Parser Module

The parser uses a **state-machine approach** to process the PDF line by line:

1. **Password Validation** — Uses pdfminer.six to validate the PDF password before full extraction.
2. **Pre-Scan (ISIN Lookup)** — Quick first pass over all pages to build a `{scheme_code: ISIN}` lookup table from lines where ISINs appear intact.
3. **Main Extraction Loop** — Iterates through each page/line:
   - Detects `Folio No:` lines → resets fund-level state
   - Detects fund name lines (scheme code pattern) → extracts fund name + ISIN
   - Detects transaction lines (date pattern) → extracts transaction data
   - Skips non-transaction lines using keyword matching
4. **ISIN Extraction (Three-Layer Strategy)**:
   - **Layer 1**: Extract from fund name line + look-ahead to complete partial ISINs split across lines
   - **Layer 2**: Search up to 5 subsequent lines for `ISIN:` patterns
   - **Layer 3**: Fall back to pre-scan lookup table
5. **Post-Processing** — Merges stamp duty into preceding transactions, removes STT rows, classifies transaction types.

### `gui_app.py` — GUI Application

A CustomTkinter-based desktop interface that:
- Lets users browse and select PDF files
- Accepts an optional password
- Runs the parser in a background thread
- Displays success/error status with colored messages
- Saves output CSV to `generated_csvs/` with a timestamped filename


## Requirements

- Python 3.7+
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — Modern Tkinter widgets
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction (includes pdfminer.six)


## Installation

1. Clone this repository:
   ```bash
   git clone <repo-url>
   cd cams_pdf2csv
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows cmd/PowerShell:
   .venv\Scripts\activate
   # On bash/macOS/Linux:
   source .venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
   Or manually:
   ```bash
   pip install customtkinter pdfplumber
   ```


## Usage

### GUI Mode (Recommended)

```bash
python gui_app.py
```

1. Click **Browse** to select your CAMS CAS PDF file
2. Enter the PDF password if it is protected
3. Click **Process PDF & Save CSV**
4. The CSV file will be saved in the `generated_csvs/` folder

### CLI Mode (for testing)

Edit the `pdf_file_path` variable at the bottom of `cams_parser.py`, then run:

```bash
python cams_parser.py
```

You will be prompted for the PDF password.


## Building the Executable (PyInstaller)

1. Ensure all dependencies are installed in your virtual environment
2. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
3. Build:
   ```bash
   pyinstaller --name "CAMS_Statement_Processor" --onefile --windowed --icon="app_icon.ico" gui_app.py
   ```
4. The executable will be in the `dist/` folder


## Known Limitations

- Designed specifically for **CAMS + KFintech CAS PDFs**. Other PDF formats (e.g., standalone AMC statements) are not supported.
- PDF text extraction via pdfplumber can produce garbled text due to multi-column layouts. The three-layer ISIN strategy handles most cases, but severely garbled pages may still result in incomplete data.
- The investor name extraction relies on a specific text pattern ("balances and valuation") found on page 1 of the CAS PDF.


## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

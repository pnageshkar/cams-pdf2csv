"""
cams_parser.py - A Python script to extract transaction data from CAMS consolidated account statements in PDF format.
This script uses the pdfplumber library to read PDF files, extract relevant transaction data, and convert it into a structured format suitable for CSV output.
"""

import re  # Regular expression operations library
import csv  # Library for working with CSV files (used by convert_to_csv_string)
from decimal import Decimal, InvalidOperation  # For precise decimal arithmetic
import io  # For handling in-memory text streams (used by convert_to_csv_string)
from typing import Optional  # Optional type hinting for better code clarity
import traceback  # For printing stack traces in case of exceptions
import pdfplumber  # Library for extracting text and information from PDF files
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument, PDFPasswordIncorrect
from pdfminer.pdfpage import PDFPage


# --- Helper Functions  ---


def is_pdf_password_valid(file_path: str, password: Optional[str]) -> Optional[bool]:
    """
    Checks if the provided password is valid for the given PDF file
    without fully parsing it with pdfplumber. Uses pdfminer.six directly.

    Args:
        file_path (str): The path to the PDF file.
        password (Optional[str]): The password to test. An empty string or None
                                   is typically used for unencrypted PDFs.

    Returns:
        Optional[bool]: True if the password is correct (or no password needed and none given),
                        False if the password is incorrect.
                        None if the file is not a valid PDF or another error occurs during check.
    """
    try:
        with open(file_path, "rb") as fs:
            parser = PDFParser(fs)
            doc = PDFDocument(parser, password=password or "")
            # Try accessing a page (forces password validation)
            # If the password is wrong, PDFPasswordIncorrect will be raised here.
            # We just need to try to get the first page generator.
            next(PDFPage.create_pages(doc))
            return True
    except PDFPasswordIncorrect:
        print("DEBUG: Incorrect password provided for PDF.")
        return False  # Password is incorrect

    except Exception as e:
        # If any other error, assume PDF is invalid or corrupted
        print(f"DEBUG: Exception while checking PDF password: {type(e).__name__}: {e}")
        return None  # Indicate an issue other than just a wrong password (e.g., invalid PDF)


def clean_numeric_value(value_str):
    """
    Cleans a string representation of a number and converts it to a Decimal object.
    Handles commas, parentheses for negative numbers, and placeholder strings like "--".

    Args:
        value_str (str or None): The string to clean and convert.

    Returns:
        Decimal or None: The cleaned number as a Decimal, or None if conversion is not possible.
    """
    if value_str is None:
        return None
    text = str(value_str).strip()
    if text == "" or text == "--":
        return None
    text = text.replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def remove_parenthetical_parts(text):
    """
    Removes parts of a string that are enclosed in parentheses, and specifically "(Non-Demat)".
    (No changes to this function's logic from the previous version you confirmed)
    """
    if text is None:
        return None
    # Remove main parenthetical parts
    text = re.sub(r"\s*\([^)]*\)", "", text)
    # Optionally, more specific removals if "(Non-Demat)" or other common ones persist
    text = text.replace("(Non-Demat)", "").strip()
    return text.strip()


# --- Core Extraction and Processing Function ---
def extract_transactions_from_pdf(
    pdf_path, pdf_password=""
):  # Default password to empty string
    """
    Main function to extract mutual fund transactions from a PDF statement.
    Now includes a pre-check for PDF password validity.

    """
    extracted_data_raw = []

    folio_regex = re.compile(r"^Folio No:\s*([\w/]+)")

    # Simplified Fund Name Regex: Captures scheme code and name.
    # It will match up to common delimiters or the end of the line if no delimiter is found early.
    # We are no longer strictly looking for " - ISIN:" as a mandatory part of the line.
    fund_name_regex = re.compile(
        # (?P<FundNameCode>[A-Z0-9]+-[A-Za-z0-9\s().'/,\-:&]+?)
        # The part `(?: ... |$)` makes the delimiters optional or end of line.
        r"^(?P<FundNameCode>[A-Z0-9]+-[A-Za-z0-9\s().'/,\-:&]+?)(?:\s*-\s*ISIN:|\s*\(formerly known as|\s*\(Non-Demat\)|$|\s*\(Advisor:)",
        re.IGNORECASE,
    )

    # Transaction regexes (remain the same)
    transaction_line_regex_full = re.compile(
        r"^(?P<Date>\d{2}-[A-Za-z]{3}-\d{4})\s+"
        r"(?P<Transaction>.+?)\s+"
        r"(?P<Amount>[\d,.-]+|\([\d,.-]+\)|--)\s+"
        r"(?P<Units>[\d,.-]+|\([\d,.-]+\)|--)\s+"
        r"(?P<NAV>[\d,.-]+|\([\d,.-]+\)|--)\s+"
        r"(?P<UnitBalance>[\d,.-]+|\([\d,.-]+\)|--)$"
    )
    transaction_line_regex_amount_only = re.compile(
        r"^(?P<Date>\d{2}-[A-Za-z]{3}-\d{4})\s+"
        r"(?P<Transaction>.+?)\s+"
        r"(?P<Amount>[\d,.-]+|\([\d,.-]+\)|--)$"
    )
    date_pattern_start = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}")
    scheme_code_start_pattern = re.compile(
        r"^[A-Z0-9]+-"
    )  # To identify potential fund name lines

    current_folio_number = None
    current_fund_name_raw = None  # Will store the matched fund name

    # Simplified state: -1: idle, 0: folio found, expecting fund name
    fund_name_detection_state = -1
    fund_name_buffer = []
    lines_since_folio_for_fund_name = 0

    # Check if the PDF password is valid before proceeding
    valid = is_pdf_password_valid(pdf_path, pdf_password)
    if valid is False:
        return None, "Incorrect password provided for PDF."
    elif valid is None:
        return None, "The selected file is not a valid PDF."

    try:
        # Open the PDF file with the provided password
        with pdfplumber.open(pdf_path, password=pdf_password) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text_content = page.extract_text(
                    x_tolerance=3, y_tolerance=3, layout=False, keep_blank_chars=True
                )
                if not text_content:
                    continue
                lines = text_content.split("\n")

                for i, raw_line_from_pdf in enumerate(lines):
                    line = raw_line_from_pdf.strip()
                    if not line:
                        continue

                    folio_match = folio_regex.match(line)
                    if folio_match:
                        current_folio_number = folio_match.group(1)
                        current_fund_name_raw = None  # Reset fund name
                        fund_name_buffer = []
                        fund_name_detection_state = 0  # Folio found, expect fund name
                        lines_since_folio_for_fund_name = 0
                        # print(f"DEBUG: Folio Found: {current_folio_number}. State: {fund_name_detection_state}")
                        continue

                    # --- Simplified Fund Name Detection ---
                    if (
                        fund_name_detection_state == 0
                        and current_folio_number
                        and not current_fund_name_raw
                    ):
                        lines_since_folio_for_fund_name += 1

                        # Expect fund name around 2 lines after "Folio No:"
                        if lines_since_folio_for_fund_name >= 2:
                            # If line starts with scheme code or we are already buffering
                            if (
                                scheme_code_start_pattern.match(line)
                                or fund_name_buffer
                            ):
                                fund_name_buffer.append(
                                    raw_line_from_pdf
                                )  # Buffer raw line

                                combined_buffered_line = " ".join(
                                    fund_name_buffer
                                ).strip()
                                fund_name_match = fund_name_regex.match(
                                    combined_buffered_line
                                )

                                if fund_name_match:
                                    current_fund_name_raw = fund_name_match.group(
                                        "FundNameCode"
                                    ).strip()
                                    # print(f"DEBUG: Fund Name Found: '{current_fund_name_raw}' from '{combined_buffered_line}'")
                                    fund_name_detection_state = (
                                        -1
                                    )  # Fund name found, reset state
                                    fund_name_buffer = []
                                    # Continue to process this line for transactions if it's a transaction line
                                    # Or move to next line if this line was purely for fund name
                                # else:
                                # print(f"DEBUG: Buffering fund name: '{combined_buffered_line}'")
                            # If the line doesn't look like a fund name start and buffer is empty,
                            # and we are past the typical fund name line, reset.
                            elif (
                                not fund_name_buffer
                                and lines_since_folio_for_fund_name > 3
                            ):
                                # print(f"DEBUG: Fund name not starting as expected for folio {current_folio_number}. Resetting state.")
                                fund_name_detection_state = -1

                        # Timeout for fund name buffering
                        if (
                            lines_since_folio_for_fund_name > 5
                            and fund_name_detection_state == 0
                        ):
                            # print(f"DEBUG: Fund name detection timed out for folio {current_folio_number}. Buffer: {' '.join(fund_name_buffer)}")
                            fund_name_detection_state = -1
                            fund_name_buffer = []

                        # If still looking for fund name (or just found it and reset state),
                        # and this line isn't a transaction, continue to gather more lines for fund name or move on.
                        if fund_name_detection_state == 0 or (
                            fund_name_detection_state == -1
                            and not date_pattern_start.match(line)
                        ):
                            continue

                    cleaned_fund_name_for_tx = remove_parenthetical_parts(
                        current_fund_name_raw
                    )

                    # Context check: Now only need folio and fund name
                    if not current_folio_number or not cleaned_fund_name_for_tx:
                        # print(f"DEBUG: Skipping line, no full context (Folio: {current_folio_number}, Fund: {cleaned_fund_name_for_tx}) Line: '{line}'")
                        continue

                    # Skip Keywords Logic (same as before)
                    skip_keywords = [
                        "our mission",
                        "consolidated account statement",
                        "email id:",
                        "phone res:",
                        "phone off:",
                        "mobile:",
                        "this consolidated account statement is brought to you",
                        "if you find any folios missing",
                        "this statement may not reflect the complete information",
                        "portfolio summary",
                        "cost value",
                        "closing unit balance:",
                        "nav on ",
                        "total cost value:",
                        "market value on ",
                        "entry load:",
                        "exit load:",
                        "important note -",
                        "wef ",
                        "gst identification number",
                        "kyc:",
                        "pan:",
                        "registrar:",
                        "nominee ",
                        "page ",
                        r"camscasws-\d+",
                        "date transaction amount units nav unit",
                        "total",
                    ]
                    line_lower = line.lower()
                    should_skip_line = False
                    if (
                        "*** no transactions during this statement period ***"
                        in line_lower
                    ):
                        should_skip_line = True
                    else:
                        for keyword in skip_keywords:
                            if re.search(
                                r"(?:^|\s)" + re.escape(keyword) + r"(?:$|\s)",
                                line_lower,
                                re.IGNORECASE,
                            ):
                                if keyword == "total" and not date_pattern_start.match(
                                    line
                                ):
                                    should_skip_line = True
                                    break
                                elif keyword != "total":
                                    should_skip_line = True
                                    break
                    if should_skip_line:
                        continue

                    # Transaction Line Detection (same as before)
                    if date_pattern_start.match(line):
                        tx_match_full = transaction_line_regex_full.match(line)
                        if tx_match_full:
                            data = tx_match_full.groupdict()
                            extracted_data_raw.append(
                                {
                                    # "ISIN": current_isin, # Removed ISIN
                                    "Fund Name": cleaned_fund_name_for_tx,
                                    "Folio Number": current_folio_number,
                                    "Date": data["Date"],
                                    "Transaction": data["Transaction"].strip(),
                                    "Amount": clean_numeric_value(data["Amount"]),
                                    "Units": clean_numeric_value(data["Units"]),
                                    "NAV": clean_numeric_value(data["NAV"]),
                                }
                            )
                            continue

                        tx_match_amount_only = transaction_line_regex_amount_only.match(
                            line
                        )
                        if tx_match_amount_only:
                            data = tx_match_amount_only.groupdict()
                            extracted_data_raw.append(
                                {
                                    # "ISIN": current_isin, # Removed ISIN
                                    "Fund Name": cleaned_fund_name_for_tx,
                                    "Folio Number": current_folio_number,
                                    "Date": data["Date"],
                                    "Transaction": data["Transaction"].strip(),
                                    "Amount": clean_numeric_value(data["Amount"]),
                                    "Units": None,
                                    "NAV": None,
                                }
                            )
                            continue

    except Exception as e:
        # print("Error during PDF processing:")  # Keep this for server-side logging
        print(f"CAUGHT GENERIC EXCEPTION: Type: {type(e)}, Message: {str(e)}")
        traceback.print_exc()
        return [], f"An unexpected error occurred during PDF processing: {str(e)}"

    # --- Post-processing (same as before) ---
    processed_data_for_csv = []
    if not extracted_data_raw:
        return [], "No transaction data extracted from PDF."

    i = 0
    while i < len(extracted_data_raw):
        current_row = extracted_data_raw[i]
        if current_row["Transaction"] == "*** Stamp Duty ***":
            if current_row["Amount"] is not None and processed_data_for_csv:
                if processed_data_for_csv[-1]["Amount"] is None:
                    processed_data_for_csv[-1]["Amount"] = Decimal("0")
                processed_data_for_csv[-1]["Amount"] += current_row["Amount"]
            i += 1
            continue
        if current_row["Transaction"] == "*** STT Paid ***":
            i += 1
            continue
        transaction_type = ""
        if current_row["Amount"] is not None:
            if current_row["Amount"] > 0:
                transaction_type = "Purchase"
            elif current_row["Amount"] < 0:
                transaction_type = "Redemption"
        current_row["Transaction Type"] = transaction_type
        processed_data_for_csv.append(current_row)
        i += 1

    if not processed_data_for_csv:
        return [], "No transaction data to write to CSV after processing."

    return processed_data_for_csv, "Success"


# --- Helper function to convert data to CSV string ---
def convert_to_csv_string(data_list):
    """
    Converts a list of dictionaries to a CSV string.
    Args:
        data_list (list): List of dictionaries containing transaction data.
    Returns:
        str: CSV formatted string of the data.
    """

    if not data_list:
        return ""
    output = io.StringIO()
    # Define the fieldnames for the CSV
    # Ensure the fieldnames match the keys in the data_list dictionaries
    fieldnames = [
        "Fund Name",
        "Folio Number",
        "Transaction",
        "Transaction Type",
        "Date",
        "Units",
        "NAV",
        "Amount",
    ]
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", restval=""
    )
    writer.writeheader()
    writer.writerows(data_list)
    return output.getvalue()


# --- Example Usage (if running this file directly for testing) ---
if __name__ == "__main__":
    import getpass
    import os
    from datetime import datetime  # Import datetime module

    pdf_file_path = (
        "your_statement.pdf"  # Placeholder: Replace with actual PDF file path.
    )

    if not os.path.exists(pdf_file_path):
        print(f"Error: PDF file not found at '{pdf_file_path}'. Please check the path.")
    else:
        statement_password = getpass.getpass(
            prompt=f"Enter password for '{os.path.basename(pdf_file_path)}' (leave blank if none): "
        )
        if not statement_password:
            statement_password = ""

        processed_data, status_message = extract_transactions_from_pdf(
            pdf_file_path, statement_password
        )

        print(f"\nStatus: {status_message}")

        if status_message == "Success" and processed_data:
            csv_string_content = convert_to_csv_string(processed_data)
            if csv_string_content:
                # --- Generate unique CSV filename with timestamp ---
                now = datetime.now()
                # Format: ddmmyyyy_hr_min_sec
                timestamp_str = now.strftime("%d%m%Y_%H_%M_%S")
                csv_output_filename = f"cams_consolidated_{timestamp_str}.csv"
                # --- End of filename generation ---

                try:
                    with open(
                        csv_output_filename, "w", encoding="utf-8", newline=""
                    ) as f:
                        f.write(csv_string_content)
                    print(f"Data successfully saved to {csv_output_filename}")
                except IOError as e:
                    print(f"Error writing to CSV file '{csv_output_filename}': {e}")
            else:
                print("\nNo data to generate CSV string.")

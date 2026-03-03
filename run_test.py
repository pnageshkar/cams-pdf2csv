import sys
import getpass
from cams_parser import extract_transactions_from_pdf, convert_to_csv_string


def run_test():
    pdf_path = "CAS_0226.pdf"
    password = sys.argv[1] if len(sys.argv) > 1 else ""

    # We will modify cams_parser.py first, then run this.
    data, msg = extract_transactions_from_pdf(pdf_path, password)
    print(msg)
    if data:
        print(f"Extracted {len(data)} transactions")
        print("First 2 data items:")
        for i in range(min(2, len(data))):
            print(data[i])


if __name__ == "__main__":
    run_test()

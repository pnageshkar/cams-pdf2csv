import os
import time
import requests

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
CACHE_FILE = "amfi_nav_cache.txt"
CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours


def fetch_amfi_data():
    """
    Fetch AMFI NAV data. Uses a local cache file if it exists and is less
    than 24 hours old. Otherwise, downloads a fresh copy from AMFI.

    Returns:
        str: The raw text content of the AMFI file.
    """
    needs_download = True

    if os.path.exists(CACHE_FILE):
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age < CACHE_EXPIRY_SECONDS:
            needs_download = False

    if needs_download:
        try:
            print("Downloading fresh AMFI NAV data...")
            response = requests.get(AMFI_URL, timeout=15)
            response.raise_for_status()
            text_content = response.text

            # Save to cache
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(text_content)

            return text_content
        except requests.RequestException as e:
            print(f"Warning: Failed to download AMFI data: {e}")
            # Fall back to stale cache if download fails but we have "some" cache
            if os.path.exists(CACHE_FILE):
                print("Falling back to cached AMFI data.")
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            return ""

    else:
        # Read from cache
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read()


def get_isin_lookup_dictionary():
    """
    Parses the AMFI data into a dictionary keyed by the 12-character ISIN code.
    If a row contains multiple ISIN codes (e.g. physical and demat forms),
    they are split so each ISIN is an individual key pointing to the same data.

    Returns:
        dict: A dictionary mapping ISIN standard codes (e.g., "INF...") to a
              dictionary of scheme details.
    """
    raw_text = fetch_amfi_data()
    lookup = {}

    if not raw_text:
        return lookup

    lines = raw_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        # Skip empty lines, headers, and section labels (which have no semicolons)
        if not line or ";" not in line or line.startswith("Scheme Code"):
            continue

        parts = line.split(";")
        # A valid data row should have exactly 6 columns:
        # Scheme Code; ISIN Div Payout/ISIN Growth; ISIN Div Reinvestment; Scheme Name; Net Asset Value; Date
        if len(parts) == 6:
            scheme_code = parts[0].strip()
            isin_col1 = parts[1].strip()
            isin_col2 = parts[2].strip()
            scheme_name = parts[3].strip()
            nav = parts[4].strip()
            date = parts[5].strip()

            fund_details = {
                "scheme_code": scheme_code,
                "scheme_name": scheme_name,
                "nav": nav,
                "date": date,
            }

            # Sometimes an AMFI column can hold multiple comma/space separated ISINs
            for isin_col in (isin_col1, isin_col2):
                if isin_col and isin_col != "-":
                    # Split by comma (and optionally clean up spaces)
                    individual_isins = [
                        code.strip() for code in isin_col.replace(" ", ",").split(",")
                    ]
                    for isin in individual_isins:
                        if len(isin) >= 12 and isin.startswith("INF"):
                            # Take exactly 12 chars to be safe
                            clean_isin = isin[:12]
                            lookup[clean_isin] = fund_details

    return lookup


# Standalone test to verify the lookup module works
if __name__ == "__main__":
    start = time.time()
    lookup = get_isin_lookup_dictionary()
    print(f"Loaded {len(lookup)} unique ISINs in {time.time() - start:.2f} seconds.")

    # Test a few known ISINs from earlier
    test_isins = ["INF179K01XZ1", "INF179KB1HU9", "INF109K011O5"]
    for isin in test_isins:
        if isin in lookup:
            print(f"{isin} -> {lookup[isin]['scheme_name']}")
        else:
            print(f"{isin} -> NOT FOUND")

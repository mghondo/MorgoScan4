import warnings
import logging
from OriginatingEntity import process_pdf
from Drivers import extract_driver_names_with_camelot, extract_driver_names_with_pdfplumber, extract_driver_names_with_ocr
from MNumber import extract_m_numbers

# Suppress CropBox warnings from pdfplumber
class CropBoxWarningFilter(logging.Filter):
    def filter(self, record):
        return "CropBox missing from /Page, defaulting to MediaBox" not in record.getMessage()

logging.getLogger().addFilter(CropBoxWarningFilter())

# Suppress other warnings (e.g., CryptographyDeprecationWarning)
warnings.filterwarnings("ignore")

def main():
    # Define the PDF file path
    pdf_file = "Appalachian Pharm Processing, LLC.pdf"

    # Check if the PDF exists
    import os
    if not os.path.exists(pdf_file):
        print(f"PDF file not found: {pdf_file}")
        return

    # 1. Run OriginatingEntity.py
    print("\n=== Originating Entity ===")
    company_result = process_pdf(pdf_file)
    print(f"Company: {company_result}")

    # 2. Run Drivers.py
    print("\n=== Driver Names ===")
    driver_names = []

    # Camelot extraction
    camelot_driver_names = extract_driver_names_with_camelot(pdf_file)
    driver_names.extend(camelot_driver_names)

    # pdfplumber extraction
    pdfplumber_driver_names = extract_driver_names_with_pdfplumber(pdf_file)
    driver_names.extend(pdfplumber_driver_names)

    # OCR extraction
    for page_num in [0, 1]:
        ocr_driver_names = extract_driver_names_with_ocr(pdf_file, page_number=page_num)
        driver_names.extend(ocr_driver_names)

    # Remove duplicates
    unique_driver_names = list(dict.fromkeys(driver_names))
    if unique_driver_names:
        for i, name in enumerate(unique_driver_names, 1):
            print(f"Driver {i}: {name}")
    else:
        print("No driver names found in the PDF")

    # 3. Run MNumber.py
    print("\n=== M Numbers ===")
    m_numbers = extract_m_numbers(pdf_file)
    if m_numbers:
        formatted_output = []
        for entry in m_numbers:
            index = entry["Index"]
            name = entry["Name"]
            m_number = entry["M_Number"]
            package_id = entry["Package_ID"]
            item_details = entry["Item_Details"]
            formatted_entry = (
                f"{index}.)\n"
                f"    Name: {name}\n"
                f"    M Number: {m_number}\n"
                f"    Package ID: {package_id}\n"
                f"    Item Details: {item_details}\n"
            )
            formatted_output.append(formatted_entry)
            print(formatted_entry)

        # Save formatted output to a text file
        with open("m_numbers_formatted.txt", "w") as f:
            f.write("Extracted M Numbers:\n\n")
            f.write("\n".join(formatted_output))

        # Save to CSV and JSON
        import pandas as pd
        m_numbers_df = pd.DataFrame(m_numbers)
        m_numbers_df.to_csv("m_numbers.csv", index=False)
        m_numbers_df.to_json("m_numbers.json", orient="records", indent=4)
        print("M Numbers saved to m_numbers.csv, m_numbers.json, and m_numbers_formatted.txt")
    else:
        print("No M Numbers found in the PDF")

if __name__ == "__main__":
    main()
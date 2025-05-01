import warnings
import logging
from OriginatingEntity import process_pdf
from Drivers import extract_driver_names_with_camelot, extract_driver_names_with_pdfplumber, extract_driver_names_with_ocr
from MNumber import extract_m_numbers
import os
import pandas as pd

# Suppress CropBox warnings from pdfplumber
class CropBoxWarningFilter(logging.Filter):
    def filter(self, record):
        return "CropBox missing from /Page, defaulting to MediaBox" not in record.getMessage()

logging.getLogger().addFilter(CropBoxWarningFilter())

# Suppress other warnings (e.g., CryptographyDeprecationWarning)
warnings.filterwarnings("ignore")

def extract_data(pdf_file):
    """
    Extract data from the PDF using OriginatingEntity, Drivers, and MNumber scripts.
    Args:
        pdf_file (str): Path to the PDF file.
    Returns:
        dict: Extracted data structured for API response.
    """
    result = {
        "originating_entity": {},
        "drivers": {},
        "m_numbers": {}
    }

    # Check if the PDF exists
    if not os.path.exists(pdf_file):
        result["error"] = f"PDF file not found: {pdf_file}"
        return result

    # 1. Originating Entity
    filename, company_result = process_pdf(pdf_file)
    result["originating_entity"] = {
        "filename": filename,
        "company": company_result
    }

    # 2. Driver Names
    driver_names = []
    filename, camelot_driver_names = extract_driver_names_with_camelot(pdf_file)
    driver_names.extend(camelot_driver_names)
    filename, pdfplumber_driver_names = extract_driver_names_with_pdfplumber(pdf_file)
    driver_names.extend(pdfplumber_driver_names)
    for page_num in [0, 1]:
        filename, ocr_driver_names = extract_driver_names_with_ocr(pdf_file, page_number=page_num)
        driver_names.extend(ocr_driver_names)
    unique_driver_names = list(dict.fromkeys(driver_names))
    result["drivers"] = {
        "filename": filename,
        "driver_names": unique_driver_names
    }

    # 3. M Numbers
    filename, m_numbers = extract_m_numbers(pdf_file)
    result["m_numbers"] = {
        "filename": filename,
        "m_numbers": m_numbers
    }

    return result

def print_data(data):
    """Print extracted data to terminal for debugging."""
    if "error" in data:
        print(data["error"])
        return

    # Originating Entity
    print("\n=== Originating Entity ===")
    print(f"File: {data['originating_entity']['filename']}")
    print(f"Company: {data['originating_entity']['company']}")

    # Driver Names
    print("\n=== Driver Names ===")
    print(f"File: {data['drivers']['filename']}")
    if data["drivers"]["driver_names"]:
        for i, name in enumerate(data["drivers"]["driver_names"], 1):
            print(f"Driver {i}: {name}")
    else:
        print("No driver names found in the PDF")

    # M Numbers
    print("\n=== M Numbers ===")
    print(f"File: {data['m_numbers']['filename']}")
    if data["m_numbers"]["m_numbers"]:
        formatted_output = []
        for entry in data["m_numbers"]["m_numbers"]:
            index = entry["Index"]
            name = entry["Name"]
            strain = entry["Strain"]
            days = entry["Days"]
            weight = entry["Weight"]
            category = entry["Category"]
            m_number = entry["M_Number"]
            package_id = entry["Package_ID"]
            item_details = entry["Item_Details"]
            formatted_entry = (
                f"{index}.)\n"
                f"    Name: {name}\n"
                f"    Strain: {strain}\n"
                f"    Days: {days}\n"
                f"    Weight: {weight}\n"
                f"    Category: {category}\n"
                f"    M Number: {m_number}\n"
                f"    Package ID: {package_id}\n"
                f"    Item Details: {item_details}\n"
            )
            formatted_output.append(formatted_entry)
            print(formatted_entry)

        with open("m_numbers_formatted.txt", "w") as f:
            f.write("Extracted M Numbers:\n\n")
            f.write("\n".join(formatted_output))

        m_numbers_df = pd.DataFrame(data["m_numbers"]["m_numbers"])
        m_numbers_df.to_csv("m_numbers.csv", index=False)
        m_numbers_df.to_json("m_numbers.json", orient="records", indent=4)
        print("M Numbers saved to m_numbers.csv, m_numbers.json, and m_numbers_formatted.txt")
    else:
        print("No M Numbers found in the PDF")

if __name__ == "__main__":
    # Run extraction and print to terminal
    pdf_file = "PurposLeafLLC.pdf"
    data = extract_data(pdf_file)
    print_data(data)
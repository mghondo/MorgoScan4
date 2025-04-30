import pdfplumber
import re
import pandas as pd
import logging

# Set up logging
logging.basicConfig(filename="m_numbers_extraction.log", level=logging.INFO)
logging.info("Starting M Number extraction")


def extract_m_numbers(pdf_path):
    """
    Extract M Numbers, Package IDs, Item Details, and Names from a METRC PDF.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        list: List of dictionaries containing M Numbers, Package IDs, Item Details, and Names.
    """
    m_numbers = []
    package_count = 0
    seen_m_numbers = set()  # To avoid duplicate M Numbers

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Step 1: Find the page where the package table starts
            table_start_page = None
            for page in pdf.pages:
                text = page.extract_text()
                if re.search(r"PACKAGE\s*[|]\s*SHIPPED", text, re.IGNORECASE):
                    table_start_page = page.page_number
                    logging.info(f"Found package table header on page {table_start_page}")
                    break

            # Fallback: If header not found, assume tables start on page 2
            if table_start_page is None:
                table_start_page = 2
                logging.warning("Package table header not found; assuming tables start on page 2")

            # Step 2: Concatenate raw text from table_start_page to second-to-last page (exclude receipt)
            full_text = ""
            for page in pdf.pages[table_start_page - 1:-1]:  # 0-based index
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    logging.debug(f"Page {page.page_number} Raw Text:\n{text}\n{'-' * 50}")

            # Step 3: Split the full text into package blocks
            # Each block starts with "X. Package | Shipped" and ends before the next package or at "Source Production Batch"
            package_blocks = re.split(r"(?=\d+\.\s*Package\s*[|]\s*Shipped)", full_text)

            # Step 4: Process each package block
            for block in package_blocks:
                if not block.strip():
                    continue
                package_count += 1
                logging.debug(f"Package {package_count} Block:\n{block}\n{'-' * 50}")

                # Extract Package ID
                # package_id_match = re.search(r"1A\d{21}", block)
                package_id_match = re.search(r"1A\d{19,30}", block)
                package_id = package_id_match.group(0) if package_id_match else "Unknown"
                logging.debug(f"Package {package_count}, Package ID: {package_id}")

                # Extract M Number from Item Name
                m_number_match = re.search(r"M\d{11}", block)
                if not m_number_match:
                    logging.warning(f"No M Number found for package {package_count}")
                    continue
                m_number = m_number_match.group(0)
                logging.info(f"Extracted M Number: {m_number}, Length: {len(m_number)}")

                # Skip if M Number already seen
                if m_number in seen_m_numbers:
                    logging.warning(f"Duplicate M Number skipped: {m_number}")
                    continue
                seen_m_numbers.add(m_number)

                # Extract Item Details
                item_details_match = re.search(r"Item Details\s*(.*?)(?=\nSource\s*(Harvest|Package)|$)", block,
                                               re.DOTALL)
                item_details = "Not Found"
                if item_details_match:
                    item_details = item_details_match.group(1).strip()
                    logging.info(f"Found Item Details for package {package_count}: {item_details}")
                else:
                    logging.warning(f"Item Details not found for package {package_count}")

                # Extract Name from Item Details
                name = "Not Found"
                if item_details and item_details != "Not Found":
                    name_match = re.match(r"(?:Brand|Strain):\s*([^|]+)", item_details)
                    if name_match:
                        name = name_match.group(1).strip()
                        logging.info(f"Extracted Name for package {package_count}: {name}")
                    else:
                        logging.warning(f"Name not found for package {package_count} in Item Details: {item_details}")

                # Add to the list
                m_numbers.append({
                    "Index": len(m_numbers) + 1,
                    "Name": name,
                    "M_Number": str(m_number),
                    "Package_ID": package_id,
                    "Item_Details": item_details
                })
                logging.info(
                    f"Found M Number: {m_number}, Package ID: {package_id}, Name: {name}, Item Details: {item_details}")

    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {e}")
        print(f"Error processing {pdf_path}: {e}")

    logging.info(f"Total packages processed: {package_count}")
    logging.info(f"Total M Numbers extracted: {len(m_numbers)}")

    return m_numbers


def process_multiple_pdfs(pdf_paths):
    """
    Process multiple PDFs and combine M Numbers.
    Args:
        pdf_paths (list): List of PDF file paths.
    Returns:
        pd.DataFrame: DataFrame of Names, M Numbers, Package IDs, and Item Details.
    """
    all_m_numbers = []

    for pdf_path in pdf_paths:
        logging.info(f"Processing {pdf_path}")
        m_numbers = extract_m_numbers(pdf_path)
        all_m_numbers.extend(m_numbers)

    # Convert to DataFrame
    df = pd.DataFrame(all_m_numbers)
    return df


# Example usage
# pdf_paths = ["/Users/morganhondros/PycharmProjects/MorgoScan4/One Orijin, LLC.pdf"]
pdf_paths = ["/Users/morganhondros/PycharmProjects/MorgoScan4/Standard Wellness Company, LLC.pdf"]
m_numbers_df = process_multiple_pdfs(pdf_paths)

# Custom formatted output
print("Extracted M Numbers:")
formatted_output = []
for _, row in m_numbers_df.iterrows():
    index = row["Index"]
    name = row["Name"]
    m_number = row["M_Number"]
    package_id = row["Package_ID"]
    item_details = row["Item_Details"]
    logging.info(f"Output M Number: {m_number}, Length: {len(m_number)}")
    entry = f"{index}.)\n    Name: {name}\n    M Number: {m_number}\n    Package ID: {package_id}\n    Item Details: {item_details}\n"
    formatted_output.append(entry)
    print(entry)

# Save formatted output to a text file
with open("m_numbers_formatted.txt", "w") as f:
    f.write("Extracted M Numbers:\n\n")
    f.write("\n".join(formatted_output))
logging.info("Formatted M Numbers saved to m_numbers_formatted.txt")

# Save to CSV without pandas index
m_numbers_df.to_csv("m_numbers.csv", index=False)
logging.info("M Numbers saved to m_numbers.csv")

# Save to JSON
m_numbers_df.to_json("m_numbers.json", orient="records", indent=4)
logging.info("M Numbers saved to m_numbers.json")
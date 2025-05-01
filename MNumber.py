import pdfplumber
import re
import logging
import os

# Set up logging
logging.basicConfig(filename="m_numbers_extraction.log", level=logging.INFO)

def extract_m_numbers(pdf_path):
    """
    Extract M Numbers, Package IDs, Item Details, Names, Strains, Days, Weight, and Category from a METRC PDF.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        tuple: (filename, list of dictionaries containing M Numbers, Package IDs, Item Details, Names, Strains, Days, Weight, and Category).
    """
    filename = os.path.basename(pdf_path)
    m_numbers = []
    package_count = 0
    seen_m_numbers = set()

    # Valid weights for Category = Flower
    valid_weights = {"2.83", "5.66", "14.13", "8.49", "11.32", "14.15"}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Step 1: Find the page where the package table starts
            table_start_page = None
            for page in pdf.pages:
                text = page.extract_text()
                if text and re.search(r"PACKAGE\s*[|]?\s*SHIPPED", text, re.IGNORECASE):
                    table_start_page = page.page_number
                    logging.info(f"Found package table header on page {table_start_page}")
                    break

            # Fallback: Start from page 1 if header not found
            if table_start_page is None:
                table_start_page = 1
                logging.warning("Package table header not found; starting from page 1")

            # Step 2: Concatenate raw text from table_start_page to last page
            full_text = ""
            for page in pdf.pages[table_start_page - 1:]:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    logging.debug(f"Page {page.page_number} Raw Text:\n{text}\n{'-' * 50}")

            # Step 3: Split the full text into package blocks
            package_blocks = re.split(r"(?=\d+\.\s*Package\s*[|]?\s*Shipped)", full_text, flags=re.IGNORECASE)
            logging.info(f"Found {len(package_blocks)} package blocks")

            # Step 4: Process each package block
            for block in package_blocks:
                if not block.strip():
                    continue
                package_count += 1
                logging.debug(f"Package {package_count} Block:\n{block}\n{'-' * 50}")

                try:
                    # Extract Package ID
                    package_id_match = re.search(r"1A\d{19,30}", block)
                    package_id = package_id_match.group(0) if package_id_match else "Unknown"
                    logging.debug(f"Package {package_count}, Package ID: {package_id}")

                    # Extract M Number
                    m_number_match = re.search(r"M\d{11}", block)
                    if not m_number_match:
                        logging.warning(f"No M Number found for package {package_count}")
                        continue
                    m_number = m_number_match.group(0)
                    logging.info(f"Extracted M Number: {m_number}, Length: {len(m_number)}")

                    if m_number in seen_m_numbers:
                        logging.warning(f"Duplicate M Number skipped: {m_number}")
                        continue
                    seen_m_numbers.add(m_number)

                    # Extract Item Details
                    item_details_match = re.search(r"Item Details\s*(.*?)(?=\nSource\s*(Harvest|Package)|$|\n\d+\.\s*Package\s*[|]?\s*Shipped)", block, re.DOTALL | re.IGNORECASE)
                    item_details = "Not Found"
                    if item_details_match:
                        item_details = item_details_match.group(1).strip()
                        logging.info(f"Found Item Details for package {package_count}: {item_details}")
                    else:
                        logging.warning(f"Item Details not found for package {package_count}")

                    name = "Not Found"
                    strain = "Not Specified"
                    days = "Not Specified"
                    weight = "Not Specified"
                    category = "Unspecified"
                    if item_details and item_details != "Not Found":
                        # Extract Name
                        name_match = re.match(r"(?:Brand|Strain):\s*([^|]+)", item_details)
                        if name_match:
                            name = name_match.group(1).strip()
                            logging.info(f"Extracted Name for package {package_count}: {name}")
                        else:
                            logging.warning(f"Name not found for package {package_count} in Item Details: {item_details}")

                        # Extract Strain
                        item_details_lower = item_details.lower()
                        if "indica" in item_details_lower:
                            strain = "Indica"
                        elif "sativa" in item_details_lower:
                            strain = "Sativa"
                        elif "hybrid" in item_details_lower:
                            strain = "Hybrid"
                        logging.info(f"Extracted Strain for package {package_count}: {strain}")

                        # Extract Days
                        days_match = re.search(r"Supply:\s*(\d+)\s*day\(s\)", item_details, re.IGNORECASE)
                        if days_match:
                            days = days_match.group(1)
                            logging.info(f"Extracted Days for package {package_count}: {days}")
                        else:
                            logging.warning(f"Days not found for package {package_count} in Item Details: {item_details}")

                        # Extract Weight and Category
                        weight_match = re.search(r"Wgt:\s*([^|]+)", item_details, re.IGNORECASE)
                        if weight_match:
                            weight_value = weight_match.group(1).strip()
                            # Extract numeric part for comparison (e.g., "2.83 g" -> "2.83")
                            numeric_weight = re.match(r"(\d+\.\d+)", weight_value)
                            if numeric_weight and numeric_weight.group(1) in valid_weights:
                                weight = weight_value
                                category = "Flower"
                                logging.info(f"Extracted Weight for package {package_count}: {weight}, Category: {category}")
                            else:
                                # Fall back to Qty:
                                qty_match = re.search(r"Qty:\s*([^|]+)", item_details, re.IGNORECASE)
                                weight = qty_match.group(1).strip() if qty_match else "Not Specified"
                                category = "Unspecified"
                                logging.info(f"Extracted Weight from Qty for package {package_count}: {weight}, Category: {category}")
                        else:
                            # No Wgt:, try Qty:
                            qty_match = re.search(r"Qty:\s*([^|]+)", item_details, re.IGNORECASE)
                            weight = qty_match.group(1).strip() if qty_match else "Not Specified"
                            category = "Unspecified"
                            logging.info(f"Extracted Weight from Qty or not found for package {package_count}: {weight}, Category: {category}")

                    m_numbers.append({
                        "Index": len(m_numbers) + 1,
                        "Name": name,
                        "Strain": strain,
                        "Days": days,
                        "Weight": weight,
                        "Category": category,
                        "M_Number": str(m_number),
                        "Package_ID": package_id,
                        "Item_Details": item_details
                    })
                    logging.info(
                        f"Found M Number: {m_number}, Package ID: {package_id}, Name: {name}, Strain: {strain}, Days: {days}, Weight: {weight}, Category: {category}, Item Details: {item_details}")

                except Exception as e:
                    logging.error(f"Error processing package {package_count}: {e}")
                    continue

    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {e}")

    logging.info(f"Total packages processed: {package_count}")
    logging.info(f"Total M Numbers extracted: {len(m_numbers)}")

    return (filename, m_numbers)
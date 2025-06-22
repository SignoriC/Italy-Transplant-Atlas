###
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import pandas as pd
import time
import os

# Button XPaths pattern
path_sx = "//button[normalize-space()='"
path_dx = "']"

def reset_main_page(driver, main_url="https://trapianti.sanita.it/statistiche/trapianti_per_anno.aspx"):
    """Reload the main year-organ table page to reset navigation."""
    driver.get(main_url)
    time.sleep(1.5)  # allow a moment for loading

    
def scrape_year(driver, year: str, organ: str):
    """Scrapes transplant data per center for a given year and organ."""
    wait = WebDriverWait(driver, 10)
    
    try:
        # Navigate through year → organ → Regione
        wait.until(EC.element_to_be_clickable((By.XPATH, path_sx + year + path_dx))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, path_sx + organ + path_dx))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, path_sx + 'Regione' + path_dx))).click()

        # Collect headers from the detailed center table
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//th")))
        headers = driver.find_elements(By.XPATH, "//th")
        header_labels = [h.text.strip() for h in headers if h.text.strip()]

        # Collect data rows
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tr")))
        rows_elements = driver.find_elements(By.XPATH, "//tr")
        data_rows = []

        for row in rows_elements[1:]:  # skip header row
            try:
                cells = row.find_elements(By.XPATH, ".//td")
                row_data = [cell.text.strip() for cell in cells]
                if row_data:
                    data_rows.append(row_data)
            except StaleElementReferenceException:
                continue

        # Return to the main table
        back_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="primo_link"]/a[2]')))
        back_btn.click()

        return header_labels, data_rows

    except TimeoutException as e:
        print(f"[Timeout] {year}-{organ}: {e}")
        return [], []

    except Exception as e:
        print(f"[Error] {year}-{organ}: {e}")
        return [], []


def save_each_organ_table_for_year(driver, year: str, organs: list, output_folder: str):
    """
    Scrapes and saves transplant tables for each organ in a year to separate CSV files.

    Args:
        driver: Selenium WebDriver instance
        year (str): The year to scrape
        organs (list): List of organ names (e.g. ['Cuore', 'Rene'])
        output_folder (str): Path to save CSV files (e.g. 'data/2024')
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    for organ in organs:
        print(f"🔄 Scraping {organ} data for {year}...")

        reset_main_page(driver)
        time.sleep(1)

        headers, rows = scrape_year(driver, year, organ)

        if not rows or not headers:
            print(f"⚠️ Skipping {organ} due to missing data.")
            continue

        # Clean and prepare header (skip title row)
        table_headers = [h for h in headers if h.strip()][1:]

        # Pad or truncate rows to match header length
        cleaned_rows = []
        for row in rows:
            row = row[:len(table_headers)]
            while len(row) < len(table_headers):
                row.append("")
            cleaned_rows.append(row)

        # Create DataFrame and save to CSV
        df = pd.DataFrame(cleaned_rows, columns=table_headers)
        filename = f"{year}_{organ}.csv".replace(" ", "_")
        filepath = f"{output_folder}/{filename}"

        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"✅ Saved: {filepath}")
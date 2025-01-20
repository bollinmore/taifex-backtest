import requests
from bs4 import BeautifulSoup
import zipfile
import os

class TaifexDownloader:
    def __init__(self, url):
        self.url = url
        self.download_folder = "download"
        os.makedirs(self.download_folder, exist_ok=True)

    def fetch_webpage(self):
        print(f"Fetching webpage content from {self.url}")
        try:
            response = requests.get(self.url, timeout=10)  # Adding a timeout to prevent hanging
            print("Webpage content fetched successfully.")
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching webpage content: {e}")
            return None

    def parse_html(self, html_content):
        print("Parsing the HTML content.")
        return BeautifulSoup(html_content, 'html.parser')

    def find_target_table(self, soup):
        print("Searching for the table with required headers.")
        tables = soup.find_all('table')
        required_headers = ["時間", "日期", "下載(*.rpt)", "下載(*.csv)"]

        for table_index, table in enumerate(tables):
            print(f"Checking table {table_index + 1}.")
            header = table.find('tr')
            if not header:
                print(f"Table {table_index + 1} has no header, skipping.")
                continue

            headers = [th.get_text(strip=True) for th in header.find_all('th')]
            print(f"Table {table_index + 1} headers: {headers}")
            if headers == required_headers:
                print(f"Table {table_index + 1} matches the required structure.")
                return table

        print("No table with the required headers found on the page.")
        return None

    def download_file(self, csv_url, target_date):
        print(f"Downloading ZIP file from {csv_url}.")
        try:
            zip_response = requests.get(csv_url, timeout=10)  # Adding a timeout to prevent hanging
            print("ZIP file downloaded successfully.")
            zip_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error downloading ZIP file: {e}")
            return None

        zip_filename = os.path.join(self.download_folder, f"data_{target_date.replace('/', '-')}.zip")
        print(f"Saving ZIP file as {zip_filename}.")
        try:
            with open(zip_filename, 'wb') as file:
                file.write(zip_response.content)
            print(f"ZIP file saved as {zip_filename}.")
            return zip_filename
        except OSError as e:
            print(f"Error saving ZIP file: {e}")
            return None

    def extract_file(self, zip_filename, target_date):
        extract_folder = os.path.join(self.download_folder, f"data_{target_date.replace('/', '-')}")
        print(f"Extracting ZIP file to folder {extract_folder}")
        try:
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            print(f"Files extracted to folder {extract_folder}")
        except zipfile.BadZipFile as e:
            print(f"Error extracting ZIP file: {e}")

    def process_target_date(self, target_table, target_date):
        print("Processing rows to find the specified date.")
        rows = target_table.find_all('tr')
        for row_index, row in enumerate(rows):
            print(f"Processing row {row_index}.")
            cells = row.find_all('td')
            if len(cells) < 4:
                print(f"Row {row_index} skipped, not enough columns.")
                continue

            date_text = cells[1].get_text(strip=True)  # Assuming date is in the second column
            csv_link = cells[3].find('input', {'onclick': True})

            print(f"Row {row_index}: Found date {date_text}.")

            if target_date == "all" or date_text == target_date:
                onclick_value = csv_link['onclick']
                csv_url = onclick_value.split("'")[1]  # Extracting the URL from the onclick string
                print(f"Downloading link found for date {date_text}. Link: {csv_url}")
                zip_filename = self.download_file(csv_url, date_text)
                if zip_filename:
                    self.extract_file(zip_filename, date_text)
                if target_date != "all":
                    return

        if target_date != "all":
            print(f"No data found for the specified date: {target_date}")

    def download_csv(self, target_date):
        html_content = self.fetch_webpage()
        if not html_content:
            return

        soup = self.parse_html(html_content)
        target_table = self.find_target_table(soup)
        if target_table:
            self.process_target_date(target_table, target_date)

# Example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python script.py <target_date|'all'>")
    else:
        target_date = sys.argv[1]
        downloader = TaifexDownloader("https://www.taifex.com.tw/cht/3/dlFutPrevious30DaysSalesData")
        print("Starting download process...")
        downloader.download_csv(target_date)
        print("Download process complete.")

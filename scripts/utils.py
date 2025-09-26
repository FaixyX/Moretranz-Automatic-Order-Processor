import os
import re
import threading

import requests
import os
from urllib.parse import urlparse, parse_qs


def extract_filename_from_url(url, default_name):
    """Extracts the filename from a URL or uses a default name."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    if 'filename' in query_params:
        file_name = query_params['filename'][0]
    else:
        # Fallback: use the default name with .png extension
        file_name = f"{default_name.replace('/', '_')}.png"

    # Ensure the filename has an extension
    if '.' not in file_name:
        file_name += '.png'

    return file_name

def create_folder(po_number, customer_name):
    """Creates a folder based on PO Number and customer name."""
    folder_name = f"{po_number}_{customer_name.replace(' ', '_')}"
    folder_path = os.path.join('attachments', folder_name)  # Hardcoded path
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def sanitize_filename(filename):
    """Remove or replace invalid characters for Windows file systems."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_and_save_attachment(url, folder_path, file_name=None):
    """Downloads an attachment from a URL and saves it to the specified folder."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Extract filename from URL and sanitize it
        if not file_name:
            parsed_url = urlparse(url)
            file_name = os.path.basename(parsed_url.path) or "downloaded_file"

        file_name = sanitize_filename(file_name)
        file_path = os.path.join(folder_path, file_name)

        # Create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Write the content to the file in chunks
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print(f"[Thread {threading.current_thread().name}] Downloaded {file_name} successfully to {file_path}.")
        return file_path
    except requests.RequestException as e:
        print(f"[Thread {threading.current_thread().name}] Failed to download {file_name} from {url}. Request Error: {e}")
        return None
    except Exception as e:
        print(f"[Thread {threading.current_thread().name}] Failed to save {file_name}. Error: {e}")
        return None

def print_pdf(file_path, printer_name=None):
    """Sends a PDF file to the default or specified network printer."""
    if printer_name:
        os.system(f'lpr -P {printer_name} {file_path}')
    else:
        os.system(f'lpr {file_path}')
    print(f"Sent {file_path} to the printer.")

def read_processed_emails(file_path):
    """Reads the list of processed email IDs from a file."""
    if not os.path.exists(file_path):
        return set()

    with open(file_path, 'r') as f:
        return set(line.strip() for line in f)

def save_processed_email(file_path, email_id):
    """Saves an email ID to the processed emails file."""
    with open(file_path, 'a') as f:
        f.write(f"{email_id}\n")


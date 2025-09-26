####################################################################################
##┳┓      ┓       ┓  ┳┓                                                           ##
##┃┃┏┓┓┏┏┓┃┏┓┏┓┏┓┏┫  ┣┫┓┏                                                         ##
##┻┛┗ ┗┛┗ ┗┗┛┣┛┗ ┗┻  ┻┛┗┫                                                         ##
##┳┳┓     ┓  ┛  ┏┓   ┓  ┛ ┓   ┓                                                   ##
##┃┃┃┓┏┏┓┏┫┓┏┏  ┃ ┏┓┏┫┏┓  ┃ ╋┏┫                                                   ##
##┛ ┗┗┻┛┗┗┻┗┻┛  ┗┛┗┛┗┻┗   ┗┛┗┗┻                                                   ##                 
##                                     _                   _               _      ##
## _ _ _ _ _ _ _ _ _   _____ _ _ ___ _| |_ _ ___ ___ ___ _| |___   ___ ___| |_    ##
##| | | | | | | | | |_|     | | |   | . | | |_ -|  _| . | . | -_|_|   | -_|  _|   ##
##|_____|_____|_____|_|_|_|_|___|_|_|___|___|___|___|___|___|___|_|_|_|___|_|     ##                                                                        
####################################################################################
import cgi
import mimetypes
import platform
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
import json
import os
import subprocess
import threading
import time
import imaplib
import re
import requests
from PIL import Image, ImageTk
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
from scripts.utils import create_folder, download_and_save_attachment, read_processed_emails, save_processed_email
from urllib.parse import urlparse, parse_qs
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from bs4 import BeautifulSoup
import os


SUMATRA_PDF_PATH = "lib/sumatrapdf.exe"
WKHTMLTOPDF_PATH = "lib/wkhtmltox/bin/wkhtmltopdf.exe"

CONFIG_PATH = 'config/config.py'
LOG_HISTORY_PATH = 'logs/processed_emails_history.txt'

mail = None
is_running = False
processing_thread = None

def load_config():
    config_file = CONFIG_PATH
    if os.path.exists(config_file):
        config_data = {}
        with open(config_file, 'r') as f:
            exec(f.read(), config_data)
        CONFIG = config_data['CONFIG']
        return CONFIG
    else:
        print(f"Config file {config_file} not found.")
        return None

CONFIG = load_config()

def save_config(config):
    """Saves the configuration back to the CONFIG.py file."""
    config_str = json.dumps(config, indent=4)
    config_str = config_str.replace('true', 'True').replace('false', 'False')
    with open(CONFIG_PATH, 'w') as file:
        file.write(f"CONFIG = {config_str}")


def update_config_field(field, value):
    CONFIG[field] = value


def update_email_field(field, value):
    CONFIG['email'][field] = value


def update_allowed_senders(new_senders):
    senders_list = new_senders.split(',')
    CONFIG['allowed_senders'] = [sender.strip() for sender in senders_list]


def save_settings():
    try:
        
        update_config_field('max_email_age_days', int(max_age_entry.get()))
        update_config_field('processed_emails_file', processed_emails_entry.get())
        update_config_field('attachments_folder', attachments_folder_entry.get())
        update_email_field('address', email_entry.get())
        update_email_field('password', password_entry.get())
        update_email_field('imap_server', imap_server_entry.get())
        update_allowed_senders(allowed_senders_entry.get())
        update_config_field('sleep_time', int(sleep_time_entry.get()))

        
        update_config_field('body_printer', body_printer_entry.get())
        update_config_field('attachment_printer', attachment_printer_entry.get())

        auto_start_value = bool(auto_start_var.get())
        update_config_field('auto_start', auto_start_value)

        
        save_config(CONFIG)
        messagebox.showinfo("Settings", "Configuration saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while saving settings: {e}")


def open_mundus_code():
    webbrowser.open("http://www.munduscode.net")


def open_url(url):
    webbrowser.open(url)


def open_root_attachment_folder():
    folder_path = CONFIG['attachments_folder']
    open_attachment_folder(folder_path)


def open_attachment_folder(folder_path):
    if os.path.exists(folder_path):
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer "{os.path.abspath(folder_path)}"')
        elif platform.system() == "Linux":
            subprocess.Popen(['xdg-open', os.path.abspath(folder_path)])
        else:
            messagebox.showerror("Error", "Opening folders is not supported on this OS.")
    else:
        messagebox.showerror("Error", f"Folder does not exist: {folder_path}")


def load_log_history():
    if os.path.exists(LOG_HISTORY_PATH):
        with open(LOG_HISTORY_PATH, 'r') as file:
            return [line.strip() for line in file.readlines()]
    return []


def save_log_history(po_number, processed_time, folder_path):
    with open(LOG_HISTORY_PATH, 'a') as file:
        file.write(f"{po_number} - {processed_time} - {folder_path}\n")


def show_settings_screen():
    settings_frame.tkraise()


def show_history_screen():
    history_frame.tkraise()


def update_history_listbox():
    history_listbox.delete(*history_listbox.get_children())
    log_history = load_log_history()
    for entry in log_history:
        parts = entry.split(" - ")
        if len(parts) >= 3:
            history_listbox.insert("", "end", values=(parts[0], parts[1], parts[2]))


def go_back_to_main():
    history_frame.tkraise()


def show_about_screen():
    about_frame.tkraise()


def update_status(message):
    status_label.config(text=message)
    status_label.update_idletasks()


def toggle_processing():
    global is_running, processing_thread
    if is_running:
        is_running = False
        start_stop_button.config(text="Start", style="Start.TButton")
        update_status("Processing stopped.")
    else:
        is_running = True
        start_stop_button.config(text="Stop", style="Stop.TButton")
        update_status("Processing started...")
        processing_thread = threading.Thread(target=process_emails)
        processing_thread.start()


def connect_to_email():
    try:
        mail = imaplib.IMAP4_SSL(CONFIG['email']['imap_server'])
        mail.login(CONFIG['email']['address'], CONFIG['email']['password'])
        mail.select("inbox")
        return mail
    except Exception as e:
        update_status(f"Failed to connect to email: {e}")
        return None
    
def create_folder_structure(email_body):
    original_po_match = re.search(r"Original PO - (\d+)", email_body)
    replacement_po_match = re.search(r"Replacement PO - (\d+[-R]*)", email_body)
    customer_name_match = re.search(r"Delivery address:\s*([A-Za-z\s]+)", email_body)
    po_number = None

    if original_po_match and replacement_po_match:
        po_number = replacement_po_match.group(1)
        customer_name = customer_name_match.group(1).strip() if customer_name_match else "Unknown"
    elif po_number_match := re.search(r"PO Number: (\d+)", email_body):
        po_number = po_number_match.group(1)
        customer_name = customer_name_match.group(1).strip() if customer_name_match else "Unknown"
    else:
        return None, None

    
    attachments_base_folder = CONFIG['attachments_folder']
    folder_path = os.path.join(attachments_base_folder, f"{po_number}_{customer_name}")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    return folder_path, po_number


def process_emails():
    global is_running, mail
    max_retries = 20
    retry_count = 0

    while is_running:
        try:
            if mail is None:
                mail = connect_to_email()
                if mail is None:
                    raise Exception("Failed to connect to email server.")
            else:
                try:
                    mail.noop()  # Check if the connection is still alive
                except imaplib.IMAP4.abort:
                    mail = connect_to_email()
                    if mail is None:
                        raise Exception("Failed to reconnect to email server.")

            # Search for unseen (unread) emails
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()

            # If no new emails are found, update the status and respect the sleep delay
            if not email_ids:
                update_status("No new emails found. Waiting for new emails...")
                time.sleep(CONFIG.get('sleep_time', 60))  # Use the configured sleep time
                continue

            email_count = len(email_ids)
            update_status(f"Processing {email_count} email(s)...")

            # Process each email
            for e_id in email_ids:
                process_single_email(mail, e_id)

                # Mark the email as read after processing to avoid infinite processing loop
                mail.store(e_id, '+FLAGS', '\\Seen')

            # Expunge to make sure the email is marked as read on the server
            mail.expunge()
            update_status(f"Processed {email_count} email(s). Waiting for new emails...")

            retry_count = 0  # Reset retry count after successful processing

        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            update_status(f"Connection error: {e}. Attempting to reconnect...")
            retry_count += 1
            if retry_count > max_retries:
                update_status("Max retries reached. Stopping email processing.")
                break
            time.sleep(10)

        except Exception as e:
            update_status(f"Error processing emails: {e}")
            retry_count += 1
            if retry_count > max_retries:
                update_status("Max retries reached. Stopping email processing.")
                break
            time.sleep(10)

    start_stop_button.config(text="Start")
    is_running = False


def convert_image_to_4x6_pdf(img_path, output_pdf, top_margin_inch=-0.5):
    img = Image.open(img_path)
    width_inch = 4
    height_inch = 6

    c = canvas.Canvas(output_pdf, pagesize=(width_inch * inch, height_inch * inch))

    img_width, img_height = img.size
    dpi = img.info.get('dpi', (203, 203))
    dpi_x, dpi_y = dpi

    img_width_inch = img_width / dpi_x
    img_height_inch = img_height / dpi_y

    scale_factor_width = width_inch / img_width_inch
    scale_factor_height = height_inch / img_height_inch
    scale_factor = min(scale_factor_width, scale_factor_height)

    new_width = img_width_inch * scale_factor * inch
    new_height = img_height_inch * scale_factor * inch

    x_offset = (width_inch * inch - new_width) / 2
    y_offset = top_margin_inch * inch + (height_inch * inch - new_height - top_margin_inch * inch) / 2

    c.drawImage(img_path, x_offset, y_offset, width=new_width, height=new_height)
    c.save()

    print(f"Label PDF created successfully: {output_pdf}")



def convert_html_to_letter_pdf(html_content, output_pdf):
    width_inch = 8.5
    height_inch = 11

    c = canvas.Canvas(output_pdf, pagesize=(width_inch * inch, height_inch * inch))

    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text()

    text_margin = 1 * inch
    text = c.beginText(text_margin, height_inch * inch - text_margin)
    text.setFont("Helvetica", 10)

    for line in text_content.split("\n"):
        text.textLine(line)

    c.drawText(text)
    c.save()

    print(f"Email body PDF created successfully: {output_pdf}")



def process_and_print_label(img_path, folder_path):
    try:
        pdf_file_path = os.path.join(folder_path, "label.pdf")
        convert_image_to_4x6_pdf(img_path, pdf_file_path)
        print_with_sumatra(pdf_file_path, CONFIG['attachment_printer'], "noscale")
    except Exception as e:
        print(f"Error processing label: {str(e)}")



def print_with_sumatra(file_path, printer_name, print_settings=None):
    try:
        sumatra_path = r"lib\sumatrapdf.exe"
        command = f'"{sumatra_path}" -print-to "{printer_name}"'

        if print_settings:
            command += f' -print-settings "{print_settings}"'
        else:
            command += f' -print-settings "noscale"'

        command += f' "{file_path}"'

        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Printed {file_path} to {printer_name}. Output: {result.stdout.decode()}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to print {file_path}. Error: {e.stderr.decode()}")



def clean_html_body(body):
    soup = BeautifulSoup(body, 'html.parser')
    for img in soup.find_all('img'):
        img.decompose()
    return str(soup)

def process_single_email(mail, e_id):
    processed_emails = read_processed_emails(CONFIG['processed_emails_file'])
    if e_id.decode() in processed_emails:
        return

    save_processed_email(CONFIG['processed_emails_file'], e_id.decode())

    status, msg_data = mail.fetch(e_id, '(BODY.PEEK[])')
    printed_files = set()
    history_updated = False

    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])

            email_date = parsedate_to_datetime(msg.get("Date"))
            current_time = datetime.now(pytz.utc)

            
            if current_time - email_date > timedelta(days=CONFIG['max_email_age_days']):
                continue

            sender = msg.get('From')
            if not any(allowed_sender in sender for allowed_sender in CONFIG['allowed_senders']):
                continue

            subject, encoding = decode_header(msg['subject'])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')

            folder_path, po_number = None, None
            body = None
            inline_images = {}

            if msg.is_multipart():
                download_tasks_attachments = []
                download_tasks_links = []
                with ThreadPoolExecutor(max_workers=3) as executor:
                    for part in msg.walk():
                        content_disposition = part.get("Content-Disposition", "")
                        content_type = part.get_content_type()
                        content_id = part.get("Content-ID")

                        
                        if content_type == "text/html":
                            html_body = part.get_payload(decode=True).decode()
                            text_body = BeautifulSoup(html_body, 'html.parser').get_text()
                            if folder_path is None:
                                folder_path, po_number = create_folder_structure(text_body)
                                if not folder_path:
                                    update_status("No valid PO number found in the email body.")
                                    continue
                                update_status(f"Processing email for PO: {po_number}")
                            body = html_body  

                        
                        elif content_type == "text/plain" and body is None:
                            body = part.get_payload(decode=True).decode()
                            if folder_path is None:
                                folder_path, po_number = create_folder_structure(body)
                                if not folder_path:
                                    update_status("No valid PO number found in the email body.")
                                    continue
                                update_status(f"Processing email for PO: {po_number}")

                        
                        elif content_disposition:
                            disposition, params = cgi.parse_header(content_disposition)
                            filename = part.get_filename()

                            if "attachment" in disposition and filename and folder_path:
                                file_path = os.path.join(folder_path, filename)
                                if not os.path.exists(file_path):
                                    download_tasks_attachments.append(executor.submit(save_attachment, part, file_path))
                                    update_status(f"Downloading attachment: {filename}")

                            elif "inline" in disposition and content_id and folder_path:
                                filename = part.get_filename()
                                if not filename:
                                    ext = mimetypes.guess_extension(content_type)
                                    filename = f"inline_image_{len(inline_images)}{ext}"
                                file_path = os.path.join(folder_path, filename)
                                with open(file_path, 'wb') as f:
                                    f.write(part.get_payload(decode=True))
                                content_id = content_id.strip('<>')
                                inline_images[content_id] = file_path

                    
                    soup = BeautifulSoup(body, 'html.parser') if body else None
                    if soup:
                        for link in soup.find_all('a', href=True):
                            url = link['href']
                            if "filename=" in url:
                                
                                parsed_url = urlparse(url)
                                query_params = parse_qs(parsed_url.query)
                                if 'filename' in query_params:
                                    filename = query_params['filename'][0]
                                else:
                                    filename = os.path.basename(parsed_url.path)
                                download_tasks_links.append(executor.submit(download_and_save_attachment, url, folder_path, filename))
                                update_status(f"Queuing external download for: {filename}")

                
                for task in download_tasks_attachments:
                    try:
                        task.result()
                    except Exception as e:
                        update_status(f"Error during attachment download: {e}")

                
                for task in download_tasks_links:
                    try:
                        task.result()
                    except Exception as e:
                        update_status(f"Error during link download: {e}")

                
                if folder_path and body:
                    
                    body = replace_cid_images(body, inline_images)
                    process_and_print_email_body(body, folder_path)

                
                for task in download_tasks_attachments:
                    file_path = task.result()
                    if file_path and file_path.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                        process_and_print_label(file_path, folder_path)

                
                if po_number and not history_updated:
                    processed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    history_listbox.insert("", "end", values=(po_number, processed_time, folder_path))
                    save_log_history(po_number, processed_time, folder_path)
                    history_updated = True

    mail.store(e_id, '+FLAGS', '\\Seen')
    mail.store(e_id, '+X-GM-LABELS', 'Jiffy_Orders')

    mail.expunge()
    update_status("Email processing completed.")

def replace_cid_images(html_body, inline_images):
    soup = BeautifulSoup(html_body, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src.startswith('cid:'):
            cid = src[4:]
            if cid in inline_images:
                img['src'] = 'file://' + os.path.abspath(inline_images[cid])
    return str(soup)


def process_and_print_email_body(email_body, folder_path):
    try:
        
        html_content = email_body

        
        html_file_path = os.path.join(folder_path, "email_body.html")
        print(f"Writing HTML content to: {html_file_path}")
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        if os.path.exists(html_file_path):
            print(f"HTML file successfully written: {html_file_path}")
        else:
            print(f"Failed to write HTML file: {html_file_path}")

        pdf_file_path = os.path.join(folder_path, "email_body.pdf")
        print(f"PDF will be saved to: {pdf_file_path}")

        
        if convert_html_to_pdf(html_file_path, pdf_file_path):
            print(f"PDF successfully created at: {pdf_file_path}")

            if os.path.exists(pdf_file_path):
                print(f"PDF file exists: {pdf_file_path}")
            else:
                print(f"PDF file does not exist: {pdf_file_path}")

            
            print(f"Attempting to print PDF: {pdf_file_path}")
            print_with_sumatra(pdf_file_path, CONFIG['body_printer'], "fit")
        else:
            print(f"Failed to convert email body to PDF for printing.")
    except Exception as e:
        print(f"Error processing email body: {str(e)}")


def convert_html_to_pdf(html_file_path, pdf_file_path):
    """
    Converts an HTML file to PDF using wkhtmltopdf.
    """
    try:
        
        if not os.path.exists(WKHTMLTOPDF_PATH):
            print(f"Error: wkhtmltopdf executable not found at {WKHTMLTOPDF_PATH}")
            return False

        
        command = [
            WKHTMLTOPDF_PATH,
            '--page-size', 'Letter',
            '--enable-smart-shrinking',
            '--no-outline',
            '--print-media-type',
            '--dpi', '300',
            '--enable-local-file-access',
            html_file_path,
            pdf_file_path
        ]

        
        print("Executing wkhtmltopdf command:")
        print(' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command))

        
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        
        print(f"wkhtmltopdf output: {result.stdout.decode()}")
        print(f"wkhtmltopdf errors: {result.stderr.decode()}")

        print(f"Converted HTML to PDF: {html_file_path} -> {pdf_file_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to convert HTML to PDF. Error code: {e.returncode}")
        print(f"Error output: {e.stderr.decode()}")
        return False
    except Exception as e:
        print(f"Unexpected error during PDF conversion: {str(e)}")
        return False


def open_selected_folder():
    try:
        selected_item = history_listbox.selection()[0]
        folder_path = history_listbox.item(selected_item, 'values')[2]
        open_attachment_folder(folder_path)
    except IndexError:
        messagebox.showerror("Error", "No item selected or invalid selection.")


def save_attachment(part, file_path):
    try:
        
        attachment_folder = os.path.dirname(file_path)
        if not os.path.exists(attachment_folder):
            os.makedirs(attachment_folder)

        
        with open(file_path, "wb") as f:
            f.write(part.get_payload(decode=True))
        update_status(f"Downloaded attachment to {file_path}")
        return file_path
    except Exception as e:
        update_status(f"Failed to save attachment {file_path}. Error: {e}")
        return None


def confirm_exit():
    if messagebox.askokcancel("Exit", "Do you really want to exit?"):
        global is_running
        is_running = False
        root.quit()


def clear_history():
    if messagebox.askokcancel("Clear History",
                              "Are you sure you want to clear the history? This cannot be undone."):
        open(LOG_HISTORY_PATH, 'w').close()
        history_listbox.delete(*history_listbox.get_children())
        open(CONFIG['processed_emails_file'], 'w').close()
        update_status("History cleared successfully.")


def discover_printers():
    printers = []
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['wmic', 'printer', 'get', 'name'], capture_output=True, text=True)
            printers = result.stdout.splitlines()[1:]
        elif platform.system() == "Linux":
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            printers = [line.split()[1] for line in result.stdout.splitlines() if line.startswith('printer')]
        else:
            update_status("Unsupported OS for printer discovery.")
    except Exception as e:
        update_status(f"Failed to fetch printers: {e}")
    return [printer.strip() for printer in printers if printer.strip()]


def fetch_printers():
    printers = []
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['wmic', 'printer', 'get', 'name'], capture_output=True, text=True)
            printers = result.stdout.splitlines()[1:]
        elif platform.system() == "Linux":
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            printers = [line.split()[1] for line in result.stdout.splitlines() if line.startswith('printer')]
        else:
            update_status("Unsupported OS for printer discovery.")
    except Exception as e:
        update_status(f"Failed to fetch printers: {e}")

    printers = [printer.strip() for printer in printers if printer.strip()]
    return printers


def populate_printer_options():
        printers = fetch_printers()
        if printers:
            body_printer_entry['values'] = printers
            attachment_printer_entry['values'] = printers

            body_printer_entry.set(CONFIG['body_printer'])
            attachment_printer_entry.set(CONFIG['attachment_printer'])

# GUI Configuration
root = tk.Tk()
root.geometry("1024x768")
root.configure(bg="#ffffff")
root.title("Moretranz Automatic Order Processor")

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

style = ttk.Style()

style.theme_use('clam')

style.configure("TLabel", font=("Helvetica", 12), background="#ffffff")
style.configure("TFrame", background="#ffffff")
style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"), background="#007bff", foreground="white")
style.configure("Treeview", font=("Helvetica", 10), background="white", foreground="black", fieldbackground="white",
                rowheight=25)

style.configure("Sidebar.TButton", font=("Helvetica", 12), padding=10, background="#007bff", foreground="#ffffff")
style.map("Sidebar.TButton",
          foreground=[('pressed', '#ffffff'), ('active', '#ffffff')],
          background=[('pressed', '#0056b3'), ('active', '#0056b3')])

sidebar = tk.Frame(root, width=220, bg="#003366", relief="raised")
sidebar.grid(row=0, column=0, sticky='ns')
sidebar.grid_propagate(False)

def create_sidebar_button(text, command):
    btn = tk.Button(sidebar, text=text, command=command, font=("Helvetica", 12), bg="#007bff", fg="#ffffff",
                    activebackground="#0056b3", activeforeground="#ffffff", bd=0, cursor="hand2")
    btn.pack(pady=15, fill=tk.X)
    return btn

create_sidebar_button("Dashboard", lambda: history_frame.tkraise())
create_sidebar_button("Settings", lambda: settings_frame.tkraise())
create_sidebar_button("Clear History", clear_history)
create_sidebar_button("About & Help", lambda: about_frame.tkraise())
create_sidebar_button("Exit", confirm_exit)

content_area = ttk.Frame(root, style="TFrame")
content_area.grid(row=0, column=1, sticky='nsew')

content_area.grid_rowconfigure(0, weight=1)
content_area.grid_columnconfigure(0, weight=1)

history_frame = ttk.Frame(content_area, style="TFrame")
history_frame.grid(row=0, column=0, sticky='nsew')

history_frame.grid_rowconfigure(1, weight=1)
history_frame.grid_columnconfigure(0, weight=1)

ttk.Label(history_frame, text="Processing Log History", font=("Helvetica", 18, "bold"), background="#ffffff").grid(
    row=0, column=0, pady=(10, 5))

history_columns = ('PO Number', 'Processed Time', 'Folder Path')
history_listbox = ttk.Treeview(history_frame, columns=history_columns, show='headings', style="Treeview")
history_listbox.heading('PO Number', text='PO Number')
history_listbox.heading('Processed Time', text='Processed Time')
history_listbox.heading('Folder Path', text='Folder Path')

history_listbox.grid(row=1, column=0, sticky='nsew', padx=20, pady=5)
history_listbox.column('PO Number', anchor='center', width=150)
history_listbox.column('Processed Time', anchor='center', width=200)
history_listbox.column('Folder Path', anchor='center', width=350)

ttk.Button(history_frame, text="Open Attachment Folder", command=open_root_attachment_folder,
           style="Sidebar.TButton").grid(row=2, column=0, pady=(10, 20), sticky='ew', padx=20)


style.configure("Start.TButton", font=("Helvetica", 12), padding=10, background="green", foreground="white")
style.map("Start.TButton",
          foreground=[('pressed', 'white'), ('active', 'white')],
          background=[('pressed', 'darkgreen'), ('active', 'darkgreen')])

style.configure("Stop.TButton", font=("Helvetica", 12), padding=10, background="red", foreground="white")
style.map("Stop.TButton",
          foreground=[('pressed', 'white'), ('active', 'white')],
          background=[('pressed', 'darkred'), ('active', 'darkred')])

start_stop_button = ttk.Button(history_frame, text="Start", command=toggle_processing, style="Start.TButton")
start_stop_button.grid(row=3, column=0, pady=20)

settings_frame = ttk.Frame(content_area, style="TFrame")
settings_frame.grid(row=0, column=0, sticky='nsew')

settings_frame.grid_columnconfigure(1, weight=1)

ttk.Label(settings_frame, text="Configuration Settings", font=("Helvetica", 18, "bold"), background="#ffffff").grid(
    row=0, column=0, columnspan=3, pady=20)

ttk.Label(settings_frame, text="Email Address", background="#ffffff").grid(row=1, column=0, sticky="e", padx=10, pady=10)
email_entry = ttk.Entry(settings_frame, width=40)
email_entry.grid(row=1, column=1, columnspan=2, pady=10, sticky='ew')
email_entry.insert(0, CONFIG['email']['address'])

ttk.Label(settings_frame, text="Email Password", background="#ffffff").grid(row=2, column=0, sticky="e", padx=10, pady=10)
password_entry = ttk.Entry(settings_frame, show="*", width=40)
password_entry.grid(row=2, column=1, columnspan=2, pady=10, sticky='ew')
password_entry.insert(0, CONFIG['email']['password'])

ttk.Label(settings_frame, text="IMAP Server", background="#ffffff").grid(row=3, column=0, sticky="e", padx=10, pady=10)
imap_server_entry = ttk.Entry(settings_frame, width=40)
imap_server_entry.grid(row=3, column=1, columnspan=2, pady=10, sticky='ew')
imap_server_entry.insert(0, CONFIG['email']['imap_server'])

ttk.Label(settings_frame, text="Allowed Senders (comma separated)", background="#ffffff").grid(row=4, column=0,
                                                                                               sticky="e", padx=10,
                                                                                               pady=10)
allowed_senders_entry = ttk.Entry(settings_frame, width=50)
allowed_senders_entry.grid(row=4, column=1, columnspan=2, pady=10, sticky='ew')
allowed_senders_entry.insert(0, ', '.join(CONFIG['allowed_senders']))

ttk.Label(settings_frame, text="Max Email Age (days)", background="#ffffff").grid(row=5, column=0, sticky="e", padx=10,
                                                                                  pady=10)
max_age_entry = ttk.Entry(settings_frame, width=10)
max_age_entry.grid(row=5, column=1, pady=10, sticky='w')
max_age_entry.insert(0, CONFIG['max_email_age_days'])

ttk.Label(settings_frame, text="Processed Emails File", background="#ffffff").grid(row=6, column=0, sticky="e", padx=10,
                                                                                   pady=10)
processed_emails_entry = ttk.Entry(settings_frame, width=50)
processed_emails_entry.grid(row=6, column=1, columnspan=2, pady=10, sticky='ew')
processed_emails_entry.insert(0, CONFIG['processed_emails_file'])

ttk.Label(settings_frame, text="Attachments Folder", background="#ffffff").grid(row=7, column=0, sticky="e", padx=10,
                                                                                pady=10)
attachments_folder_entry = ttk.Entry(settings_frame, width=50)
attachments_folder_entry.grid(row=7, column=1, columnspan=2, pady=10, sticky='ew')
attachments_folder_entry.insert(0, CONFIG['attachments_folder'])

ttk.Label(settings_frame, text="Sleep Time (seconds)", background="#ffffff").grid(row=8, column=0, sticky="e", padx=10,
                                                                                  pady=10)
sleep_time_entry = ttk.Entry(settings_frame, width=10)
sleep_time_entry.grid(row=8, column=1, pady=10, sticky='w')
sleep_time_entry.insert(0, CONFIG.get('sleep_time', 60))

def refresh_printer_list():
    populate_printer_options()
    update_status("Printer list refreshed.")

def load_resized_icon(path, size):
    icon = Image.open(path)
    icon = icon.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(icon)

refresh_icon = load_resized_icon("assets/refresh_icon.png", (16, 16))

ttk.Label(settings_frame, text="Body Printer", background="#ffffff").grid(row=9, column=0, sticky="e", padx=10, pady=10)
body_printer_entry = ttk.Combobox(settings_frame, width=48, state='readonly')
body_printer_entry.grid(row=9, column=1, pady=10, sticky='ew')
refresh_body_printer_button = ttk.Button(settings_frame, image=refresh_icon, command=refresh_printer_list)
refresh_body_printer_button.grid(row=9, column=2, padx=10, pady=10)

ttk.Label(settings_frame, text="Attachment Printer", background="#ffffff").grid(row=10, column=0, sticky="e", padx=10,
                                                                                pady=10)
attachment_printer_entry = ttk.Combobox(settings_frame, width=48, state='readonly')
attachment_printer_entry.grid(row=10, column=1, pady=10, sticky='ew')
refresh_attachment_printer_button = ttk.Button(settings_frame, image=refresh_icon, command=refresh_printer_list)
refresh_attachment_printer_button.grid(row=10, column=2, padx=10, pady=10)

auto_start_var = tk.BooleanVar()
auto_start_var.set(CONFIG.get('auto_start', False))

ttk.Label(settings_frame, text="Run on Startup", background="#ffffff").grid(row=11, column=0, sticky="e", padx=10,
                                                                            pady=10)
auto_start_checkbox = ttk.Checkbutton(settings_frame, variable=auto_start_var)
auto_start_checkbox.grid(row=11, column=1, pady=10, sticky="w")

save_button = tk.Button(settings_frame, text="Save Settings", command=save_settings, font=("Helvetica", 12),
                        bg="#007bff", fg="#ffffff", activebackground="#0056b3", activeforeground="#ffffff", bd=0,
                        cursor="hand2")
save_button.grid(row=12, column=1, pady=20, sticky="e")

about_frame = ttk.Frame(content_area, style="TFrame")
about_frame.grid(row=0, column=0, sticky='nsew')

logo_image = Image.open("assets/logo.png")
logo_image = logo_image.resize((150, 150), Image.LANCZOS)
logo_photo = ImageTk.PhotoImage(logo_image)

logo_label = tk.Label(about_frame, image=logo_photo, background="#ffffff")
logo_label.image = logo_photo
logo_label.pack(pady=20)

def open_manual():
    manual_path = os.path.abspath("MANUAL/index.html")
    if os.path.exists(manual_path):
        webbrowser.open(f"file://{manual_path}")
    else:
        print("Manual not found.")

company_info = """\
Developed By
Mundus Code Ltd
"""

company_label = ttk.Label(about_frame, text=company_info, font=("Helvetica", 14), background="#ffffff",
                          foreground="#333333")
company_label.pack(pady=(20, 0))

website_label = tk.Label(about_frame, text="www.munduscode.net", font=("Helvetica", 14, "underline"), fg="blue",
                         cursor="hand2", background="#ffffff")
website_label.pack()
website_label.bind("<Button-1>", open_mundus_code)

email_label = tk.Label(about_frame, text="info@munduscode.net", font=("Helvetica", 14, "underline"), fg="blue",
                       cursor="hand2", background="#ffffff")
email_label.pack(pady=(0, 20))
email_label.bind("<Button-1>", lambda e: open_url("mailto:info@munduscode.net"))

version_label = ttk.Label(about_frame, text="Version: 1.0.0", font=("Helvetica", 14), background="#ffffff",
                          foreground="#333333")
version_label.pack()


manual_button = ttk.Button(about_frame, text="Open Manual", command=open_manual)
manual_button.pack(pady=10)

status_bar = ttk.Frame(root, style="TFrame")
status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
status_label = ttk.Label(status_bar, text="Ready", font=("Helvetica", 12), background="#f7f7f7")
status_label.pack(fill=tk.X, padx=10, pady=5)

root.grid_rowconfigure(1, weight=0)


def on_history_double_click(event):
    try:
        selected_item = history_listbox.selection()[0]
        folder_path = history_listbox.item(selected_item, 'values')[2]
        open_attachment_folder(folder_path)
    except IndexError:
        messagebox.showerror("Error", "No item selected or invalid selection.")

history_listbox.bind("<Double-1>", on_history_double_click)

history_frame.tkraise()
update_history_listbox()
populate_printer_options()

root.protocol("WM_DELETE_WINDOW", confirm_exit)

if CONFIG.get('auto_start', False):
    toggle_processing()

root.mainloop()

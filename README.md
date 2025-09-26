# Moretranz Automatic Order Processor - Technical Documentation

## Overview

The Moretranz Automatic Order Processor is a Python-based desktop application built with Tkinter that automates email processing for order management. It monitors IMAP email accounts, processes incoming orders, downloads attachments, organizes files, and handles automated printing.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Application                       │
├─────────────────────────────────────────────────────────────┤
│  GUI Layer (Tkinter)                                       │
│  ├── Dashboard/History Frame                               │
│  ├── Settings Frame                                        │
│  └── About Frame                                           │
├─────────────────────────────────────────────────────────────┤
│  Core Processing Engine                                     │
│  ├── Email Processing (IMAP)                              │
│  ├── File Management                                       │
│  ├── PDF Operations                                        │
│  └── Printing System                                       │
├─────────────────────────────────────────────────────────────┤
│  External Dependencies                                      │
│  ├── SumatraPDF (Printing)                                │
│  ├── wkhtmltopdf (HTML to PDF)                            │
│  └── Configuration Management                              │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
source/
├── main.py                 # Main application entry point
├── main.spec              # PyInstaller build configuration
├── config/
│   ├── __init__.py
│   └── config.py          # Configuration settings
├── scripts/
│   ├── __init__.py
│   └── utils.py           # Utility functions
├── assets/
│   ├── logo.png           # Application logo
│   └── refresh_icon.png   # UI icons
├── lib/
│   ├── sumatrapdf.exe     # PDF printing utility
│   ├── SumatraPDF-settings.txt
│   └── wkhtmltox/         # HTML to PDF converter
└── logs/                  # Processing logs and history
```

## Core Components

### 1. Configuration Management

**File**: `config/config.py`

```python
CONFIG = {
    "email": {
        "address": "your_email@gmail.com",
        "password": "password", 
        "imap_server": "imap.gmail.com"
    },
    "allowed_senders": ["steve@moretranz.com"],
    "max_email_age_days": 10,
    "processed_emails_file": "logs/processed_emails.txt",
    "attachments_folder": "attachments",
    "sleep_time": 5,
    "body_printer": "BodyPrinter",
    "attachment_printer": "AttachmentPrinter", 
    "auto_start": False
}
```

**Key Functions:**
- `load_config()`: Dynamically loads configuration from file
- `save_config()`: Persists configuration changes
- `update_config_field()`: Updates specific configuration values
- `update_email_field()`: Updates email-specific settings
- `update_allowed_senders()`: Manages allowed sender list

### 2. Email Processing Engine

**Core Functions:**

#### `connect_to_email()`
- Establishes IMAP4_SSL connection
- Handles authentication with configured credentials
- Selects inbox for processing
- Returns mail connection object or None on failure

#### `process_emails()` (Main Processing Loop)
```python
def process_emails():
    global is_running, mail
    max_retries = 20
    retry_count = 0
    
    while is_running:
        # Connection management with retry logic
        # Search for unseen emails
        # Process each email individually
        # Mark emails as read
        # Handle connection errors and retries
```

**Key Features:**
- **Connection Resilience**: Automatic reconnection on IMAP failures
- **Retry Logic**: Maximum 20 retries with exponential backoff
- **Unread Email Detection**: Uses `UNSEEN` flag to find new emails
- **Concurrent Processing**: ThreadPoolExecutor for attachment downloads

#### `process_single_email(mail, e_id)`
**Email Processing Pipeline:**

1. **Duplicate Check**: Verify email hasn't been processed
2. **Age Validation**: Skip emails older than configured days
3. **Sender Validation**: Check against allowed senders list
4. **Content Extraction**: Parse multipart email structure
5. **PO Number Extraction**: Regex-based order identification
6. **Folder Creation**: Organize by PO number and customer
7. **Attachment Processing**: Download and save files
8. **Content Processing**: Handle inline images and links
9. **Printing**: Automated document printing
10. **History Logging**: Record processing details

### 3. File Management System

#### Folder Structure Creation
```python
def create_folder_structure(email_body):
    # Regex patterns for PO extraction
    original_po_match = re.search(r"Original PO - (\d+)", email_body)
    replacement_po_match = re.search(r"Replacement PO - (\d+[-R]*)", email_body)
    customer_name_match = re.search(r"Delivery address:\s*([A-Za-z\s]+)", email_body)
    
    # Create folder: {PO_NUMBER}_{CUSTOMER_NAME}
    folder_path = os.path.join(attachments_base_folder, f"{po_number}_{customer_name}")
```

#### Attachment Handling
- **Direct Attachments**: Standard email attachments with `Content-Disposition: attachment`
- **Inline Images**: Embedded images with `Content-ID` headers
- **External Links**: URLs with downloadable content
- **Concurrent Downloads**: ThreadPoolExecutor for performance

### 4. PDF Operations

#### HTML to PDF Conversion
```python
def convert_html_to_pdf(html_file_path, pdf_file_path):
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
```

#### Image to PDF Conversion
```python
def convert_image_to_4x6_pdf(img_path, output_pdf, top_margin_inch=-0.5):
    # 4x6 inch label format
    # DPI-aware scaling
    # Centered positioning with margin control
    # ReportLab canvas generation
```

### 5. Printing System

#### SumatraPDF Integration
```python
def print_with_sumatra(file_path, printer_name, print_settings=None):
    command = f'"{sumatra_path}" -print-to "{printer_name}"'
    if print_settings:
        command += f' -print-settings "{print_settings}"'
    else:
        command += f' -print-settings "noscale"'
    command += f' "{file_path}"'
```

**Print Settings:**
- `"noscale"`: No scaling for labels
- `"fit"`: Fit to page for documents
- Printer-specific routing for body vs attachments

### 6. GUI Implementation

#### Tkinter Architecture
```python
# Main window setup
root = tk.Tk()
root.geometry("1024x768")
root.configure(bg="#ffffff")

# Sidebar navigation
sidebar = tk.Frame(root, width=220, bg="#003366", relief="raised")

# Content frames (stacked)
content_area = ttk.Frame(root, style="TFrame")
├── history_frame    # Dashboard with processing history
├── settings_frame   # Configuration interface  
└── about_frame      # About and help information
```

#### Real-time Status Updates
```python
def update_status(message):
    status_label.config(text=message)
    status_label.update_idletasks()  # Force UI refresh
```

#### Threading Model
- **Main Thread**: GUI event loop
- **Processing Thread**: Email processing (background)
- **Download Threads**: Concurrent attachment downloads

### 7. Utility Functions

**File**: `scripts/utils.py`

#### Key Utilities:
```python
def create_folder(po_number, customer_name):
    # Folder creation with naming convention

def sanitize_filename(filename):
    # Windows-safe filename sanitization
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_and_save_attachment(url, folder_path, file_name=None):
    # HTTP download with streaming and error handling

def read_processed_emails(file_path):
    # Email ID tracking for duplicate prevention

def save_processed_email(file_path, email_id):
    # Persistent email processing log
```

## Dependencies

### Python Packages
```python
import tkinter as tk          # GUI framework
import imaplib               # IMAP email processing
import email                 # Email parsing
import requests              # HTTP downloads
import threading             # Background processing
import subprocess            # External process execution
from PIL import Image        # Image processing
from bs4 import BeautifulSoup # HTML parsing
from reportlab.pdfgen import canvas # PDF generation
import pytz                  # Timezone handling
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
```

### External Tools
- **SumatraPDF**: Lightweight PDF viewer and printer
- **wkhtmltopdf**: HTML to PDF conversion engine

## Configuration Details

### Email Settings
- **IMAP Server**: Gmail, Outlook, or custom IMAP servers
- **Authentication**: Username/password (app passwords recommended)
- **SSL/TLS**: Encrypted connections required

### Processing Rules
- **Allowed Senders**: Whitelist-based email filtering
- **Age Limits**: Skip emails older than specified days
- **Sleep Intervals**: Configurable polling frequency
- **Retry Logic**: Automatic error recovery

### File Organization
- **Base Folder**: Configurable attachment storage location
- **Naming Convention**: `{PO_NUMBER}_{CUSTOMER_NAME}`
- **File Types**: PDF, PNG, JPG, JPEG supported
- **Duplicate Handling**: Skip existing files

## Error Handling

### Connection Management
```python
try:
    mail.noop()  # Test connection
except imaplib.IMAP4.abort:
    mail = connect_to_email()  # Reconnect
```

### Processing Errors
- **Email Parsing**: Graceful handling of malformed emails
- **Download Failures**: Individual file error isolation
- **Print Errors**: Subprocess error capture and logging
- **File System**: Permission and disk space error handling

## Security Considerations

### Credential Management
- Plain text password storage (security risk)
- Configuration file permissions
- Email app password recommendations

### File System Access
- Unrestricted file system access
- No input sanitization for folder paths
- Potential directory traversal vulnerabilities

## Performance Characteristics

### Resource Usage
- **Memory**: ~50-100MB typical usage
- **CPU**: Low during idle, moderate during processing
- **Network**: Minimal (email polling only)
- **Disk I/O**: Variable based on attachment sizes

### Scalability Limits
- **Single-threaded** email processing
- **Local storage** limitations
- **Desktop-bound** operation
- **Single user** access

## Build and Deployment

### PyInstaller Configuration
```python
# main.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('scripts', 'scripts'), ('lib', 'lib')],
    hiddenimports=[],
    # ... additional configuration
)
```

### Build Process
```bash
# Create executable
pyinstaller main.spec

# Output location
dist/main.exe
```

## Monitoring and Logging

### Processing History
- **File**: `logs/processed_emails_history.txt`
- **Format**: `PO_NUMBER - TIMESTAMP - FOLDER_PATH`
- **GUI Display**: Sortable tree view with double-click folder access

### Email Tracking
- **File**: `logs/processed_emails.txt`
- **Content**: Email IDs to prevent reprocessing
- **Persistence**: Survives application restarts

## Known Issues and Limitations

### Technical Limitations
1. **Single Instance**: No multi-user support
2. **Local Dependency**: Requires desktop installation
3. **Print Drivers**: Windows-specific printer integration
4. **Error Recovery**: Limited automatic error recovery
5. **Security**: Plain text credential storage

### Operational Constraints
1. **Availability**: Requires computer to remain on
2. **Scalability**: Performance degrades with high email volume
3. **Maintenance**: Manual updates and configuration
4. **Backup**: No automatic data backup
5. **Monitoring**: Limited error alerting

## Future Enhancement Opportunities

### Immediate Improvements
- Encrypted credential storage
- Better error logging and alerting
- Configuration validation
- Automatic backup functionality
- Multi-printer support enhancement

### Architectural Improvements
- Web-based interface
- Multi-user support
- Cloud storage integration
- Real-time monitoring dashboard
- API-based integrations

This technical documentation provides a comprehensive understanding of the current desktop application's architecture, implementation details, and operational characteristics, serving as a foundation for maintenance, enhancement, or migration planning.

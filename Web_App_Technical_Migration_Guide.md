# Desktop to Web App Migration - Technical Implementation Guide

## Executive Summary

This document outlines the technical approach for migrating the Moretranz Automatic Order Processor from a Python/Tkinter desktop application to a modern web-based solution. The migration maintains all existing functionality while adding scalability, multi-user support, and cloud-based operations.

## Current Desktop App Analysis

### Technical Stack
```
Desktop Application:
├── Language: Python 3.x
├── GUI Framework: Tkinter
├── Email Processing: imaplib
├── PDF Generation: wkhtmltopdf + ReportLab
├── Image Processing: PIL (Pillow)
├── Web Scraping: BeautifulSoup
├── HTTP Requests: requests
├── Printing: SumatraPDF + subprocess
├── Threading: threading + ThreadPoolExecutor
└── Build Tool: PyInstaller
```

### Core Functionality Mapping
| Desktop Feature | Implementation | Web App Equivalent |
|----------------|----------------|-------------------|
| IMAP Email Processing | `imaplib` + threading | Background job queue |
| File Management | Local file system | Cloud storage + API |
| PDF Generation | wkhtmltopdf + ReportLab | Puppeteer/jsPDF + backend |
| Printing | SumatraPDF subprocess | Print service/download |
| GUI | Tkinter frames | React components |
| Configuration | Python dict + file I/O | Database + REST API |
| Real-time Updates | Direct GUI updates | WebSocket/SSE |
| Threading | Python threading | Job queues + workers |

## Proposed Web App Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Web Application                         │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React + Vite)                                   │
│  ├── Dashboard Component                                    │
│  ├── Settings Component                                     │
│  ├── History Component                                      │
│  └── Real-time Updates (WebSocket)                         │
├─────────────────────────────────────────────────────────────┤
│  Django Backend                                             │
│  ├── Django REST Framework (API)                           │
│  ├── Django Channels (WebSocket)                           │
│  ├── Authentication Middleware                             │
│  └── File Upload/Download                                  │
├─────────────────────────────────────────────────────────────┤
│  Background Services (Celery)                              │
│  ├── Email Processing Worker                               │
│  ├── PDF Generation Service                                │
│  ├── File Processing Pipeline                              │
│  └── Print Job Manager                                     │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                │
│  ├── SQLite3 Database                                      │
│  ├── Redis (Celery Broker)                                 │
│  └── Local File Storage                                    │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack Selection

### Selected Stack: React + Django + SQLite3

#### Frontend
```javascript
// Technology Stack
React 18 + JavaScript/TypeScript
Vite (Build Tool)
Tailwind CSS (Styling)
React Query/TanStack Query (State Management)
WebSocket (Real-time)
React Hook Form (Forms)
React Router (Routing)

// Key Libraries
axios                    // HTTP client
date-fns                // Date manipulation
react-hot-toast         // Notifications
lucide-react            // Icons
@headlessui/react       // UI components
```

#### Backend
```python
# Technology Stack
Django 4.2+ + Python 3.11
Django REST Framework (API)
Django Channels (WebSocket)
Celery (Background Jobs)
Django ORM (Database)
SQLite3 (Database)

# Key Libraries
imaplib                 # Email processing (reuse existing)
weasyprint             # PDF generation
Pillow                 # Image processing
requests               # HTTP client
redis                  # Job queue (for Celery)
django-cors-headers    # CORS handling
djangorestframework-simplejwt  # JWT authentication
```

#### Why This Stack?
- **Django**: Robust, mature framework with excellent ORM and admin interface
- **SQLite3**: Lightweight, serverless database perfect for single-user or small team deployments
- **React**: Modern frontend with excellent ecosystem
- **Reuse Existing Logic**: Can directly port Python email processing code
- **Simplified Deployment**: No complex database setup required
- **Cost Effective**: Minimal infrastructure requirements

## Database Schema Design

### Django Models
```python
# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EmailConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_config')
    email_address = models.EmailField()
    password_encrypted = models.TextField()
    imap_server = models.CharField(max_length=255, default='imap.gmail.com')
    allowed_senders = models.JSONField(default=list)  # Store as JSON array
    max_email_age_days = models.IntegerField(default=10)
    sleep_time = models.IntegerField(default=60)
    auto_start = models.BooleanField(default=False)
    body_printer = models.CharField(max_length=255, blank=True)
    attachment_printer = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ProcessingHistory(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processing_history')
    email_id = models.CharField(max_length=255)
    po_number = models.CharField(max_length=100, blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    sender_email = models.EmailField()
    subject = models.TextField(blank=True)
    processed_at = models.DateTimeField(default=timezone.now)
    folder_path = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='completed')
    error_message = models.TextField(blank=True, null=True)
    attachments_count = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'processed_at']),
            models.Index(fields=['po_number']),
            models.Index(fields=['status']),
        ]
        ordering = ['-processed_at']

class ProcessedEmail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processed_emails')
    email_id = models.CharField(max_length=255)
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'email_id']
        indexes = [
            models.Index(fields=['user', 'email_id']),
        ]

class FileAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    processing_history = models.ForeignKey(
        ProcessingHistory, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, blank=True)
    file_path = models.TextField()
    file_size = models.BigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    is_printed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['processing_history']),
        ]

class PrintJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='print_jobs')
    file_attachment = models.ForeignKey(
        FileAttachment, 
        on_delete=models.CASCADE, 
        related_name='print_jobs'
    )
    printer_name = models.CharField(max_length=255)
    print_settings = models.JSONField(default=dict)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    scheduled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'scheduled_at']),
        ]

class SystemSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settings')
    setting_key = models.CharField(max_length=100)
    setting_value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'setting_key']
```

### Database Migration Commands
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## API Design

### Django REST API Endpoints

#### Authentication (using DRF + JWT)
```python
# urls.py
POST   /api/auth/login/            # Login and get JWT tokens
POST   /api/auth/register/         # Register new user
POST   /api/auth/logout/           # Logout (blacklist token)
POST   /api/auth/token/refresh/    # Refresh JWT token
GET    /api/auth/profile/          # Get user profile
PUT    /api/auth/profile/          # Update user profile
```

#### Email Configuration
```python
GET    /api/config/email/          # Get email settings
PUT    /api/config/email/          # Update email settings
POST   /api/config/email/test/     # Test email connection
GET    /api/config/printers/       # Get available printers
```

#### Email Processing
```python
POST   /api/processing/start/      # Start email processing
POST   /api/processing/stop/       # Stop email processing
GET    /api/processing/status/     # Get processing status
POST   /api/processing/manual/     # Manual email check
```

#### History and Files
```python
GET    /api/history/               # Get processing history (paginated)
GET    /api/history/{id}/          # Get specific history entry
DELETE /api/history/{id}/          # Delete history entry
GET    /api/files/{id}/            # Download file
POST   /api/files/{id}/print/      # Print file
```

#### System
```python
GET    /api/system/health/         # Health check
GET    /api/system/stats/          # System statistics
PUT    /api/system/settings/       # Update system settings
```

### Django Channels WebSocket Events
```python
# WebSocket event types for Django Channels
# Client to Server
{
    "type": "start_processing",
    "data": {}
}
{
    "type": "stop_processing", 
    "data": {}
}
{
    "type": "subscribe_to_updates",
    "data": {"room": "user_updates"}
}

# Server to Client
{
    "type": "processing_started",
    "data": {"message": "Email processing started", "timestamp": "..."}
}
{
    "type": "processing_stopped",
    "data": {"message": "Email processing stopped", "timestamp": "..."}
}
{
    "type": "email_processed",
    "data": {"po_number": "12345", "customer_name": "John Doe", "status": "completed"}
}
{
    "type": "error_occurred",
    "data": {"message": "Error message", "error_type": "connection_error"}
}
{
    "type": "status_update",
    "data": {"message": "Processing email 3 of 5", "progress": 60}
}
{
    "type": "new_order_detected",
    "data": {"po_number": "12345", "sender": "steve@moretranz.com"}
}
```

## Component Migration Strategy

### 1. Email Processing Service

#### Current Implementation
```python
# Desktop: main.py - process_emails()
def process_emails():
    while is_running:
        # IMAP connection management
        # Email fetching and parsing
        # Attachment downloading
        # File organization
        # Printing
```

#### Django + Celery Implementation
```python
# tasks.py - Celery background tasks
from celery import shared_task
from django.contrib.auth import get_user_model
from .models import EmailConfig, ProcessingHistory
from .services.email_processor import EmailProcessor
import imaplib
import time

User = get_user_model()

@shared_task(bind=True)
def process_emails_task(self, user_id):
    """Background task to process emails for a user"""
    try:
        user = User.objects.get(id=user_id)
        config = user.email_config
        processor = EmailProcessor(user, config)
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(config.imap_server)
        mail.login(config.email_address, decrypt_password(config.password_encrypted))
        mail.select("inbox")
        
        while processor.is_running:
            try:
                # Search for unseen emails
                status, messages = mail.search(None, 'UNSEEN')
                email_ids = messages[0].split()
                
                if email_ids:
                    # Process each email
                    for email_id in email_ids:
                        process_single_email_task.delay(user_id, email_id.decode())
                        
                    # Send WebSocket update
                    send_websocket_update.delay(user_id, {
                        'type': 'status_update',
                        'data': {'message': f'Processing {len(email_ids)} emails'}
                    })
                
                time.sleep(config.sleep_time)
                
            except Exception as e:
                # Handle errors and retry
                send_websocket_update.delay(user_id, {
                    'type': 'error_occurred',
                    'data': {'message': str(e)}
                })
                raise self.retry(countdown=60, max_retries=3)
                
    except Exception as e:
        # Log error and notify user
        send_websocket_update.delay(user_id, {
            'type': 'error_occurred',
            'data': {'message': f'Email processing failed: {str(e)}'}
        })

@shared_task
def process_single_email_task(user_id, email_id):
    """Process a single email"""
    user = User.objects.get(id=user_id)
    processor = EmailProcessor(user, user.email_config)
    return processor.process_single_email(email_id)
```

### 2. File Management System

#### Current Implementation
```python
# Desktop: Filesystem operations
folder_path = os.path.join(attachments_base_folder, f"{po_number}_{customer_name}")
os.makedirs(folder_path, exist_ok=True)
```

#### Django Implementation
```python
# services/file_manager.py
import os
import shutil
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import FileAttachment, ProcessingHistory

class FileManager:
    def __init__(self):
        self.base_path = os.path.join(settings.MEDIA_ROOT, 'attachments')
        os.makedirs(self.base_path, exist_ok=True)
    
    def create_order_folder(self, po_number, customer_name):
        """Create folder structure for order"""
        folder_name = f"{po_number}_{customer_name.replace(' ', '_')}"
        folder_path = os.path.join(self.base_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
    
    def save_attachment(self, processing_history, filename, file_content):
        """Save attachment to local storage"""
        # Create relative path for database storage
        relative_path = os.path.join(
            'attachments', 
            os.path.basename(processing_history.folder_path),
            filename
        )
        
        # Save file using Django's file storage
        file_path = default_storage.save(relative_path, ContentFile(file_content))
        
        # Create database record
        attachment = FileAttachment.objects.create(
            processing_history=processing_history,
            filename=filename,
            original_filename=filename,
            file_path=file_path,
            file_size=len(file_content),
            content_type=self.get_content_type(filename)
        )
        
        return attachment
    
    def get_file_path(self, attachment):
        """Get absolute file path"""
        return os.path.join(settings.MEDIA_ROOT, attachment.file_path)
    
    def get_content_type(self, filename):
        """Determine content type from filename"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.html': 'text/html'
        }
        return content_types.get(ext, 'application/octet-stream')
```

### 3. PDF Generation Service

#### Current Implementation
```python
# Desktop: wkhtmltopdf + ReportLab
def convert_html_to_pdf(html_file_path, pdf_file_path):
    command = [WKHTMLTOPDF_PATH, '--page-size', 'Letter', ...]
    subprocess.run(command)
```

#### Django Implementation
```python
# services/pdf_generator.py
import os
import tempfile
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from weasyprint import HTML, CSS
from PIL import Image
import subprocess

class PDFGenerator:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def convert_html_to_pdf(self, html_content, output_path=None, options=None):
        """Convert HTML content to PDF using WeasyPrint"""
        try:
            if not output_path:
                output_path = os.path.join(self.temp_dir, 'email_body.pdf')
            
            # Create HTML object and render to PDF
            html_doc = HTML(string=html_content)
            html_doc.write_pdf(output_path)
            
            return output_path
            
        except Exception as e:
            # Fallback to wkhtmltopdf if WeasyPrint fails
            return self.convert_html_to_pdf_wkhtmltopdf(html_content, output_path)
    
    def convert_html_to_pdf_wkhtmltopdf(self, html_content, output_path):
        """Fallback PDF conversion using wkhtmltopdf"""
        # Save HTML to temp file
        html_path = os.path.join(self.temp_dir, 'temp.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Use wkhtmltopdf command (reuse existing logic)
        wkhtmltopdf_path = os.path.join(settings.BASE_DIR, 'lib', 'wkhtmltox', 'bin', 'wkhtmltopdf.exe')
        
        command = [
            wkhtmltopdf_path,
            '--page-size', 'Letter',
            '--enable-smart-shrinking',
            '--no-outline',
            '--print-media-type',
            '--dpi', '300',
            '--enable-local-file-access',
            html_path,
            output_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return output_path
        else:
            raise Exception(f"PDF conversion failed: {result.stderr}")
    
    def convert_image_to_4x6_pdf(self, image_path, output_path=None):
        """Convert image to 4x6 PDF using ReportLab (reuse existing logic)"""
        if not output_path:
            output_path = os.path.join(self.temp_dir, 'label.pdf')
        
        # Open image
        img = Image.open(image_path)
        width_inch = 4
        height_inch = 6
        
        # Create PDF canvas
        c = canvas.Canvas(output_path, pagesize=(width_inch * inch, height_inch * inch))
        
        # Get image dimensions and DPI
        img_width, img_height = img.size
        dpi = img.info.get('dpi', (203, 203))
        dpi_x, dpi_y = dpi
        
        # Calculate scaling
        img_width_inch = img_width / dpi_x
        img_height_inch = img_height / dpi_y
        
        scale_factor_width = width_inch / img_width_inch
        scale_factor_height = height_inch / img_height_inch
        scale_factor = min(scale_factor_width, scale_factor_height)
        
        new_width = img_width_inch * scale_factor * inch
        new_height = img_height_inch * scale_factor * inch
        
        # Center the image
        x_offset = (width_inch * inch - new_width) / 2
        y_offset = (height_inch * inch - new_height) / 2
        
        # Draw image and save
        c.drawImage(image_path, x_offset, y_offset, width=new_width, height=new_height)
        c.save()
        
        return output_path
```

### 4. Printing System Migration

#### Challenge: Web Apps Cannot Access Local Printers
The biggest technical challenge in the migration is handling printing functionality.

#### Solution 1: Print Agent Service
```javascript
// Local Print Agent: printAgent.js
class PrintAgent {
    constructor() {
        this.websocket = new WebSocket('ws://localhost:8080');
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.websocket.on('print-job', async (data) => {
            const { fileUrl, printerName, settings } = data;
            
            // Download file from web app
            const fileBuffer = await this.downloadFile(fileUrl);
            
            // Save temporarily
            const tempPath = await this.saveTempFile(fileBuffer);
            
            // Print using system command
            await this.printFile(tempPath, printerName, settings);
            
            // Cleanup
            await this.deleteTempFile(tempPath);
        });
    }
    
    async printFile(filePath, printerName, settings) {
        // Windows
        if (process.platform === 'win32') {
            const command = `"${SUMATRA_PATH}" -print-to "${printerName}" -print-settings "${settings}" "${filePath}"`;
            await exec(command);
        }
        // Linux
        else if (process.platform === 'linux') {
            const command = `lpr -P ${printerName} ${filePath}`;
            await exec(command);
        }
    }
}
```

#### Solution 2: Cloud Printing Service
```javascript
// Cloud Print Service: cloudPrint.js
class CloudPrintService {
    async submitPrintJob(fileBuffer, printerConfig) {
        // Integration with services like:
        // - Google Cloud Print (deprecated)
        // - PrintNode API
        // - Ezeep Blue
        // - PaperCut Mobility Print
        
        const printJob = {
            file: fileBuffer,
            printer: printerConfig.cloudPrinterId,
            settings: printerConfig.settings
        };
        
        return await this.printService.submit(printJob);
    }
}
```

### 5. Real-time Updates System

#### Current Implementation
```python
# Desktop: Direct GUI updates
def update_status(message):
    status_label.config(text=message)
    status_label.update_idletasks()
```

#### Web Implementation
```javascript
// WebSocket Service: realtimeService.js
class RealtimeService {
    constructor(io) {
        this.io = io;
    }
    
    emitToUser(userId, event, data) {
        this.io.to(`user:${userId}`).emit(event, data);
    }
    
    broadcastProcessingUpdate(userId, update) {
        this.emitToUser(userId, 'processing_update', {
            timestamp: new Date(),
            message: update.message,
            type: update.type,
            data: update.data
        });
    }
}

// Frontend: useRealtimeUpdates hook
function useRealtimeUpdates() {
    const [status, setStatus] = useState('idle');
    const [messages, setMessages] = useState([]);
    
    useEffect(() => {
        const socket = io();
        
        socket.on('processing_update', (update) => {
            setMessages(prev => [...prev, update]);
            setStatus(update.type);
        });
        
        return () => socket.disconnect();
    }, []);
    
    return { status, messages };
}
```

## Background Job Processing

### Job Queue Architecture
```javascript
// Job Definitions: jobs/index.js
const Queue = require('bull');
const redis = require('ioredis');

const emailQueue = new Queue('email processing', {
    redis: { host: 'localhost', port: 6379 }
});

// Job Types
const JOB_TYPES = {
    PROCESS_EMAIL: 'process-email',
    DOWNLOAD_ATTACHMENT: 'download-attachment',
    GENERATE_PDF: 'generate-pdf',
    PRINT_DOCUMENT: 'print-document'
};

// Email Processing Job
emailQueue.process(JOB_TYPES.PROCESS_EMAIL, async (job) => {
    const { userId, emailData } = job.data;
    
    try {
        // Extract PO information
        const poInfo = await extractPOInfo(emailData.body);
        
        // Create folder structure
        const folderPath = await createOrderFolder(poInfo.poNumber, poInfo.customerName);
        
        // Process attachments
        const attachments = await processAttachments(emailData.attachments, folderPath);
        
        // Generate email body PDF
        const bodyPdf = await generateEmailBodyPdf(emailData.body, folderPath);
        
        // Queue print jobs
        await queuePrintJobs(attachments, bodyPdf, userId);
        
        // Save to history
        await saveProcessingHistory(userId, emailData, poInfo, folderPath);
        
        // Emit real-time update
        realtimeService.broadcastProcessingUpdate(userId, {
            type: 'success',
            message: `Processed order ${poInfo.poNumber}`,
            data: { poNumber: poInfo.poNumber, folderPath }
        });
        
    } catch (error) {
        // Handle error and emit update
        realtimeService.broadcastProcessingUpdate(userId, {
            type: 'error',
            message: `Error processing email: ${error.message}`,
            data: { error: error.stack }
        });
        throw error;
    }
});
```

## Security Implementation

### Authentication & Authorization
```javascript
// JWT-based authentication
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');

class AuthService {
    async login(email, password) {
        const user = await User.findOne({ email });
        if (!user || !await bcrypt.compare(password, user.passwordHash)) {
            throw new Error('Invalid credentials');
        }
        
        const token = jwt.sign(
            { userId: user.id, email: user.email },
            process.env.JWT_SECRET,
            { expiresIn: '7d' }
        );
        
        return { token, user };
    }
    
    async authenticateToken(req, res, next) {
        const token = req.headers.authorization?.split(' ')[1];
        
        if (!token) {
            return res.status(401).json({ error: 'Access denied' });
        }
        
        try {
            const decoded = jwt.verify(token, process.env.JWT_SECRET);
            req.user = decoded;
            next();
        } catch (error) {
            res.status(403).json({ error: 'Invalid token' });
        }
    }
}
```

### Email Credential Encryption
```javascript
// Encrypt sensitive email credentials
const crypto = require('crypto');

class CredentialManager {
    encrypt(text) {
        const cipher = crypto.createCipher('aes-256-cbc', process.env.ENCRYPTION_KEY);
        let encrypted = cipher.update(text, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        return encrypted;
    }
    
    decrypt(encryptedText) {
        const decipher = crypto.createDecipher('aes-256-cbc', process.env.ENCRYPTION_KEY);
        let decrypted = decipher.update(encryptedText, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        return decrypted;
    }
}
```

## Performance Optimization

### Caching Strategy
```javascript
// Redis caching for frequently accessed data
class CacheService {
    constructor() {
        this.redis = new Redis(process.env.REDIS_URL);
    }
    
    async getEmailConfig(userId) {
        const cached = await this.redis.get(`email_config:${userId}`);
        if (cached) return JSON.parse(cached);
        
        const config = await EmailConfig.findOne({ userId });
        await this.redis.setex(`email_config:${userId}`, 300, JSON.stringify(config));
        
        return config;
    }
    
    async invalidateUserCache(userId) {
        const keys = await this.redis.keys(`*:${userId}`);
        if (keys.length > 0) {
            await this.redis.del(...keys);
        }
    }
}
```

### Database Optimization
```python
# settings.py - SQLite3 configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
            'init_command': '''
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA temp_store=memory;
                PRAGMA mmap_size=268435456;
            '''
        }
    }
}

# Connection pooling for SQLite (django-db-pool)
DATABASES = {
    'default': {
        'ENGINE': 'django_db_pool.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 10,
        }
    }
}

# Query optimization examples
# Use select_related for foreign keys
ProcessingHistory.objects.select_related('user').filter(user_id=user_id)

# Use prefetch_related for many-to-many or reverse foreign keys
ProcessingHistory.objects.prefetch_related('attachments').filter(user_id=user_id)

# Add database indexes in models (already included above)
```

## Deployment Architecture

### Infrastructure Requirements
```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SECRET_KEY=your-secret-key
      - DJANGO_DEBUG=False
      - REDIS_URL=redis://redis:6379
      - DATABASE_PATH=/app/data/db.sqlite3
    volumes:
      - sqlite_data:/app/data
      - media_files:/app/media
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  celery_worker:
    build: ./backend
    command: celery -A orderprocessor worker --loglevel=info
    environment:
      - DJANGO_SECRET_KEY=your-secret-key
      - REDIS_URL=redis://redis:6379
      - DATABASE_PATH=/app/data/db.sqlite3
    volumes:
      - sqlite_data:/app/data
      - media_files:/app/media
    depends_on:
      - redis
      - backend
  
  celery_beat:
    build: ./backend
    command: celery -A orderprocessor beat --loglevel=info
    environment:
      - DJANGO_SECRET_KEY=your-secret-key
      - REDIS_URL=redis://redis:6379
      - DATABASE_PATH=/app/data/db.sqlite3
    volumes:
      - sqlite_data:/app/data
    depends_on:
      - redis
      - backend

volumes:
  sqlite_data:
  redis_data:
  media_files:
```

### Simplified Deployment (Single Server)
```bash
# Simple deployment without Docker
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic

# Start services
python manage.py runserver 0.0.0.0:8000 &
celery -A orderprocessor worker --loglevel=info &
celery -A orderprocessor beat --loglevel=info &

# Frontend setup
cd ../frontend
npm install
npm run build
# Serve with nginx or copy to Django static files
```

### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install Python dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run Django tests
        run: |
          cd backend
          python manage.py test
      
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm install
      
      - name: Run frontend tests
        run: |
          cd frontend
          npm run test
          npm run build
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to VPS
        run: |
          # Deploy to your VPS or cloud provider
          # Copy files, restart services, etc.
          echo "Deploy to production server"
```

## Migration Timeline

### Phase 1: Foundation (Weeks 1-2)
- [ ] Setup Django project with SQLite3
- [ ] Create database models and migrations
- [ ] Implement JWT authentication with DRF
- [ ] Setup React frontend with Vite
- [ ] Configure Celery with Redis
- [ ] Setup Django Channels for WebSocket

### Phase 2: Core Email Processing (Weeks 3-4)
- [ ] Port existing IMAP email processing logic
- [ ] Create Celery tasks for background processing
- [ ] Implement email parsing and PO extraction
- [ ] Setup local file storage system
- [ ] Create basic dashboard with real-time updates

### Phase 3: Advanced Features (Weeks 5-6)
- [ ] Port PDF generation (WeasyPrint + ReportLab)
- [ ] Implement print system (local agent or download)
- [ ] Build settings management interface
- [ ] Create processing history with search/filter
- [ ] Add error handling and logging

### Phase 4: Testing & Deployment (Weeks 7-8)
- [ ] Unit and integration testing
- [ ] Performance optimization for SQLite3
- [ ] Security review and hardening
- [ ] Docker containerization
- [ ] Production deployment and migration

## Testing Strategy

### Backend Testing (Django)
```python
# tests/test_email_processing.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from orderprocessor.models import EmailConfig, ProcessingHistory
from orderprocessor.services.email_processor import EmailProcessor

User = get_user_model()

class EmailProcessingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.email_config = EmailConfig.objects.create(
            user=self.user,
            email_address='test@gmail.com',
            password_encrypted='encrypted_password',
            imap_server='imap.gmail.com',
            allowed_senders=['steve@moretranz.com']
        )
    
    @patch('orderprocessor.services.email_processor.imaplib.IMAP4_SSL')
    def test_process_valid_email_with_attachments(self, mock_imap):
        """Test processing a valid email with attachments"""
        # Mock email data
        mock_email_body = 'PO Number: 12345\nDelivery address: John Doe'
        
        processor = EmailProcessor(self.user, self.email_config)
        result = processor.process_single_email('mock_email_id')
        
        # Verify processing history was created
        history = ProcessingHistory.objects.filter(user=self.user).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.po_number, '12345')
        self.assertEqual(history.customer_name, 'John Doe')
    
    def test_po_number_extraction(self):
        """Test PO number extraction from email body"""
        processor = EmailProcessor(self.user, self.email_config)
        
        test_cases = [
            ('PO Number: 12345', '12345'),
            ('Original PO - 67890', '67890'),
            ('Replacement PO - 11111-R', '11111-R'),
        ]
        
        for body, expected_po in test_cases:
            po_info = processor.extract_po_info(body)
            self.assertEqual(po_info['po_number'], expected_po)

# tests/test_api.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

class APITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_processing_history(self):
        """Test retrieving processing history"""
        url = reverse('processing-history-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_start_email_processing(self):
        """Test starting email processing"""
        url = reverse('start-processing')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### Frontend Testing
```javascript
// React component tests
import { render, screen, waitFor } from '@testing-library/react';
import Dashboard from './Dashboard';

test('displays processing history', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
        expect(screen.getByText('Processing History')).toBeInTheDocument();
    });
});
```

### End-to-End Testing
```javascript
// Playwright E2E tests
test('complete order processing workflow', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('[data-testid="start-processing"]');
    
    // Wait for email processing
    await page.waitForSelector('[data-testid="processing-complete"]');
    
    // Verify order appears in history
    await expect(page.locator('[data-testid="order-12345"]')).toBeVisible();
});
```

## Risk Mitigation

### Technical Risks
1. **Email Connection Reliability**
   - Implement robust retry mechanisms
   - Connection pooling and health checks
   - Fallback to webhook-based email services

2. **File Storage Reliability** 
   - Multi-region storage replication
   - Automatic backup systems
   - File integrity verification

3. **Printing System Complexity**
   - Multiple printing solution options
   - Gradual rollout with fallback
   - Comprehensive testing across platforms

### Operational Risks
1. **Data Migration**
   - Export/import tools for existing data
   - Parallel running during transition
   - Rollback procedures

2. **User Adoption**
   - Training materials and documentation
   - Gradual feature rollout
   - User feedback integration

3. **Performance Under Load**
   - Load testing and optimization
   - Auto-scaling infrastructure
   - Performance monitoring

## Monitoring and Observability

### Application Monitoring
```javascript
// Monitoring setup with Winston + DataDog
const winston = require('winston');
const DatadogWinston = require('datadog-winston');

const logger = winston.createLogger({
    transports: [
        new winston.transports.Console(),
        new DatadogWinston({
            apiKey: process.env.DATADOG_API_KEY,
            hostname: 'orderprocessor-api',
            service: 'email-processing'
        })
    ]
});

// Usage in email processing
logger.info('Email processing started', {
    userId,
    emailId: email.id,
    timestamp: new Date()
});
```

### Health Checks
```javascript
// Health check endpoints
app.get('/health', async (req, res) => {
    const checks = {
        database: await checkDatabase(),
        redis: await checkRedis(),
        emailService: await checkEmailService(),
        fileStorage: await checkFileStorage()
    };
    
    const isHealthy = Object.values(checks).every(check => check.status === 'ok');
    
    res.status(isHealthy ? 200 : 503).json({
        status: isHealthy ? 'healthy' : 'unhealthy',
        checks,
        timestamp: new Date()
    });
});
```

## Conclusion

This technical migration guide provides a comprehensive roadmap for converting the desktop Moretranz Order Processor to a modern web application. The proposed architecture maintains all existing functionality while adding scalability, multi-user support, and cloud-based operations.

Key success factors:
- **Phased migration approach** minimizes risk
- **Multiple printing solutions** address the biggest technical challenge
- **Robust error handling** ensures reliability
- **Comprehensive testing** validates functionality
- **Performance optimization** handles scale
- **Security best practices** protect sensitive data

The estimated timeline of 8 weeks provides a realistic path to production deployment while maintaining high quality standards and thorough testing throughout the process.

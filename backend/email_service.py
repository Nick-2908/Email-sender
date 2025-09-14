# backend/email_service.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import ssl
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    """Service for sending emails through various providers"""
    
    def __init__(self, provider: str = "gmail"):
        self.provider = provider.lower()
        self.smtp_config = self._get_smtp_config()
    
    def _get_smtp_config(self) -> Dict:
        """Get SMTP configuration based on provider"""
        configs = {
            "gmail": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True
            },
            "outlook": {
                "smtp_server": "smtp-mail.outlook.com", 
                "smtp_port": 587,
                "use_tls": True
            },
            "yahoo": {
                "smtp_server": "smtp.mail.yahoo.com",
                "smtp_port": 587,
                "use_tls": True
            },
            "custom": {
                "smtp_server": os.getenv("CUSTOM_SMTP_SERVER", ""),
                "smtp_port": int(os.getenv("CUSTOM_SMTP_PORT", "587")),
                "use_tls": os.getenv("CUSTOM_USE_TLS", "true").lower() == "true"
            }
        }
        
        return configs.get(self.provider, configs["gmail"])
    
    def send_email(self, 
                   subject: str, 
                   body: str, 
                   recipients: List[str],
                   sender_email: Optional[str] = None,
                   sender_password: Optional[str] = None,
                   is_html: bool = False) -> Dict:
        """
        Send email using SMTP
        
        Args:
            subject: Email subject
            body: Email body content
            recipients: List of recipient email addresses
            sender_email: Sender's email (if not provided, uses env variable)
            sender_password: Sender's password/app password (if not provided, uses env variable)
            is_html: Whether the body is HTML content
            
        Returns:
            Dict with success status and message
        """
        
        # Get credentials
        sender_email = sender_email or os.getenv("EMAIL_USERNAME")
        sender_password = sender_password or os.getenv("EMAIL_PASSWORD")
        
        if not sender_email or not sender_password:
            return {
                "success": False,
                "message": "Email credentials not provided. Check EMAIL_USERNAME and EMAIL_PASSWORD in .env file"
            }
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = sender_email
            message["To"] = ", ".join(recipients)
            
            # Add body
            if is_html:
                body_part = MIMEText(body, "html")
            else:
                body_part = MIMEText(body, "plain")
            
            message.attach(body_part)
            
            # Create SMTP session
            with smtplib.SMTP(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"]) as server:
                if self.smtp_config["use_tls"]:
                    server.starttls(context=ssl.create_default_context())
                
                # Login and send email
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, message.as_string())
            
            return {
                "success": True,
                "message": f"Email sent successfully to {len(recipients)} recipient(s)"
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "Email authentication failed. Check your email and password/app password."
            }
        except smtplib.SMTPRecipientsRefused:
            return {
                "success": False,
                "message": "One or more recipients were refused. Check email addresses."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            }
    
    def test_connection(self, 
                       sender_email: Optional[str] = None,
                       sender_password: Optional[str] = None) -> Dict:
        """Test email connection without sending"""
        
        sender_email = sender_email or os.getenv("EMAIL_USERNAME")
        sender_password = sender_password or os.getenv("EMAIL_PASSWORD")
        
        if not sender_email or not sender_password:
            return {
                "success": False,
                "message": "Email credentials not provided"
            }
        
        try:
            with smtplib.SMTP(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"]) as server:
                if self.smtp_config["use_tls"]:
                    server.starttls(context=ssl.create_default_context())
                server.login(sender_email, sender_password)
            
            return {
                "success": True,
                "message": f"Successfully connected to {self.provider} email server"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }

# Email service instance
email_service = EmailService()
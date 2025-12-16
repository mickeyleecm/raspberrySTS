#!/usr/bin/env python3
"""
Email Sender Module
A reusable class for sending emails via SMTP.
Can be used by other programs to send notification emails.
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from pathlib import Path


class EmailSender:
    """
    A reusable email sender class for sending emails via SMTP.
    
    Supports:
    - SMTP with TLS/SSL
    - Authentication (username/password)
    - Plain text and HTML emails
    - Email attachments
    - Multiple recipients (TO, CC, BCC)
    """
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int = 587,
        use_tls: bool = True,
        use_ssl: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ):
        """
        Initialize the EmailSender.
        
        Args:
            smtp_server: SMTP server hostname or IP address
            smtp_port: SMTP server port (default: 587 for TLS, 465 for SSL)
            use_tls: Use TLS encryption (default: True)
            use_ssl: Use SSL encryption (default: False, mutually exclusive with TLS)
            username: SMTP username for authentication (optional)
            password: SMTP password for authentication (optional)
            from_email: Default sender email address (optional, can be overridden per email)
            from_name: Default sender name (optional, can be overridden per email)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        if use_tls and use_ssl:
            raise ValueError("Cannot use both TLS and SSL. Choose one.")
        
        if use_ssl and smtp_port != 465:
            self.logger.warning(f"SSL is typically used with port 465, but port {smtp_port} is configured.")
        
        if use_tls and smtp_port == 465:
            self.logger.warning("Port 465 typically uses SSL, but TLS is configured.")
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            body_html: HTML email body (optional, if provided, email will be multipart)
            from_email: Sender email address (uses default if not provided)
            from_name: Sender name (uses default if not provided)
            cc_emails: List of CC email addresses (optional)
            bcc_emails: List of BCC email addresses (optional)
            attachments: List of file paths to attach (optional)
            reply_to: Reply-to email address (optional)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Determine sender email and name
            sender_email = from_email or self.from_email
            sender_name = from_name or self.from_name
            
            if not sender_email:
                raise ValueError("Sender email address is required. Set from_email parameter or configure default in __init__")
            
            # Create message
            if body_html:
                msg = MIMEMultipart('alternative')
            else:
                msg = MIMEMultipart()
            
            # Set headers
            if sender_name:
                msg['From'] = f"{sender_name} <{sender_email}>"
            else:
                msg['From'] = sender_email
            
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add body
            if body_html:
                # Add both plain text and HTML versions
                part1 = MIMEText(body, 'plain')
                part2 = MIMEText(body_html, 'html')
                msg.attach(part1)
                msg.attach(part2)
            else:
                # Plain text only
                msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    self._add_attachment(msg, file_path)
            
            # Get all recipients (TO + CC + BCC)
            all_recipients = list(to_emails)
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            # Send email
            return self._send_via_smtp(msg, all_recipients)
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}", exc_info=True)
            return False
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """
        Add an attachment to the email message.
        
        Args:
            msg: MIMEMultipart message object
            file_path: Path to the file to attach
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Attachment file not found: {file_path}")
            
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {file_path_obj.name}'
            )
            msg.attach(part)
            self.logger.debug(f"Added attachment: {file_path_obj.name}")
            
        except Exception as e:
            self.logger.error(f"Error adding attachment {file_path}: {e}")
            raise
    
    def _send_via_smtp(self, msg: MIMEMultipart, recipients: List[str]) -> bool:
        """
        Send email via SMTP server.
        
        Args:
            msg: MIMEMultipart message object
            recipients: List of all recipient email addresses
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create SMTP connection
            if self.use_ssl:
                # SSL connection
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
            else:
                # Regular SMTP connection
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Enable debug output (optional, can be removed in production)
            # server.set_debuglevel(1)
            
            # Start TLS if configured
            if self.use_tls:
                server.starttls()
            
            # Authenticate if credentials provided
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Send email
            server.send_message(msg, to_addrs=recipients)
            server.quit()
            
            self.logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            self.logger.error(f"SMTP recipients refused: {e}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            self.logger.error(f"SMTP server disconnected: {e}")
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            return False
    
    def send_simple_email(
        self,
        to_email: str,
        subject: str,
        body: str
    ) -> bool:
        """
        Convenience method to send a simple email to a single recipient.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        return self.send_email(
            to_emails=[to_email],
            subject=subject,
            body=body
        )


# Example usage
if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example 1: Gmail configuration
    # email_sender = EmailSender(
    #     smtp_server='smtp.gmail.com',
    #     smtp_port=587,
    #     use_tls=True,
    #     username='your-email@gmail.com',
    #     password='your-app-password',  # Use App Password, not regular password
    #     from_email='your-email@gmail.com',
    #     from_name='Your Name'
    # )
    
    # Example 2: Outlook/Office 365 configuration
    # email_sender = EmailSender(
    #     smtp_server='smtp.office365.com',
    #     smtp_port=587,
    #     use_tls=True,
    #     username='your-email@outlook.com',
    #     password='your-password',
    #     from_email='your-email@outlook.com',
    #     from_name='Your Name'
    # )
    
    # Example 3: Custom SMTP server
    # email_sender = EmailSender(
    #     smtp_server='mail.example.com',
    #     smtp_port=587,
    #     use_tls=True,
    #     username='user@example.com',
    #     password='password',
    #     from_email='user@example.com',
    #     from_name='System Notifications'
    # )
    
    # Send a simple email
    # success = email_sender.send_simple_email(
    #     to_email='recipient@example.com',
    #     subject='Test Email',
    #     body='This is a test email from the EmailSender class.'
    # )
    
    # Send an email with HTML content
    # success = email_sender.send_email(
    #     to_emails=['recipient@example.com'],
    #     subject='Test Email with HTML',
    #     body='Plain text version',
    #     body_html='<html><body><h1>HTML version</h1><p>This is the HTML version.</p></body></html>'
    # )
    
    # Send an email with attachments
    # success = email_sender.send_email(
    #     to_emails=['recipient@example.com'],
    #     subject='Test Email with Attachment',
    #     body='Please find the attachment.',
    #     attachments=['/path/to/file.pdf']
    # )
    
    print("EmailSender class is ready to use.")
    print("Uncomment the examples above and configure with your SMTP settings to test.")


#!/usr/bin/env python3
"""
Example usage of the EmailSender class.
This demonstrates how to use the EmailSender in your programs.
Uses email_config.json for configuration.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from email_sender import EmailSender

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Default config file path
DEFAULT_CONFIG_FILE = 'email_config.json'


def load_email_config(config_file: str = DEFAULT_CONFIG_FILE) -> Optional[Dict[str, Any]]:
    """
    Load email configuration from JSON file.
    
    Args:
        config_file: Path to configuration file
    
    Returns:
        Dictionary with email configuration or None if file doesn't exist or is invalid
    """
    config_path = Path(config_file)
    if not config_path.exists():
        logging.warning(f"Email config file not found: {config_file}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logging.info(f"Loaded email configuration from {config_file}")
        return config
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Failed to load email config from {config_file}: {e}")
        return None


def get_email_config(config_file: str = DEFAULT_CONFIG_FILE) -> Dict[str, Any]:
    """
    Get email configuration, loading from file or using defaults.
    
    Args:
        config_file: Path to configuration file
    
    Returns:
        Dictionary with email configuration
    """
    config = load_email_config(config_file)
    
    if config:
        return config
    else:
        # Return default values if config file not found
        logging.warning(f"Using default email configuration (config file not found)")
        return {
            'smtp_server': '192.168.111.22',
            'smtp_port': 25,
            'smtp_use_tls': True,
            'smtp_username': '',
            'smtp_password': '',
            'from_email': 'micky.lee@netsphere.com.hk',
            'from_name': 'Micky.Lee',
            'email_recipients': ['micky.lee@netsphere.com.hk']
        }


# Load email configuration
EMAIL_CONFIG = get_email_config()


def example_basic_usage():
    """Example: Basic email sending."""
    # Initialize EmailSender with configuration from email_config.json
    email_sender = EmailSender(
        smtp_server=EMAIL_CONFIG['smtp_server'],
        smtp_port=EMAIL_CONFIG['smtp_port'],
        use_tls=EMAIL_CONFIG['smtp_use_tls'],
        username=EMAIL_CONFIG.get('smtp_username', ''),
        password=EMAIL_CONFIG.get('smtp_password', ''),
        from_email=EMAIL_CONFIG['from_email'],
        from_name=EMAIL_CONFIG.get('from_name', '')
    )
    
    # Use first recipient from config, or default
    to_email = EMAIL_CONFIG['email_recipients'][0] if EMAIL_CONFIG.get('email_recipients') else 'micky.lee@netsphere.com.hk'
    
    # Send a simple email
    success = email_sender.send_simple_email(
        to_email=to_email,
        subject='Test Email',
        body='This is a test email from the EmailSender class.'
    )
    
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")


def example_advanced_usage():
    """Example: Advanced email with HTML, CC, BCC, and attachments."""
    # Initialize EmailSender with configuration from email_config.json
    email_sender = EmailSender(
        smtp_server=EMAIL_CONFIG['smtp_server'],
        smtp_port=EMAIL_CONFIG['smtp_port'],
        use_tls=EMAIL_CONFIG['smtp_use_tls'],
        username=EMAIL_CONFIG.get('smtp_username', ''),
        password=EMAIL_CONFIG.get('smtp_password', ''),
        from_email=EMAIL_CONFIG['from_email'],
        from_name=EMAIL_CONFIG.get('from_name', '')
    )
    
    # Use recipients from config, or default
    recipients = EMAIL_CONFIG.get('email_recipients', ['micky.lee@netsphere.com.hk'])
    
    # Send email with HTML content, multiple recipients, and attachments
    success = email_sender.send_email(
        to_emails=recipients,
        subject='Important Notification',
        body='Plain text version of the email.',
        body_html='''
        <html>
            <body>
                <h1>Important Notification</h1>
                <p>This is the <b>HTML version</b> of the email.</p>
                <p>You can include <a href="https://example.com">links</a> and formatting.</p>
            </body>
        </html>
        ''',
        cc_emails=recipients if len(recipients) > 1 else None,
        bcc_emails=None,
        attachments=['C:/Users/micky.lee/Downloads/test.pdf'],  # Update path as needed
        reply_to=EMAIL_CONFIG['from_email']
    )
    
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")


def example_ups_notification():
    """Example: How to use EmailSender with UPS trap receiver."""
    # Initialize EmailSender with configuration from email_config.json
    email_sender = EmailSender(
        smtp_server=EMAIL_CONFIG['smtp_server'],
        smtp_port=EMAIL_CONFIG['smtp_port'],
        use_tls=EMAIL_CONFIG['smtp_use_tls'],
        username=EMAIL_CONFIG.get('smtp_username', ''),
        password=EMAIL_CONFIG.get('smtp_password', ''),
        from_email=EMAIL_CONFIG['from_email'],
        from_name=EMAIL_CONFIG.get('from_name', '')
    )
    
    # Example: Send notification when UPS trap is received
    trap_info = {
        'source': '192.168.1.100:162',
        'trap_name': 'upsTrapOnBattery',
        'description': 'UPS switched to battery power',
        'timestamp': '2024-01-15 10:30:45'
    }
    
    subject = f"UPS Alert: {trap_info['trap_name']}"
    body = f"""
UPS Alert Notification

Timestamp: {trap_info['timestamp']}
Source: {trap_info['source']}
Trap Name: {trap_info['trap_name']}
Description: {trap_info['description']}

Please check your UPS system immediately.
    """
    
    body_html = f"""
    <html>
        <body>
            <h2 style="color: red;">UPS Alert Notification</h2>
            <table border="1" cellpadding="5">
                <tr><td><b>Timestamp:</b></td><td>{trap_info['timestamp']}</td></tr>
                <tr><td><b>Source:</b></td><td>{trap_info['source']}</td></tr>
                <tr><td><b>Trap Name:</b></td><td>{trap_info['trap_name']}</td></tr>
                <tr><td><b>Description:</b></td><td>{trap_info['description']}</td></tr>
            </table>
            <p><b>Please check your UPS system immediately.</b></p>
        </body>
    </html>
    """
    
    # Use recipients from config
    recipients = EMAIL_CONFIG.get('email_recipients', ['micky.lee@netsphere.com.hk'])
    
    success = email_sender.send_email(
        to_emails=recipients,
        subject=subject,
        body=body,
        body_html=body_html
    )
    
    return success


if __name__ == '__main__':
    print("EmailSender Usage Examples")
    print("=" * 50)
    print(f"\nUsing configuration from: {DEFAULT_CONFIG_FILE}")
    print(f"SMTP Server: {EMAIL_CONFIG['smtp_server']}")
    print(f"From Email: {EMAIL_CONFIG['from_email']}")
    print(f"Recipients: {', '.join(EMAIL_CONFIG.get('email_recipients', []))}")
    print("\n1. Basic Usage:")
    print("   Uncomment example_basic_usage() to send a simple test email")
    print("\n2. Advanced Usage:")
    print("   Uncomment example_advanced_usage() for HTML, attachments, etc.")
    print("\n3. UPS Notification Example:")
    print("   Uncomment example_ups_notification() to see integration example")
    print("\nNote: Edit email_config.json to change SMTP settings.")
    
    # Uncomment to run examples:
    example_basic_usage()
    #example_advanced_usage()
    #example_ups_notification()


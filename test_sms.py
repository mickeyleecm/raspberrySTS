#!/usr/bin/env python3
"""
SMS Test Script for UPS SNMP Trap Receiver
Tests SMS sending functionality using configuration from config.py
"""

import sys
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime


def load_sms_config():
    """Load SMS configuration from config.py"""
    try:
        import importlib.util
        # Get the directory where this script is located
        script_dir = Path(__file__).resolve().parent
        config_path = script_dir / 'config.py'
        
        if not config_path.exists():
            print(f"ERROR: config.py not found at {config_path}")
            print(f"       Script directory: {script_dir}")
            print(f"       Current working directory: {Path.cwd()}")
            return None
        
        spec = importlib.util.spec_from_file_location("ups_config", config_path)
        ups_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ups_config)
        
        config = {
            'enabled': getattr(ups_config, 'SMS_ENABLED', False),
            'api_url': getattr(ups_config, 'SMS_API_URL', None),
            'username': getattr(ups_config, 'SMS_USERNAME', None),
            'password': getattr(ups_config, 'SMS_PASSWORD', None),
            'recipients': getattr(ups_config, 'SMS_RECIPIENTS', []),
            'type': getattr(ups_config, 'SMS_TYPE', 1),
            'return_mode': getattr(ups_config, 'SMS_RETURN_MODE', 1),
        }
        
        # Ensure recipients is a list
        if not isinstance(config['recipients'], list):
            config['recipients'] = [config['recipients']] if config['recipients'] else []
        
        return config
    except Exception as e:
        print(f"ERROR: Failed to load config.py: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_sms(api_url, username, password, recipient, message, sms_type=1, return_mode=1, timeout=10):
    """
    Send SMS via HTTP GET request
    
    Args:
        api_url: SMS API base URL
        username: SMS API username
        password: SMS API password
        recipient: Mobile number to receive SMS
        message: SMS message text
        sms_type: SMS type (default: 1)
        return_mode: Return mode (default: 1)
        timeout: Request timeout in seconds (default: 10)
    
    Returns:
        tuple: (success: bool, response: str, error: str or None)
    """
    try:
        # Build URL with parameters
        params = {
            'destinatingAddress': recipient,
            'username': username,
            'password': password,
            'SMS': message,
            'type': str(sms_type),
            'returnMode': str(return_mode)
        }
        
        # Encode parameters
        query_string = urllib.parse.urlencode(params)
        full_url = f"{api_url}?{query_string}"
        
        print(f"  URL: {full_url}")
        print(f"  Message: {message}")
        print(f"  Recipient: {recipient}")
        
        # Send HTTP GET request
        print(f"  Sending SMS...")
        with urllib.request.urlopen(full_url, timeout=timeout) as response:
            response_data = response.read().decode('utf-8')
            status_code = response.getcode()
            
            print(f"  Status Code: {status_code}")
            print(f"  Response: {response_data}")
            
            # Check if request was successful (status 200)
            if status_code == 200:
                return True, response_data, None
            else:
                return False, response_data, f"HTTP status code: {status_code}"
                
    except urllib.error.URLError as e:
        error_msg = f"URL Error: {e}"
        if hasattr(e, 'reason'):
            error_msg += f" (Reason: {e.reason})"
        if hasattr(e, 'code'):
            error_msg += f" (Code: {e.code})"
        return False, None, error_msg
    except Exception as e:
        return False, None, f"Error: {e}"


def test_sms(message=None):
    """Test SMS sending with configuration from config.py"""
    print("=" * 80)
    print("SMS Test Script for UPS SNMP Trap Receiver")
    print("=" * 80)
    print()
    
    # Load configuration
    print("Loading SMS configuration from config.py...")
    config = load_sms_config()
    
    if not config:
        print("ERROR: Failed to load configuration")
        return False
    
    print(f"  SMS Enabled: {config['enabled']}")
    print(f"  API URL: {config['api_url']}")
    print(f"  Username: {config['username']}")
    print(f"  Password: {'*' * len(config['password']) if config['password'] else 'None'}")
    print(f"  Recipients: {config['recipients']}")
    print(f"  SMS Type: {config['type']}")
    print(f"  Return Mode: {config['return_mode']}")
    print()
    
    # Validate configuration
    if not config['enabled']:
        print("ERROR: SMS is disabled in config.py (SMS_ENABLED = False)")
        return False
    
    if not config['api_url']:
        print("ERROR: SMS_API_URL is not set in config.py")
        return False
    
    if not config['username']:
        print("ERROR: SMS_USERNAME is not set in config.py")
        return False
    
    if not config['password']:
        print("ERROR: SMS_PASSWORD is not set in config.py")
        return False
    
    if not config['recipients']:
        print("ERROR: SMS_RECIPIENTS is empty in config.py")
        return False
    
    # Prepare test message
    if message:
        test_message = message
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        test_message = f"UPS Alarm Testing Message - {timestamp}"
    
    print("=" * 80)
    print("Testing SMS Sending")
    print("=" * 80)
    print()
    
    # Send SMS to all recipients
    success_count = 0
    total_count = len(config['recipients'])
    
    for idx, recipient in enumerate(config['recipients'], 1):
        print(f"[{idx}/{total_count}] Testing SMS to: {recipient}")
        print("-" * 80)
        
        success, response, error = send_sms(
            api_url=config['api_url'],
            username=config['username'],
            password=config['password'],
            recipient=recipient,
            message=test_message,
            sms_type=config['type'],
            return_mode=config['return_mode']
        )
        
        if success:
            print(f"✓ SUCCESS: SMS sent to {recipient}")
            success_count += 1
        else:
            print(f"✗ FAILED: SMS to {recipient}")
            if error:
                print(f"  Error: {error}")
            if response:
                print(f"  Response: {response}")
        
        print()
    
    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total Recipients: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    
    if success_count == total_count:
        print()
        print("✓ All SMS tests passed!")
        return True
    elif success_count > 0:
        print()
        print("⚠ Some SMS tests failed. Check the errors above.")
        return False
    else:
        print()
        print("✗ All SMS tests failed. Please check:")
        print("  1. SMS configuration in config.py")
        print("  2. Internet connectivity")
        print("  3. SMS API service availability")
        print("  4. Username and password are correct")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test SMS sending functionality for UPS SNMP Trap Receiver',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default message
  python3 test_sms.py
  
  # Test with custom message
  python3 test_sms.py --message "Custom test message"
  
  # Test with alarm-like message
  python3 test_sms.py --message "[CRITICAL] UPS Alert: lowBattery - SEVERE: The UPS batteries are low"
        """
    )
    
    parser.add_argument(
        '--message', '-m',
        type=str,
        default=None,
        help='Custom test message (default: auto-generated test message)'
    )
    
    args = parser.parse_args()
    
    try:
        success = test_sms(message=args.message)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


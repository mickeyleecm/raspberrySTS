#!/usr/bin/env python3
"""
Simple UDP/SNMP Trap Monitor
Monitors UDP port 162 (or custom port) for SNMP traps without requiring tcpdump or netcat.
Works with standard Python libraries only.
"""

import socket
import sys
import datetime
from typing import Optional

def monitor_udp_traps(port: int = 162, bind_ip: str = '0.0.0.0', filter_ip: Optional[str] = None):
    """
    Monitor UDP port for SNMP traps.
    
    Args:
        port: UDP port to listen on (default 162)
        bind_ip: IP address to bind to (default 0.0.0.0 = all interfaces)
        filter_ip: Optional source IP to filter (None = accept all)
    """
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Allow socket reuse (useful if port was recently used)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to port
        sock.bind((bind_ip, port))
        
        print(f"Monitoring UDP port {port} on {bind_ip}")
        if filter_ip:
            print(f"Filtering: Only showing traps from {filter_ip}")
        else:
            print("Accepting traps from all sources")
        print("Press Ctrl+C to stop")
        print("-" * 70)
        
        trap_count = 0
        
        while True:
            try:
                # Receive data (blocks until data arrives)
                data, addr = sock.recvfrom(65535)  # Max UDP packet size
                source_ip, source_port = addr
                
                # Filter by source IP if specified
                if filter_ip and source_ip != filter_ip:
                    continue
                
                trap_count += 1
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                
                print(f"\n[{timestamp}] Trap #{trap_count}")
                print(f"Source: {source_ip}:{source_port}")
                print(f"Size: {len(data)} bytes")
                print(f"Hex dump (first 200 bytes):")
                
                # Print hex dump (first 200 bytes)
                hex_str = ' '.join(f'{b:02x}' for b in data[:200])
                for i in range(0, len(hex_str), 48):
                    print(f"  {hex_str[i:i+48]}")
                
                # Try to extract some readable strings
                try:
                    # Look for SNMP-like patterns
                    if b'public' in data or b'private' in data:
                        print("  Contains SNMP community string")
                    
                    # Print ASCII representation (non-printable as '.')
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:100])
                    if any(c.isprintable() for c in ascii_str):
                        print(f"  ASCII (first 100 chars): {ascii_str}")
                except:
                    pass
                
                print("-" * 70)
                
            except KeyboardInterrupt:
                print(f"\n\nStopped. Total traps received: {trap_count}")
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                continue
                
    except PermissionError:
        print(f"ERROR: Permission denied. Port {port} requires root privileges.")
        print(f"Please run with: sudo python3 {sys.argv[0]}")
        print(f"Or use a port >= 1024 (e.g., port 1162)")
        sys.exit(1)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"ERROR: Port {port} is already in use.")
            print(f"Another process may be listening on this port.")
            print(f"Check with: ss -ulnp | grep {port}")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        sock.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor UDP port for SNMP traps (no tcpdump/netcat required)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor port 162 (requires sudo)
  sudo python3 monitor_ups_traps_simple.py
  
  # Monitor custom port (no sudo needed)
  python3 monitor_ups_traps_simple.py --port 1162
  
  # Filter by source IP
  sudo python3 monitor_ups_traps_simple.py --filter-ip 192.168.1.100
  
  # Bind to specific interface
  sudo python3 monitor_ups_traps_simple.py --bind 192.168.1.50
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=162,
        help='UDP port to monitor (default: 162, requires sudo)'
    )
    
    parser.add_argument(
        '--bind', '-b',
        type=str,
        default='0.0.0.0',
        help='IP address to bind to (default: 0.0.0.0 = all interfaces)'
    )
    
    parser.add_argument(
        '--filter-ip', '-f',
        type=str,
        default=None,
        help='Only show traps from this source IP address'
    )
    
    args = parser.parse_args()
    
    monitor_udp_traps(
        port=args.port,
        bind_ip=args.bind,
        filter_ip=args.filter_ip
    )


if __name__ == '__main__':
    main()


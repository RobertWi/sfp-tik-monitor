#!/usr/bin/env python3
import pexpect
import sys
import time
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def get_sfp_password():
    """Get SFP password from pass"""
    try:
        result = subprocess.run(['pass', 'zaram/sfp/admin'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error(f"Failed to get SFP password: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error running pass command for SFP password: {e}")
        return None

# Get SFP password
SFP_PASSWORD = get_sfp_password()
if not SFP_PASSWORD:
    logging.error("Failed to get SFP password. Exiting.")
    sys.exit(1)

# Configuration
ROUTER_IP = '192.168.33.1'
ROUTER_USER = 'robert'
SFP_IP = '192.168.200.1'
SFP_USER = 'admin'  # Username for SFP module telnet access

def main():
    try:
        # Start SSH session to router
        print(f"Connecting to {ROUTER_USER}@{ROUTER_IP}...")
        child = pexpect.spawn(f'ssh {ROUTER_USER}@{ROUTER_IP}')
        
        # Handle SSH password prompt if needed
        i = child.expect(['password:', pexpect.EOF, pexpect.TIMEOUT], timeout=5)
        if i == 0:  # password prompt
            password = input("Enter SSH password: ")
            child.sendline(password)
        
        # Wait for router prompt
        child.expect(r'\[.*\] >', timeout=10)
        print("Connected to RouterOS")
        
        # Start telnet to SFP
        print(f"Starting telnet to {SFP_IP}...")
        child.sendline(f'/system telnet {SFP_IP}')
        
        # Handle telnet login
        i = child.expect(['login:', 'Connection refused', pexpect.TIMEOUT], timeout=10)
        if i == 0:  # login prompt
            print("Sending username...")
            child.sendline(SFP_USER)
            i = child.expect(['Password:', pexpect.TIMEOUT], timeout=5)
            if i == 0:  # password prompt
                print("Sending password...")
                child.sendline(SFP_PASSWORD)
                
                # Look for command prompt
                i = child.expect(['ZXOS11NPI', pexpect.TIMEOUT], timeout=5)
                if i == 0:  # found prompt
                    print("Successfully logged in to SFP module")
                    
                    # Use logging instead of separate log files
                    import logging
                    
                    def run_command(cmd):
                        logging.debug(f"Running SFP command: {cmd}")
                        child.sendline(cmd)
                        try:
                            # Look for either the prompt or error message
                            i = child.expect(['ZXOS11NPI', 'error', 'not found', 'usage'], timeout=10)
                            output = child.before.decode('utf-8', 'ignore')
                            logging.debug(f"SFP command output: {output}")
                            return output
                        except pexpect.TIMEOUT:
                            logging.error("SFP command timed out")
                            return ""
                        except Exception as e:
                            logging.error(f"Error running SFP command: {str(e)}")
                            return ""
                    
                    # Run various diagnostic commands for Zaram XGSPON
                    commands = [
                        'sfp info',  # Added sfp info command to get SFP module details
                        'onu show pon',
                        'onu show pon sync',
                        'onu show pon activation',
                        'onu show pon serdes',
                        'onu show pon counter',
                        'onu show pon optic',
                        'onu show pq',
                        'onu show pmapper',
                        'onu show sram',
                        'onu show ponlink',
                        'onu show fpga',
                        'onu show key info',
                        'onu dump counter',
                        'onu dump vlan',
                        'onu dump ptp',
                        'onu dump acl'
                    ]
                    
                    print("\nCollecting SFP module information...")
                    for cmd in commands:
                        try:
                            run_command(cmd)
                            time.sleep(1)  # Small delay between commands
                        except Exception as e:
                            print(f"Error running command '{cmd}': {str(e)}")
                    
                    print("\nData collection complete. Log saved to logs directory")
                else:
                    print("Failed to get command prompt")
            else:
                print("Password prompt not found")
        elif i == 1:  # Connection refused
            print("Telnet connection refused. Is the SFP module running a telnet server?")
        else:  # Timeout
            print("Timeout waiting for telnet login prompt")
        
    except pexpect.EOF:
        print("\nConnection closed by remote host")
    except pexpect.TIMEOUT:
        print("\nOperation timed out")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        try:
            child.close()
        except:
            pass

if __name__ == "__main__":
    main()

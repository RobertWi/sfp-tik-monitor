#!/usr/bin/env python3

import os
import re
import sys
import time
import logging
import requests
import subprocess
import paramiko
import json
from prometheus_client import Gauge, Counter, Info, start_http_server, REGISTRY
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Configure logging
import logging.handlers

# Ensure logs directory exists
import os
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            'logs/sfp_monitor.log',
            maxBytes=1024*1024,  # 1MB
            backupCount=5)
    ]
)

def get_password_from_pass():
    """Get API password from pass"""
    try:
        result = subprocess.run(['pass', 'mikrotik/rt1/api-monitor/api-monitoring'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error(f"Failed to get password: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error running pass command: {e}")
        return None

def get_direct_sfp_metrics(interface):
    """Get direct SFP metrics by running sfp info command"""
    try:
        logging.info(f"Getting direct SFP metrics for interface {interface}")
        
        # Get the current API password
        global API_PASSWORD
        if API_PASSWORD is None:
            API_PASSWORD = get_password_from_pass()
            if API_PASSWORD is None:
                logging.error("Failed to get API password")
                return None
        
        # Use run_sfp_command directly with increased timeout
        logging.info("Running 'sfp info' command directly...")
        output = run_sfp_command('sfp info', timeout=30)  # Increased timeout
        
        if not output:
            logging.error("Failed to get output from 'sfp info' command")
            return None
            
        logging.info(f"Received 'sfp info' output of length: {len(output)}")
        
        # Log the output in chunks to avoid truncation in logs
        max_chunk = 500
        for i in range(0, len(output), max_chunk):
            chunk = output[i:i+max_chunk]
            logging.debug(f"Direct SFP info output chunk {i//max_chunk+1}: {chunk}")
        
        # Parse the output and update metrics
        if parse_sfp_info(output, interface):
            logging.info("Successfully parsed and updated SFP metrics")
        else:
            logging.warning("Failed to parse SFP info output")
            # Log the first few lines to help debug parsing issues
            lines = output.split('\n')[:10]
            logging.warning(f"First 10 lines of output: {lines}")
        
        return output
        
    except Exception as e:
        logging.error(f"Error getting direct SFP metrics: {e}", exc_info=True)
        return None


def compare_sfp_metrics(interface, api_data, direct_sfp_output):
    """Compare RouterOS API SFP data with direct SFP module readings"""
    try:
        logging.info(f"Comparing SFP metrics for interface {interface}")
        
        # Get link status from API data
        link_is_up = api_data.get('running', False)
        
        # Extract direct SFP values
        direct_values = {}
        
        # Extract temperature
        temp_match = re.search(r'temperature:\s+([\d.]+)C', direct_sfp_output)
        if temp_match:
            direct_values['temperature'] = float(temp_match.group(1))
            
        # Extract supply voltage
        voltage_match = re.search(r'supply voltage:\s+([\d.]+)V', direct_sfp_output)
        if voltage_match:
            direct_values['voltage'] = float(voltage_match.group(1))
            
        # Extract tx bias current
        bias_match = re.search(r'tx bias current:\s+([\d.]+)mA', direct_sfp_output)
        if bias_match:
            direct_values['tx_bias'] = float(bias_match.group(1))
            
        # Extract tx power
        tx_power_match = re.search(r'tx output power:\s+[\d.]+mW\s+\(([\d.-]+)dBm\)', direct_sfp_output)
        if tx_power_match:
            direct_values['tx_power'] = float(tx_power_match.group(1))
            
        # Extract rx power
        rx_power_match = re.search(r'rx optical power:\s+[\d.]+mW\s+\(([\d.-]+)dBm\)', direct_sfp_output)
        if rx_power_match:
            direct_values['rx_power'] = float(rx_power_match.group(1))
        
        # Get API values
        api_values = {}
        if 'sfp-temperature' in api_data:
            api_values['temperature'] = float(api_data['sfp-temperature'].rstrip('C'))
        if 'sfp-supply-voltage' in api_data:
            api_values['voltage'] = float(api_data['sfp-supply-voltage'].rstrip('V'))
        if 'sfp-tx-bias-current' in api_data:
            api_values['tx_bias'] = float(api_data['sfp-tx-bias-current'].rstrip('mA'))
        if 'sfp-tx-power' in api_data:
            api_values['tx_power'] = float(api_data['sfp-tx-power'].rstrip('dBm'))
        if 'sfp-rx-power' in api_data:
            api_values['rx_power'] = float(api_data['sfp-rx-power'].rstrip('dBm'))
        
        # Compare values and log discrepancies
        for key in set(direct_values.keys()).intersection(set(api_values.keys())):
            diff = abs(direct_values[key] - api_values[key])
            threshold = 1.0  # 1 unit difference threshold (1 dBm, 1°C, etc.)
            
            if key in ['rx_power', 'tx_power']:
                threshold = 2.0  # 2 dBm threshold for power readings
                
            if diff > threshold:
                logging.warning(f"[WARNING] Significant difference in {key} readings for {interface}: ")
                logging.warning(f"  - API value: {api_values[key]}")
                logging.warning(f"  - Direct SFP value: {direct_values[key]}")
                logging.warning(f"  - Difference: {diff}")
                
                # Mark data as potentially stale if link is down but values differ significantly
                if not link_is_up:
                    if key == 'rx_power':
                        sfp_data_stale.labels(interface=interface, metric_type='rx_power').set(1)
                    elif key == 'tx_power':
                        sfp_data_stale.labels(interface=interface, metric_type='tx_power').set(1)
                        
        return direct_values, api_values
        
    except Exception as e:
        logging.error(f"Error comparing SFP metrics: {e}", exc_info=True)
        return None, None

def get_pon_metrics(interface):
    """Get comprehensive PON and direct SFP metrics for the given interface"""
    try:
        # Run the pexpect script to get SFP module data
        logging.info(f"Running pexpect script for interface {interface}")
        output = subprocess.check_output([sys.executable, 'pexpect_sfp.py'], text=True)
        
        # Parse the output to get the OLT vendor ID
        vendor_id, vendor_name = parse_olt_vendor_id(output)
        if vendor_id:
            # Convert vendor_id to decimal for the metric (removing '0x' prefix if present)
            vendor_id_decimal = int(vendor_id.replace('0x', ''), 16)
            
            # Set the vendor ID metric with vendor name as a label
            mikrotik_olt_vendor_id.labels(interface=interface, vendor_name=vendor_name).set(vendor_id_decimal)
            logging.info(f"Set OLT vendor ID for {interface}: {vendor_id} ({vendor_name})")
            
            # Track vendor ID changes using global variables
            global last_vendor_id, last_vendor_name
            
            if last_vendor_id is None:
                logging.info(f"Initial OLT vendor detected: {vendor_name} (ID: {vendor_id})")
            elif vendor_id != last_vendor_id:
                logging.warning(f"OLT Vendor ID changed from {last_vendor_name} ({last_vendor_id}) to {vendor_name} ({vendor_id})")
                
            # Update the global tracking variables
            last_vendor_id = vendor_id
            last_vendor_name = vendor_name
        
        # Get direct SFP metrics using the sfp info command
        get_direct_sfp_metrics(interface)
        
        # Get PON FEC statistics
        logging.info("Fetching PON FEC statistics...")
        fec_output = run_sfp_command('onu show pon counter')
        if fec_output:
            logging.info(f"Received FEC output of length: {len(fec_output)}")
            logging.debug(f"FEC output: {fec_output}")
            
            # Check if we have the FEC statistics section
            if 'PON Rx FEC statistic' in fec_output:
                logging.info("Found PON Rx FEC statistic section")
                
                # Extract the FEC statistics section
                fec_section_match = re.search(r'PON Rx FEC statistic.*?-{5,}(.*?)-{5,}', fec_output, re.DOTALL)
                if fec_section_match:
                    fec_section = fec_section_match.group(1)
                    logging.info(f"Extracted FEC section: {fec_section}")
                    
                    # Extract FEC statistics from the PON Rx FEC statistic section
                    metrics = {
                        'corrected_bytes': r'Corrected byte.*?:\s*(\d+)',
                        'corrected_codewords': r'Corrected code words.*?:\s*(\d+)',
                        'uncorrectable_codewords': r'Uncorrectable code words.*?:\s*(\d+)',
                        'total_codewords': r'Total code words.*?:\s*(\d+)'
                    }
                    
                    for name, pattern in metrics.items():
                        match = re.search(pattern, fec_section)
                        if match:
                            value = float(match.group(1))
                            logging.info(f"Found FEC metric {name}: {value}")
                            if name == 'corrected_bytes':
                                pon_fec_corrected_bytes.labels(interface=interface).set(value)
                            elif name == 'corrected_codewords':
                                pon_fec_corrected_codewords.labels(interface=interface).set(value)
                            elif name == 'uncorrectable_codewords':
                                pon_fec_uncorrectable_codewords.labels(interface=interface).set(value)
                            elif name == 'total_codewords':
                                pon_fec_total_codewords.labels(interface=interface).set(value)
                        else:
                            logging.warning(f"Could not find FEC metric {name} in FEC section")
                else:
                    logging.warning("Could not extract FEC statistics section")
            else:
                logging.warning("PON Rx FEC statistic section not found in output")
        
        # Get PON link status
        link_output = run_sfp_command('onu show ponlink')
        if link_output:
            logging.debug(f"PON link output: {link_output}")
            match = re.search(r'ponlink-status\s*:\s*(\S+)', link_output)
            if match:
                status = match.group(1).strip()
                logging.info(f"Found PON link status: {status}")
                if status == 'connect-OK':
                    pon_link_status.labels(interface=interface).set(1)
                else:
                    pon_link_status.labels(interface=interface).set(0)
            else:
                logging.warning("Could not find PON link status in output")
                pon_link_status.labels(interface=interface).set(0)
        
        # Get SerDes state
        serdes_output = run_sfp_command('onu show pon serdes')
        if serdes_output:
            logging.debug(f"SerDes output: {serdes_output}")
            match = re.search(r'Serdes state\s+\|\s+([\w\s]+)\((0x[0-9a-fA-F]+)\)', serdes_output)
            if match:
                serdes_state = match.group(1).strip()
                serdes_value = int(match.group(2), 16)
                logging.info(f"Found SerDes state: {serdes_state} ({hex(serdes_value)})")
                pon_serdes_state.labels(interface=interface).set(serdes_value)
                pon_serdes_text.labels(interface=interface).info({'state': serdes_state})
            else:
                logging.warning("Could not find SerDes state in output")
        
    except Exception as e:
        logging.error(f"Error getting PON metrics: {e}")
        return None

# Get API credentials
API_PASSWORD = get_password_from_pass()
if not API_PASSWORD:
    logging.error("Failed to get API password. Exiting.")
    exit(1)

# Router SSH credentials
ROUTER_IP = '192.168.33.1'
ROUTER_USER = 'robert'
SFP_IP = '192.168.200.1'
SFP_USER = 'admin'
SFP_PASS = 'zrmt123!@#'

# Initialize metrics
# SFP Physical metrics
sfp_rx_power = Gauge('mikrotik_sfp_rx_power', 'SFP RX power in dBm', ['interface'])
sfp_tx_power = Gauge('mikrotik_sfp_tx_power', 'SFP TX power in dBm', ['interface'])
sfp_temperature = Gauge('mikrotik_sfp_temperature', 'SFP temperature in Celsius', ['interface'])
sfp_voltage = Gauge('mikrotik_sfp_voltage', 'SFP supply voltage in Volts', ['interface'])
sfp_tx_bias = Gauge('mikrotik_sfp_tx_bias_current', 'SFP TX bias current in mA', ['interface'])
sfp_link_status = Gauge('mikrotik_sfp_link_status', 'SFP link status (1=UP, 2=DOWN)', ['interface'])

# SFP data quality metrics
sfp_data_stale = Gauge('mikrotik_sfp_data_stale', 'Indicates if SFP data might be stale (1=stale, 0=fresh)', ['interface', 'metric_type'])
sfp_last_verified = Gauge('mikrotik_sfp_last_verified', 'Timestamp when SFP data was last verified as accurate', ['interface'])

# Direct SFP module readings (from sfp info command)
sfp_direct_rx_power = Gauge('mikrotik_sfp_direct_rx_power', 'SFP RX power in dBm from direct SFP module reading', ['interface'])
sfp_direct_tx_power = Gauge('mikrotik_sfp_direct_tx_power', 'SFP TX power in dBm from direct SFP module reading', ['interface'])
sfp_direct_temperature = Gauge('mikrotik_sfp_direct_temperature', 'SFP temperature in Celsius from direct SFP module reading', ['interface'])
sfp_direct_voltage = Gauge('mikrotik_sfp_direct_voltage', 'SFP supply voltage in Volts from direct SFP module reading', ['interface'])
sfp_direct_tx_bias = Gauge('mikrotik_sfp_direct_tx_bias_current', 'SFP TX bias current in mA from direct SFP module reading', ['interface'])
sfp_diagnostic_type = Gauge('mikrotik_sfp_diagnostic_type', 'SFP diagnostic monitoring type (hex value)', ['interface'])
sfp_xgspon_identifier = Gauge('mikrotik_sfp_xgspon_identifier', 'SFP XGSPON identifier present (1=yes, 0=no)', ['interface'])

# PON FEC Metrics
pon_fec_corrected_bytes = Gauge('mikrotik_pon_fec_corrected_bytes', 'Number of bytes corrected by FEC', ['interface'])
pon_fec_corrected_codewords = Gauge('mikrotik_pon_fec_corrected_codewords', 'Number of code words corrected by FEC', ['interface'])
pon_fec_uncorrectable_codewords = Gauge('mikrotik_pon_fec_uncorrectable_codewords', 'Number of uncorrectable code words', ['interface'])
pon_fec_total_codewords = Gauge('mikrotik_pon_fec_total_codewords', 'Total number of received code words', ['interface'])
pon_serdes_state = Gauge('mikrotik_pon_serdes_state', 'PON SerDes state (hex value)', ['interface'])
pon_serdes_text = Info('mikrotik_pon_serdes_text', 'PON SerDes state text description', ['interface'])
pon_link_status = Gauge('mikrotik_pon_link_status', 'PON link status (1=UP, 0=DOWN)', ['interface'])

# PON Module Diagnostic Metrics (from direct SFP info)
pon_temperature = Gauge('mikrotik_pon_temperature', 'PON module temperature in Celsius', ['interface'])
pon_voltage = Gauge('mikrotik_pon_voltage', 'PON module supply voltage in Volts', ['interface'])
pon_tx_bias = Gauge('mikrotik_pon_tx_bias_current', 'PON module TX bias current in mA', ['interface'])
pon_rx_power = Gauge('mikrotik_pon_rx_power', 'PON module RX power in dBm', ['interface'])
pon_tx_power = Gauge('mikrotik_pon_tx_power', 'PON module TX power in dBm', ['interface'])

# System Metrics
system_cpu_usage = Gauge('mikrotik_system_cpu_usage', 'System CPU usage percentage', ['interface'])
system_memory_usage = Gauge('mikrotik_system_memory_usage', 'System memory usage percentage', ['interface'])
system_memory_used = Gauge('mikrotik_system_memory_used', 'System memory used in bytes', ['interface'])
system_memory_total = Gauge('mikrotik_system_memory_total', 'Total system memory in bytes', ['interface'])
interface_link_downs = Counter('mikrotik_interface_link_downs_total', 'Total number of times the link went down', ['interface'])
interface_last_link_up = Gauge('mikrotik_interface_last_link_up_timestamp', 'Timestamp of last link up event', ['interface'])
interface_last_link_down = Gauge('mikrotik_interface_last_link_down_timestamp', 'Timestamp of last link down event', ['interface'])

# SFP Detailed Error Metrics
sfp_rx_too_short = Counter('mikrotik_sfp_rx_too_short_total', 'Frames received that were shorter than the minimum permitted size', ['interface'])
sfp_rx_too_long = Counter('mikrotik_sfp_rx_too_long_total', 'Frames received that were longer than the maximum permitted size', ['interface'])
sfp_rx_fcs_error = Counter('mikrotik_sfp_rx_fcs_error_total', 'Frames received with Frame Check Sequence error', ['interface'])
sfp_rx_fragment = Counter('mikrotik_sfp_rx_fragment_total', 'Frames received that were smaller than the minimum frame size with a bad FCS', ['interface'])
sfp_rx_overflow = Counter('mikrotik_sfp_rx_overflow_total', 'Frames not received due to lack of buffer space', ['interface'])
sfp_rx_jabber = Counter('mikrotik_sfp_rx_jabber_total', 'Frames received that were longer than the maximum permitted size with a bad FCS', ['interface'])
sfp_tx_fcs_error = Counter('mikrotik_sfp_tx_fcs_error_total', 'Frames transmitted with FCS error', ['interface'])
sfp_tx_collision = Counter('mikrotik_sfp_tx_collision_total', 'Frames transmitted with collisions', ['interface'])
sfp_tx_excessive_collision = Counter('mikrotik_sfp_tx_excessive_collision_total', 'Frames not transmitted due to excessive collisions', ['interface'])
sfp_tx_late_collision = Counter('mikrotik_sfp_tx_late_collision_total', 'Late collisions detected', ['interface'])
sfp_tx_deferred = Counter('mikrotik_sfp_tx_deferred_total', 'Frames for which the first transmission attempt was delayed', ['interface'])

# Interface metrics
interface_rx_bytes = Gauge('mikrotik_interface_rx_bytes_total', 'Total received bytes', ['interface'])
interface_tx_bytes = Gauge('mikrotik_interface_tx_bytes_total', 'Total transmitted bytes', ['interface'])
interface_rx_packets = Counter('mikrotik_interface_rx_packets_total', 'Total received packets', ['interface'])
interface_tx_packets = Counter('mikrotik_interface_tx_packets_total', 'Total transmitted packets', ['interface'])

# Error metrics (for both interfaces)
interface_rx_errors = Counter('mikrotik_interface_rx_errors_total', 'Total receive errors', ['interface'])
interface_tx_errors = Counter('mikrotik_interface_tx_errors_total', 'Total transmit errors', ['interface'])
interface_rx_drops = Counter('mikrotik_interface_rx_drops_total', 'Total receive drops', ['interface'])
interface_tx_drops = Counter('mikrotik_interface_tx_drops_total', 'Total transmit drops', ['interface'])
interface_tx_queue_drops = Counter('mikrotik_interface_tx_queue_drops_total', 'Total transmit queue drops', ['interface'])

# FastPath metrics
interface_fp_rx_bytes = Counter('mikrotik_interface_fp_rx_bytes_total', 'FastPath total received bytes', ['interface'])
interface_fp_tx_bytes = Counter('mikrotik_interface_fp_tx_bytes_total', 'FastPath total transmitted bytes', ['interface'])
interface_fp_rx_packets = Counter('mikrotik_interface_fp_rx_packets_total', 'FastPath total received packets', ['interface'])
interface_fp_tx_packets = Counter('mikrotik_interface_fp_tx_packets_total', 'FastPath total transmitted packets', ['interface'])

# OLT Vendor ID metrics
mikrotik_olt_vendor_id = Gauge('mikrotik_olt_vendor_id', 'OLT Vendor ID (hex as decimal)', ['interface', 'vendor_name'])

# Track last seen vendor ID
last_vendor_id = None
last_vendor_name = None

# OLT Vendor ID mapping based on hack-gpon.org/vendor/
OLT_VENDOR_MAP = {
    # Common vendors - exact IDs from hack-gpon.org
    "0x5a54": "ZTE",         # ZTE - ZXHN
    "0x5a53": "ZTE",         # ZTE - C320/C300
    "0x5a58": "ZTE",         # ZTE - C600
    "0x5a49": "Zaram",       # Zaram
    "0x4853": "Huawei",      # Huawei - SmartAX
    "0x4855": "Huawei",      # Huawei - MA5800
    "0x5448": "FiberHome",   # FiberHome
    "0x5443": "FiberHome",   # FiberHome - AN5506-04
    "0x544e": "Dasan",       # Dasan
    "0x4348": "CIG",         # CIG
    "0x4643": "Ubiquiti",    # Ubiquiti
    "0x4e4f": "Nokia",       # Nokia
    "0x414c": "Alcatel",     # Alcatel-Lucent
    "0x414c434c": "Alcatel", # Alcatel-Lucent variant (ALCC)
    "0x5343": "Sercomm",     # Sercomm
    "0x4243": "Broadcom",    # Broadcom
    "0x4343": "Calix",       # Calix
    "0x4253": "BSCOM",       # BSCOM
    "0x5444": "V-SOL",       # V-SOL
    "0x5355": "Sumitomo",    # Sumitomo
    "0x4f4e": "ODI",         # ODI
    "0x4353": "Commscope",   # Commscope
    "0x4349": "Cisco",       # Cisco
    "0x4d54": "Motorola",    # Motorola
    "0x4453": "D-Link",      # D-Link
    "0x4749": "Genexis",     # Genexis
    "0x4248": "BT",          # BT
    "0x4953": "Iskratel",    # Iskratel
    "0x4e45": "NEC"          # NEC
}

def get_vendor_name(vendor_id):
    """Convert vendor ID hex to vendor name"""
    # First check our comprehensive mapping
    if vendor_id.lower() in OLT_VENDOR_MAP:
        return OLT_VENDOR_MAP[vendor_id.lower()]
    
    # Legacy mappings for backward compatibility
    legacy_vendor_map = {
        '5a5445': 'ZTE',
        '465354': 'FiberHome',
        '4e4f4b49': 'Nokia',
        '49534b4d': 'Iskratel',
        '4e4543': 'NEC'
    }
    return legacy_vendor_map.get(vendor_id.lower(), 'Unknown')

def parse_olt_vendor_id(output):
    """Extract OLT vendor ID from onu dump ptp command output"""
    import re
    logging.debug(f"[DEBUG] Parsing OLT vendor ID from output: {output[:200]}...")  # Log first 200 chars
    
    # Try multiple regex patterns to extract vendor ID
    patterns = [
        r'oltVendorId:\s*([0-9a-fA-F]+)',  # Standard format
        r'OLT\s+Vendor\s+ID\s*:\s*([0-9a-fA-F]+)',  # Alternative format
        r'Vendor\s+ID\s*:\s*0x([0-9a-fA-F]+)'  # Format with 0x prefix
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            vendor_id = match.group(1).lower()
            # Add 0x prefix if not present
            if not vendor_id.startswith('0x'):
                vendor_id = '0x' + vendor_id
                
            logging.debug(f"[DEBUG] Found vendor ID match: {vendor_id}")
            vendor_name = get_vendor_name(vendor_id)
            
            # Log detailed information about the vendor
            if vendor_name == 'Unknown':
                logging.warning(f"[WARNING] Unknown OLT vendor ID: {vendor_id}")
                logging.info(f"[INFO] Consider adding this vendor ID to the OLT_VENDOR_MAP dictionary")
            else:
                logging.info(f"[INFO] Identified OLT vendor: {vendor_name} (ID: {vendor_id})")
                
            return vendor_id, vendor_name
    
    logging.warning("[WARNING] No OLT vendor ID found in output")
    logging.debug(f"[DEBUG] Output sample: {output[:500]}")
    return None, None

def parse_sfp_info(output, interface):
    """Parse the output of the 'sfp info' command from direct SFP module reading"""
    try:
        logging.debug(f"[DEBUG] Parsing sfp info output for {interface}")
        logging.debug(f"[DEBUG] Raw sfp info output: {output}")
        
        # Extract diagnostic monitoring type
        diag_match = re.search(r'diagnostic monitoring type:\s+(0x[0-9a-fA-F]+)', output)
        if diag_match:
            diag_type = int(diag_match.group(1), 16)
            logging.info(f"[DEBUG] SFP diagnostic monitoring type: {diag_match.group(1)} ({diag_type})")
            sfp_diagnostic_type.labels(interface=interface).set(diag_type)
        
        # Check for XGSPON identifier
        if '47XGSPON-STICK' in output:
            logging.info(f"[DEBUG] XGSPON identifier found: 47XGSPON-STICK")
            sfp_xgspon_identifier.labels(interface=interface).set(1)
        else:
            sfp_xgspon_identifier.labels(interface=interface).set(0)
        
        # Extract temperature
        temp_match = re.search(r'temperature:\s+([\d.]+)C', output)
        if temp_match:
            temp = float(temp_match.group(1))
            logging.info(f"[DEBUG] Direct SFP temperature: {temp}°C")
            sfp_direct_temperature.labels(interface=interface).set(temp)
            # Also set the PON temperature metric
            pon_temperature.labels(interface=interface).set(temp)
        
        # Extract supply voltage
        voltage_match = re.search(r'supply voltage:\s+([\d.]+)V', output)
        if voltage_match:
            voltage = float(voltage_match.group(1))
            logging.info(f"[DEBUG] Direct SFP voltage: {voltage}V")
            sfp_direct_voltage.labels(interface=interface).set(voltage)
            # Also set the PON voltage metric
            pon_voltage.labels(interface=interface).set(voltage)
        
        # Extract tx bias current
        bias_match = re.search(r'tx bias current:\s+([\d.]+)mA', output)
        if bias_match:
            bias = float(bias_match.group(1))
            logging.info(f"[DEBUG] Direct SFP TX bias: {bias}mA")
            sfp_direct_tx_bias.labels(interface=interface).set(bias)
            # Also set the PON tx bias metric
            pon_tx_bias.labels(interface=interface).set(bias)
        
        # Extract tx power - can be in dBm or mW format
        tx_power_match = re.search(r'tx output power:\s+[\d.]+mW\s+\(([\d.-]+)dBm\)', output)
        if tx_power_match:
            tx_power = float(tx_power_match.group(1))
            logging.info(f"[DEBUG] Direct SFP TX power: {tx_power}dBm")
            sfp_direct_tx_power.labels(interface=interface).set(tx_power)
            # Also set the PON tx power metric
            pon_tx_power.labels(interface=interface).set(tx_power)
        
        # Extract rx power - can be in dBm or mW format with optional [average] suffix
        rx_power_match = re.search(r'rx optical power:\s+[\d.]+mW\s+\(([\d.-]+)dBm\)(\s+\[average\])?', output)
        if rx_power_match:
            rx_power = float(rx_power_match.group(1))
            logging.info(f"[DEBUG] Direct SFP RX power: {rx_power}dBm{' [average]' if rx_power_match.group(2) else ''}")
            sfp_direct_rx_power.labels(interface=interface).set(rx_power)
            # Also set the PON rx power metric
            pon_rx_power.labels(interface=interface).set(rx_power)
            
        return True
    except Exception as e:
        logging.error(f"[ERROR] Error parsing sfp info: {e}", exc_info=True)
        return False

def make_request(endpoint, method='GET', data=None, params=None):
    """Make an API request with optional POST data and query parameters"""
    url = f'https://rt1.home.doemijdienamespacemaar.nl/rest/{endpoint}'
    logging.debug(f"[DEBUG] Making {method} request to {url}")
    if params:
        logging.debug(f"[DEBUG] Request params: {params}")
    if data:
        logging.debug(f"[DEBUG] Request data: {data}")
        
    try:
        if method == 'GET':
            logging.debug("[DEBUG] Sending GET request")
            response = requests.get(
                url,
                verify=False,
                auth=('api-monitor', API_PASSWORD),
                timeout=10,  # Increased timeout
                params=params
            )
        else:  # POST
            logging.debug("[DEBUG] Sending POST request")
            response = requests.post(
                url,
                verify=False,
                auth=('api-monitor', API_PASSWORD),
                json=data,
                timeout=10,  # Increased timeout
                params=params
            )
            
        logging.debug(f"[DEBUG] Response status code: {response.status_code}")
        logging.debug(f"[DEBUG] Response headers: {response.headers}")
        
        # Try to parse JSON, but don't fail if it's not JSON
        try:
            json_response = response.json()
            logging.debug(f"[DEBUG] JSON response: {json_response}")
            return json_response
        except ValueError:
            logging.debug("[DEBUG] Response is not JSON")
            return response.text
            
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"[ERROR] HTTP error occurred: {http_err}")
        if 'response' in locals():
            logging.error(f"[ERROR] Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        logging.error(f"[ERROR] Request error occurred: {req_err}")
    except Exception as e:
        logging.error(f"[ERROR] Unexpected error in make_request: {e}", exc_info=True)
        
    return None

def collect_sfp_error_stats(interface_id):
    """Collect detailed SFP error statistics for a specific interface"""
    logging.info(f"[DEBUG] Starting collect_sfp_error_stats for interface ID: {interface_id}")
    
    # Get the specific interface stats directly
    logging.debug("[DEBUG] Fetching ethernet interface stats...")
    interface_data = make_request('interface/ethernet/monitor', 
                                method='POST',
                                data={'numbers': interface_id, 'duration': '1s'})
    logging.debug(f"[DEBUG] Raw interface data: {interface_data}")
    
    if not interface_data:
        logging.error("Could not get interface data")
        return
        
    # If we got a list, take the first item
    if isinstance(interface_data, list) and interface_data:
        interface_data = interface_data[0]
    
    # Get interface name from the data
    interface_name = interface_data.get('name', interface_data.get('default-name', f'unknown-{interface_id}'))
    logging.info(f"[DEBUG] Processing SFP stats for interface: {interface_name}")
    
    if not interface_name:
        logging.error(f"Could not determine interface name from data: {interface_data}")
        return
        
    interface_name = interface_data.get('name', interface_data.get('default-name', f'unknown-{interface_id}'))
    logging.info(f"[DEBUG] Processing SFP stats for interface: {interface_name}")
    
    # Log all available stats for debugging
    logging.debug(f"[DEBUG] Available stats for {interface_name}: {list(interface_data.keys())}")
    
    # Define the metrics we're interested in with their default values
    metrics = [
        # RX Errors
        ('rx-too-short', sfp_rx_too_short, 0),
        ('rx-too-long', sfp_rx_too_long, 0),
        ('rx-fcs-error', sfp_rx_fcs_error, 0),
        ('rx-fragment', sfp_rx_fragment, 0),
        ('rx-overflow', sfp_rx_overflow, 0),
        ('rx-jabber', sfp_rx_jabber, 0),
        # TX Errors
        ('tx-fcs-error', sfp_tx_fcs_error, 0),
        ('tx-collision', sfp_tx_collision, 0),
        ('tx-excessive-collision', sfp_tx_excessive_collision, 0),
        ('tx-late-collision', sfp_tx_late_collision, 0),
        ('tx-deferred', sfp_tx_deferred, 0)
    ]
    
    # Log all available metrics in the registry before updating
    logging.debug("[DEBUG] Available metrics in registry before update:")
    from prometheus_client import REGISTRY
    for name in sorted(REGISTRY._names_to_collectors):
        logging.debug(f"[DEBUG]   {name}")
    
    # Initialize all metrics with default values first
    for stat_name, metric, default_value in metrics:
        try:
            logging.debug(f"[DEBUG] Initializing {stat_name} with default value {default_value}")
            metric.labels(interface=interface_name)._value.set(default_value)
            logging.debug(f"[DEBUG] Successfully initialized {stat_name}")
        except Exception as e:
            logging.error(f"Error initializing {stat_name}: {e}")
    
    # Now update with actual values if available
    for stat_name, metric, _ in metrics:
        try:
            if stat_name in interface_data:
                value = float(interface_data[stat_name])
                logging.debug(f"[DEBUG] Setting {stat_name} to {value} for {interface_name}")
                metric.labels(interface=interface_name)._value.set(value)
                logging.debug(f"[DEBUG] Successfully set {stat_name} to {value}")
            else:
                logging.debug(f"[DEBUG] {stat_name} not found in interface data, using default value")
        except Exception as e:
            logging.error(f"Error setting {stat_name}: {e}")
    
    # Log all error-related stats for debugging
    logging.debug("[DEBUG] Error-related stats:")
    for key, value in interface_data.items():
        if any(x in key for x in ['error', 'collision', 'drop', 'fragment', 'jabber', 'overflow']):
            logging.info(f"[DEBUG] Stat {key}: {value}")
    
    # Force a collect to ensure metrics are exposed
    logging.debug("[DEBUG] Forcing metric collection...")
    for name, metric in list(REGISTRY._names_to_collectors.items()):
        if name.startswith('mikrotik_sfp_'):
            try:
                logging.debug(f"[DEBUG] Collecting metric: {name}")
                list(metric.collect())
                logging.debug(f"[DEBUG] Successfully collected metric: {name}")
            except Exception as e:
                logging.error(f"Error in collect_sfp_error_stats: {str(e)}")
    
    logging.info("[DEBUG] Finished collect_sfp_error_stats")

def run_sfp_command(command, timeout=10):
    """Run a command on the SFP module via SSH and return the output using pexpect"""
    try:
        import pexpect
        
        logging.info(f"Connecting to {ROUTER_USER}@{ROUTER_IP}...")
        child = pexpect.spawn(f'ssh {ROUTER_USER}@{ROUTER_IP}')
        
        # Handle SSH password prompt if needed
        i = child.expect(['password:', pexpect.EOF, pexpect.TIMEOUT], timeout=5)
        if i == 0:  # password prompt
            logging.info("SSH password required, using SSH key authentication")
            # If we get here, SSH key authentication failed
            child.close()
            return None
        
        # Wait for router prompt
        i = child.expect([r'\[.*\] >', pexpect.TIMEOUT], timeout=10)
        if i != 0:  # timeout or other error
            logging.error("Failed to get router prompt")
            child.close()
            return None
            
        logging.info("Connected to RouterOS")
        
        # Start telnet to SFP
        logging.info(f"Starting telnet to {SFP_IP}...")
        child.sendline(f'/system telnet {SFP_IP}')
        
        # Handle telnet login
        i = child.expect(['login:', 'Connection refused', pexpect.TIMEOUT], timeout=10)
        if i != 0:  # not login prompt
            logging.error(f"Failed to get login prompt. Got: {child.before.decode('utf-8', 'ignore')}")
            child.close()
            return None
            
        logging.info("Sending username...")
        child.sendline(SFP_USER)
        
        i = child.expect(['Password:', pexpect.TIMEOUT], timeout=5)
        if i != 0:  # timeout or other error
            logging.error("Failed to get password prompt")
            child.close()
            return None
            
        logging.info("Sending password...")
        child.sendline(SFP_PASS)
        
        # Look for command prompt
        i = child.expect(['ZXOS11NPI', pexpect.TIMEOUT], timeout=5)
        if i != 0:  # timeout or other error
            logging.error("Failed to get SFP module prompt")
            child.close()
            return None
            
        logging.info("Successfully logged in to SFP module")
        
        # Send command
        logging.info(f"Sending command: {command}")
        child.sendline(command)
        
        # Clear the buffer before capturing output
        time.sleep(0.5)
        
        # Wait for the prompt to return
        i = child.expect(['ZXOS11NPI', pexpect.TIMEOUT], timeout=timeout)
        if i != 0:  # timeout or other error
            logging.error("Command timed out or failed")
            output = child.before.decode('utf-8', 'ignore')
            logging.error(f"Partial output before timeout: {output}")
        else:
            # Get the output, but remove the command itself from the beginning
            full_output = child.before.decode('utf-8', 'ignore')
            # Remove the command from the beginning of the output
            cmd_pattern = re.escape(command) + r'\s*\r?\n'
            output = re.sub(cmd_pattern, '', full_output, count=1)
            logging.debug(f"Command raw output length: {len(full_output)}")
            logging.debug(f"Command cleaned output length: {len(output)}")
        
        # Log the first 100 characters of the output for debugging
        if output:
            logging.debug(f"Command output first 100 chars: {output[:100]}...")
            if len(output) < 50:  # If output is suspiciously short
                logging.warning(f"Command output is suspiciously short: '{output}'")
        else:
            logging.warning("Command returned empty output")
        
        # Exit telnet and close connection
        child.sendline('exit')  # exit telnet
        child.expect(r'\[.*\] >', timeout=5)
        child.sendline('quit')  # exit SSH
        child.close()
        
        return output
        
    except Exception as e:
        logging.error(f"Error in run_sfp_command: {str(e)}", exc_info=True)
        try:
            if 'child' in locals():
                child.close()
        except:
            pass
        return None

# This function has been merged with the get_pon_metrics function at line 108
# and now includes direct SFP metrics collection

def get_system_metrics():
    """Collect system metrics from the SFP module"""
    try:
        # Get CPU usage
        cpu_output = run_sfp_command('sysmon cpu')
        if cpu_output:
            match = re.search(r'cpu usage\s*:\s*([\d.]+)\s*%', cpu_output)
            if match:
                system_cpu_usage.labels(interface='pon0').set(float(match.group(1)))
        
        # Get memory usage
        mem_output = run_sfp_command('sysmon memory')
        if mem_output:
            match = re.search(r'used/total\s*=\s*(\d+)/(\d+)\s*\(([\d.]+)%\)', mem_output)
            if match:
                used = int(match.group(1))
                total = int(match.group(2))
                percent = float(match.group(3))
                system_memory_used.labels(interface='pon0').set(used)
                system_memory_total.labels(interface='pon0').set(total)
                system_memory_usage.labels(interface='pon0').set(percent)
    
    except Exception as e:
        logging.error(f"Error getting system metrics: {e}")

def collect_metrics():
    """Collect metrics from router"""
    # Get interface list
    interfaces = make_request('interface')
    if not interfaces:
        return
    
    # Collect PON and system metrics for the SFP interface
    get_pon_metrics('sfp-sfpplus1')
    get_system_metrics()
    
    for iface in interfaces:
        name = iface.get('name', '')
        if name not in ['sfp-sfpplus1', 'pppoe-wan']:
            continue
            
        logging.info(f"Processing interface: {name}")
        iface_id = iface.get('.id', '')
        
        # Update link status and link downs
        running = iface.get('running', False)
        sfp_link_status.labels(interface=name).set(1 if running else 2)
        
        # Update link down counter and timestamps
        if 'link-downs' in iface:
            try:
                link_downs = float(iface['link-downs'])
                interface_link_downs.labels(interface=name)._value.set(link_downs)
            except (ValueError, TypeError) as e:
                logging.error(f"Error converting link-downs value for {name}: {e}")
        
        # Update last link up/down timestamps
        if 'last-link-up-time' in iface:
            try:
                last_up = datetime.strptime(iface['last-link-up-time'], '%Y-%m-%d %H:%M:%S')
                interface_last_link_up.labels(interface=name).set(last_up.timestamp())
            except Exception as e:
                logging.error(f"Error parsing last-link-up-time for {name}: {e}")
                
        if 'last-link-down-time' in iface:
            try:
                last_down = datetime.strptime(iface['last-link-down-time'], '%Y-%m-%d %H:%M:%S')
                interface_last_link_down.labels(interface=name).set(last_down.timestamp())
            except Exception as e:
                logging.error(f"Error parsing last-link-down-time for {name}: {e}")
        
        # Update basic interface stats
        if 'rx-byte' in iface:
            interface_rx_bytes.labels(interface=name).set(float(iface['rx-byte']))
        if 'tx-byte' in iface:
            interface_tx_bytes.labels(interface=name).set(float(iface['tx-byte']))
        if 'rx-packet' in iface:
            interface_rx_packets.labels(interface=name)._value.set(float(iface['rx-packet']))
        if 'tx-packet' in iface:
            interface_tx_packets.labels(interface=name)._value.set(float(iface['tx-packet']))
        
        # Update error counters
        if 'rx-error' in iface:
            interface_rx_errors.labels(interface=name)._value.set(float(iface['rx-error']))
        if 'tx-error' in iface:
            interface_tx_errors.labels(interface=name)._value.set(float(iface['tx-error']))
        if 'rx-drop' in iface:
            interface_rx_drops.labels(interface=name)._value.set(float(iface['rx-drop']))
        if 'tx-drop' in iface:
            interface_tx_drops.labels(interface=name)._value.set(float(iface['tx-drop']))
        if 'tx-queue-drop' in iface:
            interface_tx_queue_drops.labels(interface=name)._value.set(float(iface['tx-queue-drop']))
            
        # Update FastPath counters
        if 'fp-rx-byte' in iface:
            interface_fp_rx_bytes.labels(interface=name)._value.set(float(iface['fp-rx-byte']))
        if 'fp-tx-byte' in iface:
            interface_fp_tx_bytes.labels(interface=name)._value.set(float(iface['fp-tx-byte']))
        if 'fp-rx-packet' in iface:
            interface_fp_rx_packets.labels(interface=name)._value.set(float(iface['fp-rx-packet']))
        if 'fp-tx-packet' in iface:
            interface_fp_tx_packets.labels(interface=name)._value.set(float(iface['fp-tx-packet']))
        
        # Get SFP data for sfp-sfpplus1
        if name == 'sfp-sfpplus1':
            logging.info(f"[DEBUG] Collecting SFP data for interface: {name} (ID: {iface_id})")
            
            # Log the exact request we're about to make
            logging.debug(f"[DEBUG] Making request to interface/ethernet/monitor with numbers={iface_id}, duration=1s")
            
            # Get SFP monitor data (power levels, temp, etc.)
            try:
                sfp_data = make_request('interface/ethernet/monitor', 
                                      method='POST',
                                      data={'numbers': iface_id, 'duration': '1s'})
                
                logging.debug(f"[DEBUG] Raw SFP monitor data type: {type(sfp_data)}")
                logging.debug(f"[DEBUG] Raw SFP monitor data: {sfp_data}")
                
                if not sfp_data:
                    logging.warning("[DEBUG] No SFP monitor data received (empty response)")
                    return
                    
                # If we got a string response instead of JSON, log it
                if isinstance(sfp_data, str):
                    logging.warning(f"[DEBUG] Received string response instead of JSON: {sfp_data}")
                    return
                
                # Handle case where we get a list of interfaces
                if isinstance(sfp_data, list):
                    logging.debug(f"[DEBUG] Received list of {len(sfp_data)} interfaces")
                    if not sfp_data:
                        logging.warning("[DEBUG] Empty list of interfaces received")
                        return
                    
                    # Try to find our interface by name or use the first one
                    sfp_data = next((iface for iface in sfp_data 
                                  if iface.get('name') == name), sfp_data[0])
                    logging.debug(f"[DEBUG] Selected interface data: {sfp_data}")
                
                # Log all available SFP data keys for debugging
                if hasattr(sfp_data, 'keys'):
                    logging.debug(f"[DEBUG] Available SFP data keys: {list(sfp_data.keys())}")
                    
                    # Log specific SFP fields we're interested in
                    for field in ['sfp-temperature', 'sfp-tx-bias-current', 'sfp-supply-voltage', 
                                'sfp-rx-power', 'sfp-tx-power', 'name', 'type', 'status']:
                        if field in sfp_data:
                            logging.debug(f"[DEBUG] SFP {field}: {sfp_data[field]}")
                else:
                    logging.warning(f"[DEBUG] SFP data is not a dictionary: {type(sfp_data)}")
                    return
                    
            except Exception as e:
                logging.error(f"[ERROR] Error in SFP data collection: {e}", exc_info=True)
                return
                
            # Get detailed SFP error statistics
            logging.debug("[DEBUG] Collecting SFP error statistics...")
            collect_sfp_error_stats(iface_id)
            
            # Process SFP metrics
            try:
                # Check if the link is actually up
                link_is_up = iface.get('running', False)
                logging.debug(f"[DEBUG] Link status for {name}: {'UP' if link_is_up else 'DOWN'}")
                
                # Get the current time for timestamp on disconnection events
                current_time = time.time()
                
                # Process SFP metrics with link state awareness
                if 'sfp-temperature' in sfp_data:
                    temp_str = sfp_data['sfp-temperature']
                    logging.debug(f"[DEBUG] Raw temperature: {temp_str}")
                    try:
                        # Handle different formats of temperature data
                        if isinstance(temp_str, str) and 'C' in temp_str:
                            temp = float(temp_str.rstrip('C'))
                        else:
                            temp = float(temp_str)
                        logging.info(f"[DEBUG] Setting RouterOS API temperature: {temp}°C")
                        sfp_temperature.labels(interface=name).set(temp)
                    except (ValueError, TypeError) as e:
                        logging.error(f"[ERROR] Failed to parse temperature '{temp_str}': {e}")
                
                if 'sfp-tx-bias-current' in sfp_data:
                    bias_str = sfp_data['sfp-tx-bias-current']
                    logging.debug(f"[DEBUG] Raw bias current: {bias_str}")
                    try:
                        # Handle different formats of bias current data
                        if isinstance(bias_str, str) and 'mA' in bias_str:
                            bias = float(bias_str.rstrip('mA'))
                        else:
                            bias = float(bias_str)
                        logging.info(f"[DEBUG] Setting RouterOS API TX bias current: {bias} mA")
                        sfp_tx_bias.labels(interface=name).set(bias)
                    except (ValueError, TypeError) as e:
                        logging.error(f"[ERROR] Failed to parse TX bias current '{bias_str}': {e}")
                
                if 'sfp-supply-voltage' in sfp_data:
                    voltage_str = sfp_data['sfp-supply-voltage']
                    logging.debug(f"[DEBUG] Raw voltage: {voltage_str}")
                    try:
                        # Handle different formats of voltage data
                        if isinstance(voltage_str, str) and 'V' in voltage_str:
                            voltage = float(voltage_str.rstrip('V'))
                        else:
                            voltage = float(voltage_str)
                        logging.info(f"[DEBUG] Setting RouterOS API supply voltage: {voltage}V")
                        sfp_voltage.labels(interface=name).set(voltage)
                    except (ValueError, TypeError) as e:
                        logging.error(f"[ERROR] Failed to parse supply voltage '{voltage_str}': {e}")
                    
                # Special handling for optical power readings when link is down
                if 'sfp-rx-power' in sfp_data:
                    rx_power_str = sfp_data['sfp-rx-power']
                    logging.debug(f"[DEBUG] Raw RX power: {rx_power_str}")
                    try:
                        # Handle different formats of RX power data
                        if isinstance(rx_power_str, str) and 'dBm' in rx_power_str:
                            rx_power = float(rx_power_str.rstrip('dBm'))
                        else:
                            rx_power = float(rx_power_str)
                        logging.debug(f"[DEBUG] Parsed RouterOS API RX power: {rx_power} dBm")
                        
                        # Add warning if link is down but power readings are present
                        if not link_is_up and rx_power > -40.0:  # -40 dBm is very low, likely noise floor
                            logging.warning(f"[WARNING] Link is DOWN but RX power reading is {rx_power} dBm. This may be cached or incorrect data!")
                            # We still set the metric but mark it as stale
                            sfp_rx_power.labels(interface=name).set(rx_power)
                            # Set stale data indicator
                            sfp_data_stale.labels(interface=name, metric_type='rx_power').set(1)
                            # Add a timestamp for when we detected this anomaly
                            logging.info(f"[INFO] Detected potential stale RX power reading at {current_time}")
                            
                            # If this is the SFP interface, try to get direct readings for comparison
                            if name == 'sfp-sfpplus1':
                                logging.info(f"[INFO] Getting direct SFP readings to compare with RouterOS API data")
                                direct_sfp_output = get_direct_sfp_metrics(name)
                                if direct_sfp_output:
                                    # Compare the values
                                    compare_sfp_metrics(name, sfp_data, direct_sfp_output)
                        else:
                            logging.info(f"[DEBUG] Setting RouterOS API RX power: {rx_power} dBm")
                            sfp_rx_power.labels(interface=name).set(rx_power)
                            # Mark data as fresh
                            sfp_data_stale.labels(interface=name, metric_type='rx_power').set(0)
                            # Update last verified timestamp
                            sfp_last_verified.labels(interface=name).set(current_time)
                    except (ValueError, TypeError) as e:
                        logging.error(f"[ERROR] Failed to parse RX power '{rx_power_str}': {e}")
                    
                if 'sfp-tx-power' in sfp_data:
                    tx_power_str = sfp_data['sfp-tx-power']
                    logging.debug(f"[DEBUG] Raw TX power: {tx_power_str}")
                    try:
                        # Handle different formats of TX power data
                        if isinstance(tx_power_str, str) and 'dBm' in tx_power_str:
                            tx_power = float(tx_power_str.rstrip('dBm'))
                        else:
                            tx_power = float(tx_power_str)
                        logging.debug(f"[DEBUG] Parsed RouterOS API TX power: {tx_power} dBm")
                        
                        # Add warning if link is down but power readings are present
                        if not link_is_up and tx_power > -40.0:  # -40 dBm is very low, likely noise floor
                            logging.warning(f"[WARNING] Link is DOWN but TX power reading is {tx_power} dBm. This may be cached or incorrect data!")
                            # We still set the metric but mark it as stale
                            sfp_tx_power.labels(interface=name).set(tx_power)
                            # Set stale data indicator
                            sfp_data_stale.labels(interface=name, metric_type='tx_power').set(1)
                            # Add a timestamp for when we detected this anomaly
                            logging.info(f"[INFO] Detected potential stale TX power reading at {current_time}")
                        else:
                            logging.info(f"[DEBUG] Setting RouterOS API TX power: {tx_power} dBm")
                            sfp_tx_power.labels(interface=name).set(tx_power)
                            # Mark data as fresh
                            sfp_data_stale.labels(interface=name, metric_type='tx_power').set(0)
                            # Update last verified timestamp
                            sfp_last_verified.labels(interface=name).set(current_time)
                    except (ValueError, TypeError) as e:
                        logging.error(f"[ERROR] Failed to parse TX power '{tx_power_str}': {e}")
            
            except Exception as e:
                logging.error(f"[ERROR] Error processing SFP metrics: {e}", exc_info=True)
                
            # Log all SFP-related metrics
            logging.debug("[DEBUG] SFP metrics after processing:")
            for key, value in sfp_data.items():
                if key.startswith('sfp-'):
                    logging.debug(f"[DEBUG]   {key}: {value}")
            
            # Get direct SFP metrics for the SFP interface
            if name == 'sfp-sfpplus1':
                get_direct_sfp_metrics(name)

def log_metric_values():
    """Debug function to log all registered metrics and their values"""
    logging.info("=== Current Prometheus Metric Values ===")
    for metric in REGISTRY._names_to_collectors.values():
        if isinstance(metric, Gauge) or isinstance(metric, Counter):
            for sample in metric._samples():
                name = sample.name
                labels = sample.labels
                value = sample.value
                label_str = ', '.join([f"{k}={v}" for k, v in labels.items()])
                logging.info(f"Metric: {name}{{{label_str}}} = {value}")
    logging.info("=========================================")

# Call log_metric_values at the end of collect_metrics
def collect_metrics_wrapper():
    collect_metrics()
    log_metric_values()

def main():
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MikroTik SFP Monitor')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind the metrics server to')
    args = parser.parse_args()
    
    # Start up the server to expose the metrics.
    start_http_server(9700, addr=args.host)
    logging.info(f"Starting Mikrotik SFP monitor... Metrics available on {args.host}:9700")
    
    # Initial delay to let the system settle
    time.sleep(5)
    
    while True:
        try:
            collect_metrics_wrapper()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            # If there's an error, wait longer before retrying
            time.sleep(60)
        else:
            # Normal polling interval
            time.sleep(30)

if __name__ == '__main__':
    main() 
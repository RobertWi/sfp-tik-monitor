#!/usr/bin/env python3

import time
import logging
import requests
import subprocess
from prometheus_client import Gauge, Counter, start_http_server
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/sfp-monitor.log')
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

# Get API credentials
API_PASSWORD = get_password_from_pass()
if not API_PASSWORD:
    logging.error("Failed to get API password. Exiting.")
    exit(1)

# Initialize metrics
sfp_rx_power = Gauge('mikrotik_sfp_rx_power', 'SFP RX power in dBm', ['interface'])
sfp_tx_power = Gauge('mikrotik_sfp_tx_power', 'SFP TX power in dBm', ['interface'])
sfp_temperature = Gauge('mikrotik_sfp_temperature', 'SFP temperature in Celsius', ['interface'])
sfp_voltage = Gauge('mikrotik_sfp_voltage', 'SFP supply voltage in Volts', ['interface'])
sfp_tx_bias = Gauge('mikrotik_sfp_tx_bias_current', 'SFP TX bias current in mA', ['interface'])
sfp_link_status = Gauge('mikrotik_sfp_link_status', 'SFP link status (1=UP, 2=DOWN)', ['interface'])
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

def make_request(endpoint, method='GET', data=None, params=None):
    """Make an API request with optional POST data and query parameters"""
    url = f'https://rt1.home.doemijdienamespacemaar.nl/rest/{endpoint}'
    try:
        if method == 'GET':
            response = requests.get(
                url,
                verify=False,
                auth=('api-monitor', API_PASSWORD),
                timeout=5,
                params=params
            )
        else:  # POST
            response = requests.post(
                url,
                verify=False,
                auth=('api-monitor', API_PASSWORD),
                json=data,
                timeout=5,
                params=params
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"API request failed: {url} - {str(e)}")
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
                logging.error(f"Error collecting {name}: {e}")
    
    logging.info("[DEBUG] Finished collect_sfp_error_stats")

def collect_metrics():
    """Collect metrics from router"""
    # Get interface list
    interfaces = make_request('interface')
    if not interfaces:
        return
    
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
            # Get SFP monitor data (power levels, temp, etc.)
            sfp_data = make_request('interface/ethernet/monitor', 
                                  method='POST',
                                  data={'numbers': iface_id, 'duration': '1s'})
            
            # Get detailed SFP error statistics
            collect_sfp_error_stats(iface_id)
            if sfp_data:
                if isinstance(sfp_data, list) and len(sfp_data) > 0:
                    sfp_data = sfp_data[0]  # Get first item if it's a list
                
                if 'sfp-temperature' in sfp_data:
                    temp = float(sfp_data['sfp-temperature'].rstrip('C'))
                    sfp_temperature.labels(interface=name).set(temp)
                
                if 'sfp-tx-bias-current' in sfp_data:
                    bias = float(sfp_data['sfp-tx-bias-current'].rstrip('mA'))
                    sfp_tx_bias.labels(interface=name).set(bias)
                
                if 'sfp-supply-voltage' in sfp_data:
                    voltage = float(sfp_data['sfp-supply-voltage'].rstrip('V'))
                    sfp_voltage.labels(interface=name).set(voltage)
                
                if 'sfp-rx-power' in sfp_data:
                    rx_power = float(sfp_data['sfp-rx-power'].rstrip('dBm'))
                    sfp_rx_power.labels(interface=name).set(rx_power)
                
                if 'sfp-tx-power' in sfp_data:
                    tx_power = float(sfp_data['sfp-tx-power'].rstrip('dBm'))
                    sfp_tx_power.labels(interface=name).set(tx_power)

def main():
    # Start up the server to expose the metrics.
    start_http_server(9700)
    logging.info("Starting Mikrotik SFP monitor... Metrics available on port 9700")
    
    while True:
        try:
            collect_metrics()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        time.sleep(30)

if __name__ == '__main__':
    main() 
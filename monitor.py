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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('monitor.log')]
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

# Interface metrics
interface_rx_bytes = Gauge('mikrotik_interface_rx_bytes_total', 'Total received bytes', ['interface'])
interface_tx_bytes = Gauge('mikrotik_interface_tx_bytes_total', 'Total transmitted bytes', ['interface'])

# Error metrics
sfp_rx_errors = Counter('mikrotik_sfp_rx_error_events_total', 'Total receive errors', ['interface'])
sfp_tx_errors = Counter('mikrotik_sfp_tx_error_events_total', 'Total transmit errors', ['interface'])
sfp_rx_drops = Counter('mikrotik_sfp_rx_drops_total', 'Total receive drops', ['interface'])
sfp_tx_drops = Counter('mikrotik_sfp_tx_drops_total', 'Total transmit drops', ['interface'])

def make_request(endpoint, method='GET', data=None):
    """Make an API request with optional POST data"""
    url = f'https://rt1.home.doemijdienamespacemaar.nl/rest/{endpoint}'
    try:
        if method == 'GET':
            response = requests.get(
                url,
                verify=False,
                auth=('api-monitor', API_PASSWORD),
                timeout=5
            )
        else:  # POST
            response = requests.post(
                url,
                verify=False,
                auth=('api-monitor', API_PASSWORD),
                json=data,
                timeout=5
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"API request failed: {url} - {str(e)}")
        return None

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
        
        # Update link status
        running = iface.get('running', False)
        sfp_link_status.labels(interface=name).set(1 if running else 2)
        
        # Update basic interface stats
        if 'rx-byte' in iface:
            interface_rx_bytes.labels(interface=name).set(float(iface['rx-byte']))
        if 'tx-byte' in iface:
            interface_tx_bytes.labels(interface=name).set(float(iface['tx-byte']))
        
        # Update error counters
        if 'rx-error' in iface:
            sfp_rx_errors.labels(interface=name).inc(float(iface['rx-error']))
        if 'tx-error' in iface:
            sfp_tx_errors.labels(interface=name).inc(float(iface['tx-error']))
        if 'rx-drop' in iface:
            sfp_rx_drops.labels(interface=name).inc(float(iface['rx-drop']))
        if 'tx-drop' in iface:
            sfp_tx_drops.labels(interface=name).inc(float(iface['tx-drop']))
        
        # Get SFP data for sfp-sfpplus1
        if name == 'sfp-sfpplus1':
            sfp_data = make_request('interface/ethernet/monitor', 
                                  method='POST',
                                  data={'numbers': iface_id, 'duration': '1s'})
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
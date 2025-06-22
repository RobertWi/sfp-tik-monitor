#!/usr/bin/env python3

import json
import logging
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib3.exceptions import InsecureRequestWarning

from config import config
from metrics_registry import routeros_metrics, collection_metrics

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class RouterOSCollector:
    """Collector for RouterOS API metrics"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.api_password = None
        self._refresh_password()
        
        # SFP vendor serial number tracking
        self.last_sfp_vendor_serial = None
    
    def _refresh_password(self):
        """Refresh the API password"""
        self.api_password = config.get_routeros_password()
        if not self.api_password:
            logging.error("Failed to get RouterOS API password")
            raise ValueError("RouterOS API password not available")
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Any]:
        """Make a request to the RouterOS API"""
        try:
            # Refresh password if needed
            if not self.api_password:
                self._refresh_password()
            
            url = f"{config.routeros_api_protocol}://{config.routeros_host}/rest/{endpoint}"
            
            if method.upper() == 'GET':
                response = self.session.get(url, auth=(config.routeros_user, self.api_password), params=params, timeout=config.api_timeout_seconds)
            elif method.upper() == 'POST':
                response = self.session.post(url, auth=(config.routeros_user, self.api_password), json=data, timeout=config.api_timeout_seconds)
            else:
                logging.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code == 401:
                logging.warning("Authentication failed, refreshing password")
                self._refresh_password()
                # Retry once with new password
                if method.upper() == 'GET':
                    response = self.session.get(url, auth=(config.routeros_user, self.api_password), params=params, timeout=config.api_timeout_seconds)
                else:
                    response = self.session.post(url, auth=(config.routeros_user, self.api_password), json=data, timeout=config.api_timeout_seconds)
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"API request timeout for endpoint: {endpoint}")
            collection_metrics.collection_errors_total.labels(collector_type='routeros', error_type='timeout').inc()
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"API request error for endpoint {endpoint}: {e}")
            collection_metrics.collection_errors_total.labels(collector_type='routeros', error_type='request_error').inc()
            return None
        except Exception as e:
            logging.error(f"Unexpected error in API request for endpoint {endpoint}: {e}")
            collection_metrics.collection_errors_total.labels(collector_type='routeros', error_type='unexpected').inc()
            return None
    
    def collect_interface_metrics(self) -> bool:
        """Collect interface metrics from RouterOS"""
        start_time = time.time()
        success = False
        
        try:
            logging.info("Collecting RouterOS interface metrics...")
            
            # Get interface list
            interfaces = self._make_request('interface')
            if not interfaces:
                logging.error("No interfaces returned from RouterOS")
                return False
            
            # Get PPPoE interfaces
            pppoe_interfaces = self._make_request('interface/pppoe-client')
            pppoe_status = {}
            if pppoe_interfaces:
                for pppoe in pppoe_interfaces:
                    pppoe_name = pppoe.get('name')
                    if pppoe_name == 'pppoe-wan':
                        pppoe_status[pppoe_name] = pppoe.get('status', 'disconnected')
                        logging.info(f"PPPoE interface: {pppoe_name} (status: {pppoe_status[pppoe_name]})")
            
            # Process monitored interfaces
            for iface in interfaces:
                name = iface.get('name', '')
                
                # Only process configured interfaces
                if name not in config.monitored_interfaces:
                    continue
                    
                logging.info(f"Processing RouterOS interface: {name}")
                
                # Handle PPPoE interface
                if name == 'pppoe-wan':
                    running = self._get_pppoe_status(pppoe_interfaces, name)
                else:
                    running = iface.get('running') == 'true' if isinstance(iface.get('running'), str) else bool(iface.get('running', False))
                
                # Update link status
                routeros_metrics.interface_link_status.labels(interface_name=name).set(1 if running else 0)
                logging.info(f"Interface {name} running state: {running}")
                
                # Update link down counter
                if 'link-downs' in iface:
                    try:
                        link_downs = float(iface['link-downs'])
                        routeros_metrics.interface_link_downs.labels(interface_name=name).set(link_downs)
                        logging.info(f"Interface {name} link-downs: {link_downs}")
                    except (ValueError, TypeError) as e:
                        logging.error(f"Error converting link-downs value for {name}: {e}")
                
                # Update last link up/down timestamps
                self._update_link_timestamps(iface, name)
                
                # Update basic interface stats
                self._update_interface_stats(iface, name)
            
            success = True
            logging.info("RouterOS interface metrics collection completed successfully")
            
        except Exception as e:
            logging.error(f"Error collecting RouterOS interface metrics: {e}")
            collection_metrics.collection_errors_total.labels(collector_type='routeros', error_type='interface_collection').inc()
        
        finally:
            # Update collection metrics
            duration = time.time() - start_time
            collection_metrics.collection_duration_seconds.labels(collector_type='routeros').set(duration)
            collection_metrics.collection_success.labels(collector_type='routeros').set(1 if success else 0)
            if success:
                collection_metrics.last_collection_timestamp.labels(collector_type='routeros').set(time.time())
        
        return success
    
    def collect_sfp_metrics(self) -> bool:
        """Collect SFP-specific metrics from RouterOS"""
        start_time = time.time()
        success = False
        
        try:
            logging.info("Collecting RouterOS SFP metrics...")
            
            # Get interface list
            interfaces = self._make_request('interface')
            if not interfaces:
                logging.error("No interfaces returned from RouterOS")
                return False
            
            # Process SFP interface
            for iface in interfaces:
                name = iface.get('name', '')
                if name != 'sfp-sfpplus1':
                    continue
                
                logging.info(f"Processing RouterOS SFP metrics for interface: {name}")
                iface_id = iface.get('.id', '')
                
                # Get SFP monitor data
                sfp_data = self._make_request('interface/ethernet/monitor', 
                                            method='POST',
                                            data={'numbers': iface_id, 'duration': '1s'})
                
                if not sfp_data:
                    logging.warning("No SFP monitor data received")
                    continue
                
                # Handle case where we get a list of interfaces
                if isinstance(sfp_data, list):
                    if not sfp_data:
                        logging.warning("Empty list of interfaces received")
                        continue
                    sfp_data = next((iface for iface in sfp_data 
                                   if iface.get('name') == name), sfp_data[0])
                
                # Process SFP metrics
                self._process_sfp_metrics(sfp_data, name)
                
                # Get detailed SFP error statistics
                self._collect_sfp_error_stats(iface_id, name)
            
            success = True
            logging.info("RouterOS SFP metrics collection completed successfully")
            
        except Exception as e:
            logging.error(f"Error collecting RouterOS SFP metrics: {e}")
            collection_metrics.collection_errors_total.labels(collector_type='routeros', error_type='sfp_collection').inc()
        
        finally:
            # Update collection metrics
            duration = time.time() - start_time
            collection_metrics.collection_duration_seconds.labels(collector_type='routeros').set(duration)
            collection_metrics.collection_success.labels(collector_type='routeros').set(1 if success else 0)
            if success:
                collection_metrics.last_collection_timestamp.labels(collector_type='routeros').set(time.time())
        
        return success
    
    def _get_pppoe_status(self, pppoe_interfaces: List[Dict], interface_name: str) -> bool:
        """Get PPPoE interface status"""
        if not pppoe_interfaces:
            logging.warning("No PPPoE interfaces found")
            return False
        
        pppoe_client = next((p for p in pppoe_interfaces if p.get('name') == interface_name), None)
        if not pppoe_client:
            logging.warning(f"No PPPoE client found for interface {interface_name}")
            return False
        
        is_running = pppoe_client.get('running', '').lower() == 'true'
        
        # For PPPoE interfaces, if the client is running, the interface is considered up
        # RouterOS PPPoE client API doesn't provide a separate 'status' field
        # The 'running' field is sufficient to determine if the PPPoE connection is active
        running = is_running
        logging.info(f"PPPoE interface {interface_name} - running: {is_running}, final status: {'UP' if running else 'DOWN'}")
        
        return running
    
    def _update_link_timestamps(self, iface: Dict, name: str):
        """Update link up/down timestamps"""
        if 'last-link-up-time' in iface:
            try:
                last_up = datetime.strptime(iface['last-link-up-time'], '%Y-%m-%d %H:%M:%S')
                routeros_metrics.interface_last_link_up.labels(interface_name=name).set(last_up.timestamp())
                logging.info(f"Interface {name} last link up: {iface['last-link-up-time']}")
            except Exception as e:
                logging.error(f"Error parsing last-link-up-time for {name}: {e}")
                
        if 'last-link-down-time' in iface:
            try:
                last_down = datetime.strptime(iface['last-link-down-time'], '%Y-%m-%d %H:%M:%S')
                routeros_metrics.interface_last_link_down.labels(interface_name=name).set(last_down.timestamp())
                logging.info(f"Interface {name} last link down: {iface['last-link-down-time']}")
            except Exception as e:
                logging.error(f"Error parsing last-link-down-time for {name}: {e}")
    
    def _update_interface_stats(self, iface: Dict, name: str):
        """Update interface statistics"""
        stats_mapping = [
            ('rx-byte', routeros_metrics.interface_rx_bytes),
            ('tx-byte', routeros_metrics.interface_tx_bytes),
            ('rx-packet', routeros_metrics.interface_rx_packets),
            ('tx-packet', routeros_metrics.interface_tx_packets),
            ('rx-error', routeros_metrics.interface_rx_errors),
            ('tx-error', routeros_metrics.interface_tx_errors),
            ('rx-drop', routeros_metrics.interface_rx_drops),
            ('tx-drop', routeros_metrics.interface_tx_drops),
            ('tx-queue-drop', routeros_metrics.interface_tx_queue_drops)
        ]
        
        for stat, metric in stats_mapping:
            if stat in iface:
                try:
                    value = float(iface[stat])
                    metric.labels(interface_name=name)._value.set(value)
                    logging.debug(f"Updated {name} {stat}: {value}")
                except (ValueError, TypeError) as e:
                    logging.error(f"Error updating {name} {stat}: {e}")
    
    def _process_sfp_metrics(self, sfp_data: Dict, name: str):
        """Process SFP module metrics"""
        current_time = time.time()
        
        # Use the status from SFP monitor data to determine link state
        # RouterOS SFP monitor provides status: "link-ok" when the link is up
        sfp_status = sfp_data.get('status', 'down').lower()
        link_is_up = sfp_status == 'link-ok'
        
        logging.info(f"SFP interface {name} - SFP monitor status: {sfp_status}, final link_is_up: {link_is_up}")
        
        # Process temperature
        if 'sfp-temperature' in sfp_data:
            temp_str = sfp_data['sfp-temperature']
            try:
                if isinstance(temp_str, str) and 'C' in temp_str:
                    temp = float(temp_str.rstrip('C'))
                else:
                    temp = float(temp_str)
                routeros_metrics.sfp_temperature.labels(interface_name=name).set(temp)
                logging.info(f"RouterOS SFP temperature: {temp}°C")
            except (ValueError, TypeError) as e:
                logging.error(f"Failed to parse temperature '{temp_str}': {e}")
        
        # Process TX bias current
        if 'sfp-tx-bias-current' in sfp_data:
            bias_str = sfp_data['sfp-tx-bias-current']
            try:
                if isinstance(bias_str, str) and 'mA' in bias_str:
                    bias = float(bias_str.rstrip('mA'))
                else:
                    bias = float(bias_str)
                routeros_metrics.sfp_tx_bias_current.labels(interface_name=name).set(bias)
                logging.info(f"RouterOS SFP TX bias current: {bias} mA")
            except (ValueError, TypeError) as e:
                logging.error(f"Failed to parse TX bias current '{bias_str}': {e}")
        
        # Process voltage
        if 'sfp-supply-voltage' in sfp_data:
            voltage_str = sfp_data['sfp-supply-voltage']
            try:
                if isinstance(voltage_str, str) and 'V' in voltage_str:
                    voltage = float(voltage_str.rstrip('V'))
                else:
                    voltage = float(voltage_str)
                routeros_metrics.sfp_voltage.labels(interface_name=name).set(voltage)
                logging.info(f"RouterOS SFP supply voltage: {voltage}V")
            except (ValueError, TypeError) as e:
                logging.error(f"Failed to parse supply voltage '{voltage_str}': {e}")
        
        # Process optical power readings
        self._process_optical_power(sfp_data, name, link_is_up, current_time)
        
        # Process SFP vendor serial number
        self._process_sfp_vendor_serial(sfp_data, name)
    
    def _process_optical_power(self, sfp_data: Dict, name: str, link_is_up: bool, current_time: float):
        """Process optical power readings with stale data detection"""
        
        # RX Power
        if 'sfp-rx-power' in sfp_data:
            rx_power_str = sfp_data['sfp-rx-power']
            try:
                if isinstance(rx_power_str, str) and 'dBm' in rx_power_str:
                    rx_power = float(rx_power_str.rstrip('dBm'))
                else:
                    rx_power = float(rx_power_str)
                
                # Check for stale data
                if not link_is_up and rx_power > config.stale_data_threshold_dbm:
                    logging.warning(f"Link is DOWN but RX power reading is {rx_power} dBm. This may be cached data!")
                    routeros_metrics.sfp_data_stale.labels(interface_name=name, metric_type='rx_power').set(1.0)
                else:
                    routeros_metrics.sfp_data_stale.labels(interface_name=name, metric_type='rx_power').set(0.0)
                
                routeros_metrics.sfp_rx_power.labels(interface_name=name).set(rx_power)
                logging.info(f"RouterOS SFP RX power: {rx_power} dBm")
                
            except (ValueError, TypeError) as e:
                logging.error(f"Failed to parse RX power value '{rx_power_str}' for {name}: {e}")
        
        # TX Power
        if 'sfp-tx-power' in sfp_data:
            tx_power_str = sfp_data['sfp-tx-power']
            try:
                if isinstance(tx_power_str, str) and 'dBm' in tx_power_str:
                    tx_power = float(tx_power_str.rstrip('dBm'))
                else:
                    tx_power = float(tx_power_str)
                
                # Check for stale data
                if not link_is_up and tx_power > config.stale_data_threshold_dbm:
                    logging.warning(f"Link is DOWN but TX power reading is {tx_power} dBm. This may be cached data!")
                    routeros_metrics.sfp_data_stale.labels(interface_name=name, metric_type='tx_power').set(1.0)
                else:
                    routeros_metrics.sfp_data_stale.labels(interface_name=name, metric_type='tx_power').set(0.0)
                
                routeros_metrics.sfp_tx_power.labels(interface_name=name).set(tx_power)
                logging.info(f"RouterOS SFP TX power: {tx_power} dBm")
                
            except (ValueError, TypeError) as e:
                logging.error(f"Failed to parse TX power value '{tx_power_str}' for {name}: {e}")
    
    def _process_sfp_vendor_serial(self, sfp_data: Dict, name: str):
        """Process SFP vendor serial number information"""
        if 'sfp-vendor-serial' in sfp_data:
            vendor_serial = sfp_data['sfp-vendor-serial']
            if vendor_serial and vendor_serial.strip():
                # Update the metric
                routeros_metrics.sfp_vendor_serial.labels(interface_name=name).info({'serial': vendor_serial})
                
                # Check for changes
                if self.last_sfp_vendor_serial is None:
                    logging.info(f"Initial SFP vendor serial detected: {vendor_serial}")
                elif vendor_serial != self.last_sfp_vendor_serial:
                    logging.warning(f"SFP vendor serial changed from {self.last_sfp_vendor_serial} to {vendor_serial}")
                
                # Update tracking variable
                self.last_sfp_vendor_serial = vendor_serial
                logging.info(f"RouterOS SFP vendor serial: {vendor_serial}")
            else:
                logging.warning(f"Empty or invalid SFP vendor serial for {name}")
        else:
            logging.debug(f"No SFP vendor serial information available for {name}")
    
    def _collect_sfp_error_stats(self, iface_id: str, name: str):
        """Collect detailed SFP error statistics"""
        try:
            # Get SFP error statistics
            error_stats = self._make_request('interface/ethernet/monitor', 
                                           method='POST',
                                           data={'numbers': iface_id, 'duration': '1s'})
            
            if not error_stats or not isinstance(error_stats, dict):
                return
            
            # Map error statistics to metrics
            error_mapping = [
                ('sfp-tx-fcs-error', routeros_metrics.sfp_tx_fcs_error),
                ('sfp-tx-collision', routeros_metrics.sfp_tx_collision),
                ('sfp-tx-excessive-collision', routeros_metrics.sfp_tx_excessive_collision),
                ('sfp-tx-late-collision', routeros_metrics.sfp_tx_late_collision),
                ('sfp-tx-deferred', routeros_metrics.sfp_tx_deferred),
                ('sfp-rx-too-short', routeros_metrics.sfp_rx_too_short),
                ('sfp-rx-too-long', routeros_metrics.sfp_rx_too_long),
                ('sfp-rx-jabber', routeros_metrics.sfp_rx_jabber),
                ('sfp-rx-fcs-error', routeros_metrics.sfp_rx_fcs_error),
                ('sfp-rx-align-error', routeros_metrics.sfp_rx_align_error),
                ('sfp-rx-fragment', routeros_metrics.sfp_rx_fragment),
                ('sfp-rx-overflow', routeros_metrics.sfp_rx_overflow),
                ('sfp-tx-underrun', routeros_metrics.sfp_tx_underrun)
            ]
            
            for stat, metric in error_mapping:
                if stat in error_stats:
                    try:
                        value = float(error_stats[stat])
                        metric.labels(interface_name=name)._value.set(value)
                        logging.debug(f"Updated {name} {stat}: {value}")
                    except (ValueError, TypeError) as e:
                        logging.error(f"Error updating {name} {stat}: {e}")
                        
        except Exception as e:
            logging.error(f"Error collecting SFP error statistics for {name}: {e}")
    
    def collect_all_metrics(self) -> bool:
        """Collect all RouterOS metrics"""
        interface_success = self.collect_interface_metrics()
        sfp_success = self.collect_sfp_metrics()
        
        return interface_success and sfp_success 
#!/usr/bin/env python3

import logging
import time
import re
import pexpect
from typing import Dict, Optional, Any, Tuple, TypeVar, Callable
from datetime import datetime
from functools import wraps

from config import Config
from metrics_registry import zaram_ont_metrics, collection_metrics

# Type variable for generic return type
T = TypeVar('T')

def retry_on_failure(max_retries: int = 3, delay: float = 1.0) -> Callable:
    """Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (will be exponentially increased)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    # For command outputs, retry if empty
                    if isinstance(result, dict) and not any(result.values()):
                        raise ValueError("All command outputs are empty")
                    if isinstance(result, str) and not result.strip():
                        raise ValueError("Command output is empty")
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
            logging.error(f"All {max_retries} attempts failed. Last error: {str(last_exception)}")
            raise last_exception
        return wrapper
    return decorator

class ZaramONTCollector:
    """Collector for Zaram ONT metrics"""

    def __init__(self):
        """Initialize the collector"""
        # Load config
        config_obj = Config()
        
        self.interface_name = config_obj.monitored_interfaces[0]  # Use first interface
        self.ssh_host = config_obj.ssh_host
        self.ssh_user = config_obj.ssh_user
        self.zaram_ont_ip = config_obj.zaram_ont_ip
        self.zaram_ont_user = config_obj.zaram_ont_user
        self.zaram_ont_password = config_obj.get_zaram_ont_password()
        if not self.zaram_ont_password:
            raise ValueError("Failed to get Zaram ONT password")
            
        self.logger = logging.getLogger(__name__)
        
        # Load OLT vendor map from config
        self.olt_vendor_map = config_obj.olt_vendor_map
        self.last_vendor_id = None
        self.last_vendor_name = None
        self.last_olt_version = None
    
    def collect_all_metrics(self) -> bool:
        """Collect all Zaram ONT metrics"""
        start_time = time.time()
        success = False
        
        try:
            logging.info("Collecting Zaram ONT metrics...")
            
            # Connect to the ONT module and collect data
            command_outputs = self._connect_and_collect()
            
            if command_outputs:
                # Process the collected data
                self._process_sfp_metrics(command_outputs)
                self._process_pon_metrics(command_outputs)
                self._process_system_metrics(command_outputs)
                self._process_olt_info(command_outputs)
                
                success = True
                logging.info("Zaram ONT metrics collection completed successfully")
            else:
                logging.error("Failed to collect data from Zaram ONT module")
        
        except Exception as e:
            logging.error(f"Error collecting Zaram ONT metrics: {e}")
            collection_metrics.collection_errors_total.labels(collector_type='zaram_ont', error_type='collection_error').inc()
        
        finally:
            # Update collection metrics
            duration = time.time() - start_time
            collection_metrics.collection_duration_seconds.labels(collector_type='zaram_ont').set(duration)
            collection_metrics.collection_success.labels(collector_type='zaram_ont').set(1 if success else 0)
            if success:
                collection_metrics.last_collection_timestamp.labels(collector_type='zaram_ont').set(time.time())
        
        return success

    def collect_regular_metrics(self) -> bool:
        """Collect regular Zaram ONT metrics (excluding OLT vendor info)"""
        start_time = time.time()
        success = False
        
        try:
            logging.info("Collecting Zaram ONT regular metrics...")
            
            # Connect to the ONT module and collect data
            command_outputs = self._connect_and_collect_regular()
            
            if command_outputs:
                # Process the collected data (excluding OLT info)
                self._process_sfp_metrics(command_outputs)
                self._process_pon_metrics(command_outputs)
                self._process_system_metrics(command_outputs)
                
                success = True
                logging.info("Zaram ONT regular metrics collection completed successfully")
            else:
                logging.error("Failed to collect regular data from Zaram ONT module")
        
        except Exception as e:
            logging.error(f"Error collecting Zaram ONT regular metrics: {e}")
            collection_metrics.collection_errors_total.labels(collector_type='zaram_ont', error_type='collection_error').inc()
        
        finally:
            # Update collection metrics
            duration = time.time() - start_time
            collection_metrics.collection_duration_seconds.labels(collector_type='zaram_ont').set(duration)
            collection_metrics.collection_success.labels(collector_type='zaram_ont').set(1 if success else 0)
            if success:
                collection_metrics.last_collection_timestamp.labels(collector_type='zaram_ont').set(time.time())
        
        return success

    def collect_olt_vendor_info(self) -> bool:
        """Collect OLT vendor information"""
        try:
            logging.info("Collecting OLT vendor information...")
            
            # Connect to the ONT module and collect data
            command_outputs = self._connect_and_collect_olt_vendor()
            
            if command_outputs:
                # Process the collected data
                self._process_olt_info(command_outputs)
                
                success = True
                logging.info("OLT vendor information collection completed successfully")
            else:
                logging.error("Failed to collect data from Zaram ONT module")
        
        except Exception as e:
            logging.error(f"Error collecting OLT vendor information: {str(e)}")
            collection_metrics.collection_errors_total.labels(collector_type='zaram_ont', error_type='collection_error').inc()
        
        finally:
            # Update collection metrics
            duration = time.time() - time.time()
            collection_metrics.collection_duration_seconds.labels(collector_type='zaram_ont').set(duration)
            collection_metrics.collection_success.labels(collector_type='zaram_ont').set(1 if success else 0)
            if success:
                collection_metrics.last_collection_timestamp.labels(collector_type='zaram_ont').set(time.time())
        
        return success
    
    def _connect_and_collect(self) -> Optional[Dict[str, str]]:
        """Connect to the ONT module and collect command outputs"""
        try:
            logging.info(f"Connecting to {self.ssh_user}@{self.ssh_host}...")
            child = pexpect.spawn(f'ssh {self.ssh_user}@{self.ssh_host}')
            
            # Handle SSH password prompt if needed (should use SSH keys)
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
            logging.info(f"Starting telnet to {self.zaram_ont_ip}...")
            child.sendline(f'/system telnet {self.zaram_ont_ip}')
            
            # Handle telnet login
            i = child.expect(['login:', 'Connection refused', pexpect.TIMEOUT], timeout=10)
            if i != 0:  # not login prompt
                error_msg = child.before.decode('utf-8', 'ignore') if child.before else 'None'
                logging.error(f"Failed to get login prompt. Got: {error_msg}")
                child.close()
                return None
                
            logging.info("Sending username...")
            child.sendline(self.zaram_ont_user)
            
            i = child.expect(['Password:', pexpect.TIMEOUT], timeout=5)
            if i != 0:  # timeout or other error
                logging.error("Failed to get password prompt")
                child.close()
                return None
                
            logging.info("Sending password...")
            if self.zaram_ont_password:
                child.sendline(self.zaram_ont_password)
            else:
                logging.error("Zaram ONT password is None")
                child.close()
                return None
            
            # Look for command prompt
            i = child.expect(['ZXOS11NPI', pexpect.TIMEOUT], timeout=5)
            if i != 0:  # timeout or other error
                logging.error("Failed to get SFP module prompt")
                child.close()
                return None
                
            logging.info("Successfully logged in to SFP module")
            
            # Run commands and collect outputs
            command_outputs = self._run_commands(child)
            
            # Exit telnet and close connection
            child.sendline('exit')  # exit telnet
            child.expect(r'\[.*\] >', timeout=5)
            child.sendline('quit')  # exit SSH
            child.close()
            
            return command_outputs
            
        except Exception as e:
            logging.error(f"Error in _connect_and_collect: {str(e)}", exc_info=True)
            try:
                if 'child' in locals():
                    child.close()
            except:
                pass
            return None
    
    def _run_commands(self, child) -> Dict[str, str]:
        """Run commands on the ONT module and return outputs"""
        command_outputs = {}
        
        # Essential commands for ONT monitoring
        commands = [
            'sfp info',              # Basic SFP module details
            'onu dump ptp',          # PTP timing info including vendor ID
            'onu show pon counter',  # FEC counters (at the end of output)
            'onu show ponlink',      # PON link status
            'onu show pon serdes',   # SerDes state
            'sysmon cpu',            # CPU usage
            'sysmon memory'          # Memory usage
        ]
        
        logging.info("Collecting ONT module information...")
        
        for cmd in commands:
            try:
                # Try up to 3 times for each command
                max_retries = 3
                retry_delay = 1.0  # Initial delay in seconds
                
                for attempt in range(max_retries):
                    logging.info(f"Running command: {cmd}" + (f" (attempt {attempt + 1}/{max_retries})" if attempt > 0 else ""))
                    
                    # Send the command - ensure cmd is str
                    cmd_str: str = str(cmd)
                    child.sendline(cmd_str)
                    
                    # Clear the buffer before capturing output
                    time.sleep(0.5)
                    
                    # Wait for the prompt to return - use the actual prompt format
                    i = child.expect([r'admin@ZXOS11NPI\s+\[/\]\s+#', r'ZXOS11NPI.*#', pexpect.TIMEOUT], timeout=10)
                    if i == 2:  # timeout
                        logging.error(f"Command '{cmd}' timed out")
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logging.warning(f"Retrying in {wait_time:.1f}s...")
                            time.sleep(wait_time)
                            continue
                        command_outputs[cmd] = ""
                        break
                    
                    # Get the output - use before which contains everything up to the prompt
                    raw_output = child.before
                    if raw_output is None:
                        full_output = ""
                    else:
                        try:
                            full_output = raw_output.decode('utf-8', 'ignore')
                        except (AttributeError, UnicodeDecodeError):
                            full_output = str(raw_output)
                    
                    # Remove the command from the beginning of the output
                    cmd_pattern = re.escape(cmd) + r'\s*\r?\n'
                    output = re.sub(cmd_pattern, '', full_output, count=1)
                    
                    # Clean up the output - remove empty lines and prompt artifacts
                    cleaned_output = '\n'.join([line.strip() for line in output.split('\n') 
                                             if line.strip() and 'admin@' not in line and 'ZXOS11NPI' not in line])
                    
                    # Check if output is too short or just contains prompt
                    if not cleaned_output or cleaned_output == '[/] #' or len(cleaned_output) < 10:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logging.warning(f"Command '{cmd}' returned empty/short output. Retrying in {wait_time:.1f}s...")
                            time.sleep(wait_time)
                            continue
                    
                    command_outputs[cmd] = cleaned_output
                    logging.debug(f"Command '{cmd}' output length: {len(cleaned_output)}")
                    if cleaned_output:
                        logging.debug(f"Command '{cmd}' output: '{cleaned_output[:200]}...'")
                    break  # Success - exit retry loop
                
                time.sleep(0.5)  # Small delay between commands
                
            except Exception as e:
                logging.error(f"Error running command '{cmd}': {str(e)}")
                command_outputs[cmd] = ""
        
        return command_outputs
    
    def _process_sfp_metrics(self, command_outputs: Dict[str, str]):
        """Process SFP module metrics from command outputs"""
        if 'sfp info' not in command_outputs:
            logging.warning("No 'sfp info' output available")
            return
        
        sfp_output = command_outputs['sfp info']
        interface_name = self.interface_name
        
        # Only log raw output if it's empty or very short (for debugging)
        if not sfp_output or len(sfp_output) < 10:
            logging.warning(f"Raw SFP info output is empty or too short: '{sfp_output}'")
            return
        
        # Parse SFP temperature - format: "temperature: 53.250C"
        temp_match = re.search(r'temperature\s*:\s*([\d.-]+)\s*C', sfp_output, re.IGNORECASE)
        if temp_match:
            try:
                temp = float(temp_match.group(1))
                zaram_ont_metrics.ont_sfp_temperature.labels(interface_name=interface_name).set(temp)
                # Only log temperature if it's high (potential issue)
                if temp > 70:
                    logging.warning(f"ONT SFP temperature high: {temp}°C")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SFP temperature: {e}")
        else:
            logging.warning("Could not find temperature in SFP info output")
        
        # Parse SFP RX power - format: "rx optical power: 0.013mW (-18.697dBm) [average]"
        rx_power_match = re.search(r'rx\s*optical\s*power\s*:\s*[\d.]+\s*mW\s*\(([\d.-]+)\s*dBm\)', sfp_output, re.IGNORECASE)
        if rx_power_match:
            try:
                rx_power = float(rx_power_match.group(1))
                zaram_ont_metrics.ont_sfp_rx_power.labels(interface_name=interface_name).set(rx_power)
                # Only log RX power if it's outside normal range (potential issue)
                if rx_power < -30 or rx_power > -8:
                    logging.warning(f"ONT SFP RX power outside normal range: {rx_power} dBm")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SFP RX power: {e}")
        else:
            logging.warning("Could not find RX power in SFP info output")
        
        # Parse SFP TX power - format: "tx output power: 4.785mW (6.799dBm)"
        tx_power_match = re.search(r'tx\s*output\s*power\s*:\s*[\d.]+\s*mW\s*\(([\d.-]+)\s*dBm\)', sfp_output, re.IGNORECASE)
        if tx_power_match:
            try:
                tx_power = float(tx_power_match.group(1))
                zaram_ont_metrics.ont_sfp_tx_power.labels(interface_name=interface_name).set(tx_power)
                # Only log TX power if it's outside normal range (potential issue)
                if tx_power < 0 or tx_power > 10:
                    logging.warning(f"ONT SFP TX power outside normal range: {tx_power} dBm")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SFP TX power: {e}")
        else:
            logging.warning("Could not find TX power in SFP info output")
        
        # Parse SFP voltage - format: "supply voltage: 3.340V"
        voltage_match = re.search(r'supply\s*voltage\s*:\s*([\d.]+)\s*V', sfp_output, re.IGNORECASE)
        if voltage_match:
            try:
                voltage = float(voltage_match.group(1))
                zaram_ont_metrics.ont_sfp_voltage.labels(interface_name=interface_name).set(voltage)
                # Only log voltage if it's outside normal range (potential issue)
                if voltage < 3.0 or voltage > 3.6:
                    logging.warning(f"ONT SFP voltage outside normal range: {voltage}V")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SFP voltage: {e}")
        else:
            logging.warning("Could not find voltage in SFP info output")
        
        # Parse SFP TX bias current - format: "tx bias current: 18.368mA"
        bias_match = re.search(r'tx\s*bias\s*current\s*:\s*([\d.]+)\s*mA', sfp_output, re.IGNORECASE)
        if bias_match:
            try:
                bias = float(bias_match.group(1))
                zaram_ont_metrics.ont_sfp_tx_bias_current.labels(interface_name=interface_name).set(bias)
                # Only log bias current if it's outside normal range (potential issue)
                if bias < 5 or bias > 30:
                    logging.warning(f"ONT SFP TX bias current outside normal range: {bias} mA")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SFP TX bias current: {e}")
        else:
            logging.warning("Could not find bias current in SFP info output")
        
        # Parse diagnostic type - format: "diagnostic monitoring type: 0x68"
        diag_match = re.search(r'diagnostic\s*monitoring\s*type\s*:\s*(0x[0-9a-fA-F]+)', sfp_output, re.IGNORECASE)
        if diag_match:
            try:
                diag_type = int(diag_match.group(1), 16)
                zaram_ont_metrics.ont_sfp_diagnostic_type.labels(interface_name=interface_name).set(diag_type)
                # Only log diagnostic type changes (not every time)
                logging.debug(f"ONT SFP diagnostic type: {diag_match.group(1)}")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SFP diagnostic type: {e}")
        else:
            logging.warning("Could not find diagnostic type in SFP info output")
    
    def _process_pon_metrics(self, command_outputs: Dict[str, str]):
        """Process PON-specific metrics"""
        interface_name = self.interface_name
        
        # Process FEC statistics
        if 'onu show pon counter' in command_outputs:
            fec_output = command_outputs['onu show pon counter']
            self._parse_fec_statistics(fec_output, interface_name)
        
        # Process PON status (link status)
        if 'onu show ponlink' in command_outputs:
            status_output = command_outputs['onu show ponlink']
            self._parse_pon_status(status_output, interface_name)
        
        # Process SerDes state (from separate command)
        if 'onu show pon serdes' in command_outputs:
            serdes_output = command_outputs['onu show pon serdes']
            self._parse_serdes_state(serdes_output, interface_name)
    
    def _parse_fec_statistics(self, fec_output: str, interface_name: str):
        """Parse FEC statistics from command output"""
        # Only log raw output if it's empty or very short (for debugging)
        if not fec_output or len(fec_output) < 10:
            logging.warning(f"Raw FEC statistics output is empty or too short: '{fec_output}'")
            return
        
        # Parse corrected bytes - format: "Corrected byte(8-byte) : <number>"
        corrected_bytes_match = re.search(r'Corrected byte\(8-byte\)\s*:\s*(\d+)', fec_output, re.IGNORECASE)
        if corrected_bytes_match:
            try:
                corrected_bytes = int(corrected_bytes_match.group(1))
                zaram_ont_metrics.ont_pon_fec_corrected_bytes.labels(interface_name=interface_name).set(corrected_bytes)
                # Only log if there are significant corrections
                if corrected_bytes > 1000:
                    logging.warning(f"PON FEC corrected bytes high: {corrected_bytes}")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing FEC corrected bytes: {e}")
        else:
            logging.warning(f"Could not find corrected bytes in FEC output")
        
        # Parse corrected codewords - format: "Corrected code words(8-byte) : <number>"
        corrected_codewords_match = re.search(r'Corrected code words\(8-byte\)\s*:\s*(\d+)', fec_output, re.IGNORECASE)
        if corrected_codewords_match:
            try:
                corrected_codewords = int(corrected_codewords_match.group(1))
                zaram_ont_metrics.ont_pon_fec_corrected_codewords.labels(interface_name=interface_name).set(corrected_codewords)
                # Only log if there are significant corrections
                if corrected_codewords > 100:
                    logging.warning(f"PON FEC corrected codewords high: {corrected_codewords}")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing FEC corrected codewords: {e}")
        else:
            logging.warning(f"Could not find corrected codewords in FEC output")
        
        # Parse uncorrectable codewords - format: "Uncorrectable code words(8-byte) : <number>"
        uncorrectable_match = re.search(r'Uncorrectable code words\(8-byte\)\s*:\s*(\d+)', fec_output, re.IGNORECASE)
        if uncorrectable_match:
            try:
                uncorrectable = int(uncorrectable_match.group(1))
                zaram_ont_metrics.ont_pon_fec_uncorrectable_codewords.labels(interface_name=interface_name).set(uncorrectable)
                # Log any uncorrectable errors (these are always concerning)
                if uncorrectable > 0:
                    logging.warning(f"PON FEC uncorrectable codewords detected: {uncorrectable}")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing FEC uncorrectable codewords: {e}")
        else:
            logging.warning(f"Could not find uncorrectable codewords in FEC output")
        
        # Parse total codewords - format: "Total code words(8-byte) : <number>"
        total_match = re.search(r'Total code words\(8-byte\)\s*:\s*(\d+)', fec_output, re.IGNORECASE)
        if total_match:
            try:
                total = int(total_match.group(1))
                zaram_ont_metrics.ont_pon_fec_total_codewords.labels(interface_name=interface_name).set(total)
                # Only log total codewords in debug mode
                logging.debug(f"PON FEC total codewords: {total}")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing FEC total codewords: {e}")
        else:
            logging.warning(f"Could not find total codewords in FEC output")
    
    def _parse_pon_status(self, status_output: str, interface_name: str):
        """Parse PON status from command output"""
        # Only log raw output if it's empty or very short (for debugging)
        if not status_output or len(status_output) < 10:
            logging.warning(f"Raw PON link status output is empty or too short: '{status_output}'")
            return
        
        # Parse PON link status - handle the actual output format
        # Output format: "ponlink-status : connect-OK" or similar
        link_match = re.search(r'ponlink-status\s*:\s*(connect-OK|connect-FAIL|disconnect)', status_output, re.IGNORECASE)
        if link_match:
            status_text = link_match.group(1).lower()
            link_status = 1 if 'connect-ok' in status_text else 0
            zaram_ont_metrics.ont_pon_link_status.labels(interface_name=interface_name).set(link_status)
            # Only log if link is down (issue)
            if not link_status:
                logging.warning(f"PON link status: DOWN ({status_text})")
        else:
            # Try a more flexible pattern that handles the exact format we see
            link_match = re.search(r'ponlink-status\s*:\s*([^\s]+)', status_output, re.IGNORECASE)
            if link_match:
                status_text = link_match.group(1).lower()
                link_status = 1 if 'connect-ok' in status_text else 0
                zaram_ont_metrics.ont_pon_link_status.labels(interface_name=interface_name).set(link_status)
                # Only log if link is down (issue)
                if not link_status:
                    logging.warning(f"PON link status: DOWN ({status_text})")
            else:
                # Fallback to original patterns
                link_match = re.search(r'link\s*status\s*:\s*(up|down)', status_output, re.IGNORECASE)
                if link_match:
                    link_status = 1 if link_match.group(1).lower() == 'up' else 0
                    zaram_ont_metrics.ont_pon_link_status.labels(interface_name=interface_name).set(link_status)
                    # Only log if link is down (issue)
                    if not link_status:
                        logging.warning(f"PON link status: DOWN")
                else:
                    logging.warning(f"Could not find PON link status in output: '{status_output}'")
                    # Try alternative patterns
                    alt_patterns = [
                        r'status\s*:\s*(up|down)',
                        r'link\s*:\s*(up|down)',
                        r'pon\s*status\s*:\s*(up|down)',
                        r'connection\s*:\s*(up|down)'
                    ]
                    for pattern in alt_patterns:
                        alt_match = re.search(pattern, status_output, re.IGNORECASE)
                        if alt_match:
                            link_status = 1 if alt_match.group(1).lower() == 'up' else 0
                            zaram_ont_metrics.ont_pon_link_status.labels(interface_name=interface_name).set(link_status)
                            # Only log if link is down (issue)
                            if not link_status:
                                logging.warning(f"PON link status (alt pattern): DOWN")
                            break
    
    def _parse_serdes_state(self, serdes_output: str, interface_name: str):
        """Parse SerDes state from command output"""
        # Parse SerDes state - format: "Serdes state | Very good(0x3e)"
        serdes_match = re.search(r'Serdes\s*state\s*\|\s*([\w\s]+)\((0x[0-9a-fA-F]+)\)', serdes_output, re.IGNORECASE)
        if serdes_match:
            try:
                serdes_text = serdes_match.group(1).strip()
                serdes_hex = serdes_match.group(2)
                serdes_value = int(serdes_hex, 16)
                
                # Set the numeric state value
                zaram_ont_metrics.ont_pon_serdes_state.labels(interface_name=interface_name).set(serdes_value)
                
                # Set the text state as a gauge with value 1 for current state
                possible_states = ["Very good", "Good", "Poor", "Error", "Failed", "Unknown"]
                for state in possible_states:
                    value = 1 if state == serdes_text else 0
                    zaram_ont_metrics.ont_pon_serdes_text_state.labels(interface_name=interface_name, state=state).set(value)
                
                # Only log if SerDes state indicates an issue
                if 'error' in serdes_text.lower() or 'fail' in serdes_text.lower():
                    logging.warning(f"PON SerDes state indicates issue: {serdes_text} ({serdes_hex})")
            except (ValueError, TypeError) as e:
                logging.error(f"Error parsing SerDes state: {e}")
        else:
            logging.warning(f"Could not find SerDes state in output: '{serdes_output}')")
    
    def _get_serdes_state_description(self, serdes_value: int) -> str:
        """Get human-readable description of SerDes state"""
        serdes_states = {
            0x00: "Reset",
            0x01: "Initializing",
            0x02: "Ready",
            0x03: "Active",
            0x04: "Error",
            0x05: "Disconnected"
        }
        return serdes_states.get(serdes_value, f"Unknown (0x{serdes_value:02x})")
    
    def _process_system_metrics(self, command_outputs: Dict[str, str]):
        """Process system metrics (CPU, memory)"""
        interface_name = self.interface_name
        
        # Process CPU usage
        if 'sysmon cpu' in command_outputs:
            cpu_output = command_outputs['sysmon cpu']
            cpu_match = re.search(r'cpu\s*usage\s*:\s*([\d.]+)\s*%', cpu_output, re.IGNORECASE)
            if cpu_match:
                try:
                    cpu_usage = float(cpu_match.group(1))
                    zaram_ont_metrics.ont_cpu_usage.labels(interface_name=interface_name).set(cpu_usage)
                    # Only log if CPU usage is high (potential issue)
                    if cpu_usage > 80:
                        logging.warning(f"ONT CPU usage high: {cpu_usage}%")
                except (ValueError, TypeError) as e:
                    logging.error(f"Error parsing CPU usage: {e}")
        
        # Process memory usage
        if 'sysmon memory' in command_outputs:
            mem_output = command_outputs['sysmon memory']
            
            mem_match = re.search(r'used/total\s*=\s*(\d+)/(\d+)\s*\(([\d.]+)\s*%\)', mem_output)
            if mem_match:
                try:
                    used = int(mem_match.group(1))
                    total = int(mem_match.group(2))
                    percent = float(mem_match.group(3))
                    
                    zaram_ont_metrics.ont_memory_used.labels(interface_name=interface_name).set(used)
                    zaram_ont_metrics.ont_memory_total.labels(interface_name=interface_name).set(total)
                    zaram_ont_metrics.ont_memory_usage.labels(interface_name=interface_name).set(percent)
                    
                    # Only log if memory usage is high (potential issue)
                    if percent > 85:
                        logging.warning(f"ONT memory usage high: {used}/{total} bytes ({percent}%)")
                except (ValueError, TypeError) as e:
                    logging.error(f"Error parsing memory usage: {e}")
            else:
                logging.warning(f"Memory output did not match expected pattern. Output: '{mem_output}'")
        else:
            logging.warning("No 'sysmon memory' output available")
    
    def _process_olt_info(self, command_outputs: Dict[str, str]) -> None:
        """Process OLT vendor information"""
        if 'onu dump ptp' not in command_outputs:
            self.logger.warning("No 'onu dump ptp' output available")
            return

        output = command_outputs['onu dump ptp']
        
        # Log raw output for debugging if it's empty or very short
        if not output or len(output) < 10:
            self.logger.warning(f"Raw OLT vendor info output is empty or too short: '{output}'")
            return
        else:
            self.logger.debug(f"Raw OLT vendor info output: {output}")
        
        try:
            # Extract vendor ID and version
            vendor_id = self._extract_olt_vendor_id(output)
            if vendor_id:
                vendor_name = self._get_vendor_name(vendor_id)
                zaram_ont_metrics.ont_olt_vendor_id.labels(
                    interface_name=self.interface_name,
                    vendor_name=vendor_name
                ).set(vendor_id)
            
            # Extract version
            version_match = re.search(r'version\s*:\s*([0-9a-fA-F]+)', output, re.IGNORECASE)
            if version_match:
                version = version_match.group(1)
                zaram_ont_metrics.ont_olt_version.labels(
                    interface_name=self.interface_name,
                    version=version
                ).set(1)  # Using 1 as the value since we're using the label for the actual version
            else:
                self.logger.warning("Could not find OLT version in output")
            
        except Exception as e:
            self.logger.error(f"Error processing OLT vendor information: {str(e)}")
            raise

    def _extract_olt_vendor_id(self, output):
        """Extract OLT vendor ID from onu dump ptp output"""
        try:
            # Look for vendor ID in OLT-G section
            vendor_match = re.search(r'oltVendorId\s*:\s*([0-9a-fA-F]+)', output, re.IGNORECASE)
            if vendor_match:
                return int(vendor_match.group(1), 16)  # Convert hex to decimal
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting OLT vendor ID: {str(e)}")
            return None

    def _get_vendor_name(self, vendor_id):
        """Get vendor name from vendor ID"""
        # Convert decimal vendor_id back to hex string format
        hex_id = f"0x{vendor_id:08x}"
        return self.olt_vendor_map.get(hex_id, "Unknown")

    def _connect_and_collect_regular(self) -> Optional[Dict[str, str]]:
        """Connect to the ONT module and collect regular command outputs (excluding OLT vendor)"""
        try:
            logging.info(f"Connecting to {self.ssh_user}@{self.ssh_host}...")
            child = pexpect.spawn(f'ssh {self.ssh_user}@{self.ssh_host}')
            
            # Handle SSH password prompt if needed (should use SSH keys)
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
            logging.info(f"Starting telnet to {self.zaram_ont_ip}...")
            child.sendline(f'/system telnet {self.zaram_ont_ip}')
            
            # Handle telnet login
            i = child.expect(['login:', 'Connection refused', pexpect.TIMEOUT], timeout=10)
            if i != 0:  # not login prompt
                error_msg = child.before.decode('utf-8', 'ignore') if child.before else 'None'
                logging.error(f"Failed to get login prompt. Got: {error_msg}")
                child.close()
                return None
                
            logging.info("Sending username...")
            child.sendline(self.zaram_ont_user)
            
            i = child.expect(['Password:', pexpect.TIMEOUT], timeout=5)
            if i != 0:  # timeout or other error
                logging.error("Failed to get password prompt")
                child.close()
                return None
                
            logging.info("Sending password...")
            if not self.zaram_ont_password:
                logging.error("Zaram ONT password is None")
                child.close()
                return None
            password: str = self.zaram_ont_password  # Type assertion
            child.sendline(password)
            
            # Look for command prompt
            i = child.expect(['ZXOS11NPI', pexpect.TIMEOUT], timeout=5)
            if i != 0:  # timeout or other error
                logging.error("Failed to get SFP module prompt")
                child.close()
                return None
                
            logging.info("Successfully logged in to SFP module")
            
            # Run regular commands and collect outputs (excluding OLT vendor)
            command_outputs = self._run_regular_commands(child)
            
            # Exit telnet and close connection
            child.sendline('exit')  # exit telnet
            child.expect(r'\[.*\] >', timeout=5)
            child.sendline('quit')  # exit SSH
            child.close()
            
            return command_outputs
            
        except Exception as e:
            logging.error(f"Error in _connect_and_collect_regular: {str(e)}", exc_info=True)
            try:
                if 'child' in locals():
                    child.close()
            except:
                pass
            return None

    def _connect_and_collect_olt_vendor(self) -> Optional[Dict[str, str]]:
        """Connect to the ONT module and collect only OLT vendor command outputs"""
        try:
            logging.info(f"Connecting to {self.ssh_user}@{self.ssh_host}...")
            child = pexpect.spawn(f'ssh {self.ssh_user}@{self.ssh_host}')
            
            # Handle SSH password prompt if needed (should use SSH keys)
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
            logging.info(f"Starting telnet to {self.zaram_ont_ip}...")
            child.sendline(f'/system telnet {self.zaram_ont_ip}')
            
            # Handle telnet login
            i = child.expect(['login:', 'Connection refused', pexpect.TIMEOUT], timeout=10)
            if i != 0:  # not login prompt
                error_msg = child.before.decode('utf-8', 'ignore') if child.before else 'None'
                logging.error(f"Failed to get login prompt. Got: {error_msg}")
                child.close()
                return None
                
            logging.info("Sending username...")
            child.sendline(self.zaram_ont_user)
            
            i = child.expect(['Password:', pexpect.TIMEOUT], timeout=5)
            if i != 0:  # timeout or other error
                logging.error("Failed to get password prompt")
                child.close()
                return None
                
            logging.info("Sending password...")
            if not self.zaram_ont_password:
                logging.error("Zaram ONT password is None")
                child.close()
                return None
            password: str = self.zaram_ont_password  # Type assertion
            child.sendline(password)
            
            # Look for command prompt
            i = child.expect(['ZXOS11NPI', pexpect.TIMEOUT], timeout=5)
            if i != 0:  # timeout or other error
                logging.error("Failed to get SFP module prompt")
                child.close()
                return None
                
            logging.info("Successfully logged in to SFP module")
            
            # Run only OLT vendor command and collect output
            command_outputs = self._run_olt_vendor_command(child)
            
            # Exit telnet and close connection
            child.sendline('exit')  # exit telnet
            child.expect(r'\[.*\] >', timeout=5)
            child.sendline('quit')  # exit SSH
            child.close()
            
            return command_outputs
            
        except Exception as e:
            logging.error(f"Error in _connect_and_collect_olt_vendor: {str(e)}", exc_info=True)
            try:
                if 'child' in locals():
                    child.close()
            except:
                pass
            return None

    def _run_regular_commands(self, child) -> Dict[str, str]:
        """Run regular commands on the ONT module (excluding OLT vendor) and return outputs"""
        command_outputs = {}
        
        # Regular commands for ONT monitoring (excluding OLT vendor)
        commands = [
            'sfp info',              # Basic SFP module details
            'onu show pon counter',  # FEC counters (at the end of output)
            'onu show ponlink',      # PON link status
            'onu show pon serdes',   # SerDes state
            'sysmon cpu',            # CPU usage
            'sysmon memory'          # Memory usage
        ]
        
        logging.info("Collecting ONT module regular information...")
        
        for cmd in commands:
            try:
                logging.info(f"Running command: {cmd}")
                
                # Send the command
                child.sendline(cmd)
                
                # Clear the buffer before capturing output
                time.sleep(0.5)
                
                # Wait for the prompt to return - use the actual prompt format
                i = child.expect([r'admin@ZXOS11NPI\s+\[/\]\s+#', r'ZXOS11NPI.*#', pexpect.TIMEOUT], timeout=10)
                if i == 2:  # timeout
                    logging.error(f"Command '{cmd}' timed out")
                    command_outputs[cmd] = ""
                else:
                    # Get the output - use before which contains everything up to the prompt
                    output = child.before.decode('utf-8', 'ignore')
                    # Remove the command from the output
                    output = output.replace(cmd, '').strip()
                    command_outputs[cmd] = output
                
                # Add a small delay between commands
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error running command '{cmd}': {str(e)}")
                command_outputs[cmd] = ""
                
        return command_outputs

    def _run_olt_vendor_command(self, child) -> Dict[str, str]:
        """Run only OLT vendor command on the ONT module and return output"""
        command_outputs = {}
        
        # Only OLT vendor command
        commands = [
            'onu dump ptp'          # PTP timing info including vendor ID
        ]
        
        logging.info("Collecting OLT vendor information...")
        
        for cmd in commands:
            try:
                logging.info(f"Running command: {cmd}")
                
                # Send the command
                child.sendline(cmd)
                
                # Clear the buffer before capturing output
                time.sleep(0.5)
                
                # Wait for the prompt to return - use the actual prompt format
                i = child.expect([r'admin@ZXOS11NPI\s+\[/\]\s+#', r'ZXOS11NPI.*#', pexpect.TIMEOUT], timeout=10)
                if i == 2:  # timeout
                    logging.error(f"Command '{cmd}' timed out")
                    command_outputs[cmd] = ""
                else:
                    # Get the output - use before which contains everything up to the prompt
                    full_output = child.before.decode('utf-8', 'ignore') if child.before else ""
                    
                    # Remove the command from the beginning of the output
                    cmd_pattern = re.escape(cmd) + r'\s*\r?\n'
                    output = re.sub(cmd_pattern, '', full_output, count=1)
                    
                    # Clean up the output - remove empty lines and prompt artifacts
                    cleaned_output = '\n'.join([line.strip() for line in output.split('\n') 
                                             if line.strip() and 'admin@' not in line and 'ZXOS11NPI' not in line])
                    command_outputs[cmd] = cleaned_output
                    
                    logging.debug(f"Command '{cmd}' output length: {len(cleaned_output)}")
                    if cleaned_output:
                        logging.debug(f"Command '{cmd}' output: '{cleaned_output[:200]}...'")
                
                time.sleep(0.5)  # Small delay between commands
                
            except Exception as e:
                logging.error(f"Error running command '{cmd}': {str(e)}")
                command_outputs[cmd] = ""
        
        return command_outputs 
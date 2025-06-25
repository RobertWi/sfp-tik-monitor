#!/usr/bin/env python3

import os
import subprocess
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration management for the SFP monitoring system"""
    
    def __init__(self):
        # RouterOS API Configuration
        self.routeros_host = os.getenv('ROUTEROS_HOST')
        if not self.routeros_host:
            raise ValueError("ROUTEROS_HOST must be set in environment")
        
        self.routeros_user = os.getenv('ROUTEROS_USER')
        if not self.routeros_user:
            raise ValueError("ROUTEROS_USER must be set in environment")
            
        self.routeros_api_protocol = os.getenv('ROUTEROS_API_PROTOCOL')
        if not self.routeros_api_protocol:
            raise ValueError("ROUTEROS_API_PROTOCOL must be set in environment")
            
        self.routeros_pass_path = os.getenv('ROUTEROS_PASS_PATH')
        if not self.routeros_pass_path:
            raise ValueError("ROUTEROS_PASS_PATH must be set in environment")
        
        # Zaram ONT Module Configuration
        self.zaram_ont_ip = os.getenv('ZARAM_ONT_IP')
        if not self.zaram_ont_ip:
            raise ValueError("ZARAM_ONT_IP must be set in environment")
            
        self.zaram_ont_user = os.getenv('ZARAM_ONT_USER')
        if not self.zaram_ont_user:
            raise ValueError("ZARAM_ONT_USER must be set in environment")
            
        self.zaram_pass_path = os.getenv('ZARAM_PASS_PATH')
        if not self.zaram_pass_path:
            raise ValueError("ZARAM_PASS_PATH must be set in environment")
        
        # Monitoring Configuration
        monitored_interfaces = os.getenv('MONITORED_INTERFACES')
        if not monitored_interfaces:
            raise ValueError("MONITORED_INTERFACES must be set in environment")
        self.monitored_interfaces = monitored_interfaces.split(',')
        
        collection_interval = os.getenv('COLLECTION_INTERVAL_SECONDS')
        if not collection_interval:
            raise ValueError("COLLECTION_INTERVAL_SECONDS must be set in environment")
        self.collection_interval_seconds = int(collection_interval)
        
        metrics_port = os.getenv('METRICS_PORT')
        if not metrics_port:
            raise ValueError("METRICS_PORT must be set in environment")
        self.metrics_port = int(metrics_port)
        
        self.metrics_host = os.getenv('METRICS_HOST')
        if not self.metrics_host:
            raise ValueError("METRICS_HOST must be set in environment")
        
        # Logging Configuration
        self.log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())  # keeping INFO as safe default
        
        self.log_file = os.getenv('LOG_FILE')
        if not self.log_file:
            raise ValueError("LOG_FILE must be set in environment")
            
        log_max_bytes = os.getenv('LOG_MAX_BYTES')
        if not log_max_bytes:
            raise ValueError("LOG_MAX_BYTES must be set in environment")
        self.log_max_bytes = int(log_max_bytes)
        
        log_backup_count = os.getenv('LOG_BACKUP_COUNT')
        if not log_backup_count:
            raise ValueError("LOG_BACKUP_COUNT must be set in environment")
        self.log_backup_count = int(log_backup_count)
        
        self.debug_logging = os.getenv('DEBUG_LOGGING', 'false').lower() == 'true'  # keeping false as safe default
        
        # SSH Configuration
        self.ssh_user = os.getenv('SSH_USER')
        if not self.ssh_user:
            raise ValueError("SSH_USER must be set in environment")
            
        self.ssh_host = os.getenv('SSH_HOST')
        if not self.ssh_host:
            raise ValueError("SSH_HOST must be set in environment")
        
        # Timeout Configuration - Hardcoded values
        self.api_timeout_seconds = 10
        self.ssh_timeout_seconds = 10
        self.telnet_timeout_seconds = 10
        
        # Data Quality Configuration - Hardcoded value
        self.stale_data_threshold_dbm = -40.0  # dBm threshold for stale data detection
        
        # OLT Vendor ID mapping
        self.olt_vendor_map = {
            "0x414c434c": "Alcatel-Lucent",  # ALCL
            "0x414c4c47": "Allgon",          # ALLG
            "0x41564d47": "AVM",             # AVMG
            "0x41534b59": "Askey",           # ASKY
            "0x43444b54": "Comkey",          # CDKT
            "0x43494747": "CIG",             # CIGG
            "0x43584e4b": "Cisco",           # CXNK
            "0x44444b54": "Dasan",           # DDKT
            "0x444c4e4b": "D-Link",          # DLNK
            "0x44534e57": "Dasan",           # DSNW
            "0x454c5458": "Eltex",           # ELTX
            "0x46485454": "FiberHome",       # FHTT
            "0x474d544b": "Gemtek",          # GMTK
            "0x474e5853": "Genexis",         # GNXS
            "0x47504e43": "GPON",            # GPNC
            "0x47504f4e": "GPON",            # GPON
            "0x47544847": "GTHG",            # GTHG
            "0x48414c4e": "Halon",           # HALN
            "0x48424d54": "HBM",             # HBMT
            "0x48554d41": "Huawei",          # HUMA
            "0x48575443": "Huawei",          # HWTC
            "0x49435452": "iControl",        # ICTR
            "0x49534b54": "iSKT",            # ISKT
            "0x4b414f4e": "Kaon",            # KAON
            "0x4c454f58": "Leox",            # LEOX
            "0x4c514445": "LQDE",            # LQDE
            "0x4d535443": "MSTC",            # MSTC
            "0x4e4f4b47": "Nokia",           # NOKG
            "0x4e4f4b57": "Nokia",           # NOKW
            "0x5054494e": "PTIN",            # PTIN
            "0x52544b47": "Realtek",         # RTKG
            "0x53434f4d": "Sercomm",         # SCOM
            "0x534b5957": "Skyworth",        # SKYW
            "0x534d4253": "SMBS",            # SMBS
            "0x53504741": "SPGA",            # SPGA
            "0x544d4242": "Thomson",         # TMBB
            "0x54504c47": "TP-Link",         # TPLG
            "0x55424e54": "Ubiquiti",        # UBNT
            "0x55475244": "UGRD",            # UGRD
            "0x59485443": "YHTC",            # YHTC
            "0x5a4e5453": "Zioncom",         # ZNTS
            "0x5a524d54": "ZRMT",            # ZRMT
            "0x5a544547": "ZTE",             # ZTEG
            "0x5a59574e": "ZYWNE",           # ZYWN
            "0x5a595845": "ZYXEL",           # ZYXE
            "0x5a54": "ZTE",                 # ZTE - ZXHN
            "0x5a53": "ZTE",                 # ZTE - C320/C300
            "0x5a58": "ZTE",                 # ZTE - C600
            "0x5a49": "Zaram",               # Zaram
            "0x4853": "Huawei",              # Huawei - SmartAX
        }
    
    def get_routeros_password(self) -> Optional[str]:
        """Get RouterOS API password from pass"""
        try:
            if not self.routeros_pass_path:
                logging.error("RouterOS password path not set")
                return None
                
            result = subprocess.run(
                ['pass', self.routeros_pass_path], 
                capture_output=True, 
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get RouterOS password: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Error running pass command for RouterOS password: {e}")
            return None
    
    def get_zaram_ont_password(self) -> Optional[str]:
        """Get Zaram ONT password from pass"""
        try:
            if not self.zaram_pass_path:
                logging.error("Zaram ONT password path not set")
                return None
                
            result = subprocess.run(
                ['pass', self.zaram_pass_path], 
                capture_output=True, 
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get Zaram ONT password: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Error running pass command for Zaram ONT password: {e}")
            return None
    
    def get_ssh_password(self) -> Optional[str]:
        """SSH uses keys, so no password is needed."""
        return None
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check required passwords
        if not self.get_routeros_password():
            errors.append("RouterOS API password not available")
        
        if not self.get_zaram_ont_password():
            errors.append("Zaram ONT password not available")
        
        if not self.get_ssh_password():
            errors.append("SSH password not available")
        
        # Check network connectivity
        if not self.monitored_interfaces:
            errors.append("No monitored interfaces configured")
        
        # Check timeouts
        if self.collection_interval_seconds <= 0:
            errors.append("Collection interval must be positive")
        
        if self.api_timeout_seconds <= 0:
            errors.append("API timeout must be positive")
        
        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False
        
        return True
    
    def log_configuration(self):
        """Log current configuration (without sensitive data)"""
        logging.info("=== Configuration ===")
        logging.info(f"RouterOS Host: {self.routeros_host}")
        logging.info(f"RouterOS User: {self.routeros_user}")
        logging.info(f"Zaram ONT IP: {self.zaram_ont_ip}")
        logging.info(f"Zaram ONT User: {self.zaram_ont_user}")
        logging.info(f"Monitored Interfaces: {', '.join(self.monitored_interfaces)}")
        logging.info(f"Collection Interval: {self.collection_interval_seconds}s")
        logging.info(f"Metrics Port: {self.metrics_port}")
        logging.info(f"Metrics Host: {self.metrics_host}")
        logging.info(f"API Timeout: {self.api_timeout_seconds}s")
        logging.info(f"SSH Timeout: {self.ssh_timeout_seconds}s")
        logging.info(f"Telnet Timeout: {self.telnet_timeout_seconds}s")
        logging.info(f"Stale Data Threshold: {self.stale_data_threshold_dbm} dBm")
        logging.info("=====================")

    def enable_debug_logging(self):
        """Enable debug logging for troubleshooting"""
        self.log_level = logging.DEBUG
        self.debug_logging = True
        logging.info("Debug logging enabled")
    
    def disable_debug_logging(self):
        """Disable debug logging"""
        self.log_level = logging.WARNING
        self.debug_logging = False
        logging.info("Debug logging disabled")


# Global configuration instance
config = Config() 
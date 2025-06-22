#!/usr/bin/env python3

import os
import subprocess
import logging
from typing import Optional

class Config:
    """Configuration management for the SFP monitoring system"""
    
    def __init__(self):
        # RouterOS API Configuration
        self.routeros_host = 'rt1.home.doemijdienamespacemaar.nl'
        self.routeros_user = 'api-monitor'
        self.routeros_api_protocol = 'https'  # Use https:// protocol for API
        
        # Zaram ONT Module Configuration
        self.zaram_ont_ip = '192.168.200.1'
        self.zaram_ont_user = 'admin'
        
        # Monitoring Configuration
        self.monitored_interfaces = ['sfp-sfpplus1', 'pppoe-wan']
        self.collection_interval_seconds = 30
        self.metrics_port = 9700
        self.metrics_host = '0.0.0.0'
        
        # Logging Configuration
        self.log_level = logging.INFO  # Changed back to INFO to reduce verbose output
        self.log_file = 'logs/sfp_monitor.log'
        self.log_max_bytes = 1024 * 1024  # 1MB
        self.log_backup_count = 5
        self.debug_logging = False  # Set to False to reduce verbose logging
        
        # SSH Configuration
        self.ssh_user = 'robert'
        self.ssh_host = '192.168.33.1'  # Keep SSH on local IP
        
        # Timeout Configuration
        self.api_timeout_seconds = 10
        self.ssh_timeout_seconds = 10
        self.telnet_timeout_seconds = 10
        
        # Data Quality Configuration
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
            result = subprocess.run(
                ['pass', 'mikrotik/rt1/api-monitor/api-monitoring'], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logging.error(f"Failed to get RouterOS password: {result.stderr}")
                return None
        except Exception as e:
            logging.error(f"Error running pass command for RouterOS password: {e}")
            return None
    
    def get_zaram_ont_password(self) -> Optional[str]:
        """Get Zaram ONT password from pass"""
        try:
            result = subprocess.run(
                ['pass', 'zaram/sfp/admin'], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logging.error(f"Failed to get Zaram ONT password: {result.stderr}")
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
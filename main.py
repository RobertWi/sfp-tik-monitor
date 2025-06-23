#!/usr/bin/env python3

import logging
import logging.handlers
import time
from prometheus_client import start_http_server
from config import config
from metrics_registry import log_metrics_summary
from routeros_collector import RouterOSCollector
from zaram_ont_collector import ZaramONTCollector


def setup_logging():
    """Configure logging for the application."""
    log_level = config.log_level
    log_file = config.log_file
    log_max_bytes = config.log_max_bytes
    log_backup_count = config.log_backup_count
    
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=log_max_bytes, backupCount=log_backup_count
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logging.basicConfig(level=log_level, handlers=[handler])


def main():
    setup_logging()
    config.log_configuration()
    
    # Only log metrics summary in debug mode
    if config.debug_logging:
        log_metrics_summary()

    # Start Prometheus HTTP server
    start_http_server(config.metrics_port, addr=config.metrics_host)
    logging.info(f"Prometheus metrics server started on {config.metrics_host}:{config.metrics_port}")

    # Initialize collectors
    routeros_collector = RouterOSCollector()
    zaram_ont_collector = ZaramONTCollector()

    # Timer variables for different collection intervals
    last_regular_collection = 0
    last_olt_vendor_collection = 0
    olt_vendor_interval = 300  # 5 minutes (300 seconds)
    
    logging.info(f"Starting collection with regular interval: {config.collection_interval_seconds}s, OLT vendor interval: {olt_vendor_interval}s")

    # Main collection loop
    while True:
        try:
            current_time = time.time()
            
            # Check if it's time for regular collection (every 30 seconds)
            if current_time - last_regular_collection >= config.collection_interval_seconds:
                logging.info("Starting regular metrics collection cycle...")
                routeros_collector.collect_all_metrics()
                zaram_ont_collector.collect_regular_metrics()
                last_regular_collection = current_time
                
                # Only log metrics summary in debug mode
                if config.debug_logging:
                    log_metrics_summary()
            
            # Check if it's time for OLT vendor collection (every 5 minutes)
            if current_time - last_olt_vendor_collection >= olt_vendor_interval:
                logging.info("Starting OLT vendor collection cycle...")
                zaram_ont_collector.collect_olt_vendor_info()
                last_olt_vendor_collection = current_time
            
            # Sleep for a short interval to avoid busy waiting
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error in main collection loop: {e}", exc_info=True)
            time.sleep(60)  # Wait longer on error


if __name__ == '__main__':
    main() 
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

    # Main collection loop
    while True:
        try:
            logging.info("Starting metrics collection cycle...")
            routeros_collector.collect_all_metrics()
            zaram_ont_collector.collect_all_metrics()
            
            # Only log metrics summary in debug mode
            if config.debug_logging:
                log_metrics_summary()
        except Exception as e:
            logging.error(f"Error in main collection loop: {e}", exc_info=True)
            time.sleep(60)  # Wait longer on error
        else:
            time.sleep(config.collection_interval_seconds)


if __name__ == '__main__':
    main() 
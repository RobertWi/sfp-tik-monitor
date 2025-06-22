#!/usr/bin/env python3

from prometheus_client import Gauge, Counter, Info
import logging

# RouterOS API Metrics
class RouterOSMetrics:
    """Metrics collected via RouterOS API"""
    
    # Interface status and basic stats
    interface_link_status = Gauge(
        'routeros_interface_link_status', 
        'Interface link status (1=UP, 0=DOWN)', 
        ['interface_name']
    )
    
    interface_rx_bytes = Gauge(
        'routeros_interface_rx_bytes_total', 
        'Total received bytes', 
        ['interface_name']
    )
    
    interface_tx_bytes = Gauge(
        'routeros_interface_tx_bytes_total', 
        'Total transmitted bytes', 
        ['interface_name']
    )
    
    interface_rx_packets = Counter(
        'routeros_interface_rx_packets_total', 
        'Total received packets', 
        ['interface_name']
    )
    
    interface_tx_packets = Counter(
        'routeros_interface_tx_packets_total', 
        'Total transmitted packets', 
        ['interface_name']
    )
    
    interface_rx_errors = Counter(
        'routeros_interface_rx_errors_total', 
        'Total receive errors', 
        ['interface_name']
    )
    
    interface_tx_errors = Counter(
        'routeros_interface_tx_errors_total', 
        'Total transmit errors', 
        ['interface_name']
    )
    
    interface_rx_drops = Counter(
        'routeros_interface_rx_drops_total', 
        'Total receive drops', 
        ['interface_name']
    )
    
    interface_tx_drops = Counter(
        'routeros_interface_tx_drops_total', 
        'Total transmit drops', 
        ['interface_name']
    )
    
    interface_tx_queue_drops = Counter(
        'routeros_interface_tx_queue_drops_total', 
        'Total transmit queue drops', 
        ['interface_name']
    )
    
    interface_link_downs = Gauge(
        'routeros_interface_link_downs_total', 
        'Total number of times the link has gone down', 
        ['interface_name']
    )
    
    interface_last_link_up = Gauge(
        'routeros_interface_last_link_up_seconds', 
        'Timestamp when the interface was last up', 
        ['interface_name']
    )
    
    interface_last_link_down = Gauge(
        'routeros_interface_last_link_down_seconds', 
        'Timestamp when the interface was last down', 
        ['interface_name']
    )
    
    # SFP module metrics (via RouterOS API)
    sfp_temperature = Gauge(
        'routeros_sfp_temperature_celsius', 
        'SFP module temperature in Celsius', 
        ['interface_name']
    )
    
    sfp_rx_power = Gauge(
        'routeros_sfp_rx_power_dbm', 
        'SFP received optical power in dBm', 
        ['interface_name']
    )
    
    sfp_tx_power = Gauge(
        'routeros_sfp_tx_power_dbm', 
        'SFP transmitted optical power in dBm', 
        ['interface_name']
    )
    
    sfp_voltage = Gauge(
        'routeros_sfp_voltage_volts', 
        'SFP module supply voltage in Volts', 
        ['interface_name']
    )
    
    sfp_tx_bias_current = Gauge(
        'routeros_sfp_tx_bias_current_ma', 
        'SFP laser bias current in mA', 
        ['interface_name']
    )
    
    # SFP vendor serial number (from RouterOS API)
    sfp_vendor_serial = Info(
        'routeros_sfp_vendor_serial', 
        'SFP module vendor serial number from RouterOS', 
        ['interface_name']
    )
    
    # SFP error statistics
    sfp_tx_fcs_error = Counter(
        'routeros_sfp_tx_fcs_errors_total', 
        'Frames transmitted with FCS error', 
        ['interface_name']
    )
    
    sfp_tx_collision = Counter(
        'routeros_sfp_tx_collisions_total', 
        'Frames transmitted with collisions', 
        ['interface_name']
    )
    
    sfp_tx_excessive_collision = Counter(
        'routeros_sfp_tx_excessive_collisions_total', 
        'Frames not transmitted due to excessive collisions', 
        ['interface_name']
    )
    
    sfp_tx_late_collision = Counter(
        'routeros_sfp_tx_late_collisions_total', 
        'Late collisions detected', 
        ['interface_name']
    )
    
    sfp_tx_deferred = Counter(
        'routeros_sfp_tx_deferred_total', 
        'Frames for which the first transmission attempt was delayed', 
        ['interface_name']
    )
    
    sfp_rx_too_short = Counter(
        'routeros_sfp_rx_too_short_total', 
        'Received frames that were too short', 
        ['interface_name']
    )
    
    sfp_rx_too_long = Counter(
        'routeros_sfp_rx_too_long_total', 
        'Received frames that were too long', 
        ['interface_name']
    )
    
    sfp_rx_jabber = Counter(
        'routeros_sfp_rx_jabber_total', 
        'Received jabber frames', 
        ['interface_name']
    )
    
    sfp_rx_fcs_error = Counter(
        'routeros_sfp_rx_fcs_errors_total', 
        'Received frames with FCS errors', 
        ['interface_name']
    )
    
    sfp_rx_align_error = Counter(
        'routeros_sfp_rx_align_errors_total', 
        'Received frames with alignment errors', 
        ['interface_name']
    )
    
    sfp_rx_fragment = Counter(
        'routeros_sfp_rx_fragments_total', 
        'Received fragment frames', 
        ['interface_name']
    )
    
    sfp_rx_overflow = Counter(
        'routeros_sfp_rx_overflows_total', 
        'Receive FIFO overflows', 
        ['interface_name']
    )
    
    sfp_tx_underrun = Counter(
        'routeros_sfp_tx_underruns_total', 
        'Transmit FIFO underruns', 
        ['interface_name']
    )
    
    # Data quality indicators
    sfp_data_stale = Gauge(
        'routeros_sfp_data_stale', 
        'Indicates if SFP data might be stale (1=stale, 0=fresh)', 
        ['interface_name', 'metric_type']
    )
    
    sfp_last_verified = Gauge(
        'routeros_sfp_last_verified_seconds', 
        'Timestamp when SFP data was last verified as accurate', 
        ['interface_name']
    )


# Zaram ONT Module Metrics
class ZaramONTMetrics:
    """Metrics collected via direct SSH/telnet to Zaram SFP ONT module"""
    
    # Direct SFP module readings
    ont_sfp_temperature = Gauge(
        'zaram_ont_sfp_temperature_celsius', 
        'ONT SFP temperature in Celsius from direct telnet session', 
        ['interface_name']
    )
    
    ont_sfp_rx_power = Gauge(
        'zaram_ont_sfp_rx_power_dbm', 
        'ONT SFP RX power in dBm from direct telnet session', 
        ['interface_name']
    )
    
    ont_sfp_tx_power = Gauge(
        'zaram_ont_sfp_tx_power_dbm', 
        'ONT SFP TX power in dBm from direct telnet session', 
        ['interface_name']
    )
    
    ont_sfp_voltage = Gauge(
        'zaram_ont_sfp_voltage_volts', 
        'ONT SFP supply voltage in Volts from direct telnet session', 
        ['interface_name']
    )
    
    ont_sfp_tx_bias_current = Gauge(
        'zaram_ont_sfp_tx_bias_current_ma', 
        'ONT SFP TX bias current in mA from direct telnet session', 
        ['interface_name']
    )
    
    ont_sfp_diagnostic_type = Gauge(
        'zaram_ont_sfp_diagnostic_type', 
        'ONT SFP diagnostic monitoring type (hex value) from direct telnet session', 
        ['interface_name']
    )
    
    # PON-specific metrics
    ont_pon_fec_corrected_bytes = Gauge(
        'zaram_ont_pon_fec_corrected_bytes_total', 
        'Number of bytes corrected by FEC', 
        ['interface_name']
    )
    
    ont_pon_fec_corrected_codewords = Gauge(
        'zaram_ont_pon_fec_corrected_codewords_total', 
        'Number of code words corrected by FEC', 
        ['interface_name']
    )
    
    ont_pon_fec_uncorrectable_codewords = Gauge(
        'zaram_ont_pon_fec_uncorrectable_codewords_total', 
        'Number of uncorrectable code words', 
        ['interface_name']
    )
    
    ont_pon_fec_total_codewords = Gauge(
        'zaram_ont_pon_fec_total_codewords_total', 
        'Total number of received code words', 
        ['interface_name']
    )
    
    ont_pon_serdes_state = Gauge(
        'zaram_ont_pon_serdes_state', 
        'PON SerDes state (hex value)', 
        ['interface_name']
    )
    
    ont_pon_serdes_text = Info(
        'zaram_ont_pon_serdes_text', 
        'PON SerDes state text description', 
        ['interface_name']
    )
    
    ont_pon_link_status = Gauge(
        'zaram_ont_pon_link_status', 
        'PON link status (1=UP, 0=DOWN)', 
        ['interface_name']
    )
    
    # System metrics
    ont_cpu_usage = Gauge(
        'zaram_ont_cpu_usage_percent', 
        'ONT CPU usage percentage', 
        ['interface_name']
    )
    
    ont_memory_usage = Gauge(
        'zaram_ont_memory_usage_percent', 
        'ONT memory usage percentage', 
        ['interface_name']
    )
    
    ont_memory_used = Gauge(
        'zaram_ont_memory_used_bytes', 
        'ONT memory used in bytes', 
        ['interface_name']
    )
    
    ont_memory_total = Gauge(
        'zaram_ont_memory_total_bytes', 
        'Total ONT memory in bytes', 
        ['interface_name']
    )
    
    # OLT information
    ont_olt_vendor_id = Gauge(
        'zaram_ont_olt_vendor_id', 
        'OLT Vendor ID (hex as decimal)', 
        ['interface_name', 'vendor_name']
    )
    
    ont_olt_version = Gauge(
        'zaram_ont_olt_version', 
        'OLT Firmware Version', 
        ['interface_name', 'version']
    )
    
    # XGSPON specific metrics
    ont_xgspon_identifier = Gauge(
        'zaram_ont_xgspon_identifier', 
        'ONT XGSPON identifier present (1=yes, 0=no)', 
        ['interface_name']
    )


# Connection and collection status metrics
class CollectionMetrics:
    """Metrics about the collection process itself"""
    
    collection_duration_seconds = Gauge(
        'sfp_monitor_collection_duration_seconds', 
        'Time spent collecting metrics in seconds', 
        ['collector_type']
    )
    
    collection_success = Gauge(
        'sfp_monitor_collection_success', 
        'Collection success status (1=success, 0=failure)', 
        ['collector_type']
    )
    
    collection_errors_total = Counter(
        'sfp_monitor_collection_errors_total', 
        'Total number of collection errors', 
        ['collector_type', 'error_type']
    )
    
    last_collection_timestamp = Gauge(
        'sfp_monitor_last_collection_timestamp_seconds', 
        'Timestamp of last successful collection', 
        ['collector_type']
    )


# Create instances for easy access
routeros_metrics = RouterOSMetrics()
zaram_ont_metrics = ZaramONTMetrics()
collection_metrics = CollectionMetrics()


def get_all_metrics():
    """Return all registered metrics for debugging"""
    from prometheus_client import REGISTRY
    metrics = []
    for metric in REGISTRY.collect():
        metrics.append({
            'name': metric.name,
            'type': metric.type,
            'samples': [sample for sample in metric.samples]
        })
    return metrics


def log_metrics_summary():
    """Log a summary of all registered metrics"""
    from prometheus_client import REGISTRY
    logging.info("=== Registered Prometheus Metrics ===")
    for metric in REGISTRY.collect():
        logging.info(f"- {metric.name} ({metric.type})")
    logging.info("=====================================") 
terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.25"
    }
  }
}

# Alert Rules
resource "grafana_rule_group" "sfp_monitoring" {
  name             = "SFP Monitoring Alerts"
  folder_uid       = var.folder_uid
  interval_seconds = var.alert_evaluation_interval

  rule {
    name = "SFP Interface Link Down"
    condition = "A"
    for = "2m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "routeros_interface_link_status{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "SFP interface sfp-sfpplus1 is down"
      description = "SFP interface sfp-sfpplus1 has been down for more than 1 minute. This indicates a link failure or hardware issue."
    }
  }

  rule {
    name = "SFP Temperature Critical"
    condition = "A"
    for = "2m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "routeros_sfp_temperature_celsius{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} > 85"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "SFP temperature critical for sfp-sfpplus1"
      description = "SFP module temperature is critically high ({{ $value }}°C) for interface sfp-sfpplus1. Immediate attention required."
    }
  }

  rule {
    name = "SFP RX Power Too Low"
    condition = "A"
    for = "2m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "routeros_sfp_rx_power_dbm{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} < -30"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "SFP RX power too low for sfp-sfpplus1"
      description = "SFP RX power is below threshold ({{ $value }} dBm) for interface sfp-sfpplus1. This may indicate fiber issues or signal degradation."
    }
  }

  rule {
    name = "SFP RX Power Too High"
    condition = "A"
    for = "2m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "routeros_sfp_rx_power_dbm{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} > -8"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "SFP RX power too high for sfp-sfpplus1"
      description = "SFP RX power is above threshold ({{ $value }} dBm) for interface sfp-sfpplus1. This may indicate signal overload or excessive optical power."
    }
  }

  rule {
    name = "SFP Data Stale"
    condition = "A"
    for = "2m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "count(routeros_sfp_data_stale{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} == 1) > 0"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "SFP data appears stale for sfp-sfpplus1"
      description = "SFP power readings appear to be stale/cached data for interface sfp-sfpplus1. This may indicate the SFP module is not reporting fresh data."
    }
  }

  rule {
    name = "ONT PON Link Down"
    condition = "A"
    for = "2m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "zaram_ont_pon_link_status{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "ont"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "ONT PON link down for sfp-sfpplus1"
      description = "ONT PON link is down for interface sfp-sfpplus1. This indicates loss of connectivity to the OLT."
    }
  }

  rule {
    name = "ONT CPU Usage High"
    condition = "A"
    for = "5m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "zaram_ont_cpu_usage_percent{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} > 95"
      })
    }

    labels = {
      severity = "warning"
      category = "ont"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "ONT CPU usage high for sfp-sfpplus1"
      description = "ONT CPU usage is high ({{ $value }}%) for interface sfp-sfpplus1. This may indicate performance issues."
    }
  }

  rule {
    name = "OLT Vendor Changed"
    condition = "A"
    for = "1h"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 7200
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "changes(zaram_ont_olt_vendor_id{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"}[1h]) > 0"
      })
    }

    labels = {
      severity = "warning"
      category = "ont"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "OLT vendor changed for sfp-sfpplus1"
      description = "OLT vendor has changed for interface sfp-sfpplus1. This may indicate OLT replacement or configuration changes."
    }
  }

  rule {
    name = "SFP and PPPoE WAN Interfaces Down"
    condition = "A"
    for = "5m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "routeros_interface_link_status{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"} == 0 and routeros_interface_link_status{job=\"mikrotik_sfp\", interface_name=\"pppoe-wan\"} == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "connectivity"
      interface = "sfp-sfpplus1,pppoe-wan"
    }

    annotations = {
      summary = "SFP and PPPoE WAN interfaces are down"
      description = "Both the SFP interface (sfp-sfpplus1) and PPPoE WAN interface are down. This indicates a complete connectivity failure."
    }
  }

  rule {
    name = "PPPoE WAN Link Down"
    condition = "A"
    for = "2m"

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "routeros_interface_link_status{job=\"mikrotik_sfp\", interface_name=\"pppoe-wan\"} == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "wan"
      interface = "pppoe-wan"
    }

    annotations = {
      summary = "PPPoE WAN interface pppoe-wan is down"
      description = "PPPoE WAN interface pppoe-wan has been down for more than 1 minute. This indicates a link failure or hardware issue."
    }
  }

  rule {
    name = "ONT FEC Uncorrectable Codewords High"
    condition = "A"
    for = "5m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "increase(zaram_ont_pon_fec_uncorrectable_codewords_total{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"}[5m]) > 1000"
      })
    }

    labels = {
      severity = "critical"
      category = "ont"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "High FEC uncorrectable codewords rate for sfp-sfpplus1"
      description = "ONT FEC uncorrectable codewords are increasing rapidly ({{ $value }} in 5m) for interface sfp-sfpplus1. This indicates severe signal quality issues."
    }
  }

  rule {
    name = "ONT FEC Error Rate Critical"
    condition = "A"
    for = "5m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "(increase(zaram_ont_pon_fec_uncorrectable_codewords_total{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"}[5m]) / increase(zaram_ont_pon_fec_total_codewords_total{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"}[5m])) * 100 > 0.1"
      })
    }

    labels = {
      severity = "critical"
      category = "ont"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "Critical FEC error rate for sfp-sfpplus1"
      description = "ONT FEC error rate is critical ({{ $value | humanizePercentage }}) for interface sfp-sfpplus1. This indicates severe optical signal degradation."
    }
  }

  rule {
    name = "ONT FEC Corrected Codewords Increasing"
    condition = "A"
    for = "10m"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 1200
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr         = "rate(zaram_ont_pon_fec_corrected_codewords_total{job=\"mikrotik_sfp\", interface_name=\"sfp-sfpplus1\"}[5m]) > 100"
      })
    }

    labels = {
      severity = "warning"
      category = "ont"
      interface = "sfp-sfpplus1"
    }

    annotations = {
      summary = "High FEC correction rate for sfp-sfpplus1"
      description = "ONT FEC is correcting codewords at a high rate ({{ $value }}/min) for interface sfp-sfpplus1. This indicates ongoing signal quality issues."
    }
  }
}

# Variables
variable "folder_uid" {
  description = "UID of the folder to store alert rules. Set to null to use General folder."
  type        = string
  default     = null
}

variable "alert_evaluation_interval" {
  description = "Alert evaluation interval in seconds"
  type        = number
  default     = 90
}

variable "sfp_temperature_critical_threshold" {
  description = "Critical temperature threshold for SFP modules (°C)"
  type        = number
  default     = 70
}

variable "sfp_rx_power_low_threshold" {
  description = "Low RX power threshold for SFP modules (dBm)"
  type        = number
  default     = -25
}

variable "sfp_rx_power_high_threshold" {
  description = "High RX power threshold for SFP modules (dBm)"
  type        = number
  default     = -3
}

variable "ont_cpu_warning_threshold" {
  description = "Warning threshold for ONT CPU usage (%)"
  type        = number
  default     = 80
}

variable "datasource_uid" {
  description = "UID of the datasource to use for alert rules"
  type        = string
}

# Outputs
output "alert_rule_ids" {
  description = "IDs of created alert rules"
  value       = grafana_rule_group.sfp_monitoring.rule[*].uid
} 
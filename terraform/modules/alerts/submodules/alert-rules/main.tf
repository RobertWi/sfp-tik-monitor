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
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "min by(interface_name) (routeros_interface_link_status{job=\"mikrotik_sfp\"}) == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "interface"
    }

    annotations = {
      summary = "Interface $${labels.interface_name} is down"
      description = "Interface $${labels.interface_name} is reporting link status DOWN."
    }
  }

  rule {
    name = "SFP Temperature Critical"
    condition = "A or B"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (routeros_sfp_temperature_celsius{job=\"mikrotik_sfp\"}) > 85"
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (zaram_ont_sfp_temperature_celsius{job=\"mikrotik_sfp\"}) > 85"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
    }

    annotations = {
      summary = "Critical temperature for $${labels.interface_name}"
      description = "SFP module temperature is $${printf \"%.1f\" $value}°C (threshold: 85°C) for interface $${labels.interface_name}."
    }
  }

  rule {
    name = "SFP RX Power Too Low"
    condition = "A or B"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "min by(interface_name) (routeros_sfp_rx_power_dbm{job=\"mikrotik_sfp\"}) < ${var.sfp_rx_power_low_threshold}"
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "min by(interface_name) (zaram_ont_sfp_rx_power_dbm{job=\"mikrotik_sfp\"}) < ${var.sfp_rx_power_low_threshold}"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
    }

    annotations = {
      summary = "Low RX power for $${labels.interface_name}"
      description = "SFP RX power is $${printf \"%.2f\" $value} dBm (threshold: ${var.sfp_rx_power_low_threshold} dBm) for interface $${labels.interface_name}."
    }
  }

  rule {
    name = "SFP RX Power Too High"
    condition = "A or B"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (routeros_sfp_rx_power_dbm{job=\"mikrotik_sfp\"}) > ${var.sfp_rx_power_high_threshold}"
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (zaram_ont_sfp_rx_power_dbm{job=\"mikrotik_sfp\"}) > ${var.sfp_rx_power_high_threshold}"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
    }

    annotations = {
      summary = "High RX power for $${labels.interface_name}"
      description = "SFP RX power is $${printf \"%.2f\" $value} dBm (threshold: ${var.sfp_rx_power_high_threshold} dBm) for interface $${labels.interface_name}."
    }
  }

  rule {
    name = "SFP Data Stale"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (routeros_sfp_data_stale{job=\"mikrotik_sfp\"}) > 0"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
    }

    annotations = {
      summary = "Stale SFP data for $${labels.interface_name}"
      description = "SFP module data is stale for interface $${labels.interface_name}. This could indicate issues with SFP monitoring."
    }
  }

  rule {
    name = "SFP Vendor Version Changed"
    condition = "A"
    for = "0m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 3600  # 1h
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "changes(zaram_ont_olt_version{job=\"mikrotik_sfp\"}[1h]) > 0"
      })
    }

    labels = {
      severity = "warning"
      category = "sfp"
    }

    annotations = {
      summary = "SFP module changed for $${labels.interface_name}"
      description = "SFP module version has changed for interface $${labels.interface_name}, indicating a possible module replacement or connectivity issue."
    }
  }

  rule {
    name = "ONT PON Link Down"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "min by(interface_name) (zaram_ont_pon_link_status{job=\"mikrotik_sfp\"}) == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "ont"
    }

    annotations = {
      summary = "PON link down for $${labels.interface_name}"
      description = "ONT PON link is DOWN for interface $${labels.interface_name}. This indicates loss of connectivity to the OLT."
    }
  }

  

  rule {
    name = "OLT Vendor Changed"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "changes(zaram_ont_olt_vendor_id{job=\"mikrotik_sfp\"}[1h]) > 0"
      })
    }

    labels = {
      severity = "warning"
      category = "ont"
    }

    annotations = {
      summary = "OLT vendor changed for $${labels.interface_name}"
      description = "OLT vendor has changed in the last hour for interface $${labels.interface_name}. This indicates a change in the upstream OLT."
    }
  }

  rule {
    name = "Combined SFP and WAN Interface Down"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "min by(interface_name) (routeros_interface_link_status{job=\"mikrotik_sfp\", interface_name=~\"sfp.*\"}) == 0 and min by(interface_name) (routeros_interface_link_status{job=\"mikrotik_sfp\", interface_name=~\"pppoe.*\"}) == 0"
      })
    }

    labels = {
      severity = "critical"
      category = "interface"
    }

    annotations = {
      summary = "Both SFP and WAN interfaces are down"
      description = "Both SFP and PPPoE WAN interfaces are down. This indicates a complete loss of connectivity."
    }
  }

  rule {
    name = "ONT FEC Corrected Codewords Increasing"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (deriv(zaram_ont_pon_fec_corrected_codewords_total{job=\"mikrotik_sfp\"}[5m])) > 100"
      })
    }

    labels = {
      severity = "warning"
      category = "ont"
    }

    annotations = {
      summary = "High FEC correction rate for $${labels.interface_name}"
      description = "The FEC correction rate is high (> 100 codewords/sec) for interface $${labels.interface_name}, indicating potential signal quality issues."
    }
  }

  rule {
    name = "ONT FEC Uncorrectable Errors"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (increase(zaram_ont_pon_fec_uncorrectable_codewords_total{job=\"mikrotik_sfp\"}[5m])) > 0"
      })
    }

    labels = {
      severity = "critical"
      category = "ont"
    }

    annotations = {
      summary = "FEC uncorrectable errors detected for $${labels.interface_name}"
      description = "ONT has detected uncorrectable FEC errors in the last 5 minutes for interface $${labels.interface_name}. This indicates severe signal quality issues that could not be corrected."
    }
  }

  rule {
    name = "ONT FEC Error Rate High"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (increase(zaram_ont_pon_fec_corrected_codewords_total{job=\"mikrotik_sfp\"}[5m])) / max by(interface_name) (increase(zaram_ont_pon_fec_total_codewords_total{job=\"mikrotik_sfp\"}[5m])) > 0.01"
      })
    }

    labels = {
      severity = "warning"
      category = "ont"
    }

    annotations = {
      summary = "High FEC correction rate for $${labels.interface_name}"
      description = "ONT FEC correction rate is high (>1%) for interface $${labels.interface_name}. This indicates signal quality issues that are being corrected but could worsen."
    }
  }

  rule {
    name = "SFP TX Power Critical"
    condition = "A or B"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (routeros_sfp_tx_power_dbm{job=\"mikrotik_sfp\"}) > 7 or min by(interface_name) (routeros_sfp_tx_power_dbm{job=\"mikrotik_sfp\"}) < 6"
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (zaram_ont_sfp_tx_power_dbm{job=\"mikrotik_sfp\"}) > 7 or min by(interface_name) (zaram_ont_sfp_tx_power_dbm{job=\"mikrotik_sfp\"}) < 6"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
    }

    annotations = {
      summary = "Critical TX power for $${labels.interface_name}"
      description = "SFP TX power is outside acceptable range (6-7 dBm) for interface $${labels.interface_name}."
    }
  }

  rule {
    name = "SFP Voltage Critical"
    condition = "A or B"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (routeros_sfp_voltage_volts{job=\"mikrotik_sfp\"}) > 3.5 or min by(interface_name) (routeros_sfp_voltage_volts{job=\"mikrotik_sfp\"}) < 3.1"
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (zaram_ont_sfp_voltage_volts{job=\"mikrotik_sfp\"}) > 3.5 or min by(interface_name) (zaram_ont_sfp_voltage_volts{job=\"mikrotik_sfp\"}) < 3.1"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
    }

    annotations = {
      summary = "Voltage out of range for $${labels.interface_name}"
      description = "SFP voltage is $${printf \"%.2f\" $value}V (should be between 3.1-3.5V) for interface $${labels.interface_name}."
    }
  }

  rule {
    name = "SFP Bias Current Critical"
    condition = "A or B"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (routeros_sfp_tx_bias_current_ma{job=\"mikrotik_sfp\"}) > 20 or min by(interface_name) (routeros_sfp_tx_bias_current_ma{job=\"mikrotik_sfp\"}) < 10"
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "max by(interface_name) (zaram_ont_sfp_tx_bias_current_ma{job=\"mikrotik_sfp\"}) > 20 or min by(interface_name) (zaram_ont_sfp_tx_bias_current_ma{job=\"mikrotik_sfp\"}) < 10"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
    }

    annotations = {
      summary = "Bias current out of range for $${labels.interface_name}"
      description = "SFP TX bias current is $${printf \"%.2f\" $value}mA (should be between 10-20mA) for interface $${labels.interface_name}."
    }
  }

  rule {
    name = "ONT SerDes State Critical"
    condition = "A"
    for = "2m"
    no_data_state = "OK"
    
    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.datasource_uid
      model = jsonencode({
        expr = "min by(interface_name) (zaram_ont_pon_serdes_state{job=\"mikrotik_sfp\"}) < 56 or min by(interface_name) (zaram_ont_pon_serdes_text_info{job=\"mikrotik_sfp\", state!=\"Very good\"}) > 0"
      })
    }

    labels = {
      severity = "critical"
      category = "sfp"
    }

    annotations = {
      summary = "Critical SerDes state for $${labels.interface_name}"
      description = "PON SerDes state is below acceptable threshold (0x38) or not in 'Very good' state. This indicates a potential optical link issue. Please check the optical connection and consider rebooting the XGSPON module. If the issue persists, the SFP module may need replacement."
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
  default     = 80
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
  description = "Warning threshold for ONT CPU usage (%). Default is 95% to match ONT specifications."
  type        = number
  default     = 95
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
# Alerts Module

This module manages Grafana Cloud alerting configuration including alert rules, contact points, and notification policies.

## Features

- Alert rules for SFP monitoring (temperature, optical power, interface status)
- Contact point configuration for email notifications
- Notification policies with grouping and timing rules
- Integration with Grafana Cloud alerting

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | Environment name (e.g., production, staging) | `string` | n/a | yes |
| project_name | Project name for resource tagging | `string` | n/a | yes |
| folder_uid | UID of the alerts folder | `string` | n/a | yes |
| datasource_uid | UID of the Prometheus datasource | `string` | n/a | yes |
| alert_evaluation_interval | Alert evaluation interval in seconds | `number` | `60` | no |
| sfp_temperature_critical_threshold | Critical temperature threshold in Celsius | `number` | `85.0` | no |
| sfp_rx_power_low_threshold | Low RX power threshold in dBm | `number` | `-30.0` | no |
| sfp_rx_power_high_threshold | High RX power threshold in dBm | `number` | `-19.0` | no |
| ont_cpu_warning_threshold | ONT CPU warning threshold percentage | `number` | `80.0` | no |
| contact_point_name | Name for the contact point | `string` | n/a | yes |
| notification_policy_name | Name for the notification policy | `string` | n/a | yes |
| email_address | Email address for notifications | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| alert_rule_ids | List of created alert rule IDs |
| contact_point_uid | UID of the created contact point |
| notification_policy_uid | UID of the created notification policy |

## Usage

```hcl
module "alerts" {
  source = "./modules/alerts"
  
  environment = "production"
  project_name = "sfp-monitoring"
  folder_uid = module.folders.alerts_folder_uid
  datasource_uid = var.datasource_uid
  
  # Alert thresholds
  sfp_temperature_critical_threshold = 85.0
  sfp_rx_power_low_threshold = -30.0
  sfp_rx_power_high_threshold = -19.0
  
  # Notification configuration
  contact_point_name = "SFP Monitoring Team"
  notification_policy_name = "SFP Monitoring Alerts"
  email_address = "alerts@example.com"
}
```

## Alert Rules

This module creates the following alert rules:

1. **SFP Temperature Critical** - Alerts when SFP temperature exceeds critical threshold
2. **SFP RX Power Low** - Alerts when RX power is below minimum threshold
3. **SFP RX Power High** - Alerts when RX power is above maximum threshold
4. **Interface Link Down** - Alerts when monitored interfaces go down
5. **ONT CPU High** - Alerts when ONT CPU usage is high
6. **ONT Memory High** - Alerts when ONT memory usage is high 
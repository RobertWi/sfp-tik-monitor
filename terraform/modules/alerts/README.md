# Alerts Module

This module manages Grafana Cloud alerting configuration including alert rules, contact points, and notification policies.

## Features

- Alert rules for SFP monitoring (temperature, optical power, interface status)
- Data source health monitoring and error detection
- Contact point configuration for email notifications
- Notification policies with grouping and timing rules
- Integration with Grafana Cloud alerting
- Intelligent handling of temporary data source issues and evaluation delays

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | Environment name (e.g., production, staging) | `string` | n/a | yes |
| project_name | Project name for resource tagging | `string` | n/a | yes |
| folder_uid | UID of the alerts folder | `string` | n/a | yes |
| datasource_uid | UID of the Prometheus datasource | `string` | n/a | yes |
| alert_evaluation_interval | Alert evaluation interval in seconds | `number` | `60` | no |
| sfp_temperature_critical_threshold | Critical temperature threshold in Celsius | `number` | `80.0` | no |
| sfp_rx_power_low_threshold | Lower bound RX power threshold in dBm (more negative value) | `number` | `-30.0` | no |
| sfp_rx_power_high_threshold | Upper bound RX power threshold in dBm (less negative value) | `number` | `-20.0` | no |
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

## Alert Rules

This module creates the following alert rules:

1. **SFP Monitoring Data Source Issues** - Detects data source connectivity problems, timeouts, and evaluation delays
2. **SFP Temperature Critical** - Alerts when SFP temperature exceeds critical threshold of 80°C (with proper value formatting)
3. **SFP RX Power Too Low** - Alerts when RX power drops below -30.0 dBm (lower bound)
4. **SFP RX Power Too High** - Alerts when RX power exceeds -20.0 dBm (upper bound)
5. **SFP Data Stale** - Detects when SFP modules stop reporting fresh data
6. **SFP Vendor Serial Changed** - Alerts on SFP module replacements or changes
7. **Interface Link Down** - Alerts when monitored interfaces go down
8. **ONT CPU High** - Alerts when ONT CPU usage is high
9. **ONT PON Link Down** - Alerts when ONT loses connectivity to OLT

## Alert Features

- All numeric alerts include properly formatted values (e.g., "%.2f" for dBm, "%.1f" for temperature)
- Intelligent handling of missing data and evaluation delays
- Clear descriptions including both current values and thresholds
- Proper interface labeling for multi-interface setups
- Rate-based detection for certain metrics to handle missing scrapes 
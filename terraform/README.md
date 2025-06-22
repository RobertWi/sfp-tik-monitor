# Terraform Infrastructure for SFP Monitoring

This directory contains the Terraform configuration for deploying the SFP monitoring infrastructure to Grafana Cloud, following the [official Grafana Terraform provisioning documentation](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/terraform-provisioning/).

## Structure

```
terraform/
├── providers.tf              # Provider configuration
├── main.tf                   # Main configuration and module calls
├── variables.tf              # Variable definitions
├── terraform.tfvars          # Variable values (not in git)
├── terraform.tfvars.example  # Example variable values
├── deploy.sh                 # Deployment script
├── destroy.sh                # Destruction script
└── modules/
    ├── folders/              # Folder organization module
    │   └── main.tf
    ├── dashboards/           # Dashboard module
    │   └── main.tf
    └── alerts/               # Alerts module with submodules
        ├── main.tf           # Main alerts module
        └── submodules/
            ├── contact-points/       # Contact point configuration
            │   └── main.tf
            ├── notification-policies/ # Notification policy configuration
            │   └── main.tf
            └── alert-rules/          # Alert rules configuration
                └── main.tf
```

## Modules

### Main Configuration (`main.tf`)
- Orchestrates the deployment of all modules
- Defines common tags and local values
- Calls the folders, dashboards, and alerts modules in the correct order

### Providers (`providers.tf`)
- Contains the Grafana Cloud provider configuration
- Defines required provider versions
- Centralized provider management

### Folders Module
- Creates organized folder structure in Grafana
- **RouterOS Monitoring** (parent folder)
  - **SFP Monitoring** (for dashboards)
  - **Alerts** (for alert rules)
- Follows Grafana best practices for organization

### Dashboards Module
- Deploys the SFP monitoring dashboard
- Uses the dashboard JSON configuration file
- Places dashboard in the SFP Monitoring folder

### Alerts Module
The alerts module is split into submodules for better organization, following the textbook approach:

#### Contact Points Submodule
- Creates email contact points for notifications
- Configurable email addresses and message templates
- Follows [Grafana contact point documentation](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/terraform-provisioning/)

#### Notification Policies Submodule
- Defines notification policies
- Configurable grouping, timing, and repeat intervals
- Implements proper notification routing

#### Alert Rules Submodule
- Contains all alert rule definitions
- Uses proper folder organization via `folder_uid`
- Includes alerts for:
  - SFP interface status
  - SFP temperature monitoring
  - SFP RX power monitoring
  - ONT PON link status
  - ONT CPU usage
  - OLT vendor changes
  - SFP vendor serial changes
  - Combined SFP and PPPoE WAN interface failures

## Textbook Compliance

This implementation follows the [official Grafana Terraform provisioning guide](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/terraform-provisioning/) and includes:

✅ **Grafana Folders** - Proper folder organization using `grafana_folder` resources  
✅ **Contact Points** - Email notification configuration  
✅ **Notification Policies** - Alert routing and timing configuration  
✅ **Alert Rules** - Properly organized in folders with `folder_uid`  
✅ **Provider Configuration** - Centralized in `providers.tf`  
✅ **Module Structure** - Organized submodules for maintainability  

## Usage

1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Update the variable values in `terraform.tfvars`
3. Run Terraform commands:

```bash
# Using the deployment script
./deploy.sh

# Or manually
terraform init
terraform plan
terraform apply
```

## Variables

Key variables that need to be configured:

- `grafana_url`: Grafana Cloud instance URL
- `grafana_auth`: Grafana Cloud authentication token
- `email_address`: Email address for alert notifications
- `environment`: Environment name for tagging
- `project_name`: Project name for tagging

## Benefits of Textbook Approach

1. **Official Compliance** - Follows Grafana's recommended patterns
2. **Proper Organization** - Uses folders for logical grouping
3. **Maintainability** - Clear separation of concerns
4. **Scalability** - Easy to add more dashboards and alerts
5. **Best Practices** - Implements Grafana's recommended structure

## Folder Structure in Grafana

After deployment, your Grafana instance will have:

```
📁 RouterOS Monitoring
├── 📁 SFP Monitoring
│   └── 📊 SFP Monitor Dashboard
└── 📁 Alerts
    └── 🚨 SFP Monitoring Alerts (rule group)
```

This structure provides clear organization and follows Grafana's recommended practices for monitoring infrastructure.

## 🏗️ Architecture

The Terraform setup uses a modular approach:

```
terraform/
├── main.tf                 # Main configuration and module calls
├── variables.tf            # Variable definitions with validation
├── terraform.tfvars.example # Example configuration file
├── modules/
│   ├── dashboards/         # Dashboard management module
│   │   └── main.tf        # SFP monitoring dashboard
│   └── alerts/            # Alert management module
│       └── main.tf        # Alert rules and notification policies
└── README.md              # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- Terraform >= 1.0
- Grafana Cloud account with API access
- Service account with appropriate permissions

### 2. Grafana Cloud Permissions

**⚠️ Important: Folder Creation Permissions Required**

The service account used for Terraform deployment **must have folder creation permissions** in Grafana Cloud. Without these permissions, the deployment will fail with a 403 error.

#### Required Permissions:
- **Folders**: Create, Read, Write, Delete
- **Alerting**: Read/Write/Delete
- **Metrics**: Read
- **Dashboards**: Read/Write
- **Annotations**: Read/Write

#### Setting Up Permissions:

1. **In Grafana Cloud Console**:
   - Go to your Grafana Cloud instance
   - Navigate to **Access Control** → **Service Accounts**
   - Create or edit your service account
   - Ensure the service account has **Admin** role or custom role with folder permissions

2. **Custom Role Setup** (if not using Admin):
   - Create a custom role with these permissions:
     - `folders:create`
     - `folders:read`
     - `folders:write`
     - `folders:delete`
     - `alerting:read`
     - `alerting:write`
     - `dashboards:read`
     - `dashboards:write`

3. **Alternative Workaround** (if folder permissions are not available):
   - Comment out the folders module in `main.tf`
   - Set `folder_uid = null` in dashboard and alert modules
   - Resources will be created in the General folder

#### Troubleshooting Permission Issues:

If you encounter permission errors like:
```
Error: [POST /folders][403] createFolderForbidden {"message":"You'll need additional permissions to perform this action. Permissions needed: folders:create"}
```

**Solutions**:
1. **Request folder permissions** from your Grafana Cloud administrator
2. **Use the workaround** above to deploy without folders
3. **Check service account role** - ensure it has Admin or custom role with folder permissions

### 3. Configuration

1. Copy the example configuration:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your settings:
   ```hcl
   grafana_url = "https://your-instance.grafana.net"
   grafana_auth = "glsa_your_service_account_token_here"
   environment = "production"
   project_name = "sfp-monitoring"
   ```

3. Customize thresholds and notification settings as needed.

### 4. Deployment

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

## 📊 Dashboards

The dashboards module creates:

- **SFP Monitoring Dashboard**: Comprehensive monitoring dashboard with:
  - SFP Power Levels (RX/TX)
  - SFP Temperature
  - Interface Status
  - ONT CPU/Memory Usage
  - PON Link Status
  - FEC Errors
  - Stale Data Indicator
  - OLT Information

### Dashboard Features

- **Templating**: Interface and severity filters
- **Thresholds**: Color-coded alerts for different values
- **Real-time**: 30-second refresh intervals
- **Responsive**: Adaptive layout for different screen sizes

## 🚨 Alerts

The alerts module creates comprehensive alert rules:

### Critical Alerts
- **SFP Interface Link Down**: Interface down for >1 minute
- **SFP Temperature Critical**: Temperature >85°C
- **ONT PON Link Down**: Loss of connectivity to OLT

### Warning Alerts
- **SFP RX Power Too Low**: Below -30 dBm
- **SFP Data Stale**: Cached power readings detected
- **ONT CPU Usage High**: Above 80%
- **OLT Vendor Changed**: Hardware/vendor changes detected

### Alert Features

- **Grouping**: Alerts grouped by alertname, interface, and severity
- **Throttling**: Configurable notification intervals
- **Escalation**: Different policies for critical vs warning alerts
- **Annotations**: Rich alert descriptions and context

## ⚙️ Configuration Options

### SFP Thresholds
- `sfp_rx_power_low_threshold`: RX power low threshold (-30.0 dBm)
- `sfp_rx_power_high_threshold`: RX power high threshold (-8.0 dBm)
- `sfp_temperature_warning_threshold`: Temperature warning (70.0°C)
- `sfp_temperature_critical_threshold`: Temperature critical (85.0°C)

### ONT Thresholds
- `ont_cpu_warning_threshold`: CPU usage warning (80.0%)
- `ont_memory_warning_threshold`: Memory usage warning (85.0%)

### Notification Settings
- `notification_group_wait`: Initial notification delay (30s)
- `notification_group_interval`: Group notification interval (5m)
- `notification_repeat_interval`: Repeat notification interval (4h)

## 🔧 Customization

### Adding New Alerts

1. Edit `modules/alerts/main.tf`
2. Add new rule blocks to the `grafana_rule_group` resource
3. Follow the existing pattern for data sources and conditions

### Modifying Dashboards

1. Edit `modules/dashboards/main.tf`
2. Modify the `config_json` in the dashboard resource
3. Add new panels or modify existing ones

### Adding Notification Channels

1. Edit the contact point in `modules/alerts/main.tf`
2. Add new notification channels (Slack, PagerDuty, etc.)
3. Configure the notification policy accordingly

## 🔒 Security

### Service Account Permissions

The service account needs these Grafana Cloud permissions:
- **Folders**: Create, Read, Write, Delete ⚠️ **Required for folder creation**
- **Alerting**: Read/Write/Delete
- **Metrics**: Read
- **Dashboards**: Read/Write
- **Annotations**: Read/Write

**Note**: Folder creation permissions are essential for this deployment. Without them, you'll need to use the workaround described in the [Grafana Cloud Permissions](#2-grafana-cloud-permissions) section above.

### Sensitive Data

- API tokens are marked as sensitive in Terraform
- Use environment variables or secure secret management
- Never commit `terraform.tfvars` with real credentials

## 📈 Monitoring

### Terraform State

- Use remote state storage (S3, Azure Storage, etc.)
- Enable state locking for team collaboration
- Regular state backups

### Resource Tracking

- All resources are tagged with environment and project
- Use Terraform outputs to track created resources
- Monitor resource costs and usage

## 🛠️ Troubleshooting

### Common Issues

1. **Provider Authentication**:
   ```bash
   export TF_VAR_grafana_auth="your_token"
   ```

2. **Module Dependencies**:
   ```bash
   terraform init -upgrade
   ```

3. **State Conflicts**:
   ```bash
   terraform refresh
   terraform plan
   ```

### Debugging

- Enable Terraform debug logging:
  ```bash
  export TF_LOG=DEBUG
  export TF_LOG_PATH=terraform.log
  ```

- Check Grafana Cloud API logs for authentication issues

## 🔄 Updates and Maintenance

### Updating Dashboards

1. Modify the dashboard configuration
2. Run `terraform plan` to see changes
3. Apply with `terraform apply`

### Updating Alerts

1. Modify alert rules in the alerts module
2. Test changes in a staging environment
3. Deploy to production

### Version Management

- Use semantic versioning for modules
- Tag releases in Git
- Document breaking changes

## 📚 Additional Resources

- [Grafana Cloud API Documentation](https://grafana.com/docs/grafana-cloud/reference/cloud-api/)
- [Terraform Grafana Provider](https://registry.terraform.io/providers/grafana/grafana/latest/docs)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 
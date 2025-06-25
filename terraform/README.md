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
    ├── dashboards/           # Internal dashboard module
    │   └── main.tf
    ├── dashboards-public/    # Public dashboard module
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
- Calls the folders, dashboards, dashboards-public, and alerts modules in the correct order

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
- Deploys the internal SFP monitoring dashboard
- Uses the dashboard JSON configuration file
- Places dashboard in the SFP Monitoring folder
- Provides full editing capabilities for administrators

### Dashboards Public Module
- Deploys the public version of the SFP monitoring dashboard
- Creates a read-only, publicly accessible dashboard
- Perfect for sharing with external stakeholders
- Includes time selection and annotation features
- No authentication required for access

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
│   ├── 📊 SFP Monitor Dashboard (Internal)
│   └── 📊 SFP Monitor Dashboard (Public)
└── 📁 Alerts
    └── 🚨 SFP Monitoring Alerts (rule group)
```

This structure provides clear organization and follows Grafana's recommended practices for monitoring infrastructure. The internal dashboard is fully editable by administrators, while the public dashboard provides read-only access through a public URL.

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

The dashboards module manages two types of dashboards:

### Internal Dashboard (Editable)
- **Location**: `modules/dashboards/`
- **Purpose**: Internal monitoring and configuration
- **Features**:
  - Full editing capabilities for administrators
  - Complete control over dashboard settings
  - Located in the SFP Monitoring folder
  - Requires authentication to access
  - Used for detailed analysis and configuration

### Public Dashboard (Read-only)
- **Location**: `modules/dashboards-public/`
- **Purpose**: Sharing monitoring data with external stakeholders
- **Features**:
  - Read-only access for security
  - Public URL access without authentication
  - Simplified view for external users
  - Time selection enabled for analysis
  - Annotations enabled for context
  - Perfect for sharing with vendors or support teams

### Dashboard Features (Both Versions)
- **Templating**: Interface and severity filters
- **Thresholds**: Color-coded alerts for different values
- **Real-time**: 30-second refresh intervals
- **Responsive**: Adaptive layout for different screen sizes
- **Metrics Displayed**:
  - SFP Power Levels (RX/TX)
  - SFP Temperature
  - Interface Status
  - ONT CPU/Memory Usage
  - PON Link Status
  - FEC Errors
  - Stale Data Indicator
  - OLT Information

## 🚨 Alerts

The alerts module creates comprehensive alert rules:

### System Alerts
- **SFP Monitoring Data Source Issues**: Detects connectivity problems, timeouts, and evaluation delays
- **SFP Data Stale**: Detects when SFP modules stop reporting fresh data

### Critical Alerts
- **SFP Interface Link Down**: Interface down for >1 minute (with rate-based detection)
- **SFP Temperature Critical**: Temperature >80°C (with proper value formatting)
- **ONT PON Link Down**: Loss of connectivity to OLT

### Warning Alerts
- **SFP RX Power Too Low**: Below -30.0 dBm (lower bound)
- **SFP RX Power Too High**: Above -20.0 dBm (upper bound)
- **SFP Vendor Serial Changed**: Hardware/module changes detected
- **ONT CPU Usage High**: Above 80% (with proper value formatting)

### Alert Features

- **Value Formatting**: Proper decimal places (%.2f for dBm, %.1f for temperature)
- **Data Source Handling**: Intelligent handling of timeouts and evaluation delays
- **Grouping**: Alerts grouped by alertname, interface, and severity
- **Throttling**: Configurable notification intervals
- **Escalation**: Different policies for critical vs warning alerts
- **Annotations**: Rich alert descriptions with current values and thresholds
- **Dynamic Labeling**: Proper interface labeling for multi-interface setups
- **Rate Detection**: Rate-based detection for handling missing scrapes

## ⚙️ Configuration Options

### SFP Thresholds
- `sfp_rx_power_low_threshold`: Lower bound RX power threshold (-30.0 dBm, more negative)
- `sfp_rx_power_high_threshold`: Upper bound RX power threshold (-20.0 dBm, less negative)
- `sfp_temperature_critical_threshold`: Temperature critical (80.0°C)

### ONT Thresholds
- `
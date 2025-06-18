# Mikrotik SFP Monitor

This script monitors SFP metrics from a Mikrotik router and exports them to Prometheus.

## Features

- Monitors SFP metrics (RX power, TX power, temperature, voltage)
- Uses Mikrotik API over SSL
- Exports metrics in Prometheus format
- Secure credential storage using `pass`

## Requirements

- Python 3.x
- `pass` for credential storage
- Virtual environment
- Required Python packages (see requirements.txt)

## Setup

1. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Store API credentials in pass:
   ```bash
   pass insert mikrotik/rt1/api-monitor/api-monitoring
   ```

4. Install systemd service:
   ```bash
   sudo cp mikrotik-monitor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable mikrotik-monitor
   sudo systemctl start mikrotik-monitor
   ```

5. Add to Prometheus config:
   ```yaml
   scrape_configs:
     - job_name: 'mikrotik_sfp'
       static_configs:
         - targets: ['localhost:9100']
   ```

## Metrics

The following metrics are exported:
- mikrotik_sfp_rx_power
- mikrotik_sfp_tx_power
- mikrotik_sfp_temperature
- mikrotik_sfp_voltage

## Prerequisites

- Linux server (tested on Ubuntu)
- Python 3.8 or higher
- Access to Mikrotik router with API enabled
- User account with sudo privileges

## 1. Router Configuration

### 1.1 Enable API on RouterOS
```
/ip service
set api disabled=no
set www-ssl disabled=no
```


### 1.2 Create API User
```
/user group
add name=api-monitoring policy=read,api,rest-api,!write

/user
add name=api-monitor group=api-monitoring password="secure_password"
```

## 2. Monitoring Server Setup (192.168.33.110)

### 2.1 Create Project Directory
```bash
mkdir -p ~/development/script-api-tik-monitor
cd ~/development/script-api-tik-monitor
```

### 2.2 Create Required Files

#### monitor.py
```python
#!/usr/bin/env python3
import requests
import time
import logging
from requests.auth import HTTPBasicAuth
from prometheus_client import start_http_server, Gauge

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)

# Prometheus metrics
sfp_rx_power = Gauge('mikrotik_sfp_rx_power', 'SFP RX Power Level')
sfp_tx_power = Gauge('mikrotik_sfp_tx_power', 'SFP TX Power Level')
sfp_temperature = Gauge('mikrotik_sfp_temperature', 'SFP Temperature')
sfp_voltage = Gauge('mikrotik_sfp_voltage', 'SFP Voltage')

# Router configuration
ROUTER_CONFIG = {
    'host': '192.168.33.1',
    'user': 'robert',
    'password': 'your_password',  # Change this
    'port': 443
}

def collect_metrics():
    base_url = f"https://{ROUTER_CONFIG['host']}/rest"
    
    try:
        response = requests.get(
            f"{base_url}/interface/ethernet/sfp-sfpplus1/monitor",
            auth=HTTPBasicAuth(ROUTER_CONFIG['user'], ROUTER_CONFIG['password']),
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Update Prometheus metrics
            rx_power = data.get('sfp-rx-power')
            tx_power = data.get('sfp-tx-power')
            temperature = data.get('sfp-temperature')
            voltage = data.get('sfp-voltage')
            
            if rx_power is not None:
                sfp_rx_power.set(rx_power)
                logging.info(f"RX Power: {rx_power}")
            
            if tx_power is not None:
                sfp_tx_power.set(tx_power)
                logging.info(f"TX Power: {tx_power}")
            
            if temperature is not None:
                sfp_temperature.set(temperature)
                logging.info(f"Temperature: {temperature}°C")
            
            if voltage is not None:
                sfp_voltage.set(voltage)
                logging.info(f"Voltage: {voltage}V")
            
        else:
            logging.error(f"API request failed with status code: {response.status_code}")
            
    except Exception as e:
        logging.error(f"Error collecting metrics: {e}")

def main():
    # Disable SSL warnings
    requests.packages.urllib3.disable_warnings()
    
    # Start Prometheus HTTP server
    start_http_server(9100)
    logging.info("Prometheus metrics server started on port 9100")
    
    # Collection loop
    while True:
        try:
            collect_metrics()
        except Exception as e:
            logging.error(f"Main loop error: {e}")
        time.sleep(30)  # Collect every 30 seconds

if __name__ == '__main__':
    main()
```

#### requirements.txt
```
requests>=2.28.0
prometheus-client>=0.16.0
```

#### mikrotik-monitor.service
```ini
[Unit]
Description=Mikrotik SFP Monitoring Service
After=network.target

[Service]
Type=simple
User=robert
WorkingDirectory=/home/robert/development/script-api-tik-monitor
Environment=PATH=/home/robert/development/script-api-tik-monitor/venv/bin
ExecStart=/home/robert/development/script-api-tik-monitor/venv/bin/python monitor.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

#### setup.sh
```bash
#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Make monitor.py executable
chmod +x monitor.py

# Set up systemd service
sudo cp mikrotik-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mikrotik-monitor
sudo systemctl start mikrotik-monitor

echo "Setup complete. Check status with: systemctl status mikrotik-monitor"
```

## 3. Installation Steps

1. Create project directory and navigate to it:
```bash
mkdir -p ~/development/script-api-tik-monitor
cd ~/development/script-api-tik-monitor
```

2. Create all required files:
```bash
# Create files
touch monitor.py requirements.txt setup.sh mikrotik-monitor.service

# Make setup script executable
chmod +x setup.sh
```

3. Copy the contents provided above into each respective file.

4. Update the configuration in monitor.py:
- Set correct router IP
- Update username and password
- Adjust port if needed

5. Run the setup script:
```bash
./setup.sh
```

## 4. Verification

1. Check service status:
```bash
systemctl status mikrotik-monitor
```

2. View logs:
```bash
journalctl -u mikrotik-monitor -f
```

3. Test metrics endpoint:
```bash
curl http://localhost:9100/metrics | grep mikrotik
```

## 5. Prometheus Configuration

Add to your prometheus.yml:
```yaml
scrape_configs:
  - job_name: 'mikrotik'
    static_configs:
      - targets: ['192.168.33.110:9100']
```

## 6. Grafana Dashboard

Import the following JSON to create a basic dashboard:
```json
{
  "panels": [
    {
      "title": "SFP Power Levels",
      "type": "graph",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "mikrotik_sfp_rx_power",
          "legendFormat": "RX Power"
        },
        {
          "expr": "mikrotik_sfp_tx_power",
          "legendFormat": "TX Power"
        }
      ]
    },
    {
      "title": "SFP Temperature",
      "type": "gauge",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "mikrotik_sfp_temperature",
          "legendFormat": "Temperature"
        }
      ],
      "thresholds": [
        { "value": 70, "color": "yellow" },
        { "value": 85, "color": "red" }
      ]
    }
  ]
}
```

## 7. Troubleshooting

### Common Issues

1. Service won't start:
- Check logs: `journalctl -u mikrotik-monitor -f`
- Verify Python virtual environment
- Check file permissions

2. No metrics available:
- Verify router API access
- Check firewall rules
- Verify network connectivity

3. API connection errors:
- Verify router IP address
- Check credentials
- Ensure API service is enabled on router

### Debug Commands

1. Test API connection:
```bash
curl -k -u robert:password https://192.168.33.1/rest/interface/ethernet/sfp-sfpplus1/monitor
```

2. Check service logs:
```bash
journalctl -u mikrotik-monitor -n 50
```

3. Test Python script directly:
```bash
cd ~/development/script-api-tik-monitor
source venv/bin/activate
python monitor.py
```

## 8. Maintenance

### Regular Tasks

1. Log rotation (if needed):
```bash
sudo nano /etc/logrotate.d/mikrotik-monitor
```

Add:
```
/home/robert/development/script-api-tik-monitor/monitor.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

2. Update dependencies:
```bash
cd ~/development/script-api-tik-monitor
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

3. Backup configuration:
```bash
cp -r ~/development/script-api-tik-monitor ~/backup/script-api-tik-monitor-$(date +%Y%m%d)
```

### Security Considerations

1. Regular password updates
2. Keep Python packages updated
3. Monitor system logs for unauthorized access attempts
4. Use SSL for API connections when possible
5. Implement proper firewall rules

## 9. Support

For issues or questions:
1. Check the logs
2. Review RouterOS API documentation
3. Verify network connectivity
4. Check system resources 
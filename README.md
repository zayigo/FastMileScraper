<div align="center">
  <h1 align="center">FastMileScraper</h1>

  <p align="center">
    Python scraper and management toolkit for Nokia FastMile 4G outdoor receivers / modems.
    <br />
    <a href="https://github.com/zayigo/FastMileScraper/issues">Report Bug</a>
    ·
    <a href="https://github.com/zayigo/FastMileScraper/issues">Request Feature</a>
  </p>
</div>

<br>

<details>
  <summary><strong>Table of Contents</strong></summary>
  <ol>
    <li><a href="#about">About</a></li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#configuration">Configuration (config.yaml)</a></li>
        <li><a href="#compatibility">Compatibility</a></li>
        <li><a href="#fcc-reports-and-documentation">FCC Reports & Documentation</a></li>
      </ul>
    </li>
    <li>
      <a href="#cli-usage">CLI Usage</a>
      <ul>
        <li><a href="#options-reference">Options Reference</a></li>
        <li><a href="#status-scraping">Status Scraping</a></li>
        <li><a href="#lte-band-selection">LTE Band Selection</a></li>
        <li><a href="#pci--cell-lock">PCI / Cell Lock</a></li>
        <li><a href="#apn-management">APN Management</a></li>
        <li><a href="#ssh-access-management">SSH Access Management</a></li>
        <li><a href="#troubleshooting-ssh-in-router-mode">Troubleshooting SSH in Router Mode</a></li>
        <li><a href="#cell-measurements">Cell Measurements</a></li>
        <li><a href="#reboot">Reboot</a></li>
      </ul>
    </li>
    <li><a href="#python-library-usage">Python Library Usage</a></li>
    <li><a href="#json-output-structure">JSON Output Structure</a></li>
    <li><a href="#earfcn-to-band-mapping">EARFCN to Band Mapping</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<br>

---

## About

![FastMile 4G receiver mounted](https://i.imgur.com/f76ONCY.jpeg)

**FastMileScraper** is a Python library and CLI tool built to interact with Nokia FastMile 4G outdoor receivers (e.g. 4G17-A).

It supports:
- **Unauthenticated status monitoring** (`status.php`): traffic stats (Ethernet & LTE), signal quality metrics (RSRP, RSRQ, RSSI, SINR), attached carrier aggregation bands, active/neighbor cells, APN IP addresses, and hardware/software info.
- **LTE Band selection** (`band.php`): query enabled/configured bands and toggle individual bands (B1, B3, B7, B20, B32, etc.).
- **PCI / Cell Locking** (`network.php`): lock the receiver to specific cell sectors by specifying Physical Cell ID (PCI) and channel number (EARFCN).
- **APN configuration** (`network.php`): view, add, edit, or delete APN profiles (Bridge Mode or Router Mode, VLAN tagging, MTU, netmask, authentication).
- **SSH access configuration** (`system.php`, `ssh.php`): query and toggle SSH server access for LAN and WAN interfaces.
- **EARFCN frequency and band resolution**: converts Downlink EARFCN values into official 3GPP LTE band numbers and MHz frequencies.
- **Neighbor cell measurements** (`measurements.php`): trigger on-demand radio measurements across surrounding towers.
- **Remote reboot** (`restart.php`): cleanly restart the modem via the web interface.
- **VPN / Network interface binding**: optional `SO_BINDTODEVICE` socket binding so you can communicate with the modem over a local adapter even when a VPN (e.g. WireGuard, OpenVPN, Cloudflare WARP) captures default routing.

> [!NOTE]
> Read-only status scraping requires **no authentication**. Management operations (band selection, cell lock, APN changes, reboot) require valid installer credentials (`fm2-installer`).

---

## Getting Started

### Prerequisites

Install the required Python dependencies:

* Using **pip**:
  ```sh
  pip install -r requirements.txt
  ```

* Using **pipenv**:
  ```sh
  pipenv install
  ```

The modem must be reachable at its management address (default: `https://192.168.0.1/`).

![Modem status page](https://i.imgur.com/iNzB4ga.png)

> [!TIP]
> If your modem is configured in Bridge Mode, ensure you have an APN configured in Router Mode or a dedicated management VLAN to access the web GUI.

### Configuration

You can store connection parameters and credentials in a `config.yaml` file in the project root:

```yaml
connection:
  host: 192.168.0.1
  protocol: https
  timeout: 30
  interface: wlp0s20f3  # Optional: network interface name (useful when VPN is active)

auth:
  username: fm2-installer
  password: your-password
```

> [!WARNING]
> Credentials in `config.yaml` are stored in plain text. Keep `config.yaml` in your `.gitignore` to avoid exposing credentials. Command-line flags always take precedence over values in `config.yaml`.

### Compatibility

Tested and verified on:
- **Nokia FastMile 4G17-A**
  - `FASTMILE2_D020111B90T0101M01E0130S`
  - `FASTMILE2_D020116B10T0101M01E0115S`

### FCC Reports and Documentation

- [User Manual Part 1 (FCC)](https://fccid.io/2ADZR4G01C/User-Manual/User-manual-part-1-5024260.pdf)
- [User Manual Part 2 (FCC)](https://fccid.io/2ADZR4G01C/User-Manual/User-manual-part-2-5024262.pdf)
- FCC IDs: [4G01-A](https://fccid.io/2ADZR34003800FM20), [4G01-B](https://fccid.io/2ADZR34003800FM201), [4G01-C](https://fccid.io/2ADZR4G01C), [4G01-D](https://fccid.io/2ADZR4G01D), [4G03-A](https://fccid.io/2ADZR23002690FM20), [4G05-A](https://fccid.io/2ADZR4G05A), [4G06-A](https://fccid.io/2ADZR4G06A)

---

## CLI Usage

### Options Reference

```text
usage: main.py [-h] [-H HOST] [-t TIMEOUT] [-i INTERFACE] [-u USERNAME] [-p PASSWORD]
               [--list-bands] [--enable-band BAND] [--disable-band BAND]
               [--list-cells] [--lock-cell PCI:EARFCN] [--unlock-cell PCI:EARFCN]
               [--list-apns] [--add-apn NAME:VLAN] [--delete-apn NAME]
               [--measure] [--reboot]

Nokia FastMile 4G API & Scraper

options:
  -h, --help            show this help message and exit
  -H, --host HOST       Modem hostname or IP address (default: 192.168.0.1)
  -t, --timeout TIMEOUT Connection timeout in seconds (default: 30)
  -i, --interface INTERFACE
                        Network interface to bind to (e.g. wlp0s20f3) (default: None)
  -u, --username USERNAME
                        Login username (default: from config)
  -p, --password PASSWORD
                        Login password (default: from config)

Band Selection:
  --list-bands          List supported LTE bands and their status
  --enable-band BAND    Enable a specific LTE band (e.g. B32 or 32)
  --disable-band BAND   Disable a specific LTE band (e.g. B20 or 20)

Cell / PCI Lock:
  --list-cells          List currently locked cells (PCI + EARFCN)
  --lock-cell PCI:EARFCN
                        Lock modem to cell as PCI:EARFCN (e.g. 383:3350)
  --unlock-cell PCI:EARFCN
                        Remove cell lock as PCI:EARFCN (e.g. 383:3350)

APN Management:
  --list-apns           List detailed APN configurations
  --add-apn NAME:VLAN   Add APN as NAME:VLAN (e.g. internet.wind:10)
  --delete-apn NAME     Delete APN by name

SSH Management:
  --get-ssh             Get current SSH access configuration (LAN/WAN)
  --enable-ssh-lan      Enable SSH access on LAN interface
  --disable-ssh-lan     Disable SSH access on LAN interface
  --enable-ssh-wan      Enable SSH access on WAN interface
  --disable-ssh-wan     Disable SSH access on WAN interface

Device Operations:
  --measure             Trigger cell measurement (scans neighboring cells)
  --reboot              Reboot the modem
```

---

### Status Scraping

Prints complete modem diagnostic metrics in structured JSON format. No authentication required.

```sh
python3 main.py
```

---

### LTE Band Selection

View supported LTE bands and enable or disable specific bands:

#### List available bands
```sh
python3 main.py --list-bands
```
Example output:
```json
[
  { "band": "B1", "enabled": true },
  { "band": "B3", "enabled": true },
  { "band": "B7", "enabled": true },
  { "band": "B20", "enabled": true },
  { "band": "B32", "enabled": false }
]
```

#### Enable or disable bands
```sh
# Enable supplementary downlink band B32
python3 main.py --enable-band B32

# Disable band B20
python3 main.py --disable-band B20
```

> [!NOTE]
> At least one band must remain enabled. The modem firmware requires a reboot to apply band modifications.

---

### PCI / Cell Lock

Lock the modem onto a specific base station sector using its Physical Cell ID (PCI) and Downlink EARFCN channel.

#### List active cell locks
```sh
python3 main.py --list-cells
```
Example output:
```json
[
  {
    "pci": 383,
    "earfcn": 3350,
    "band": 7,
    "frequency_mhz": 2680.0
  },
  {
    "pci": 500,
    "earfcn": 100,
    "band": 1,
    "frequency_mhz": 2120.0
  },
  {
    "pci": 500,
    "earfcn": 1650,
    "band": 3,
    "frequency_mhz": 1850.0
  }
]
```

#### Add a cell lock
```sh
# Lock to cell with PCI 383 on EARFCN 3350 (Band 7, 2680 MHz)
python3 main.py --lock-cell 383:3350
```

#### Remove a cell lock
```sh
# Remove the lock for PCI 383 on EARFCN 3350
python3 main.py --unlock-cell 383:3350
```

---

### APN Management

#### List configured APN profiles
```sh
python3 main.py --list-apns
```
Example output:
```json
[
  {
    "index": 0,
    "name": "internet.it",
    "forwarding_mode": "RouterMode",
    "vlan": 0,
    "mtu": 1500,
    "subnet_mask": "255.255.255.0",
    "auth_mode": "None"
  }
]
```

#### Add a new APN
```sh
# Add an APN with VLAN ID 10
python3 main.py --add-apn internet.wind:10
```

#### Delete an APN
```sh
python3 main.py --delete-apn internet.wind
```

---

### SSH Access Management

The modem's Dropbear SSH server can be toggled on LAN or WAN interfaces:

#### Check current SSH status
```sh
python3 main.py --get-ssh
```
Example output:
```json
{
  "lan": true,
  "wan": false
}
```

#### Enable or disable LAN SSH
```sh
# Enable LAN SSH access
python3 main.py --enable-ssh-lan

# Disable LAN SSH access
python3 main.py --disable-ssh-lan
```

#### Enable or disable WAN SSH
```sh
# Enable WAN SSH access (requires trusted IPv4 whitelist on the device)
python3 main.py --enable-ssh-wan

# Disable WAN SSH access
python3 main.py --disable-ssh-wan
```

---

### Troubleshooting SSH in Router Mode

A common issue encountered with Nokia FastMile 4G modems is that **SSH port 22 does not respond even when LAN SSH is toggled ON** in the Web GUI (`system.php`) or via API.

If your modem does not answer on port 22, review the following causes and solutions:

#### 1. Modem Reboot Required
In Nokia FastMile firmware, submitting the SSH switch to `ssh.php` writes the flag into the internal configuration storage/UCI, but **does not dynamically start Dropbear or reload `iptables` rules**.
* **Fix**: After enabling SSH LAN, restart the receiver (via `python3 main.py --reboot` or power cycle). Dropbear is initialized at boot time when the configuration flag is set.

#### 2. Subnet and Firewall Restrictions in Router Mode
In **Router Mode**, the modem acts as a NAT router and firewall gateway (`br-lan` on `192.168.0.1/24`). Its `iptables` `INPUT` chain typically accepts SSH connections **only from clients directly connected to its LAN subnet (`192.168.0.0/24`)**.
* If your PC is connected behind another cascaded router (e.g. your PC has IP `192.168.1.x` or `192.168.178.x` and connects to the FastMile PoE port via WAN/LAN uplink), the FastMile firewall drops packets from non-local subnets.
* **Fix**: Connect your PC directly to the LAN port of the PoE injector, configure your network adapter with a static IP in the same subnet (e.g., `192.168.0.50`, netmask `255.255.255.0`), and try connecting to `192.168.0.1:22`.

#### 3. WAN SSH Requires an IP Whitelist
Enabling WAN SSH without specifying at least one trusted IPv4 address in the Web GUI (`system.php`) will cause the device to return an HTTP 500 error (`Make sure that trusted IPv4 white list is not empty before enabling SSH WAN Access`).

#### 4. Operator Firmware Restrictions
Certain ISP firmware releases (e.g., specific operator-locked FWA distributions) deliberately disable interactive shell access for `fm2-installer` or restrict Dropbear authentication exclusively to cryptographic public keys pre-installed in the root filesystem.

---

### Cell Measurements

Triggers an RF scan of all surrounding base station signals.

```sh
python3 main.py --measure
```

> [!WARNING]
> Triggering a measurement temporarily interrupts cellular connectivity (approximately 30–60 seconds) while the receiver sweeps neighboring frequencies. Once the scan completes, run `python3 main.py` to view the refreshed `available` cells list.

---

### Reboot

Reboots the Nokia FastMile receiver cleanly:

```sh
python3 main.py --reboot
```

---

## Python Library Usage

You can import `FMScraper` directly into your own automation scripts:

```python
from fastmile import FMScraper, earfcn_to_band, earfcn_to_frequency

# 1. Initialize scraper
scraper = FMScraper(
    host="192.168.0.1",
    username="fm2-installer",
    password="your-password",
    interface="wlp0s20f3",  # Optional: bind to local interface if VPN is active
    timeout=30,
)

# 2. Status page scraping (no login needed)
scraper.download()
print("Device Info:", scraper.get_device_info())
print("Primary Cell:", scraper.get_primary_cell())
print("Secondary Cells:", scraper.get_secondary_cells())
print("Carrier Aggregation:", scraper.get_ca_info())
print("APN IPs:", scraper.get_apns())

# 3. Authenticated session
scraper.login()

# --- LTE Bands ---
bands = scraper.get_bands()
print("Supported Bands:", bands)
scraper.set_band("B32", enable=True)
scraper.set_band("B20", enable=False)

# --- Cell Lock (PCI / EARFCN) ---
cells = scraper.get_locked_cells()
print("Locked Cells:", cells)
scraper.add_cell_lock(pci=383, earfcn=3350)
scraper.delete_cell_lock(pci=383, earfcn=3350)

# --- APN Profiles ---
apns = scraper.get_apn_configs()
print("APN Configs:", apns)
scraper.add_apn(name="custom.apn", vlan=10, fwd_mode="BridgeMode")
scraper.edit_apn(old_name="custom.apn", mtu=1420)
scraper.delete_apn(name="custom.apn")

# --- SSH Access ---
ssh_status = scraper.get_ssh_status()
print("SSH Status:", ssh_status)
scraper.enable_ssh_lan(True)
# scraper.enable_ssh_wan(False)

# --- Reboot & Measurements ---
# scraper.trigger_measurement()
# scraper.reboot()

scraper.logout()
```

#### Standalone EARFCN Functions
```python
from fastmile import earfcn_to_band, earfcn_to_frequency

# Band lookup
print(earfcn_to_band(3350))       # 7
print(earfcn_to_band(100))        # 1
print(earfcn_to_band(1650))       # 3
print(earfcn_to_band(6300))       # 20

# Downlink center frequency lookup
print(earfcn_to_frequency(3350))  # 2680.0 MHz
print(earfcn_to_frequency(100))   # 2120.0 MHz
print(earfcn_to_frequency(1650))  # 1850.0 MHz
print(earfcn_to_frequency(6300))  # 806.0 MHz
```

---

## JSON Output Structure

Below is an annotated reference of the JSON returned by `main.py`:

```jsonc
{
  "info": {
    "model": "ODU - Multiband - 4G17-A",                  // Hardware model
    "sw_version": "FASTMILE2_D020116B10T0101M01E0115S",   // Firmware release
    "serial_number": "FSHxxxxxxxxx",                     // Unit serial number
    "imei": "35602811xxxxxxx",                           // Modem IMEI
    "imsi": "22288241xxxxxxx",                           // SIM IMSI
    "mac": "DC:8D:8A:xx:xx:xx",                          // Ethernet interface MAC address
    "lock_status": "Normal"                              // SIM lock status
  },
  "apns": [
    {
      "name": "internet.it.mnc088.mcc222.gprs",          // APN host identifier
      "ipv4": "10.10.11.239",                            // Assigned IPv4
      "ipv6": null                                       // Assigned IPv6
    }
  ],
  "data": {
    "eth": {                                             // Ethernet interface traffic since boot
      "download": { "val": 17.29, "unit": "GB", "val_gb": 17.29 },
      "upload": { "val": 7.19, "unit": "GB", "val_gb": 7.19 }
    },
    "lte": {                                             // LTE interface traffic since boot
      "download": { "val": 7.36, "unit": "GB", "val_gb": 7.36 },
      "upload": { "val": 17.29, "unit": "GB", "val_gb": 17.29 }
    }
  },
  "lte": {
    "ca": {
      "enb": 348105,                                     // Current eNodeB ID
      "cid": 20,                                         // Cell ID on primary carrier
      "dl_bands": [1, 3, 7],                             // Aggregated downlink bands (first is primary)
      "ul_bands": [1]                                    // Aggregated uplink bands
    },
    "cells": {
      "active": [                                        // Active component carriers
        {
          "pci": 500,                                    // Physical Cell ID
          "earfcn": 1650,                                // Downlink EARFCN
          "band": 3,                                     // 3GPP Band
          "frequency_mhz": 1850.0,                       // DL center frequency (MHz)
          "rsrp": -98,                                   // Reference Signal Received Power (dBm)
          "rsrq": -30,                                   // Reference Signal Received Quality (dB)
          "rssi": -63,                                   // Received Signal Strength Indicator (dBm)
          "sinr": 4,                                     // Signal to Interference-plus-Noise Ratio (dB)
          "type": "secondary"                            // Primary or secondary carrier
        },
        {
          "pci": 500,
          "earfcn": 100,
          "band": 1,
          "frequency_mhz": 2120.0,
          "rsrp": -95,
          "rsrq": -14,
          "rssi": -61,
          "sinr": -2,
          "type": "primary"
        }
      ],
      "available": []                                    // Populated after running --measure
    }
  }
}
```

---

## EARFCN to Band Mapping

The library implements the full **3GPP TS 36.101 Table 5.7.3-1** mapping for LTE bands 1 through 85.

The calculation uses the standard formula:
$$F_{DL} = F_{DL\_low} + 0.1 \times (N_{DL} - N_{Offs-DL})$$

Sample mappings:

| EARFCN | LTE Band | Downlink Frequency |
|:------:|:--------:|:------------------:|
| 100    | B1       | 2120.0 MHz         |
| 1650   | B3       | 1850.0 MHz         |
| 3350   | B7       | 2680.0 MHz         |
| 6300   | B20      | 806.0 MHz          |
| 10100  | B32      | 1470.0 MHz         |

---

## Roadmap

- [x] Test with different models and firmware versions (4G17-A)
- [x] Test with carrier aggregation disabled
- [x] Estimate LTE band and center frequency from EARFCN (3GPP TS 36.101)
- [x] Add "Trigger Measurement" command (`measurements.php`)
- [x] Session login and CSRF token handling (`login.php` + `network.php`)
- [x] LTE Band selection: query, enable, disable (`band.php`)
- [x] PCI / Cell Lock: query, add, delete (`network.php`)
- [x] APN configuration: query, add, edit, delete (`network.php`)
- [x] SSH Access configuration (LAN/WAN) via API and CLI (`ssh.php` / `system.php`)
- [x] Remote reboot (`restart.php`)
- [x] Network interface binding (`SO_BINDTODEVICE`) for VPN routing compatibility

---

## License

Distributed under the GNU General Public License v3.0. See [`LICENSE`](LICENSE) for more details.

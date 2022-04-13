<div align="center">
  <h1 align="center">FastMileScraper</h1>

  <p align="center">
    Scraper for Nokia FastMile 4G Modems/Routers
    <br />
    <a href="https://github.com/zayigo/FastMileScraper/issues">Report Bug</a>
    ·
    <a href="https://github.com/zayigo/FastMileScraper/issues">Request Feature</a>
  </p>
</div>

<br>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about">About</a>
      <ul>
        <li><a href="#disclaimer">Disclaimer</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#compatibility">Compatibility</a></li>
        <li><a href="#manual-and-fcc-reports">Manual and FCC Reports</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#examples">Examples</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<br>

## About

![FastMile 4G mounted on a pole](https://i.imgur.com/f76ONCY.jpeg)

This library is meant to be used with the [Nokia FastMile 4G](https://www.nokia.com/networks/products/fastmile-4g-receiver/) line of outdoor modems/routers. 

It can parse the data provided from the `status.php` page, no credentials required.

You can choose to use the example code provided in the `main.py` file to get a *JSON-formatted* output with all the information currently available or import the `fastmile.py` library in your own project.

### Disclaimer

At the moment no credentials are needed for this library to work but that might change in the future, *do not ask* for them if you own an isp-locked modem. Google is your friend.

## Getting Started

### Prerequisites

To install the required libraries you can use `pipenv` or `pip`.
* with *pipenv*
  ```sh
  pipenv install
  ```
* with *pip*
  ```sh
  pip install -r requirements.txt
  ```

A working connection to the modem's management interface (by default `https://192.168.0.1/status.php`) it's needed.

![Status page](https://i.imgur.com/iNzB4ga.png)

If you use bridge mode, you will need to create an APN in "router mode" on a different VLAN.

### Compatibility

At this time this library has been tested with the following models and software versions:
- Nokia Fastmile 4G17-A 
  - FASTMILE2_D020111B90T0101M01E0130S

Feel free to  [open an issue](https://github.com/zayigo/FastMileScraper/issues) or contact me at [info@nlab.pw](mailto:info@nlab.pw) to expand this list.

### Manual and FCC Reports

If you would like to dive deeper in the FastMile 4G lineup of products, the FFC published the user manual and datasheets:
- [Part 1](https://fccid.io/2ADZR4G01C/User-Manual/User-manual-part-1-5024260.pdf)
- [Part 2](https://fccid.io/2ADZR4G01C/User-Manual/User-manual-part-2-5024262.pdf)

you can also read the full reports:
- [FastMile 4G01-A](https://fccid.io/2ADZR34003800FM20)
- [FastMile 4G01-B](https://fccid.io/2ADZR34003800FM201)
- [FastMile 4G01-C](https://fccid.io/2ADZR4G01C)
- [FastMile 4G01-D](https://fccid.io/2ADZR4G01D)
- [FastMile 4G03-A](https://fccid.io/2ADZR23002690FM20)
- [FastMile 4G05-A](https://fccid.io/2ADZR4G05A)
- [FastMile 4G06-A](https://fccid.io/2ADZR4G06A)


## Usage

You can use the provided example (`main.py`) to get all the available information.
```sh
python3 main.py -h
usage: main.py [-h] [-H HOST] [-t TIMEOUT]

Nokia FastMile API

optional arguments:
  -h, --help            show this help message and exit
  -H HOST, --host HOST  Modem hostname or IP address (default: 192.168.0.1)
  -t TIMEOUT, --timeout TIMEOUT
                        Connection timeout (default: 30)
```


Alternatively you can use the provided library in your own projects.
```python
from fastmile import FMScraper

scraper = FMScraper(host="192.168.0.1", timeout=30)

scraper.download()

print(scraper.get_apns())

```

## Examples


### Hardware and software info
```jsonc
"info": {
  "model": "ODU - Multiband - 4G17-A", // Model
  "sw_version": "FASTMILE2_D020111B90T0101M01E0130S", // Software version
  "serial_number": "FSHxxxxxxxxx", // Serial numberi
  "imei": "xxxxxxxxxxxxxxx", // IMEI 
  "imsi": "xxxxxxxxxxxxxx", // IMSI
  "mac": "0C:7C:28:xx:xx:xx", // MAC Address of the ethernet interface
  "lock_status": "Normal" // Unknown, maybe related to SIM PIN code?
}
```

### APNs and IP
If you are behind CG-NAT the IP will be "internal" one.
```jsonc
"apns": [
  {
    "name": "internet.wind.mnc088.mcc222.gprs", // APN hostname
    "ipv4": "10.16.231.61", // IPv4 provided by the APN
    "ipv6": null // IPv6 provided by the APN
  },
  {
    "name": "internet.it.mnc088.mcc222.gprs",
    "ipv4": "10.10.95.146",
    "ipv6": null
  }
]
```

### Traffic on LTE and Ethernet interfaces
```jsonc
"data": {
  "eth": {  // Traffic since the last boot
    "download": {
      "val": 12.73,
      "unit": "GB",
      "val_gb": 12.73 // initially the traffic is displayed in MB
    },
    "upload": {
      "val": 451.2,
      "unit": "MB",
      "val_gb": 0.4512
    }
  },
  "lte": {  // Should be the same of the ethernet interface, just reversed
    "download": {
      "val": 451.2,
      "unit": "MB",
      "val_gb": 0.4512
    },
    "upload": {
      "val": 12.7,
      "unit": "GB",
      "val_gb": 12.7
    }
  }
}
```

### Carrier aggregation status
```jsonc
"ca": {
  "enb": xxxxx, // Current eNodeB 
  "cid": xx, // CID of the primary band
  "dl_bands": [ // Bands used for download, first one is primary
    1,
    7,
    3
  ],
  "ul_bands": [ // Bands used for upload, first one is primary
    1,
    7
  ]
}
```

### Active cells signal
```jsonc
"active": [
  {
    "pci": 197, // Physical Cell Id
    "earfcn": 3350, // E-UTRA Absolute Radio Frequency Channel Number
    "rsrp": -65, // Reference Signal Received Power
    "rsrq": -9, // Reference Signal Received Quality
    "rssi": -31, // Received Signal Strength Indicator
    "sinr": 30, // Signal to Noise Ration
    "type": "secondary" // Primary or secondary in case of carrier-aggregation
  },
  ...
]
```

### Available cells signal
**Note: this is updated only when you press "Trigger Measurement" on the status page and temporarily stops internet connectivity**
```jsonc
"available": [
  {
    "pci": 470,
    "earfcn": 150,
    "rsrp": -56,
    "rsqr": -14,
    "rssi": -31,
    "sinr": 30
  },
  ...
]
```

## Roadmap

- [ ] Test with different models and software versions
- [X] Test with carrier aggregation disabled
- [ ] Estimate band from EARFCN
- [ ] Add "Trigger Measurement" command
- [ ] Add login and login-protected functions
    - [ ] Bands selection
    - [ ] PCI Lock
    - [ ] APN edit/add
    - [ ] Reboot


## License

Distributed under the GNU General Public License v3.0. See `LICENSE` for more information.

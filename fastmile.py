import socket
import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from bs4 import BeautifulSoup, Comment, Tag
import re
from typing import Optional, Dict, Union, List, Tuple

# FastMile modems accept requests only via HTTPS with an unsigned certificate
requests.packages.urllib3.disable_warnings()

# 3GPP TS 36.101 Table 5.7.3-1: E-UTRA channel numbers (Downlink)
# Format: band -> (FDL_low MHz, NDL_offset, NDL_range_low, NDL_range_high)
EARFCN_BAND_TABLE: Dict[int, Tuple[float, int, int, int]] = {
    1:  (2110.0,     0,     0,   599),
    2:  (1930.0,   600,   600,  1199),
    3:  (1805.0,  1200,  1200,  1949),
    4:  (2110.0,  1950,  1950,  2399),
    5:  (869.0,   2400,  2400,  2649),
    6:  (875.0,   2650,  2650,  2749),
    7:  (2620.0,  2750,  2750,  3449),
    8:  (925.0,   3450,  3450,  3799),
    9:  (1844.9,  3800,  3800,  4149),
    10: (2110.0,  4150,  4150,  4749),
    11: (1475.9,  4750,  4750,  4949),
    12: (729.0,   5010,  5010,  5179),
    13: (746.0,   5180,  5180,  5279),
    14: (758.0,   5280,  5280,  5379),
    17: (734.0,   5730,  5730,  5849),
    18: (860.0,   5850,  5850,  5999),
    19: (875.0,   6000,  6000,  6149),
    20: (791.0,   6150,  6150,  6449),
    21: (1495.9,  6450,  6450,  6599),
    22: (3510.0,  6600,  6600,  7399),
    23: (2180.0,  7500,  7500,  7699),
    24: (1525.0,  7700,  7700,  8039),
    25: (1930.0,  8040,  8040,  8689),
    26: (859.0,   8690,  8690,  9039),
    27: (852.0,   9040,  9040,  9209),
    28: (758.0,   9210,  9210,  9659),
    29: (717.0,   9660,  9660,  9769),
    30: (2350.0,  9770,  9770,  9869),
    31: (462.5,   9870,  9870,  9919),
    32: (1452.0,  9920,  9920, 10359),
    33: (1900.0, 36000, 36000, 36199),
    34: (2010.0, 36200, 36200, 36349),
    35: (1850.0, 36350, 36350, 36949),
    36: (1930.0, 36950, 36950, 37549),
    37: (1910.0, 37550, 37550, 37749),
    38: (2570.0, 37750, 37750, 38249),
    39: (1880.0, 38250, 38250, 38649),
    40: (2300.0, 38650, 38650, 39649),
    41: (2496.0, 39650, 39650, 41589),
    42: (3400.0, 41590, 41590, 43589),
    43: (3600.0, 43590, 43590, 45589),
    44: (703.0,  45590, 45590, 46589),
    45: (1447.0, 46590, 46590, 46789),
    46: (5150.0, 46790, 46790, 54539),
    47: (5855.0, 54540, 54540, 55239),
    48: (3550.0, 55240, 55240, 56739),
    65: (2110.0, 65536, 65536, 66435),
    66: (2110.0, 66436, 66436, 67335),
    67: (738.0,  67336, 67336, 67535),
    68: (753.0,  67536, 67536, 67835),
    69: (2570.0, 67836, 67836, 68335),
    70: (1995.0, 68336, 68336, 68585),
    71: (617.0,  68586, 68586, 68935),
    72: (461.0,  68936, 68936, 68985),
    73: (460.0,  68986, 68986, 69035),
    74: (1475.0, 69036, 69036, 69465),
    75: (1432.0, 69466, 69466, 70315),
    76: (1427.0, 70316, 70316, 70365),
    85: (728.0,  70366, 70366, 70545),
}


def earfcn_to_band(earfcn: int) -> Optional[int]:
    """Estimates the LTE band from a Downlink EARFCN value.

    Uses the 3GPP TS 36.101 Table 5.7.3-1 mapping.

    Args:
        earfcn (int): E-UTRA Absolute Radio Frequency Channel Number (Downlink).

    Returns:
        Optional[int]: The LTE band number, or None if EARFCN is not in the table.
    """
    for band, (_, _, n_low, n_high) in EARFCN_BAND_TABLE.items():
        if n_low <= earfcn <= n_high:
            return band
    return None


def earfcn_to_frequency(earfcn: int) -> Optional[float]:
    """Converts a Downlink EARFCN to its center frequency in MHz.

    Uses the 3GPP TS 36.101 formula: F_DL = F_DL_low + 0.1 * (N_DL - N_Offs-DL)

    Args:
        earfcn (int): E-UTRA Absolute Radio Frequency Channel Number (Downlink).

    Returns:
        Optional[float]: Downlink frequency in MHz, or None if EARFCN is not found.
    """
    for _, (f_dl_low, n_offs, n_low, n_high) in EARFCN_BAND_TABLE.items():
        if n_low <= earfcn <= n_high:
            return round(f_dl_low + 0.1 * (earfcn - n_offs), 1)
    return None


class _InterfaceAdapter(HTTPAdapter):
    """Custom HTTP adapter that binds sockets to a specific network interface via SO_BINDTODEVICE."""

    def __init__(self, interface: str, **kwargs):
        self.interface = interface
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        socket_opt = getattr(socket, "SO_BINDTODEVICE", 25)
        opt = (socket.SOL_SOCKET, socket_opt, self.interface.encode("utf-8") + b"\0")
        pool_kwargs["socket_options"] = HTTPConnection.default_socket_options + [opt]
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


class FMScraper:

    def __init__(self, host: str = "192.168.0.1", timeout: int = 30,
                 username: Optional[str] = None, password: Optional[str] = None,
                 interface: Optional[str] = None) -> None:
        """Creates an instance of the FMScraper class

        Args:
            host (str): IP Address or hostname of the Nokia FastMile 4G Modem. Defaults to "192.168.0.1".
            timeout (int, optional): Request timeout in seconds. Defaults to 30.
            username (str, optional): Username for authenticated operations. Defaults to None.
            password (str, optional): Password for authenticated operations. Defaults to None.
            interface (str, optional): Network interface name to bind to (e.g. 'wlp0s20f3', 'eth0').
                                      Useful when a VPN is routing default traffic.
        """
        self.host = host
        self.timeout = timeout
        self.username = username
        self.password = password
        self.interface = interface
        self.soup = None
        self.network_soup = None
        self.session = requests.Session()
        self.session.verify = False

        if self.interface:
            adapter = _InterfaceAdapter(self.interface)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

        self._csrf_token: Optional[str] = None
        self._is_logged_in: bool = False

    @staticmethod
    def parse_ip(ip: str) -> Optional[str]:
        return None if (ip == "::") else ip

    @staticmethod
    def parse_int(html_element: Tag) -> Optional[int]:
        try:
            return int(html_element.get_text(strip=True))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def parse_used_data(val: str) -> Optional[Dict[str, Union[float, str]]]:
        val = val.upper()
        unit = re.search("[A-Z]+", val)
        if not unit:
            return None
        unit_str = unit.group()
        float_val = float(val.replace(unit_str, ""))
        val_gb = float_val / 1000 if (unit_str == "MB") else float_val
        return {"val": float_val, "unit": unit_str, "val_gb": val_gb}

    @staticmethod
    def parse_cell(val: List[Tag]) -> Dict[str, Union[int, str, None]]:
        earfcn_val = FMScraper.parse_int(val[1])
        return {
            "pci": FMScraper.parse_int(val[0]),
            "earfcn": earfcn_val,
            "band": earfcn_to_band(earfcn_val) if earfcn_val is not None else None,
            "frequency_mhz": earfcn_to_frequency(earfcn_val) if earfcn_val is not None else None,
            "rsrp": FMScraper.parse_int(val[3]),
            "rsrq": FMScraper.parse_int(val[4]),
            "rssi": FMScraper.parse_int(val[5]),
            "sinr": FMScraper.parse_int(val[6]),
        }

    @staticmethod
    def parse_bands(tag: Tag) -> List[int]:
        bands = tag.get_text(strip=True)
        if (bands != "CA Not Available"):
            b_list = bands.split("+")
            return [int(b.replace("B", "")) for b in b_list]
        return []

    @property
    def is_logged_in(self) -> bool:
        """Returns True if an authenticated session is active."""
        return self._is_logged_in

    def _require_auth(self) -> None:
        """Raises an error if no authenticated session is active."""
        if not self._is_logged_in:
            raise PermissionError(
                "Authentication required. Call login() first with valid credentials."
            )

    # --- Authentication ---

    def login(self) -> bool:
        """Authenticates with the Nokia FastMile gateway web interface.

        Submits credentials to /login.php and retrieves the CSRF token
        from /network.php for subsequent management actions.

        Returns:
            bool: True on successful login.

        Raises:
            ValueError: If username or password is not provided.
            ConnectionError: If authentication fails (e.g. invalid credentials).
        """
        if not self.username or not self.password:
            raise ValueError("Username and password are required for login.")

        login_url = f"https://{self.host}/login.php"
        resp = self.session.post(
            login_url,
            data={
                "access_login": self.username,
                "access_password": self.password,
                "submit": "Login",
            },
            timeout=self.timeout,
        )

        if resp.status_code != 200:
            raise ConnectionError(
                f"Login failed: HTTP {resp.status_code}. Please verify host and credentials."
            )

        self._is_logged_in = True
        self._refresh_network_page()
        return True

    def logout(self) -> None:
        """Logs out from the Nokia FastMile gateway and ends the active session."""
        if self._is_logged_in:
            try:
                logout_data = {"logout": "logout"}
                if self._csrf_token:
                    logout_data["token"] = self._csrf_token
                self.session.post(
                    f"https://{self.host}/network.php",
                    data=logout_data,
                    timeout=self.timeout,
                )
            except Exception:
                pass
            finally:
                self._is_logged_in = False
                self._csrf_token = None
                self.network_soup = None

    def _refresh_network_page(self) -> BeautifulSoup:
        """Fetches /network.php and extracts the current CSRF token."""
        url = f"https://{self.host}/network.php"
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            self._is_logged_in = False
            raise ConnectionError(f"Failed to access network.php: HTTP {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")
        logout_div = soup.find(id="logout")
        if not logout_div or "Welcome" not in logout_div.get_text():
            self._is_logged_in = False
            self._csrf_token = None
            raise PermissionError("Session expired or credentials rejected.")

        token_input = soup.find("input", {"name": "token"})
        if token_input and token_input.get("value"):
            self._csrf_token = token_input["value"]

        self.network_soup = soup
        return soup

    # --- Unauthenticated Status Operations ---

    def download(self) -> None:
        """Downloads and parses the status page

        Raises:
            ConnectionError: On wrong response code (!= 200)
        """
        response = self.session.get(
            f"https://{self.host}/status.php",
            timeout=self.timeout,
        )
        if (response.status_code != 200):
            raise ConnectionError(f"Got wrong response code {response.status_code}")
        self.soup = BeautifulSoup(response.text, "html.parser")

    def get_interface_data(self, name: str) -> Dict[str, Dict[str, Union[str, int]]]:
        """Returns the traffic of the given interface

        Args:
            name (str): Interface name
        """
        if not self.soup:
            raise AttributeError("Status page soup is missing")
        lte_stats = self.soup.find(class_=name).find_all(class_="bytes")
        return {
            "download": FMScraper.parse_used_data(lte_stats[0].get_text(strip=True)),
            "upload": FMScraper.parse_used_data(lte_stats[1].get_text(strip=True)),
        }

    def get_lte_data(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """Returns the traffic of the LTE interface since the last boot"""
        return self.get_interface_data("LTE")

    def get_ethernet_data(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """Returns the traffic of the Ethernet interface since the last boot"""
        return self.get_interface_data("Ethernet")

    def get_apns(self) -> List[Dict[str, str]]:
        """Returns the active APNs and their IP addresses"""
        if not self.soup:
            raise AttributeError("Status page soup is missing")
        apn_section = self.soup.find(text=lambda text: isinstance(text, Comment) and text.strip() == "APNs card")
        apn_section = apn_section.findNextSibling("div")
        values = apn_section.find_all("div", id=None)[2:]
        result = []
        for n in range(len(values) // 3):
            offset = n * 3
            ipv4 = values[offset + 1].get_text(strip=True)
            ipv6 = values[offset + 2].get_text(strip=True)
            result.append({
                "name": values[offset].get_text(strip=True),
                "ipv4": FMScraper.parse_ip(ipv4),
                "ipv6": FMScraper.parse_ip(ipv6),
            })
        return result

    def get_device_info(self) -> Dict[str, str]:
        """Returns HW and SW info about the device"""
        if not self.soup:
            raise AttributeError("Status page soup is missing")
        return {
            "model": self.soup.find(id="model-value").get_text(strip=True),
            "sw_version": self.soup.find(id="software-version-val").get_text(strip=True),
            "serial_number": self.soup.find(id="sn-value").get_text(strip=True),
            "imei": self.soup.find(id="imei-value").get_text(strip=True),
            "imsi": self.soup.find(id="imsi-name-value").get_text(strip=True),
            "mac": self.soup.find(id="eth-mac-value").get_text(strip=True),
            "lock_status": self.soup.find(id="lockStatus-name-value").get_text(strip=True),
        }

    def get_available_cells(self) -> List[Dict[str, Union[int, None, float]]]:
        """Returns the signal values of the measured cells but will not trigger a measurement"""
        if not self.soup:
            raise AttributeError("Status page soup is missing")
        available_cells_status = self.soup.find(id="available-cell-id")
        result = []
        if (not available_cells_status):
            count = 0
            end = False
            while not end:
                cell = self.soup.find(id=f"available-cell-id-{count}")
                if (not cell):
                    end = True
                    break
                earfcn_val = FMScraper.parse_int(self.soup.find(id=f"available-earfcn-{count}"))
                result.append({
                    "pci": FMScraper.parse_int(cell),
                    "earfcn": earfcn_val,
                    "band": earfcn_to_band(earfcn_val) if earfcn_val is not None else None,
                    "frequency_mhz": earfcn_to_frequency(earfcn_val) if earfcn_val is not None else None,
                    "rsrp": FMScraper.parse_int(self.soup.find(id=f"rsrp-{count}")),
                    "rsqr": FMScraper.parse_int(self.soup.find(id=f"rsrq-{count}")),
                    "rssi": FMScraper.parse_int(self.soup.find(id=f"rssi-{count}")),
                    "sinr": FMScraper.parse_int(self.soup.find(id=f"sinr-{count}")),
                })
                count += 1
        return result

    def get_values_after_comment(self, comment: str) -> List[Tag]:
        if not self.soup:
            raise AttributeError("Status page soup is missing")
        comment = self.soup.find(text=lambda text: isinstance(text, Comment) and text.strip() == comment)
        section = comment.findNextSibling("div")
        return section.find_all(class_="name-of-value-in-card-bold")

    def get_primary_cell(self) -> Dict[str, Union[str, int, None, float]]:
        """Returns the signal values of the primary cell (includes estimated band from EARFCN)"""
        values = self.get_values_after_comment("Primary Cell information card")
        result = FMScraper.parse_cell(values)
        result["type"] = "primary"
        return result

    def get_secondary_cells(self) -> List[Dict[str, Union[str, int, None, float]]]:
        """Returns the signal values of the secondary cells (includes estimated band from EARFCN)"""
        values = self.get_values_after_comment("Secondary Cell information card")
        result = []
        for n in range(len(values) // 7):
            offset = n * 7
            cell = FMScraper.parse_cell(values[offset:offset + 7])
            cell["type"] = "secondary"
            result.append(cell)
        return result

    def get_ca_info(self) -> Dict[str, Union[int, List[int]]]:
        """Returns info about carrier aggregation (DL-CA and UL-CA) and the current eNodeB"""
        if not self.soup:
            raise AttributeError("Status page soup is missing")
        attached_cell = self.soup.find(id="attached-cell-val").find_all("span")
        result = {"enb": FMScraper.parse_int(attached_cell[0]), "cid": FMScraper.parse_int(attached_cell[1])}
        primary_band = FMScraper.parse_int(attached_cell[2])
        ca_dl = FMScraper.parse_bands(self.soup.find(id="bandDL-val"))
        ca_ul = FMScraper.parse_bands(self.soup.find(id="bandUL-val"))
        result["dl_bands"] = [primary_band, *ca_dl]
        result["ul_bands"] = [primary_band, *ca_ul]
        return result

    # --- Trigger Measurement ---

    def trigger_measurement(self) -> bool:
        """Triggers a cell measurement on the FastMile gateway.

        This temporarily interrupts internet connectivity while the device
        scans for available neighboring cells. Results can be read afterwards
        with get_available_cells() after re-downloading the status page.

        Returns:
            bool: True if the measurement was triggered.
        """
        resp = self.session.post(
            f"https://{self.host}/measurements.php",
            data={"Submit": "Trigger"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.status_code == 200

    # --- Reboot (Requires Login) ---

    def reboot(self) -> bool:
        """Reboots the Nokia FastMile gateway.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the reboot command was accepted.

        Raises:
            PermissionError: If not logged in.
            ConnectionError: If the command fails.
        """
        self._require_auth()
        self._refresh_network_page()
        try:
            resp = self.session.post(
                f"https://{self.host}/restart.php",
                data={"token": self._csrf_token, "Submit": "Reboot"},
                timeout=self.timeout,
            )
            return resp.status_code == 200
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # Device reboots immediately and terminates connection
            return True

    # --- Bands Selection (Requires Login) ---

    def get_bands(self) -> List[Dict[str, Union[str, bool]]]:
        """Returns the list of LTE bands supported by the device and their configured status.

        Requires an active authenticated session (call login() first).

        Returns:
            List of dicts, each with:
                - band (str): Band identifier, e.g. 'B1', 'B3', 'B7', 'B20', 'B32'
                - enabled (bool): True if the band is enabled in configuration
        """
        self._require_auth()
        soup = self._refresh_network_page()
        bands = []
        for form in soup.find_all("form", class_="band-switch-form"):
            data_input = form.find("input", id=lambda x: x and x.startswith("data_"))
            toggle_input = form.find("input", id=lambda x: x and x.startswith("bandtoggle_"))
            if data_input:
                b_name = data_input.get("value", "")
                enabled = toggle_input.has_attr("checked") if toggle_input else False
                bands.append({
                    "band": b_name,
                    "enabled": enabled,
                })
        return bands

    def set_band(self, band: str, enable: bool) -> bool:
        """Enables or disables a specific LTE band on the gateway.

        Args:
            band (str): Band name, e.g. "B1", "B3", "B7", "B20", "B32" (or integer band number 1, 3, etc.).
            enable (bool): True to enable the band, False to disable it.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the change was accepted.

        Raises:
            ValueError: If the gateway rejects the action (e.g. attempting to disable all bands).
            PermissionError: If session has expired.
            ConnectionError: If request fails.

        Note:
            At least one band must remain enabled at all times.
            A modem reboot is required by the firmware to apply band configuration changes.
        """
        self._require_auth()
        if isinstance(band, int):
            band = f"B{band}"
        elif not band.startswith("B") and band.isdigit():
            band = f"B{band}"

        resp = self.session.post(
            f"https://{self.host}/band.php",
            data={
                "band-toggle": "true" if enable else "false",
                "data": band,
            },
            timeout=self.timeout,
        )

        if resp.status_code == 401:
            self._is_logged_in = False
            raise PermissionError("Session expired. Please log in again.")
        if resp.status_code == 500:
            raise ValueError(
                f"Failed to set band {band}: illegal action. Must have at least one enabled band."
            )
        resp.raise_for_status()
        return resp.status_code == 200

    # --- Cell Lock / PCI Lock (Requires Login) ---

    def get_locked_cells(self) -> List[Dict[str, Union[int, None, float]]]:
        """Returns the list of cells currently locked (PCI + EARFCN).

        Requires an active authenticated session (call login() first).

        Returns:
            List of dicts with keys:
                - pci (int): Physical Cell ID
                - earfcn (int): Downlink EARFCN channel number
                - band (int, optional): Estimated LTE band
                - frequency_mhz (float, optional): Estimated DL frequency in MHz
        """
        self._require_auth()
        soup = self._refresh_network_page()
        cells = []
        for earfcn_div in soup.find_all("div", class_="value-in-card-with-x"):
            img = earfcn_div.find("img", class_="button-x")
            if img and img.get("name") and img.get("id"):
                try:
                    pci = int(img["name"])
                    earfcn = int(img["id"])
                    cells.append({
                        "pci": pci,
                        "earfcn": earfcn,
                        "band": earfcn_to_band(earfcn),
                        "frequency_mhz": earfcn_to_frequency(earfcn),
                    })
                except (ValueError, TypeError):
                    continue
        return cells

    def add_cell_lock(self, pci: int, earfcn: int) -> bool:
        """Locks the modem to a specific cell (PCI and EARFCN).

        Args:
            pci (int): Physical Cell ID (0-503).
            earfcn (int): Downlink EARFCN channel number.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the cell lock was added.

        Raises:
            ValueError: If pci or earfcn values are out of bounds.
        """
        self._require_auth()
        if not (0 <= pci <= 503):
            raise ValueError(f"PCI must be in range 0-503, got {pci}")
        if earfcn < 0:
            raise ValueError(f"EARFCN must be non-negative, got {earfcn}")

        self._refresh_network_page()
        resp = self.session.post(
            f"https://{self.host}/network.php",
            data={
                "pci": str(pci),
                "downearfcn": str(earfcn),
                "token": self._csrf_token,
                "Submit": "Add Cell",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.status_code == 200

    def delete_cell_lock(self, pci: int, earfcn: int) -> bool:
        """Deletes a previously configured cell lock.

        Args:
            pci (int): Physical Cell ID.
            earfcn (int): Downlink EARFCN channel number.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the cell lock was removed.
        """
        self._require_auth()
        self._refresh_network_page()
        resp = self.session.post(
            f"https://{self.host}/network.php",
            data={
                "dpci": str(pci),
                "dear": str(earfcn),
                "token": self._csrf_token,
                "Submit": "Delete",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.status_code == 200

    # --- APN Management (Requires Login) ---

    def get_apn_configs(self) -> List[Dict[str, Union[str, int]]]:
        """Returns the configured APN profiles from the network management page.

        Requires an active authenticated session (call login() first).

        Returns:
            List of dicts with keys:
                - index (int): Card index
                - name (str): APN name
                - forwarding_mode (str): 'RouterMode' or 'BridgeMode'
                - vlan (int): VLAN ID
                - mtu (int): MTU size
                - subnet_mask (str): Subnet mask
                - auth_mode (str): 'None', 'PAP', or 'CHAP'
        """
        self._require_auth()
        soup = self._refresh_network_page()
        apns = []
        for div in soup.find_all("div", id=lambda x: x and x.startswith("apn_name_display-")):
            try:
                idx = int(div["id"].split("-")[1])
            except (IndexError, ValueError):
                continue
            name_tag = div.find("div", id=lambda x: x and x.startswith("apn-name-"))
            name = name_tag.get_text(strip=True) if name_tag else ""

            props = {}
            names = div.find_all("div", class_="name-of-value-in-card")
            values = div.find_all("div", class_="value-in-card")
            for n, v in zip(names, values):
                props[n.get_text(strip=True)] = v.get_text(strip=True)

            apns.append({
                "index": idx,
                "name": name,
                "forwarding_mode": props.get("Forwarding mode", ""),
                "vlan": int(props.get("VLAN", 0)),
                "mtu": int(props.get("MTU size", 1500)),
                "subnet_mask": props.get("Subnet Mask", ""),
                "auth_mode": props.get("Auth. Mode", "None"),
            })
        return apns

    def add_apn(self, name: str, vlan: int, fwd_mode: str = "BridgeMode",
                username: str = "", password: str = "", auth_mode: str = "None",
                mtu: int = 1500, netmask: str = "255.255.255.0") -> bool:
        """Adds a new Access Point Name (APN).

        Args:
            name (str): APN name (e.g. 'internet.wind.it'). Max 63 characters.
            vlan (int): VLAN ID (1-4094).
            fwd_mode (str): 'BridgeMode' or 'RouterMode'. Defaults to 'BridgeMode'.
            username (str, optional): APN username. Defaults to "".
            password (str, optional): APN password. Defaults to "".
            auth_mode (str): Authentication mode ('None', 'PAP', 'CHAP'). Defaults to 'None'.
            mtu (int): MTU size (0-1500). Defaults to 1500.
            netmask (str): Netmask. Defaults to '255.255.255.0'.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the APN was created.
        """
        self._require_auth()
        self._refresh_network_page()
        resp = self.session.post(
            f"https://{self.host}/network.php",
            data={
                "fwd_model": fwd_mode,
                "apn_name": name,
                "apn_username": username,
                "apn_password": password,
                "apn_password_retype": password,
                "apn_auth_mode": auth_mode,
                "vlan": str(vlan),
                "mtu": str(mtu),
                "netmask": netmask,
                "token": self._csrf_token,
                "Submit": "Add Access Point",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.status_code == 200

    def edit_apn(self, old_name: str, new_name: Optional[str] = None,
                 vlan: Optional[int] = None, fwd_mode: Optional[str] = None,
                 username: Optional[str] = None, password: Optional[str] = None,
                 auth_mode: Optional[str] = None, mtu: Optional[int] = None,
                 netmask: Optional[str] = None) -> bool:
        """Modifies an existing Access Point Name (APN).

        Unspecified fields will preserve their current values.

        Args:
            old_name (str): The current APN name to edit.
            new_name (str, optional): The new APN name (if changing).
            vlan (int, optional): New VLAN ID.
            fwd_mode (str, optional): 'BridgeMode' or 'RouterMode'.
            username (str, optional): New username.
            password (str, optional): New password.
            auth_mode (str, optional): 'None', 'PAP', or 'CHAP'.
            mtu (int, optional): New MTU size.
            netmask (str, optional): New subnet mask.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the APN was saved.
        """
        self._require_auth()
        current_configs = self.get_apn_configs()
        target = next((a for a in current_configs if a["name"] == old_name), None)
        if not target:
            raise ValueError(f"APN with name '{old_name}' not found.")

        final_name = new_name if new_name is not None else old_name
        final_vlan = vlan if vlan is not None else target["vlan"]
        final_fwd = fwd_mode if fwd_mode is not None else target["forwarding_mode"]
        final_auth = auth_mode if auth_mode is not None else target["auth_mode"]
        final_mtu = mtu if mtu is not None else target["mtu"]
        final_netmask = netmask if netmask is not None else target["subnet_mask"]

        self._refresh_network_page()
        resp = self.session.post(
            f"https://{self.host}/network.php",
            data={
                "fwd_model": final_fwd,
                "apn_name": final_name,
                "old_apn_name": old_name,
                "apn_username": username or "",
                "apn_password": password or "",
                "apn_password_retype": password or "",
                "apn_auth_mode": final_auth,
                "vlan": str(final_vlan),
                "mtu": str(final_mtu),
                "netmask": final_netmask,
                "token": self._csrf_token,
                "Submit": "Save",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.status_code == 200

    def delete_apn(self, name: str) -> bool:
        """Deletes an Access Point Name (APN) by name.

        Args:
            name (str): APN name to delete.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if the APN was deleted.
        """
        self._require_auth()
        self._refresh_network_page()
        resp = self.session.post(
            f"https://{self.host}/network.php",
            data={
                "apn_name_del": name,
                "token": self._csrf_token,
                "Submit": "Delete",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.status_code == 200

    # --- SSH Access Management (Requires Login) ---

    def get_ssh_status(self) -> Dict[str, bool]:
        """Returns the current SSH access configuration status (LAN and WAN).

        Requires an active authenticated session (call login() first).

        Returns:
            Dict[str, bool]: {'lan': bool, 'wan': bool} indicating if SSH is enabled.
        """
        self._require_auth()
        resp = self.session.get(f"https://{self.host}/system.php", timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        lan_cb = soup.find("input", id="lan")
        wan_cb = soup.find("input", id="wan")

        return {
            "lan": lan_cb.has_attr("checked") if lan_cb else False,
            "wan": wan_cb.has_attr("checked") if wan_cb else False,
        }

    def set_ssh(self, lan: Optional[bool] = None, wan: Optional[bool] = None) -> bool:
        """Configures SSH access permissions for LAN and/or WAN.

        Args:
            lan (bool, optional): Enable (True) or disable (False) LAN SSH access.
            wan (bool, optional): Enable (True) or disable (False) WAN SSH access.

        Requires an active authenticated session (call login() first).

        Returns:
            bool: True if configuration was applied.

        Raises:
            ValueError: If WAN SSH cannot be enabled (e.g. trusted IPv4 whitelist is empty).
            ConnectionError: If request fails.

        Note:
            On Nokia FastMile 4G modems, enabling LAN SSH saves the setting to the
            configuration database. However, in Router Mode, a device reboot is
            frequently required to start the Dropbear SSH service and update iptables rules.
        """
        self._require_auth()
        success = True

        if lan is not None:
            data = {"ssh-lan": "on", "lan-toggle": "false"} if lan else {"lan-toggle": "true"}
            resp = self.session.post(
                f"https://{self.host}/ssh.php",
                data=data,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                success = False

        if wan is not None:
            data = {"ssh-wan": "on", "wan-toggle": "false"} if wan else {"wan-toggle": "true"}
            resp = self.session.post(
                f"https://{self.host}/ssh.php",
                data=data,
                timeout=self.timeout,
            )
            if resp.status_code == 500:
                raise ValueError(
                    "Failed to enable WAN SSH: trusted IPv4 whitelist cannot be empty."
                )
            if resp.status_code != 200:
                success = False

        return success

    def enable_ssh_lan(self, enable: bool = True) -> bool:
        """Enables or disables LAN SSH access.

        Args:
            enable (bool): True to enable, False to disable.
        """
        return self.set_ssh(lan=enable)

    def enable_ssh_wan(self, enable: bool = True) -> bool:
        """Enables or disables WAN SSH access.

        Args:
            enable (bool): True to enable, False to disable.
        """
        return self.set_ssh(wan=enable)


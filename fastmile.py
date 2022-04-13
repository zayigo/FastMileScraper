import requests
from bs4 import BeautifulSoup, Comment, Tag
import re
from typing import Optional, Dict, Union, List

# FastMile modems accept requests only via HTTPS with an unsigned certificate
requests.packages.urllib3.disable_warnings()


class FMScraper:

    def __init__(self, host: str = "192.168.0.1", timeout: int = 30) -> None:
        """Creates an instance of the FMScraper class

        Args:
            host (str): IP Address or hostname of the Nokia FastMile 4G Modem. Defaults to "192.168.0.1".
            timeout (int, optional): Status page request timeout. Defaults to 30.
        """
        self.host = host
        self.timeout = timeout
        self.soup = None

    @staticmethod
    def parse_ip(ip: str) -> Optional[str]:
        return None if (ip == "::") else ip

    @staticmethod
    def parse_int(html_element: Tag) -> Optional[int]:
        try:
            return int(html_element.get_text(strip=True))
        except ValueError:
            return None

    @staticmethod
    def parse_used_data(val: str) -> Optional[Dict[str, Union[float, str]]]:
        val = val.upper()
        unit = re.search("[A-Z]+", val)
        if not unit:
            return None
        unit_str = unit.group()
        float_val = float(val.replace(unit_str, ""))
        return {"val": float_val, "unit": unit_str}

    @staticmethod
    def parse_cell(val: List[Tag]) -> Dict[str, Union[int, str]]:
        return {
            "pci": FMScraper.parse_int(val[0]),
            "earfcn": FMScraper.parse_int(val[1]),
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

    def download(self) -> None:
        """Downloads and parses the status page

        Raises:
            ConnectionError: On wrong response code (!= 200)
        """
        response = requests.get(f"https://{self.host}/status.php", verify=False, timeout=self.timeout)
        if (response.status_code != 200):
            raise ConnectionError(f"Got wrong response code {response.status_code}")
        self.soup = BeautifulSoup(response.text, 'html.parser')

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
            "upload": FMScraper.parse_used_data(lte_stats[1].get_text(strip=True))
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
                "ipv6": FMScraper.parse_ip(ipv6)
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
            "lock_status": self.soup.find(id="lockStatus-name-value").get_text(strip=True)
        }

    def get_available_cells(self) -> List[Dict[str, int]]:
        """Returns the signal values of the measured cells but will not trigger a measurement"""
        # TODO: try to guess band from earfcn
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
                result.append({
                    "pci": FMScraper.parse_int(cell),
                    "earfcn": FMScraper.parse_int(self.soup.find(id=f"available-earfcn-{count}")),
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

    def get_primary_cell(self) -> Dict[str, Union[str, int]]:
        """Returns the signal values of the primary cell"""
        # TODO: try to guess band from earfcn
        values = self.get_values_after_comment("Primary Cell information card")
        result = FMScraper.parse_cell(values)
        result["type"] = "primary"
        return result

    def get_secondary_cells(self) -> List[Dict[str, Union[str, int]]]:
        """Returns the signal values of the secondary cells"""
        # TODO: test without carrier aggregation
        # TODO: try to guess band from earfcn
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

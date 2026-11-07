import sys
import json
import argparse
import yaml
from fastmile import FMScraper


def load_config(config_path: str = "config.yaml") -> dict:
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def main() -> None:
    """Nokia FastMile 4G modem scraper and management CLI."""
    config = load_config()

    conn = config.get("connection", {})
    auth = config.get("auth", {})

    parser = argparse.ArgumentParser(
        description="Nokia FastMile 4G API & Scraper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Connection options
    parser.add_argument("-H", "--host", help="Modem hostname or IP address",
                        default=conn.get("host", "192.168.0.1"))
    parser.add_argument("-t", "--timeout", help="Connection timeout in seconds", type=int,
                        default=conn.get("timeout", 30))
    parser.add_argument("-i", "--interface", help="Network interface to bind to (e.g. wlp0s20f3)",
                        default=conn.get("interface"))

    # Auth options
    parser.add_argument("-u", "--username", help="Login username",
                        default=auth.get("username"))
    parser.add_argument("-p", "--password", help="Login password",
                        default=auth.get("password"))

    # Actions - Bands
    band_group = parser.add_argument_group("Band Selection")
    band_group.add_argument("--list-bands", help="List supported LTE bands and their status",
                            action="store_true")
    band_group.add_argument("--enable-band", help="Enable a specific LTE band (e.g. B32 or 32)",
                            metavar="BAND")
    band_group.add_argument("--disable-band", help="Disable a specific LTE band (e.g. B20 or 20)",
                            metavar="BAND")

    # Actions - Cell / PCI Lock
    cell_group = parser.add_argument_group("Cell / PCI Lock")
    cell_group.add_argument("--list-cells", help="List currently locked cells (PCI + EARFCN)",
                            action="store_true")
    cell_group.add_argument("--lock-cell", help="Lock modem to cell as PCI:EARFCN (e.g. 383:3350)",
                            metavar="PCI:EARFCN")
    cell_group.add_argument("--unlock-cell", help="Remove cell lock as PCI:EARFCN (e.g. 383:3350)",
                            metavar="PCI:EARFCN")

    # Actions - APN
    apn_group = parser.add_argument_group("APN Management")
    apn_group.add_argument("--list-apns", help="List detailed APN configurations",
                           action="store_true")
    apn_group.add_argument("--add-apn", help="Add APN as NAME:VLAN (e.g. internet.wind:10)",
                           metavar="NAME:VLAN")
    apn_group.add_argument("--delete-apn", help="Delete APN by name",
                           metavar="NAME")

    # Actions - SSH Management
    ssh_group = parser.add_argument_group("SSH Management")
    ssh_group.add_argument("--get-ssh", help="Get current SSH access configuration (LAN/WAN)",
                           action="store_true")
    ssh_group.add_argument("--enable-ssh-lan", help="Enable SSH access on LAN interface",
                           action="store_true")
    ssh_group.add_argument("--disable-ssh-lan", help="Disable SSH access on LAN interface",
                           action="store_true")
    ssh_group.add_argument("--enable-ssh-wan", help="Enable SSH access on WAN interface",
                           action="store_true")
    ssh_group.add_argument("--disable-ssh-wan", help="Disable SSH access on WAN interface",
                           action="store_true")

    # Actions - Device
    dev_group = parser.add_argument_group("Device Operations")
    dev_group.add_argument("--measure", help="Trigger cell measurement (scans neighboring cells)",
                           action="store_true")
    dev_group.add_argument("--reboot", help="Reboot the modem",
                           action="store_true")

    args = parser.parse_args()

    scraper = FMScraper(
        host=args.host,
        timeout=args.timeout,
        username=args.username,
        password=args.password,
        interface=args.interface,
    )

    # Determine if any authenticated action was requested
    auth_actions = [
        args.list_bands, args.enable_band, args.disable_band,
        args.list_cells, args.lock_cell, args.unlock_cell,
        args.list_apns, args.add_apn, args.delete_apn,
        args.get_ssh, args.enable_ssh_lan, args.disable_ssh_lan,
        args.enable_ssh_wan, args.disable_ssh_wan,
        args.reboot
    ]

    if any(auth_actions):
        if not args.username or not args.password:
            print("Error: --username and --password (or config.yaml) are required for this action.",
                  file=sys.stderr)
            sys.exit(1)

        try:
            scraper.login()
        except Exception as e:
            print(f"Login failed: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            # Bands
            if args.list_bands:
                bands = scraper.get_bands()
                print(json.dumps(bands, indent=2))
                return

            if args.enable_band:
                scraper.set_band(args.enable_band, enable=True)
                print(f"Band {args.enable_band} enabled successfully. Note: reboot required to apply.",
                      file=sys.stderr)
                return

            if args.disable_band:
                scraper.set_band(args.disable_band, enable=False)
                print(f"Band {args.disable_band} disabled successfully. Note: reboot required to apply.",
                      file=sys.stderr)
                return

            # Cell Lock
            if args.list_cells:
                cells = scraper.get_locked_cells()
                print(json.dumps(cells, indent=2))
                return

            if args.lock_cell:
                try:
                    pci_str, earfcn_str = args.lock_cell.split(":")
                    pci = int(pci_str)
                    earfcn = int(earfcn_str)
                except ValueError:
                    print("Error: format must be PCI:EARFCN (e.g. 383:3350)", file=sys.stderr)
                    sys.exit(1)
                scraper.add_cell_lock(pci, earfcn)
                print(f"Cell lock added: PCI={pci}, EARFCN={earfcn}", file=sys.stderr)
                return

            if args.unlock_cell:
                try:
                    pci_str, earfcn_str = args.unlock_cell.split(":")
                    pci = int(pci_str)
                    earfcn = int(earfcn_str)
                except ValueError:
                    print("Error: format must be PCI:EARFCN (e.g. 383:3350)", file=sys.stderr)
                    sys.exit(1)
                scraper.delete_cell_lock(pci, earfcn)
                print(f"Cell lock removed: PCI={pci}, EARFCN={earfcn}", file=sys.stderr)
                return

            # APN
            if args.list_apns:
                apns = scraper.get_apn_configs()
                print(json.dumps(apns, indent=2))
                return

            if args.add_apn:
                try:
                    name, vlan_str = args.add_apn.split(":")
                    vlan = int(vlan_str)
                except ValueError:
                    print("Error: format must be NAME:VLAN (e.g. myapn:10)", file=sys.stderr)
                    sys.exit(1)
                scraper.add_apn(name=name, vlan=vlan)
                print(f"APN '{name}' added with VLAN={vlan}", file=sys.stderr)
                return

            if args.delete_apn:
                scraper.delete_apn(args.delete_apn)
                print(f"APN '{args.delete_apn}' deleted", file=sys.stderr)
                return

            # SSH Management
            if args.get_ssh:
                ssh_status = scraper.get_ssh_status()
                print(json.dumps(ssh_status, indent=2))
                return

            if args.enable_ssh_lan:
                scraper.enable_ssh_lan(True)
                print("LAN SSH enabled successfully. Note: In router mode, a modem reboot is typically required to start Dropbear.",
                      file=sys.stderr)
                return

            if args.disable_ssh_lan:
                scraper.enable_ssh_lan(False)
                print("LAN SSH disabled successfully.", file=sys.stderr)
                return

            if args.enable_ssh_wan:
                scraper.enable_ssh_wan(True)
                print("WAN SSH enabled successfully. Note: Requires configured trusted IPv4 whitelist.",
                      file=sys.stderr)
                return

            if args.disable_ssh_wan:
                scraper.enable_ssh_wan(False)
                print("WAN SSH disabled successfully.", file=sys.stderr)
                return

            # Reboot
            if args.reboot:
                scraper.reboot()
                print("Reboot command sent to modem.", file=sys.stderr)
                return

        finally:
            scraper.logout()

    # Trigger measurement (can be done without login on this firmware)
    if args.measure:
        try:
            scraper.trigger_measurement()
            print("Measurement triggered. Internet connectivity will be temporarily interrupted.",
                  file=sys.stderr)
            print("Re-run status scrape once scanning completes to view updated available cells.",
                  file=sys.stderr)
        except Exception as e:
            print(f"Measurement trigger failed: {e}", file=sys.stderr)
        return

    # Default action: status page scraping
    try:
        scraper.download()
    except Exception as e:
        print(f"Failed to download status page: {e}", file=sys.stderr)
        sys.exit(1)

    result = {"info": scraper.get_device_info()}
    result["apns"] = scraper.get_apns()
    result["data"] = {
        "eth": scraper.get_ethernet_data(),
        "lte": scraper.get_lte_data(),
    }

    result["lte"] = {
        "ca": scraper.get_ca_info(),
        "cells": {
            "active": [*scraper.get_secondary_cells(), scraper.get_primary_cell()],
            "available": scraper.get_available_cells(),
        }
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

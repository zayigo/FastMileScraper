import sys
import json
import argparse
from fastmile import FMScraper


def main() -> None:
    """Prints an example JSON of all the data available from the status page"""
    parser = argparse.ArgumentParser(
        description="Nokia FastMile API", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-H", "--host", help="Modem hostname or IP address", default="192.168.0.1")
    parser.add_argument("-t", "--timeout", help="Connection timeout", default=30)
    config = vars(parser.parse_args())
    scraper = FMScraper(host=config["host"], timeout=config["timeout"])

    try:
        scraper.download()
    except Exception as e:
        print(e)
        sys.exit(1)

    result = {"info": scraper.get_device_info()}

    result["apns"] = scraper.get_apns()
    result["data"] = {}
    result["data"]["eth"] = scraper.get_ethernet_data()
    result["data"]["lte"] = scraper.get_lte_data()

    result["lte"] = {}
    result["lte"]["ca"] = scraper.get_ca_info()
    result["lte"]["cells"] = {}
    cell_primary = scraper.get_primary_cell()
    cells_secondary = scraper.get_secondary_cells()
    cells_secondary.append(cell_primary)
    result["lte"]["cells"]["active"] = cells_secondary
    result["lte"]["cells"]["available"] = scraper.get_available_cells()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

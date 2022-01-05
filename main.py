"""
This is a project to fetch compressed csvs from https://data.everef.net/public-contracts/
and insert the data within into a database.
"""

import csv
import datetime
import json
import tarfile
from datetime import timedelta, datetime
from io import BytesIO
from pathlib import Path
import logging

import requests
from bs4 import BeautifulSoup
from more_itertools import chunked
from filelock import FileLock, Timeout

from models import PublicContract, PublicContractItem

logger = logging.getLogger(__name__)


lock = FileLock("update_contracts.json.lock")


def everef_public_contract_pages_since(last_update: datetime):
    host = "https://data.everef.net"
    res = requests.get(f"{host}/public-contracts/history/")
    res.raise_for_status()
    year_soup = BeautifulSoup(res.content, features="html.parser")
    for year_a_tag in year_soup.find_all("a", class_="url"):
        url = f"{host}{year_a_tag['href']}"
        res = requests.get(url)
        res.raise_for_status()
        day_soup = BeautifulSoup(res.content, features="html.parser")
        for day_a_tag in day_soup.find_all("a", class_="url"):
            date = datetime.strptime(day_a_tag.text, "%Y-%m-%d")
            if date <= last_update - timedelta(days=1):
                continue
            yield f"{host}{day_a_tag['href']}"


def load_public_contract_history_index():
    logger.info("load_public_contract_history_index")
    try:
        with lock.acquire(timeout=0):  # acquire immediately or give up
            try:
                update_contracts_data = json.loads(Path("update_contracts.json").read_text())
            except FileNotFoundError:
                update_contracts_data = {"last_update": (datetime.utcnow() - timedelta(days=30)).timestamp()}

            last_update = datetime.fromtimestamp(update_contracts_data["last_update"])

            host = "https://data.everef.net"
            for url in everef_public_contract_pages_since(last_update):
                res = requests.get(url)
                res.raise_for_status()
                soup = BeautifulSoup(res.content, features="html.parser")
                for a_tag in soup.find_all("a", class_="data-file-url"):
                    file_name = a_tag.text
                    created_at = datetime.datetime.strptime(
                        file_name, "public-contracts-%Y-%m-%d_%H-%M-%S.v2.tar.bz2"
                    )

                    if created_at <= last_update:
                        continue

                    url = f"{host}{a_tag['href']}"
                    logger.info(
                        "public contract history",
                        extra={"file_name": file_name, "url": url},
                    )
                    load_public_contract_history(url)
                    Path("update_contracts.json").write_text(json.dumps({"last_update": created_at.timestamp()}))
    except Timeout:
        logger.info("Failed to get lock, returning.")
        return


def load_public_contract_history(url):
    res = requests.get(url)
    res.raise_for_status()

    tar = tarfile.open(fileobj=BytesIO(res.content), mode="r:bz2")
    try:
        data = tar.extractfile("contracts.csv").read().decode().splitlines()
        csv_reader = csv.DictReader(data)

        for to_insert in chunked(generate_public_contracts(csv_reader), 10_000):
            PublicContract.objects.bulk_create(to_insert, ignore_conflicts=True)
    except KeyError:
        pass

    try:
        data = tar.extractfile("contract_items.csv").read().decode().splitlines()
        csv_reader = csv.DictReader(data)

        for to_insert in chunked(generate_public_contract_items(csv_reader), 10_000):
            PublicContractItem.objects.bulk_create(to_insert, ignore_conflicts=True)
    except KeyError:
        pass


def str_to_bool(value, default=None):
    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        return default


def generate_public_contracts(csv_reader):
    contract_ids = set(
        PublicContract.objects.filter(
            date_issued__gte=datetime.utcnow() - timedelta(days=30)
        ).values_list("contract_id", flat=True)
    )

    for public_contract in csv_reader:
        contract_type = public_contract.get("type")
        if contract_type not in ("auction", "item_exchange"):
            continue
        contract_id = int(public_contract.get("contract_id"))
        if contract_id in contract_ids:
            continue

        yield PublicContract(
            ...
        )


def generate_public_contract_items(csv_reader):
    contract_ids = dict(
        PublicContract.objects.filter(
            date_issued__gte=datetime.utcnow() - timedelta(days=30)
        ).values_list("contract_id", "id")
    )
    record_ids = set(
        PublicContractItem.objects.filter(
            contract__date_issued__gte=datetime.utcnow() - timedelta(days=30)
        ).values_list("record_id", flat=True)
    )

    for public_contract_item in csv_reader:
        contract_id = int(public_contract_item.get("contract_id"))
        if contract_id not in contract_ids:
            continue
        record_id = int(public_contract_item.get("record_id"))
        if record_id in record_ids:
            continue

        yield PublicContractItem(
            ...
        )
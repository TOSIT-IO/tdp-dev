# HBase REST documentation https://hbase.apache.org/book.html#_rest
import base64
import hashlib
import io
import json
import time
from typing import Callable, Generator, List

import pytest
from testinfra import host

from .conftest import USERS, retry

testinfra_hosts = ["edge"]


def hbase_table_from_user(user: str):
    return f"{user}_table_hbase".upper()


@pytest.fixture(scope="module")
def hbase_table(user: str) -> str:
    return hbase_table_from_user(user)


@pytest.fixture(scope="module")
def nb_region_server(host: host.Host) -> int:
    return len(host.backend.get_hosts("hbase_rs"))


@pytest.fixture(scope="module")
def hbase_ranger_policy(
    nb_region_server: int,
    ranger_policy: Callable[[str, str, dict, List[dict], int], dict],
):
    resources = {
        "table": {
            "values": [hbase_table_from_user(user) for user in USERS],
            "isExcludes": False,
        },
        "column-family": {"values": ["*"], "isExcludes": False},
        "column": {"values": ["*"], "isExcludes": False},
    }
    policyItems = [
        {
            "users": USERS,
            "accesses": [
                {"isAllowed": True, "type": "read"},
                {"isAllowed": True, "type": "write"},
                {"isAllowed": True, "type": "create"},
                {"isAllowed": True, "type": "admin"},
            ],
        }
    ]
    ranger_policy("hbase_pytest", "hbase-tdp", resources, policyItems, nb_region_server)


def to_base64(value):
    return str(base64.b64encode(bytes(value, "utf-8")), "ascii")


def create_hbase_dataset(
    host: host.Host,
    user: str,
    hbase_table: str,
    dataset_weight: List[dict],
    curl: Callable,
    hbase_rest: str,
) -> int:
    nb_lines = len(dataset_weight)
    row_ids = [
        hashlib.sha256(bytes(str(time.time()), "utf-8")).hexdigest()
        + "_"
        + str(data["id"])
        for data in dataset_weight
    ]

    weight_column = to_base64("car:weight")
    category_column = to_base64("car:category")
    data = {
        "Row": [
            {
                "key": to_base64(row_id),
                "Cell": [
                    {
                        "column": weight_column,
                        "$": to_base64(str(data["weight"])),
                    },
                    {
                        "column": category_column,
                        "$": to_base64(data["category"]),
                    },
                ],
            }
            for row_id, data in zip(row_ids, dataset_weight)
        ]
    }
    curl_args = [
        "--negotiate",
        "--user :",
        "--header 'Accept: application/json'",
        "--header 'Content-Type: application/json'",
        "--request PUT",
        f"--data '{json.dumps(data)}'",
        f"{hbase_rest}/{hbase_table}/fakerow",
    ]
    with host.sudo(user):
        curl(" ".join(curl_args))
    return nb_lines


@pytest.fixture(scope="module")
def setup_hbase_table(
    host: host.Host,
    user: str,
    hbase_table: str,
    lock: Callable,
    hbase_ranger_policy: None,
    dataset_weight: List[dict],
    curl: Callable,
    hbase_rest: str,
) -> Generator[dict, None, None]:
    nb_lines: int
    with lock(f"hbase_table_{hbase_table}") as data:
        if not data.setdefault("hbase_table_created", False):
            table_schema = {
                "ColumnSchema": [
                    {"name": "car", "VERSIONS": 3},
                    {"name": "opinion", "VERSIONS": 5},
                ]
            }
            curl_args = [
                "--negotiate",
                "--user :",
                "--header 'Accept: application/json'",
                "--header 'Content-Type: application/json'",
                "--request POST",
                f"--data '{json.dumps(table_schema)}'",
                f"{hbase_rest}/{hbase_table}/schema",
            ]
            with host.sudo(user):

                @retry
                def create_table():
                    curl(" ".join(curl_args))

                create_table()
                data["hbase_table_created"] = True
            nb_lines = create_hbase_dataset(
                host, user, hbase_table, dataset_weight, curl, hbase_rest
            )
            data["hbase_nb_lines"] = nb_lines
        else:
            nb_lines = data["hbase_nb_lines"]

    yield {"table_name": hbase_table, "nb_lines": nb_lines}

    with lock(f"hbase_table_{hbase_table}", teardown=True) as data:
        if not data["last_worker"]:
            return
        curl_args = [
            "--negotiate",
            "--user :",
            "--request DELETE",
            f"{hbase_rest}/{hbase_table}/schema",
        ]
        with host.sudo(user):
            curl(" ".join(curl_args))
            data["hbase_table_created"] = False


def test_scanning_with_filter_works(
    host: host.Host,
    user: str,
    setup_hbase_table: dict,
    hbase_rest: str,
    curl: Callable,
):
    hbase_table = setup_hbase_table["table_name"]
    nb_lines = setup_hbase_table["nb_lines"]
    scanner_args = {
        "batch": nb_lines,
        "filter": json.dumps(
            {
                "op": "EQUAL",
                "type": "RowFilter",
                "comparator": {"value": "_150", "type": "SubstringComparator"},
            }
        ),
    }
    curl_args = [
        "--negotiate",
        "--user :",
        "--header 'Accept: application/json'",
        "--header 'Content-Type: application/json'",
    ]

    curl_data_args = [
        "--request POST",
        f"--data '{json.dumps(scanner_args)}'",
        f"{hbase_rest}/{hbase_table}/scanner",
    ]

    with host.sudo(user):
        curl_result = curl(" ".join(curl_args + curl_data_args))
        for line in io.StringIO(curl_result["command"].stderr).readlines():
            if "Location:" in line:
                scanner_uri = line.split(": ")[1].strip()
                break
        else:
            raise ValueError("Pas trouvé d'url location pour le scanner")
        try:
            curl_result = curl(" ".join(curl_args + [scanner_uri]))
            data = json.loads(curl_result["command"].stdout)
            assert len(data["Row"]) == 1
        finally:
            # free the scanner
            curl(" ".join(curl_args + ["--request DELETE", scanner_uri]))


def test_hbase_script_is_executed(
    host: host.Host,
    user: str,
    setup_hbase_table: dict,
    render_file: Callable,
):

    hbase_table = setup_hbase_table["table_name"]
    nb_lines = setup_hbase_table["nb_lines"]

    script = "count '{table}'"
    script_path = f"/tmp/{user}_count_script.hrb"

    render_file(
        script_path,
        script,
        {"table": hbase_table},
        owner=user,
        group=user,
        permissions=0o644,
    )

    with host.sudo(user):
        stdout = host.check_output(
            f"cat '{script_path}' | hbase shell --noninteractive"
        )
        assert f"{nb_lines} row(s)" in stdout


def test_hbase_mapreduce_row_count_works(
    host: host.Host,
    user: str,
    setup_hbase_table: dict,
):
    hbase_table = setup_hbase_table["table_name"]
    nb_lines = setup_hbase_table["nb_lines"]
    with host.sudo(user):
        stdout = host.run_expect(
            [0], f"hbase org.apache.hadoop.hbase.mapreduce.RowCounter '{hbase_table}'"
        ).stdout
        assert f"ROWS={nb_lines}" in stdout

import textwrap
from typing import Callable, Generator, List

import pytest

from testinfra import host

from .conftest import retry

testinfra_hosts = ["edge"]


@pytest.fixture(scope="module")
def hive_database(user: str) -> str:
    return f"{user}_db"


@pytest.fixture(scope="module")
def hive_table(user: str) -> str:
    return f"{user}_table"

@pytest.fixture(scope="module")
def hive_iceberg_table(user: str) -> str:
    return f"{user}_iceberg_table"


@pytest.fixture(scope="module")
def hive_ranger_policy(
    user: str,
    hive_database: str,
    ranger_policy: Callable[[str, str, dict, List[dict]], dict],
):
    resources = {
        "database": {"values": [hive_database], "isExcludes": False},
        "table": {"values": ["*"], "isExcludes": False},
        "column": {"values": ["*"], "isExcludes": False},
    }
    policyItems = [
        {
            "users": [user],
            "accesses": [
                {"isAllowed": True, "type": "select"},
                {"isAllowed": True, "type": "update"},
                {"isAllowed": True, "type": "create"},
                {"isAllowed": True, "type": "drop"},
                {"isAllowed": True, "type": "alter"},
                {"isAllowed": True, "type": "index"},
                {"isAllowed": True, "type": "lock"},
                {"isAllowed": True, "type": "all"},
                {"isAllowed": True, "type": "read"},
                {"isAllowed": True, "type": "write"},
                {"isAllowed": True, "type": "refresh"},
            ],
        }
    ]
    ranger_policy(f"{user}_hive_test", "hive-tdp", resources, policyItems)


@pytest.fixture(scope="module")
def setup_hive_database(
    host: host.Host,
    user: str,
    hive_database: str,
    hive_ranger_policy: None,
) -> Generator[str, None, None]:
    with host.sudo(user):
        retry(
            lambda: host.check_output(
                f"beeline -e \"CREATE DATABASE {hive_database} LOCATION '{hive_database}'\""
            )
        )()
    yield hive_database
    with host.sudo(user):
        host.check_output(f"beeline -e 'DROP DATABASE {hive_database}'")


@pytest.fixture(scope="module")
def setup_hive_table(
    host: host.Host,
    user: str,
    dataset_weight_csv: dict,
    setup_hive_database: str,
    hive_table: str,
    render_file: Callable,
) -> Generator[str, None, None]:
    hive_database = setup_hive_database
    dataset_csv = dataset_weight_csv["hdfs_dir"]
    create_table_script = """
    USE {database};

    CREATE EXTERNAL TABLE {table} (
        id int,
        weight float,
        category varchar(9)
    )
        ROW FORMAT DELIMITED
        FIELDS TERMINATED BY ","
        STORED AS TEXTFILE 
        LOCATION "{dataset_csv}"
        tblproperties("skip.header.line.count"="1");
    """
    create_table_script = textwrap.dedent(create_table_script)
    distant_path = f"/tmp/{user}_create_table.hql"
    render_file(
        distant_path,
        create_table_script,
        {
            "database": hive_database,
            "table": hive_table,
            "dataset_csv": dataset_csv,
        },
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        host.check_output(f"beeline -f '{distant_path}'")
    yield hive_table
    with host.sudo(user):
        host.check_output(
            f"beeline -e 'use {hive_database}' -e 'DROP TABLE {hive_table}'"
        )

@pytest.fixture(scope="module")
def setup_hive_iceberg_table(
    host: host.Host,
    user: str,
    dataset_weight_csv: dict,
    setup_hive_database: str,
    hive_iceberg_table: str,
    render_file: Callable,
) -> Generator[str, None, None]:
    hive_database = setup_hive_database
    create_table_script = """
    USE {database};

    CREATE TABLE {table} (
        trip_id bigint,
        trip_distance float,
        fare_amount double,
        store_and_fwd_flag string
    )
    PARTITIONED BY (vendor_id bigint) STORED BY ICEBERG;

    INSERT INTO {table}
    VALUES (1000371, 1.8, 15.32, 'N', 1), (1000372, 2.5, 22.15, 'N', 2), (1000373, 0.9, 9.01, 'N', 2), (1000374, 8.4, 42.13, 'Y', 1);
    """
    create_table_script = textwrap.dedent(create_table_script)
    distant_path = f"/tmp/{user}_create_iceberg_table.hql"
    render_file(
        distant_path,
        create_table_script,
        {
            "database": hive_database,
            "table": hive_iceberg_table,
        },
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        host.check_output(f"beeline -f '{distant_path}'")
    yield hive_iceberg_table
    with host.sudo(user):
        host.check_output(
            f"beeline -e 'use {hive_database}' -e 'DROP TABLE {hive_iceberg_table}'"
        )

def test_hive_csv_script_is_executed(
    host: host.Host,
    user: str,
    dataset_weight_csv: dict,
    setup_hive_database: str,
    setup_hive_table: str,
    render_file: Callable,
):
    nb_lines = dataset_weight_csv["nb_lines"]
    hive_database = setup_hive_database
    hive_table = setup_hive_table
    script = """
    USE {database};

    SELECT COUNT(*) FROM {table};
    """
    script = textwrap.dedent(script)
    script_path = f"/tmp/{user}_script.hql"
    render_file(
        script_path,
        script,
        {
            "database": hive_database,
            "table": hive_table,
        },
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        stdout = host.check_output(f"beeline -f '{script_path}'")
        assert f"{nb_lines}" in stdout

def test_hive_iceberg_execution(
    host: host.Host,
    user: str,
    setup_hive_database: str,
    setup_hive_iceberg_table: str,
    render_file: Callable,
):
    hive_database = setup_hive_database
    hive_iceberg_table = setup_hive_iceberg_table
    script = """
    USE {database};

    SELECT fare_amount
    FROM {table}
    WHERE trip_id==1000373;
    """
    script = textwrap.dedent(script)
    script_path = f"/tmp/{user}_iceberg_script.hql"
    render_file(
        script_path,
        script,
        {
            "database": hive_database,
            "table": hive_iceberg_table,
        },
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        stdout = host.check_output(f"beeline -f '{script_path}'")
        assert "9.01" in stdout

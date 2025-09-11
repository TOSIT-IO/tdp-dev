import textwrap
from typing import Callable, Generator, List

import pytest

from testinfra import host

from .conftest import retry

testinfra_hosts = ["edge"]


@pytest.fixture(scope="module")
def phoenix_table(user: str) -> str:
    return f"{user}_table_phoenix".upper()


@pytest.fixture(scope="module")
def phoenix_ranger_policy(
    user: str,
    phoenix_table: str,
    ranger_policy: Callable[[str, str, dict, List[dict]], dict],
):
    resources = {
        "table": {"values": [phoenix_table], "isExcludes": False},
        "column-family": {"values": ["*"], "isExcludes": False},
        "column": {"values": ["*"], "isExcludes": False},
    }
    policyItems = [
        {
            "users": [user],
            "accesses": [
                {"isAllowed": True, "type": "read"},
                {"isAllowed": True, "type": "write"},
                {"isAllowed": True, "type": "create"},
                {"isAllowed": True, "type": "admin"},
            ],
        }
    ]
    ranger_policy(f"{user}_phoenix_test", "hbase-tdp", resources, policyItems)


@pytest.fixture(scope="module")
def setup_phoenix_table(
    host: host.Host,
    user: str,
    phoenix_table: str,
    render_file: Callable,
    phoenix_ranger_policy: None,
    phoenix_queryserver: str,
) -> Generator[str, None, None]:
    create_table_script = """
    CREATE TABLE IF NOT EXISTS {table} (
        id bigint not null,
        car.weight float,
        car.category varchar,
        CONSTRAINT pk PRIMARY KEY (id)
    );
    """
    create_table_script = textwrap.dedent(create_table_script)
    script_path = f"/tmp/{user}_create_table.sql"
    render_file(
        script_path,
        create_table_script,
        {"table": phoenix_table},
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):

        def create_table():
            host.check_output(f"sqlline-thin.py '{phoenix_queryserver}' '{script_path}'")

        retry(create_table)()
    yield phoenix_table
    drop_table_script = "DROP TABLE {table};"
    script_path = f"/tmp/{user}_drop_table.sql"
    render_file(
        script_path,
        drop_table_script,
        {"table": phoenix_table},
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        host.check_output(f"sqlline-thin.py '{phoenix_queryserver}' '{script_path}'")


@pytest.fixture(scope="module")
def phoenix_dataset(
    host: host.Host,
    user: str,
    setup_phoenix_table: str,
    render_file: Callable,
    dataset_weight: List[dict],
    phoenix_queryserver: str,
) -> dict:
    phoenix_table = setup_phoenix_table
    nb_lines = len(dataset_weight)
    upsert = "UPSERT INTO {table} VALUES ({id}, {weight}, '{category}');"
    upsert_commands = [
        upsert.format(
            table=phoenix_table,
            id=data["id"],
            weight=data["weight"],
            category=data["category"],
        )
        for data in dataset_weight
    ]
    categories = list(set(data["category"] for data in dataset_weight))
    script = "\n".join(upsert_commands)

    script_path = f"/tmp/{user}_dataset.sql"
    render_file(
        script_path,
        script,
        owner=user,
        group=user,
        permissions=0o644,
    )

    with host.sudo(user):
        host.check_output(f"sqlline-thin.py '{phoenix_queryserver}' '{script_path}'")
    return {"nb_lines": nb_lines, "categories": categories}


def test_phoenix_script_is_executed(
    host: host.Host,
    user: str,
    setup_phoenix_table: str,
    render_file: Callable,
    phoenix_dataset: dict,
    phoenix_queryserver: str,
):
    phoenix_table = setup_phoenix_table
    categories = phoenix_dataset["categories"]
    script = """
    SELECT * FROM {table} LIMIT 10;  
    SELECT COUNT(*) FROM {table} WHERE car.weight > 10;
    SELECT car.category, AVG(car.weight) FROM {table} GROUP BY car.category;
    """
    script = textwrap.dedent(script)
    script_path = f"/tmp/{user}_script.sql"
    render_file(
        script_path,
        script,
        {
            "table": phoenix_table,
        },
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        stdout = host.check_output(f"sqlline-thin.py '{phoenix_queryserver}' '{script_path}'")
        # can't assert because phoenix sqlline client doing tricks in terminal
        # can only rely on command return code
        # assert all(category in stdout for category in categories)

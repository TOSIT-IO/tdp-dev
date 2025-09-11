import textwrap
from typing import Any, Callable, Generator

import pytest

from testinfra import host

from .conftest import retry

testinfra_hosts = ["edge"]


@pytest.fixture(scope="module", params=["spark3"])
def spark_version(request: Any) -> str:
    return request.param


@pytest.fixture(scope="module")
def spark_database(user: str) -> str:
    return f"{user}_spark_db"


@pytest.fixture(scope="module")
def spark_table(user: str) -> str:
    return f"{user}_spark_table"


@pytest.fixture(scope="module")
def setup_spark_database(
    host: host.Host,
    user: str,
    spark_database: str,
) -> Generator[str, None, None]:
    with host.sudo(user):
        retry(
            lambda: host.check_output(
                f"spark3-sql -e \"CREATE DATABASE {spark_database} LOCATION '/user/{user}/{spark_database}'\""
            )
        )()
    yield spark_database
    with host.sudo(user):
        host.check_output(f"spark3-sql -e 'DROP DATABASE {spark_database}'")


@pytest.fixture(scope="module")
def setup_spark_iceberg_table(
    host: host.Host,
    user: str,
    setup_spark_database: str,
    spark_table: str,
    render_file: Callable,
) -> Generator[str, Any, None]:
    spark_database = setup_spark_database
    code = """

    USE {database};
    
    CREATE TABLE {table}
    (
    vendor_id bigint,
    trip_id bigint,
    trip_distance float,
    fare_amount double,
    store_and_fwd_flag string
    )
    USING iceberg PARTITIONED BY (vendor_id);

    INSERT INTO {table}
    VALUES (1, 1000371, 1.8, 15.32, 'N'), (2, 1000372, 2.5, 22.15, 'N'), (2, 1000373, 0.9, 9.01, 'N'), (1, 1000374, 8.4, 42.13, 'Y');
    """
    code = textwrap.dedent(code)
    code_path = f"/tmp/{user}_spark_iceberg.sql"
    owner = user
    group = user
    permissions = 0o755

    render_file(
        code_path,
        code,
        {
            "database": spark_database,
            "table": spark_table,
        },
        owner=owner,
        group=group,
        permissions=permissions,
    )
    with host.sudo(user):
        host.check_output(f"spark3-sql -f '{code_path}'")
    yield spark_table
    with host.sudo(user):
        host.check_output(
            f"spark3-sql -e 'DROP TABLE {spark_database}.{spark_table}'"
        )


def test_pyspark_csv_script_is_executed(
    host: host.Host,
    user: str,
    spark_version: str,
    dataset_weight_csv: dict,
    render_file: Callable,
):
    code = """
    #!/bin/sh
    export SPARK_CONF_DIR=/etc/{spark_version}/conf
    expect -c "
    set timeout 45
    spawn /opt/tdp/{spark_version}/bin/pyspark --master yarn --deploy-mode client --executor-memory 5G --num-executors 3 --executor-cores 2
    expect \\">>>\\"
    send \\"data = spark.read.option(\\\\\\"header\\\\\\", True).csv(\\\\\\"{dataset_hdfs_path}\\\\\\")\\r\\"
    expect \\">>>\\"
    send \\"print(\\\\\\"data count is {{}}\\\\\\".format(data.count()))\\r\\"
    expect \\">>>\\"
    send \\"quit()\\r\\"
    interact
    exit 0
    "
    """
    code = textwrap.dedent(code)
    dataset_hdfs_path = dataset_weight_csv["hdfs_path"]
    code_path = f"/tmp/{user}_pyspark_test.sh"
    owner = user
    group = user
    permissions = 0o755

    render_file(
        code_path,
        code,
        {
            "dataset_hdfs_path": dataset_hdfs_path,
            "spark_version": spark_version,
        },
        owner=owner,
        group=group,
        permissions=permissions,
    )

    nb_lines = dataset_weight_csv["nb_lines"]
    with host.sudo(user):
        stdout = host.check_output(code_path)
        assert f"data count is {nb_lines}" in stdout


def test_spark_submit_csv_script_is_executed(
    host: host.Host,
    user: str,
    spark_version: str,
    dataset_weight_csv: dict,
    render_file: Callable,
):
    code = """
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName(
        "Test spark-submit"
    ).getOrCreate()

    data = spark.read.option(
        "header", True
    ).csv("{dataset_hdfs_path}")

    print(
        "data count is {{}}".format(
            data.count()
        )
    )
    """
    code = textwrap.dedent(code)
    dataset_hdfs_path = dataset_weight_csv["hdfs_path"]
    code_path = f"/tmp/{user}_spark_test.py"
    owner = user
    group = user
    permissions = 0o755

    render_file(
        code_path,
        code,
        {
            "dataset_hdfs_path": dataset_hdfs_path,
        },
        owner=owner,
        group=group,
        permissions=permissions,
    )

    nb_lines = dataset_weight_csv["nb_lines"]
    with host.sudo(user):
        stdout = host.check_output(
            f"SPARK_CONF_DIR=/etc/{spark_version}/conf"
            f" /opt/tdp/{spark_version}/bin/spark-submit"
            " --master yarn"
            " --deploy-mode client"
            " --executor-memory 5G"
            " --num-executors 3"
            " --executor-cores 2"
            f" {code_path}"
        )
        assert f"data count is {nb_lines}" in stdout


def test_spark_submit_jar_is_executed(host: host.Host, user: str, spark_version: str):
    with host.sudo(user):
        spark_stdout = host.check_output(
            f"SPARK_CONF_DIR=/etc/{spark_version}/conf"
            f" /opt/tdp/{spark_version}/bin/spark-submit"
            " --master yarn"
            " --deploy-mode client"
            " --executor-memory 5G"
            " --num-executors 3"
            " --executor-cores 2"
            " --class org.apache.spark.examples.JavaSparkPi"
            f" /opt/tdp/{spark_version}/examples/jars/spark-examples*.jar 50"
        )
        assert "Pi is roughly" in spark_stdout


def test_spark_sql_iceberg_execution(
    host: host.Host,
    user: str,
    setup_spark_database: str,
    setup_spark_iceberg_table: str,
    render_file: Callable,
):
    spark_database = setup_spark_database
    spark_table = setup_spark_iceberg_table
    script = """
    USE {database};

    SELECT fare_amount
    FROM {table}
    WHERE trip_id==1000373;
    """
    script = textwrap.dedent(script)
    script_path = f"/tmp/{user}_spark_iceberg_script.sql"
    render_file(
        script_path,
        script,
        {
            "database": spark_database,
            "table": spark_table,
        },
        owner=user,
        group=user,
        permissions=0o644,
    )
    with host.sudo(user):
        stdout = host.check_output(f"spark3-sql -f '{script_path}'")
        assert "9.01" in stdout

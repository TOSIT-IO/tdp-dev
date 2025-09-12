import textwrap
from typing import Any, Callable

import pytest

from testinfra import host

testinfra_hosts = ["edge"]


@pytest.fixture(scope="module", params=["spark3"])
def spark_version(request: Any) -> str:
    return request.param


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

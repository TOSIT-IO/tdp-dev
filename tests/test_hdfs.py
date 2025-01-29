import json
import os
from typing import Callable, Dict

from testinfra import host

from .conftest import retry


testinfra_hosts = ["edge"]


def test_keytab_file_is_conform(host: host.Host, user: str):
    keytab = host.file(os.path.join("/home", user, f"{user}.keytab"))
    assert keytab.user == user
    assert keytab.group == user
    assert keytab.mode == 0o600


def test_hdfs_user_directory_exists(host: host.Host, user: str):
    with host.sudo(user):
        host.check_output(f"hdfs dfs -ls {os.path.join('/user', user)}")


def test_create_temporary_file_in_user_directory(
    host: host.Host,
    user: str,
    user_file: Dict[str, str],
):
    distant_file = user_file["distant_file"]
    distant_hdfs_path = user_file["distant_hdfs_path"]
    file_content = user_file["file_content"]

    with host.sudo(user):
        hdfs_cmd = host.run_expect(
            [0], f"hdfs dfs -put {distant_file} {distant_hdfs_path}"
        )
        assert hdfs_cmd.stderr == "", hdfs_cmd
        assert hdfs_cmd.stdout == "", hdfs_cmd

        try:
            hdfs_cmd = host.run_expect(
                [0], f"hdfs dfs -stat '%F:%u:%g:%a' {distant_hdfs_path}"
            )
            assert hdfs_cmd.stderr == "", hdfs_cmd
            assert user in hdfs_cmd.stdout, hdfs_cmd
            assert "644" in hdfs_cmd.stdout, hdfs_cmd

            hdfs_cmd = host.run_expect([0], f"hdfs dfs -cat {distant_hdfs_path}")
            assert hdfs_cmd.stderr == "", hdfs_cmd
            assert hdfs_cmd.stdout == file_content, hdfs_cmd
        finally:
            hdfs_cmd = host.run_expect([0], f"hdfs dfs -rm {distant_hdfs_path}")
            assert hdfs_cmd.stderr == "", hdfs_cmd
            assert f"Deleted {distant_hdfs_path}" in hdfs_cmd.stdout, hdfs_cmd

        hdfs_cmd = host.run_expect(
            [1], f"hdfs dfs -stat '%F:%u:%g:%a' {distant_hdfs_path}"
        )
        assert "No such file or directory" in hdfs_cmd.stderr, hdfs_cmd
        assert hdfs_cmd.stdout == "", hdfs_cmd


def test_create_webhdfs_temporary_file_in_user_directory(
    host: host.Host,
    user: str,
    user_file: Dict[str, str],
    webhdfs_gateway: str,
    curl: Callable,
):
    distant_file = user_file["distant_file"]
    distant_hdfs_path = user_file["distant_hdfs_path"]
    file_content = user_file["file_content"]
    webhdfs_url = webhdfs_gateway
    webhdfs_gateway_url = f"{webhdfs_url}/webhdfs/v1"

    with host.sudo(user):
        curl_result = retry(
            lambda: curl(
                f"-L -T {distant_file} --negotiate -u : -X PUT '{webhdfs_gateway_url}/user/{user}/{distant_hdfs_path}?op=CREATE'"
            )
        )()
        assert curl_result["http_status"] == 201, curl_result

        try:
            curl_result = curl(
                f"-L --negotiate -u : -X GET '{webhdfs_gateway_url}/user/{user}/{distant_hdfs_path}?op=OPEN'"
            )
            assert file_content in curl_result["command"].stdout, curl_result

            curl_result = curl(
                f"-L --negotiate -u : -X GET '{webhdfs_gateway_url}/user/{user}/{distant_hdfs_path}?op=LISTSTATUS'"
            )
            assert curl_result["http_status"] == 200, curl_result

            liststatus = json.loads(curl_result["command"].stdout)
            assert "FileStatuses" in liststatus, curl_result
            assert "FileStatus" in liststatus["FileStatuses"], curl_result
            assert len(liststatus["FileStatuses"]["FileStatus"]) == 1, curl_result

            filestatus = liststatus["FileStatuses"]["FileStatus"][0]
            assert filestatus["group"] == user, curl_result
            assert filestatus["owner"] == user, curl_result
            assert filestatus["type"] == "FILE", curl_result
        finally:
            curl_result = curl(
                f"-L --negotiate -u : -X DELETE '{webhdfs_gateway_url}/user/{user}/{distant_hdfs_path}?op=DELETE'"
            )
            assert curl_result["http_status"] == 200, curl_result

        curl_result = curl(
            f"-L --negotiate -u : -X GET '{webhdfs_gateway_url}/user/{user}/{distant_hdfs_path}?op=LISTSTATUS'",
            check_status_code=False,
        )
        liststatus = json.loads(curl_result["command"].stdout)
        assert "RemoteException" in liststatus, curl_result

        assert "exception" in liststatus["RemoteException"], curl_result
        assert (
            "FileNotFoundException" in liststatus["RemoteException"]["exception"]
        ), curl_result

        assert "message" in liststatus["RemoteException"], curl_result
        assert (
            f"File /user/{user}/{distant_hdfs_path} does not exist."
            in liststatus["RemoteException"]["message"]
        ), curl_result

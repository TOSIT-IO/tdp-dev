import json
from typing import Callable, Dict, List

import pytest

from testinfra import host

from .conftest import USERS, retry

testinfra_hosts = ["edge"]


@pytest.fixture(scope="module")
def webhdfs_ranger_policy(
    ranger_policy: Callable[[str, str, dict, List[dict]], dict],
):
    resources = {
        "topology": {"values": ["tdpldap"], "isExcludes": False},
        "service": {"values": ["WEBHDFS"], "isExcludes": False},
    }
    policyItems = [
        {
            "users": USERS,
            "accesses": [
                {"isAllowed": True, "type": "allow"},
            ],
        }
    ]
    ranger_policy("webhdfs_test", "knox-tdp", resources, policyItems)


def test_create_webhdfs_temporary_file_in_user_directory(
    host: host.Host,
    user: str,
    user_file: Dict[str, str],
    webhdfs_ranger_policy: None,
    knox_gateway: Dict[str, str],
    curl: Callable,
):
    distant_file = user_file["distant_file"]
    distant_hdfs_path = user_file["distant_hdfs_path"]
    file_content = user_file["file_content"]
    user_creds = knox_gateway["user_creds"]
    knox_url = knox_gateway["url"]
    knox_gateway_url = f"{knox_url}/gateway/tdpldap/webhdfs/v1"

    curl_result = retry(
        lambda: curl(
            f"-L -T {distant_file} -u {user}:{user_creds} -X PUT '{knox_gateway_url}/user/{user}/{distant_hdfs_path}?op=CREATE'"
        )
    )()
    assert curl_result["http_status"] == 201, curl_result

    try:
        curl_result = curl(
            f"-L -u {user}:{user_creds} -X GET '{knox_gateway_url}/user/{user}/{distant_hdfs_path}?op=OPEN'"
        )
        assert file_content in curl_result["command"].stdout, curl_result

        curl_result = curl(
            f"-L -u {user}:{user_creds} -X GET '{knox_gateway_url}/user/{user}/{distant_hdfs_path}?op=LISTSTATUS'"
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
            f"-L -u {user}:{user_creds} -X DELETE '{knox_gateway_url}/user/{user}/{distant_hdfs_path}?op=DELETE'"
        )
        assert curl_result["http_status"] == 200, curl_result

    curl_result = curl(
        f"-L -u {user}:{user_creds} -X GET '{knox_gateway_url}/user/{user}/{distant_hdfs_path}?op=LISTSTATUS'",
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

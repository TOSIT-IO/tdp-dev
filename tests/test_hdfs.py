import os
from typing import Dict

from testinfra import host

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

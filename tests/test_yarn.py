from testinfra import host

testinfra_hosts = ["edge"]


def test_yarn_works(host: host.Host, user: str):
    with host.sudo(user):
        yarn_stdout = host.check_output(
            'yarn jar "/opt/tdp/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar" pi 3 50'
        )
        assert "Estimated value of Pi is" in yarn_stdout

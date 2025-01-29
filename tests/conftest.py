import contextlib
import csv
import functools
import io
import json
import logging
import re
import tempfile
import time
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

import pytest
import testinfra
from filelock import FileLock
from testinfra.host import Host

logger = logging.getLogger("testinfra")

RE_CURL_HTTP_STATUS = re.compile("< HTTP/[^ ]+ ([^ ]+) ")

USERS = [
    "tdp_user",
    "smoke_user",
]

USERS_CREDS = {
    "tdp_user": "tdp_user123",
    "smoke_user": "smoke_user123",
}


# Based on testinfra.plugin.pytest_generate_tests
# Enables to have a "host" fixture with a"session" scope
def pytest_generate_tests(metafunc):
    if "_testinfra_host_custom" in metafunc.fixturenames:
        if metafunc.config.option.hosts is not None:
            hosts = metafunc.config.option.hosts.split(",")
        elif hasattr(metafunc.module, "testinfra_hosts"):
            hosts = metafunc.module.testinfra_hosts
        else:
            hosts = [None]
        params = testinfra.get_hosts(
            hosts,
            connection=metafunc.config.option.connection,
            ssh_config=metafunc.config.option.ssh_config,
            ssh_identity_file=metafunc.config.option.ssh_identity_file,
            sudo=metafunc.config.option.sudo,
            sudo_user=metafunc.config.option.sudo_user,
            ansible_inventory=metafunc.config.option.ansible_inventory,
            force_ansible=metafunc.config.option.force_ansible,
        )
        params = sorted(params, key=lambda x: x.backend.get_pytest_id())
        ids = [e.backend.get_pytest_id() for e in params]
        metafunc.parametrize(
            "_testinfra_host_custom", params, ids=ids, scope="session", indirect=True
        )


@pytest.fixture(scope="session")
def _testinfra_host_custom(request):
    return request.param


@pytest.fixture(scope="session")
def host(_testinfra_host_custom):
    return _testinfra_host_custom


def retry(
    func: Optional[Callable] = None,
    nb_retries: int = 6,
    sleep_time_between_tries: int = 10,
):
    if func is None:
        return functools.partial(
            retry,
            nb_retries=nb_retries,
            sleep_time_between_tries=sleep_time_between_tries,
        )

    @functools.wraps(func)
    def retry_func(*args, **kwargs):
        for i in range(nb_retries - 1):
            try:
                return func(*args, **kwargs)
            except:
                time.sleep(sleep_time_between_tries)
        return func(*args, **kwargs)

    return retry_func


@pytest.fixture(scope="session")
def realm(host: Host) -> str:
    return host.ansible.get_variables()["realm"]


# https://github.com/pytest-dev/pytest-xdist/tree/v2.4.0#making-session-scoped-fixtures-execute-only-once
@pytest.fixture(scope="session")
def lock(tmp_path_factory, worker_id: str):
    no_lock_data = {}

    # Mode séquentiel
    # Les variables à sauvegarder sont dans un "dict"
    # de la fixture "no_lock_data"
    @contextlib.contextmanager
    def no_lock_context(namespace: str, teardown: bool = False):
        yield no_lock_data.setdefault(namespace, {"last_worker": True})

    # Mode parallèle
    # Les variables à sauvegarder et à partager entre les workers
    # sont sauvegardés sur un emplacement partagé entre les workers
    # avec un format JSON et un lock
    @contextlib.contextmanager
    def lock_context(namespace: str, teardown: bool = False):
        data = {}
        # get the temp directory shared by all workers
        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        fn = f"{root_tmp_dir}/{namespace}.json"
        with FileLock(f"{fn}.lock"):
            try:
                with open(fn, "r") as fd:
                    data = json.load(fd)
            except:
                pass

            if teardown:
                workers = data.setdefault("workers", {})
                if worker_id in workers:
                    del workers[worker_id]
                data.setdefault("workers_teardown", []).append(worker_id)
            else:
                # Un "set" n'est pas serializable en json donc
                # utilisation d'un "dict" à la place
                data.setdefault("workers", {})[worker_id] = True
                data.setdefault("workers_used", []).append(worker_id)

            data["last_worker"] = not data["workers"]
            if data["last_worker"]:
                data.setdefault("workers_last", []).append(worker_id)
            yield data
            with open(fn, "w") as fd:
                json.dump(data, fd)

    if worker_id == "master":
        return no_lock_context
    return lock_context


@pytest.fixture(scope="session")
def users() -> List[str]:
    return USERS


@pytest.fixture(scope="session", params=USERS)
def user(
    host: Host, request: Any, realm: str, lock: Callable
) -> Generator[str, None, None]:
    user: str = request.param
    with lock(f"user_{user}"):
        with host.sudo(user):
            kinit_cmd = host.run(f"kinit -kt /home/{user}/{user}.keytab {user}@{realm}")
            if kinit_cmd.rc != 0:
                pytest.fail(kinit_cmd.stderr)

    yield user
    with lock(f"user_{user}", teardown=True) as data:
        if not data["last_worker"]:
            return
        with host.sudo(user):
            host.run("kdestroy")


@pytest.fixture(scope="session")
def zk_hosts(host: Host) -> List[str]:
    return host.backend.get_hosts("zk")


@pytest.fixture(scope="session")
def ranger_manager(host: Host) -> Dict[str, str]:
    return {
        "url": f"https://{host.backend.get_hosts('ranger_admin')[0]}:6182",
        "auth_creds": "admin:RangerAdmin123",
    }


@pytest.fixture(scope="session")
def knox_gateway(host: Host, user: str) -> Dict[str, str]:
    return {
        "url": f"https://{host.backend.get_hosts('knox')[0]}:8443",
        "user_creds": USERS_CREDS[user],
    }


@pytest.fixture(scope="session")
def webhdfs_gateway(host: Host, user: str) -> str:
    return f"https://{host.backend.get_hosts('hdfs_nn')[0]}:9871"


@pytest.fixture(scope="session")
def hbase_rest(host: Host) -> str:
    return f"https://{host.backend.get_hosts('hbase_rest')[0]}:8080"


@pytest.fixture(scope="session")
def upload_file(
    host: Host,
    lock: Callable,
) -> Generator[
    Callable[[str, str, Optional[str], Optional[str], Optional[int]], None], None, None
]:
    def scp_func(
        local_file: str,
        distant_file: str,
        owner: Optional[str] = None,
        group: Optional[str] = None,
        permissions: Optional[int] = None,
    ):
        with lock("upload_file") as data:
            if distant_file in data.setdefault("uploaded_files", []):
                return
            add_opts = []

            if owner:
                add_opts += [f"owner={owner}"]
            if group:
                add_opts += [f"group={group}"]
            if permissions:
                add_opts += [f"mode={permissions:o}"]
            result = host.ansible(
                "copy",
                f"src={local_file} dest={distant_file} {' '.join(add_opts)}",
                check=False,
            )
            data["uploaded_files"].append(distant_file)
            assert "state" in result, result["msg"]

    yield scp_func
    with lock("upload_file", teardown=True) as data:
        if not data["last_worker"]:
            return
        uploaded_files = data.get("uploaded_files", [])
        for uploaded_file in uploaded_files[:]:
            host.ansible("file", f"state=absent path={uploaded_file}", check=False)
            uploaded_files.remove(uploaded_file)


@pytest.fixture(scope="session")
def render_file(
    lock: Callable,
    upload_file: Callable[
        [str, str, Optional[str], Optional[str], Optional[int]], None
    ],
) -> Callable[[str, str, Optional[Dict[str, str]]], None]:
    def render_func(
        distant_path: str,
        content: str,
        render_variables: Optional[Dict[str, str]] = None,
        *args,
        **kwargs,
    ):
        with lock("render_file"):
            if render_variables is None:
                rendered_content = content
            else:
                rendered_content = content.format(**render_variables)

            with tempfile.NamedTemporaryFile() as file_descriptor:
                file_descriptor.write(bytes(rendered_content, "utf-8"))
                file_descriptor.flush()
                upload_file(file_descriptor.name, distant_path, *args, **kwargs)

    return render_func


@pytest.fixture(scope="session")
def hdfs_dir(
    host: Host,
    user: str,
    lock: Callable,
) -> Generator[Callable[[str], None], None, None]:
    def hdfs_dir_func(distant_hdfs_path: str):
        with lock(f"hdfs_dir_{user}") as data:
            if distant_hdfs_path in data.setdefault("hdfs_dirs", []):
                return
            with host.sudo(user):
                host.check_output(f"hdfs dfs -mkdir '{distant_hdfs_path}'")
                data["hdfs_dirs"].append(distant_hdfs_path)

    yield hdfs_dir_func
    with lock(f"hdfs_dir_{user}", teardown=True) as data:
        if not data["last_worker"]:
            return
        with host.sudo(user):
            hdfs_dirs = data.get("hdfs_dirs", [])
            for hdfs_dir in reversed(hdfs_dirs[:]):
                host.check_output(f"hdfs dfs -rm -r -f {hdfs_dir}")
                hdfs_dirs.remove(hdfs_dir)


@pytest.fixture(scope="session")
def render_hdfs_file(
    host: Host,
    user: str,
    lock: Callable,
    render_file: Callable[[str, str, Optional[Dict[str, str]]], None],
) -> Generator[
    Callable[
        [
            str,
            str,
            Optional[Dict[str, str]],
            Optional[str],
            Optional[str],
            Optional[str],
            Optional[int],
        ],
        None,
    ],
    None,
    None,
]:
    def render_hdfs_func(
        distant_hdfs_path: str,
        content: str,
        render_variables: Optional[Dict[str, str]] = None,
        distant_path: Optional[str] = None,
        owner: Optional[str] = None,
        group: Optional[str] = None,
        permissions: Optional[int] = None,
    ):
        if distant_path is None:
            distant_path = f"/tmp/{user}_{distant_hdfs_path.replace('/', '_')}"

        render_file(
            distant_path,
            content,
            render_variables,
            owner=user,
            group=user,
            permissions=permissions,
        )
        with lock(f"render_hdfs_file_{user}") as data:
            if distant_hdfs_path in data.setdefault("rendered_hdfs_files", []):
                return
            with host.sudo(user):
                host.check_output(
                    f"hdfs dfs -put '{distant_path}' '{distant_hdfs_path}'"
                )
                data["rendered_hdfs_files"].append(distant_hdfs_path)
                if owner:
                    host.check_output(
                        f"hdfs dfs -chown '{owner}' '{distant_hdfs_path}'"
                    )
                if group:
                    host.check_output(
                        f"hdfs dfs -chgrp '{group}' '{distant_hdfs_path}'"
                    )
                if permissions:
                    host.check_output(
                        f"hdfs dfs -chmod '{permissions:0}' '{distant_hdfs_path}'"
                    )

    yield render_hdfs_func
    with lock(f"render_hdfs_file_{user}", teardown=True) as data:
        if not data["last_worker"]:
            return
        with host.sudo(user):
            rendered_hdfs_files = data.get("rendered_hdfs_files", [])
            for hdfs_file in rendered_hdfs_files[:]:
                host.check_output(f"hdfs dfs -rm -f {hdfs_file}")
                rendered_hdfs_files.remove(hdfs_file)


@pytest.fixture(scope="session")
def dataset_weight() -> List[dict]:
    nb_lines = 200
    categories = ("sportscar", "truck", "berline")
    dataset = [
        {
            "id": i,
            "weight": i / 10 + 50,
            "category": categories[i % len(categories)],
        }
        for i in range(nb_lines)
    ]
    return dataset


@pytest.fixture(scope="session")
def dataset_weight_csv(
    dataset_weight: List[dict],
    hdfs_dir: Callable[[str], None],
    render_hdfs_file: Callable[[str, str], None],
) -> dict:
    dataset_dir = "dataset_csv"
    dataset_file = "weight.csv"
    dataset_hdfs_path = f"{dataset_dir}/{dataset_file}"
    nb_lines = len(dataset_weight)
    hdfs_dir(dataset_dir)

    with io.StringIO(newline="") as string_buffer:
        fieldnames = dataset_weight[0].keys() if len(dataset_weight) > 0 else []
        writer = csv.DictWriter(string_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset_weight)
        dataset_content = string_buffer.getvalue()

    render_hdfs_file(dataset_hdfs_path, dataset_content)

    return {
        "hdfs_dir": dataset_dir,
        "hdfs_path": dataset_hdfs_path,
        "nb_lines": nb_lines,
    }


@pytest.fixture(scope="session")
def curl(
    host: Host,
) -> Callable:
    def curl_func(
        curl_args: str,
        check_status_code: bool = True,
    ) -> dict:
        curl_cmd = "curl --verbose --insecure"
        curl_result = host.run_expect([0], f"{curl_cmd} {curl_args}")

        match = RE_CURL_HTTP_STATUS.findall(curl_result.stderr)
        if match:
            http_status = int(match[-1])

            if check_status_code and http_status >= 400:
                pytest.fail(f"Erreur curl http status {http_status}\n{curl_result}")
            return {
                "command": curl_result,
                "http_status": http_status,
            }
        else:
            pytest.fail(f"HTTP status non trouvé\n{curl_result}")
        return {}

    return curl_func


@pytest.fixture(scope="session")
def ranger_policy(
    lock: Callable,
    curl: Callable,
    ranger_manager: Dict[str, str],
) -> Generator[Callable[[str, str, dict, List[dict], int], None], None, None]:
    ranger_url = ranger_manager["url"]
    ranger_policy_url = f"{ranger_url}/service/public/v2/api/policy"
    ranger_audits_url = f"{ranger_url}/service/assets/exportAudit?pageSize=10&sortBy=createDate&sortType=desc"
    ranger_creds = ranger_manager["auth_creds"]
    curl_args = f"--user '{ranger_creds}' -H 'Accept: application/json'"

    def ranger_policy_func(
        name: str,
        service: str,
        resources: dict,
        policyItems: List[dict],
        minimum_policy_pulled: int = 0,
        **kwargs,
    ):
        with lock("ranger_policy") as data:
            if name in data.setdefault("created_policies", {}):
                return
            policy = {
                "name": name,
                "service": service,
                "description": name,
                "isEnabled": True,
                "isAuditEnabled": True,
                "resources": resources,
                "policyItems": policyItems,
            }
            policy.update(kwargs)
            curl_args_create = f"{curl_args} -H 'Content-Type: application/json' -X POST '{ranger_policy_url}' -d '{json.dumps(policy)}'"
            curl_result = curl(curl_args_create)
            policy = json.loads(curl_result["command"].stdout)
            data["created_policies"][name] = policy["id"]
            policy_created_time = datetime.utcfromtimestamp(policy["createTime"] / 1000)
            if minimum_policy_pulled > 0:

                @retry(sleep_time_between_tries=5, nb_retries=10)
                def check_policy_pulled_n_times():
                    curl_result = curl(
                        f"{curl_args} '{ranger_audits_url}&repository={service}'"
                    )
                    result = json.loads(curl_result["command"].stdout)
                    times_pulled = 0
                    for audit in result["vXPolicyExportAudits"]:
                        audit_update_date = datetime.strptime(
                            audit["updateDate"], "%Y-%m-%dT%H:%M:%SZ"
                        )
                        if audit_update_date >= policy_created_time:
                            times_pulled += 1
                            if times_pulled >= minimum_policy_pulled:
                                break
                    else:
                        raise ValueError(
                            "Pas assez de machines ont pull la dernière version de policy"
                        )

                check_policy_pulled_n_times()

    yield ranger_policy_func
    with lock("ranger_policy", teardown=True) as data:
        if not data["last_worker"]:
            return
        created_policies = data.get("created_policies", {})
        for policy_name in list(created_policies.keys()):
            policy_id = created_policies[policy_name]
            curl_args_delete = (
                f"{curl_args} -X DELETE '{ranger_policy_url}/{policy_id}'"
            )
            curl(curl_args_delete)
            del created_policies[policy_name]


@pytest.fixture(scope="function")
def user_file(
    user: str, render_file: Callable[[str, str], dict], request: pytest.FixtureRequest
) -> Dict[str, str]:
    distant_file = f"/tmp/{user}_tempory_file_{request.node.originalname}"
    distant_hdfs_path = "temporary_file"
    file_content = f"{user} file test"
    render_file(
        distant_file,
        file_content,
        owner=user,
        group=user,
        permissions=0o644,
    )

    return {
        "distant_file": distant_file,
        "distant_hdfs_path": distant_hdfs_path,
        "file_content": file_content,
    }

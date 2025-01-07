# TDP dev

Use this repository to have a working directory where you run deploy commands with predefined virtual infrastructure with Vagrant or your own infrastructure.

## Requirements

- Docker
- Libvirt

## Quickstart

The below steps will deploy a TDP cluster with all features so you MUST install all requirements.

If Vagrant is enabled, the Ansible hosts.ini file will be generated using the hosts variable in tdp-vagrant/vagrant.yml.

### Clone the project and submodules

Clone the project with every submodule to that last commit on the `master/main` branch.

```sh
git clone --recursive https://github.com/TOSIT-IO/tdp-dev.git
```

Clone the main repository and manually chose the submodules. *NB*: the `ansible_collections/tosit/tdp` repository is manadatory. All submodules can be found in the `.gitmodules` file.

```sh
# Clone the main repository
git clone https://github.com/TOSIT-IO/tdp-dev.git
# enter the directory
cd tdp-dev
# Clone the submodule example:`git submodule update --init ansible_collections/tosit/tdp
git submodule update --init --remote <submodule-path>
```

To update all cloned submodules if necessary:

```sh
git submodule update --recursive --remote
```

### Setup the virtual machines

If you have Libvirt on your host machine, follow the steps explained in the `README.md` file of the `tdp-vagrant` submodule to start the container that will launch the VMs.

Vagrant moreover creates the `hosts` file in the `inventory` directory later used by Ansible. for each modification of the `tdp-vagrant/vagrant.yml` file or destruction of the VMs it is recommended to remove the `hosts` file and let it be generated again. However, since the private ssh key paths are absolute and will not match inside a container, lets transform them to realtive paths by removing everything before the `/.vagrant/machine`:

```sh
sed -i "s|\(ansible_ssh_private_key_file='\)[^']*/\.vagrant/machines|\1.vagrant/machines|" .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory
```

### Ansible setup

Ansible configuration has been preconfigured for the Vagrant setup in the `ansible.cfg` file and symbolic links have alredy been set in `inventory/topologies/` to the different collections' topology files.

### TDP-dev python environment setup

Now to setup the python dependecis for TDP-dev which are marked in the poetry.lock file at the root of the project we are going to use a container.

First build the image and run the container:

```sh
# Build command:
docker build -t tdp-dev dev

# make the .poetrycache folder
mkdir .poetrycache

# Run command:
docker run --rm -it \
-v $PWD:/home/tdp/tdp-dev \
-v $PWD/.poetrycache:/home/tdp/.cache/pypoetry \
--network=host \
--env CONTAINER_UID=$(id -u) --env CONTAINER_GID=$(id -g) \
--env DISPLAY=$DISPLAY \
tdp-dev
```

- `-v $PWD:/home/tdp/tdp-dev` binds the working directory of your container to this repository in your host.
- `-v $PWD/.poetrycache:/home/tdp/.cache/pypoetry` binds the `.poetrycache` folder to the poetry cache in the container.
- With the `--network=host` option the container is connected to your host network which enables it to communicate with the VMs.
- The `--env CONTAINER_UID=$(id -u) --env CONTAINER_GID=$(id -g)` environment variables enable the container to have the same user as your host.
- The `--env DISPLAY=$DISPLAY` environment variable is for the tdp-lib command `tdp dag` to be able to display the dag in a new window on your host.

Inside the container create the `venv-dev` virtual environment which will contain all dependencies to deploy all TDP collections.

```sh
python -m venv venv-dev
source venv-dev/bin/activate
poetry install
```

TDP-lib is contained in the dependencies but not its development dependencies.

### Download the component releases

The text file `scripts/tdp-release-uris.txt` contains uris to the component releases of the stack TDP 1.1 to this date. They might be outdated and not correspond to the versions set in the collections after a certain time. you may have to ajust the uris in this case.

Download the relases from in the `files`directory with the `download_releases.sh` file from the container:

```sh
./scripts/download_releases.sh
```

### Setup TDP-lib development dependecies (optional)

If you desire de develop TDP-lib with pytest, use the linter ruff, you will have to install all dependencies contained in the pyproject.toml of the `tdp-lib` directory. However, since they might be conflicting with the ones in the tdp-dev pyproject.toml, they must be setup in a different environment.

Inside the container create the `venv-lib` virtual environment and install the dependencies:

```sh
python -m venv venv-lib
source venv-lib/bin/activate
poetry install -C tdp-lib -E visualization -E mysql -E postgresql-binary
```

Read the `tdp-lib` documentation for more information.

### Prerequisites

Before starting to deploy TDP components, the TDP collection prerequisites must be run first which sets up the VMs and installs certain programms.

In the container, you first have to install the Ansible Galaxy collections `general`, `crypto` and `postgresql` as follows.

```sh
ansible-galaxy install -r ansible_collections/requirements.yml
```

Now if your internet connection is using a proxy, set it up in the commented out variables `http_proxy` and `https_proxy` variables of the `inventory/group_vars/all.yml` file.

Then you can install the `tdp_prerequisites` collection as follows:

```sh
ansible-playbook ansible_collections/tosit/tdp_prerequisites/playbooks/all.yml
```

### Deploying TDP

TDP can either be deployed with the manager or directly with Ansible.

**Deploying it directly with Ansible is not recommended** as it will take the default variables in the default variables itf the `tdp_vars` folder has not been created yet and gives you less flexibility. **It is recommended to use the manager**.

**Note:** If you are deploying TDP Observability you either have to set the values in `tdp_vars/prometheus/alertmanager.yml` for the the variables `alertmanager_receivers` and `alertmanager_route` if you want to setup the alertmanager or not deploy it by commenting out the `[alertmanager:children]` in the `topology.ini` of TDP Observability.

1. Deploying it directly with Ansible:

    ```sh
    # Deploying TDP collection
    ansible-playbook ansible_collections/tosit/tdp/playbooks/meta/all.yml
    # Deploying TDP collection extra
    ansible-playbook ansible_collections/tosit/tdp_extra/playbooks/meta/all.yml
    # Deploying TDP collection observability
    ansible-playbook ansible_collections/tosit/tdp_observability/playbooks/meta/all.yml
    ```

2. Deploying it with TDP-Lib:

    The `TDP_COLLECTION_PATH` variable in the`.env` file is set for all TDP collections. Remove a collection from the path if you do not desire it. SQLite has been chosen by default as database. Change the `TDP_DATABASE_DSN` value if you desire another one. Then source the file:

    ```sh
    source .env
    ```

    Initialize the database and create the `tdp_vars` directory with the `tdp_vars_overrides` variables:

    ```sh
    tdp init --overrides tdp_vars_overrides
    ```

    Make the DAG of operations:

    ```sh
    tdp plan dag
    ```

    Execute the DAG:

    ```sh
    tdp deploy
    ```

Execute the playbooks to create the `tdp_user` and give him the permissions in ranger.

```sh
ansible-playbook ansible_collections/tosit/tdp/playbooks/utils/hdfs_user_homes.yml
ansible-playbook ansible_collections/tosit/tdp/playbooks/utils/ranger_policies.yml
```

## Connect to the Machine

Inside the `manager` container, run the following command to connect to the edge node:

```bash
vagrant ssh edge-01
```

## Test Components

Run the following commands from `edge-01` to test various components.

```bash
sudo su - tdp_user
kinit -ki
```

### Test HDFS Access

To test HDFS access for `tdp_user`, run:

```bash
echo "This is the first line." | hdfs dfs -put - /user/tdp_user/test-file.txt
echo "This is the second (appended) line." | hdfs dfs -appendToFile - /user/tdp_user/test-file.txt
hdfs dfs -cat /user/tdp_user/test-file.txt
```

### Test Hive Interaction

To interact with Hive using the Beeline CLI, run:

```bash
export hive_truststore_password='Truststore123!'

# Connect to HiveServer2 using ZooKeeper
beeline -u "jdbc:hive2://master-01.tdp:2181,master-02.tdp:2181,master-03.tdp:2181/;serviceDiscoveryMode=zooKeeper;zooKeeperNamespace=hiveserver2;sslTrustStore=/etc/ssl/certs/truststore.jks;trustStorePassword=${hive_truststore_password}"

# Create the database
CREATE DATABASE IF NOT EXISTS tdp_user LOCATION '/user/tdp_user/warehouse/tdp_user.db';
USE tdp_user;

# Show databases and tables
SHOW DATABASES;
SHOW TABLES;

# Create and insert into a table
CREATE TABLE IF NOT EXISTS table1 (
  col1 INT COMMENT 'Integer Column',
  col2 STRING COMMENT 'String Column'
);
INSERT INTO TABLE table1 VALUES (1, 'one'), (2, 'two');

# Select from the table
SELECT * FROM table1;
```

### Test HBase Access

To access the HBase shell, run:

```bash
hbase shell
```

You can then run the following commands to test HBase:

```bash
list
list_namespace
create 'tdp_user_table', 'cf'
put 'tdp_user_table', 'row1', 'cf:testColumn', 'testValue'
scan 'tdp_user_table'
disable 'tdp_user_table'
drop 'tdp_user_table'
```

## Automatic python tests with pytest and testinfra

Run the tests sequentially:

```sh
py.test tests
```

Run the tests in parallel:

```sh
py.test -n 2 tests
```

**Note:** Running the tests in parallel requires more resources and tests might fail if resources are not sufficient.

## Web UI links

To access the components web UI links on your host , you will have to setup the IP adresses with their respective FQDN in `etc/hosts`, introduce the SSL certificate into your browser and install and configure Kerberos client. Luckely a container image has been created where verything is alraedy setup. However, the SSl certificate which is created with the `ansible_collections/tosit/tdp_prerequisites/playbooks/certificates.yml` playbook must already present in `files/tdp_getting_started_certs` otherwise the build will fail.

### Firefox container

1. Build the container:

    ```sh
    docker build -t firefox-kerberos -f firefox-container/Dockerfile .
    ```

2. Run the container:

    ```sh
    # Run the container
    docker run --rm -it \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    firefox-kerberos
    ```

    **Note**: If Docker does not have the rights to access the X-Server execute `xhost +local:`

3. Inside the container create a Kerberos ticket for example:

    ```sh
    # Do a ticket demand
    echo 'tdp_user123' | kinit tdp_user@REALM.TDP
    ```

4. Launch the browser and access the web UIs:

    ```sh
    firefox
    ```

### TDP links

- [HDFS NN Master 01](https://master-01.tdp:9871/dfshealth.html)
- [HDFS NN Master 02](https://master-02.tdp:9871/dfshealth.html)
- [YARN RM Master 01](https://master-01.tdp:8090/cluster/apps)
- [YARN RM Master 02](https://master-02.tdp:8090/cluster/apps)
- [MapReduce Job History Server](https://master-03.tdp:19890/jobhistory)
- [HBase Master 01](https://master-01.tdp:16010/master-status)
- [HBase Master 02](https://master-02.tdp:16010/master-status)
- [Spark History Server](https://master-03.tdp:18081/)
- [Spark3 History Server](https://master-03.tdp:18083/)
- [Ranger Admin](https://master-03.tdp:6182/index.html)

### TDP Extra links

- [JupyterHub](https://master-03.tdp:8000/)
- [Hue](https://edge-01.tdp:8888/)
- [Livy Spark](https://edge-01.tdp:8998/ui)
- [Livy Spark3](https://edge-01.tdp:8999/ui)

### TDP Observability links

- [Grafana](https://master-01.tdp:3000/)
- [Prometheus](https://master-01.tdp:9090/)

Default username and passwords for Ranger, Grafana and Promotheus are `admin` as username for all and  respectively `RangerAdmin123`, `GrafanaAdmin123` and `PrometheusAdmin123` as password.

**Note:** TDP extra deploys a firewall which is enabled, if you do not need it enabled for development you may disable it as follows:

```sh
ansible-playbook ansible_collections/tosit/tdp_extra/playbooks/firewall_generic_stop.yml
```

## Destroy the Cluster

To destroy the cluster, execute the following commands in the `tdp-vagrant` container:

```bash
vagrant destroy
rm -rf .vagrant
```

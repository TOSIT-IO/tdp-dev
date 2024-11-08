# TDP dev

Use this repository to have a working directory where you run deploy commands with predefined virtual infrastructure with Vagrant or your own infrastructure.

## Requirements

- Libvirt
- Docker and Docker Compose

## Quickstart

The below steps will deploy a TDP cluster with all features so you MUST install all requirements.

### Clone the Project and Submodules

To clone the project along with all its submodules at the latest commit on the `master/main` branch, use the following command:

1. **Clone the main repository**:

    ```sh
    git clone https://github.com/TOSIT-IO/tdp-dev.git
    ```

2. **Navigate to the directory**:

    ```sh
    cd tdp-dev
    ```

3. **Clone the Required Submodules**:

    You can edit the `.gitmodules` file if you want to remove any collections. 

    The available submodules are: **ansible_collections/tosit/tdp**, **ansible_collections/tosit/tdp_prerequisites**, **tdp-vagrant**, **tdp-lib**, **ansible_collections/tosit/tdp_extra** (optional), and **ansible_collections/tosit/tdp_observability** (optional). 

    To clone a specific submodule, use the following command:

    ```sh
    git submodule update --init --remote <submodule-path>
    ```

    To update all cloned submodules later, run:

    ```sh
    git submodule update --recursive --remote
    ```

### Setup manager Containers
Two Docker containers are provided with the necessary dependencies for TDP installation:

- **manager Container**: This container includes all required dependencies, such as Vagrant with libvirt, Ansible, and Python 3.
- **Firefox Container**: This container enables access to the component web UI links from your host. It includes the configuration of etc/hosts, browser settings, importing the TDP SSL certificate into the browser, and configuring the Kerberos client.

To start both containers, run:

```sh
docker compose up -d
```

### Setup the virtual machines

After the manager container is up and running, you can access it using this command :

```sh
docker compose exec -it manager bash
```

Once inside the container, execute the vagrant up command. You can define `vagrant.yml` file to update the machine resources according to your machine's RAM and core count. The file `tdp-vagrant/vagrant.yml` contains default values.

```sh
vagrant up
```

### Download Component Releases

The `scripts/tdp-release-uris.json` file contains the URIs for the TDP stack component releases as of version 1.1. Please note that these URIs may become outdated and may require manual adjustment over time. To download releases for specific collections (`tdp-collection`, `tdp-observability`, `tdp-extras`), or to download all collections, use the following commands:

For a specific collection:
```bash
./scripts/download_releases.sh <collection>
```
Example:
```bash
./scripts/download_releases.sh tdp-collection
```

For all collections:
```bash
./scripts/download_releases.sh all
```

### Setup TDP-lib development dependecies

TDP lib is a Python library that enhances Ansible for cluster management, allowing users to define task relationships in a directed acyclic graph (DAG) and manage variables centrally.

To install the dependencies and the package in a virtual environment inside the `manager` container, use the following commands:

```sh
python3 -m venv venv
source venv/bin/activate
poetry install -C tdp-lib -E visualization -E mysql -E postgresql-binary
```

### Prerequisites

Before deploying TDP components, you need to run the TDP collection prerequisites to set up the VMs and install required programs.

Start by entering the `manager` container and installing the necessary Ansible Galaxy collections.

```sh
ansible-galaxy collection install community.general community.crypto community.postgresql
```

If your internet connection uses a proxy, configure the `http_proxy` and `https_proxy` variables in the `inventory/group_vars/all.yml` file.

Finally, run the following command to install the `tdp_prerequisites` collection:

```sh
ansible-playbook ansible_collections/tosit/tdp_prerequisites/playbooks/all.yml
```

### Deploying TDP

TDP can be deployed in two ways: using the manager or directly with Ansible. Before you start, you need to set up the `tdp_vars` that Ansible will use.

#### Step 1: Configure Environment Variables

1. **Edit the `.env` file**:
   - Set the `TDP_COLLECTION_PATH` variable to include all necessary TDP collections. Remove any collections you do not want to include.
   - SQLite is set as the default database. If you want to use a different database, update the `TDP_DATABASE_DSN` value.

2. **Source the file**:
   ```sh
   source venv/bin/activate && source .env 
   ```

#### Step 2: Initialize TDP

- Run the following command to initialize the database and create the `tdp_vars` directory with the `tdp_vars_overrides` variables:
   ```sh
   tdp init --overrides tdp_vars_overrides
   ```

**Note:** If you are deploying TDP Observability, configure the `alertmanager_receivers` and `alertmanager_route` variables in `tdp_vars/prometheus/alertmanager.yml` to set up Alertmanager. Alternatively, comment out the `[alertmanager:children]` section in the `topology.ini` file of TDP Observability if you wish to skip its deployment.

#### Step 3: Deployment Options

##### Option 1: Deploying Directly with Ansible

Run the following commands to deploy the TDP collections:

```sh
# Deploying the main TDP collection
ansible-playbook ansible_collections/tosit/tdp/playbooks/meta/all_per_service.yml

# Deploying additional TDP collection
ansible-playbook ansible_collections/tosit/tdp_extra/playbooks/meta/all_per_service.yml

# Deploying TDP Observability collection
ansible-playbook ansible_collections/tosit/tdp_observability/playbooks/meta/all_per_service.yml
```

##### Option 2: Deploying with TDP-Lib

Create the Directed Acyclic Graph (DAG) of operations:
   ```sh
   tdp plan dag
   ```

Execute the DAG:

   ```sh
   tdp deploy
   ```

#### Step 4: Post-Installation Tasks

After deploying the TDP cluster, run the playbooks to create the `tdp_user` and assign the necessary permissions in Ranger:

```sh
ansible-playbook ansible_collections/tosit/tdp/playbooks/utils/hdfs_user_homes.yml
ansible-playbook ansible_collections/tosit/tdp/playbooks/utils/ranger_policies.yml
``` 

## Web UI

To access the component web UIs from your host, a Firefox container with Kerberos client configuration is started using Docker Compose.

### Firefox Container

1. **Access the Container**:

   Use the following command to enter the Firefox container:

   ```sh
   docker compose exec -it firefox bash
   ```

2. **Create a Kerberos Ticket**:

   Inside the container, authenticate the tdp_user with their Kerberos principal by executing the following command:

   ```sh
    echo 'tdp_user123' | kinit tdp_user@REALM.TDP
   ```

3. **Run the Setup Script**:

   The setup script will configure the IP addresses and their respective FQDNs in `etc/hosts`, install the TDP SSL certificate into the browser, and set up SPNEGO for Kerberos authentication over HTTP.

   ```sh
   ./setup_for_tdp.sh
   ```

4. **Launch the Browser**:

   Finally, start Firefox to access the web UIs:

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

The Ranger UI can be accessed with the user `admin` and password `RangerAdmin123` (assuming default ranger_admin_password parameter).

You can also access the WebUIs through Knox:

- [HDFS NN](https://edge-01.tdp:8443/gateway/tdpldap/hdfs)
- [YARN RM](https://edge-01.tdp:8443/gateway/tdpldap/yarn)
- [MapReduce Job History Server](https://edge-01.tdp:8443/gateway/tdpldap/jobhistory)
- [HBase Master](https://edge-01.tdp:8443/gateway/tdpldap/hbase/webui/master/master-status?host=master-01.tdp&port=16010)
- [Spark History Server](https://edge-01.tdp:8443/gateway/tdpldap/sparkhistory)
- [Spark3 History Server](https://edge-01.tdp:8443/gateway/tdpldap/spark3history)
- [Ranger Admin](https://edge-01.tdp:8443/gateway/tdpldap/ranger)

### TDP Extra links

- [JupyterHub](https://master-03.tdp:8000/)
- [Hue](https://edge-01.tdp:8888/)
- [Livy Spark](https://edge-01.tdp:8998/ui)
- [Livy Spark3](https://edge-01.tdp:8999/ui)

### TDP Observability links

- [Grafana](https://master-01.tdp:3000/)
- [Prometheus](https://master-01.tdp:9090/)

**Note:** TDP extra deploys a firewall which is enabled, if you do not need it enabled for development you may disable it as follows:

```sh
ansible-playbook ansible_collections/tosit/tdp_extra/playbooks/firewall_generic_stop.yml
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

## Destroy the Cluster

To destroy the cluster, execute the following commands inside the `manager` container:

```bash
vagrant destroy
rm -rf .vagrant
```
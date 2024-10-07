# TDP dev

Use this repository to have a working directory where you run deploy commands with predefined virtual infrastructure with Vagrant or your own infrastructure.

## Requirements

- Libvirt or Virtualbox
- Vagrant
- Docker
- Python3

## Quickstart

The below steps will deploy a TDP cluster with all features so you MUST install all requirements.

If Vagrant is enabled, the Ansible hosts.ini file will be generated using the hosts variable in tdp-vagrant/vagrant.yml.

### Clone the project ans submodules

Clone the project with every submodule to that last commit on the `master/main` branch.

```sh
git clone -b feat/container --recursive https://github.com/TOSIT-IO/tdp-dev.git
```

Clone the main repository and manually chose the submodules. *NB*: the `ansible_collections/tosit/tdp` repository is manadatory. All submodules can be found in the `.gitmodules` file.

```sh
# Clone the main repository
git clone -b feat/container https://github.com/TOSIT-IO/tdp-dev.git
# enter the directory
cd tdp-dev
# Clone the submodule example:`git submodule update --init ansible_collections/tosit/tdp
git submodule update --init <submodule-path>
```

To update all cloned submodules if necessary:

```sh
git submodule update --recursive
```

### Download the component releases

The text file `scripts/tdp-release-uris.txt` contains uris to the component releases of the stack TDP 1.1 to this date. They might be outdated and not correspond to the versions set in the collections after a certain time. you may have to ajust the uris in this case.

Download the relases in the `files`directory with the `download_releases.sh` file:

```sh
./scripts/download_releases.sh
```

### Setup the virtual machines

In the main project directory the machines indicated in the `tdp-vagrant/vagrant.yml` are started on your host with Vagrant. HoweverAnsible is requested to provision the machines and cretae the inventory file. Therefore, create a virtual environment with Python3 and install Ansible.

```sh
python3 -m venv venv-vagrant
source venv-vagrant/bin/activate
pip install ansible
```

Now start the machines:

```sh
vagrant up
```

It moreover creates the `hosts.ini` file in the `inventory` directory later used by Ansible. for each modification of the `tdp-vagrant/vagrant.yml` file or destruction of the VMs it is recommended to remove the `hosts.ini` file and let it be generated again. However, since the private ssh key paths are absolute and will not match inside a container, lets transform them to realtive paths by removing everything before the `/.vagrant/machine`:

```sh
sed -i "s|\(ansible_ssh_private_key_file='\)[^']*/\.vagrant/machines|\1.vagrant/machines|" .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory
```

### Ansible setup

Ansible configuration has been preconfigured for the Vagrant setup in the `ansible.cfg` file and symbolic links have alredy been set in `inventory/topologies/` to the different collections' topology files.

The configured ansible uses the ssh keys created by vagrant for the machines and their path is mentioned in the `hosts.ini` file.

If you use your own infrastructure, modify the configuration accordingly.

### TDP-dev python environment setup

Now to setup the python dependecis for TDP-dev which are marked in the poetry.lock file at the root of the project we are going to use a container.


First build the image and run the container:

```sh
# Build command:
docker build -t tdp-dev dev

# Run command:
docker run --rm -it -v $PWD:/home/tdp/tdp-dev --network=host --env CONTAINER_UID=$(id -u) --env CONTAINER_GID=$(id -g) --env DISPLAY=$DISPLAY tdp-dev
```

Inside the conatiner create the `venv-dev` virtual environment which will contain all dependencies to deploy all TDP collections.

```sh
python -m venv venv-dev
source venv-dev/bin/activate
poetry install --no-root
```

TDP-lib is contained in the dependencies but not its development dependencies and the visialization dependencies to execute `tdp dag`.

### Setup TDP-lib development dependecies (optional)

If you desire de develop TDP-lib with pytest, visualise all operation dependencies with the command `tdp dag` and connect it to Posgres, MariaDB or MySQl database, you will have to install all dependencies contained in the pyproject.toml of the `tdp-lib` directory. However, since they might be conflicting with the ones in the tdp-dev pyproject.toml, they must be setup in a different environment.

Inside the container create the `venv-lib` virtual environment and install the dependencies:

```sh
python -m venv venv-lib
source venv-lib/bin/activate
cd tdp-lib
poetry install -E visualization -E mysql -E postgresql-binary
```

Read the `tdp-lib` documenetation for more information.

### Prerequisites

Before starting to deploy TDP components, the TDP collection prerequisites must be run first which sets up the VMs and installs certain programms.

Either in your host or in the container depending on where you have Ansible installed, you first have to install the Ansible Galaxy collections `general`, `crypto` and `postgresql` as follows.

```sh
ansible-galaxy collection install community.general
ansible-galaxy collection install community.crypto
ansible-galaxy collection install community.postgresql
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
    ansible-playbook ansible_collections/tosit/tdp/playbooks/meta/all_per_service.yml
    # Deploying TDP collection extra
    ansible-playbook ansible_collections/tosit/tdp_extra/playbooks/meta/all_per_service.yml
    # Deploying TDP collection observability
    ansible-playbook ansible_collections/tosit/tdp_observability/playbooks/meta/all_per_service.yml
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

## Web UIs Links

### TDP

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

### TDP Extra

- [JupyterHub](https://master-03.tdp:8000/)
- [Hue](https://edge-01.tdp:8888/)
- [Livy Spark](https://edge-01.tdp:8998/ui)
- [Livy Spark3](https://edge-01.tdp:8999/ui)

### TDP Observability

- [Grafana](https://master-01.tdp:3000/)
- [Prometheus](https://master-01.tdp:9090/)

**Note:** All the WebUIs are Kerberized, you need to have a working Kerberos client on your host, configure the KDC in your `/etc/krb5.conf` file and obtain a valid ticket.

**Note:** TDP extra deploys a firewall which is enabled, if you do not need it enabled for development you may disable it as follows:

```sh
ansible-playbook ansible_collections/tosit/tdp_extra/playbooks/firewall_generic_stop.yml
```

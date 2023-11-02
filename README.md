# TDP dev

Launch a fully-featured virtual TDP Hadoop cluster with a single command _or_ customize the infrastructure.

## Requirements

- Vagrant >= 2.2.19 (to launch and manage the VMs)

You must choose a provider to launch VMs. By default, Vagrant use Virtualbox.

### Virtualbox provider

- VirtualBox >= 6.1.26

This is the default provider, no plugin needed.

### Libvirt provider

- Vagrant libvirt plugin (vagrant-libvirt) >= 0.9.0
- NFS server system package to use the nfs synced folder.

Follow documentation to install it https://vagrant-libvirt.github.io/vagrant-libvirt/.

## Setup python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Launch cluster

```bash
# Activate Python virtual env
source ./venv/bin/activate
# With default virtualbox provider
vagrant up
# With libvirt provider
vagrant up --provider=libvirt
```

You can change the default provider with environment variable.
Please also set provider in tdp_config.yml, as explained in next section.
```bash
export VAGRANT_DEFAULT_PROVIDER=libvirt
vagrant up
```

**Important:** The Vagrantfile create an internal network so you must not run Vagrant in parallel because the internal network can be created multiple times leading to undefined behavior. With the Libvirt provider, VMs are launch in parallel so, if you want speed, use Libvirt provider.

## Configuration

The `tdp_config.yml` file allows you to customize various aspects of TDP dev installation. 

| Configuration Option        | Description                                                           | Default Value     |
|----------------------------|------------------------------------------------------------------------|-------------------|
| vagrant_provider           | vagrant provider you are using.                                        | `virtualbox`
| clean_install              | Reset collections, TDP vars, database, and Python virtual environment. | `false` |
| project_dir                | Location where TDP will be installed.                                  | `/opt/tdp-dev` |
| tdp_collections_dir        | Directory for TDP collections inside project_dir.                      | `ansible_collections/tosit` |
| python_bin                 | Specify the Python binary for installation.                            | `python3.9` |
| http_proxy                 | HTTP proxy URL.                                                        | empty |
| https_proxy                | HTTPS proxy URL.                                                       | empty |
| no_proxy                   | Domains to exclude from proxy.                                         | empty |

### Feature Configuration

The main features of TDP are:
- **TDP Manager:** [TDP-Lib](https://github.com/TOSIT-IO/tdp-lib), [TDP-Server](https://github.com/TOSIT-IO/tdp-server), and [TDP-UI](https://github.com/TOSIT-IO/tdp-ui).
- **TDP Collections:** [core](https://github.com/TOSIT-IO/tdp-collection), [prerequisites](https://github.com/TOSIT-IO/tdp-collection-prerequisites), [extras](https://github.com/TOSIT-IO/tdp-collection-extras), and [observability](https://github.com/TOSIT-IO/tdp-observability).

tdp-observability is disabled by default. Plan to increase CPU and Memory allocated to master-03 when enabling tdp-observability.

Please note that TDP Collection core is mandatory if any other TDP Collection is enabled. Similarly, TDP-Server is mandatory if TDP-UI is enabled.

| Configuration Option | Description                    |
|----------------------|--------------------------------|
| feature_enabled     | Enable or disable the feature. |
| feature_git_project_url  | Git repository URL for the feature. |
| feature_git_project_version  | Version or branch of the feature. |
| feature_dir            | Directory name where the feature is installed inside tdp_collections_dir. |

## Development: 

For easier development on the tdp-dev machine, we've set up a folder called "tdp-dev-sync" that syncs with the "project_dir" location inside the tdp-dev virtual machine. Any changes you make in your local machine's "tdp-dev" directory will automatically appear in the tdp-dev VM.

You can falso connect the tdp-dev VM with your Visual Studio Code. Here are the steps:

- In your repository's folder, open a terminal and run t`vagrant ssh-config`. This will display the configuration details for the tdp-dev VM.
- Copy the configuration part for the tdp-dev host, and past it in a new file `~/.ssh/tdp-dev`.
- Open Visual Studio Code and install the "Remote - SSH" extension.
- In Visual Studio Code, press Ctrl+Shift+P to open the command palette. Search for "Remote-SSH: Open configuration file" and select the ~/.ssh/tdp-dev file you created earlier.
- In the remote explorer sidebar, select the tdp-dev configuration and connect. Then, click the "Open Folder" option and navigate to our `project_dir` folder.

## TDP Quick Start

To deploy a TDP cluster, follow these steps:

### TDP Prerequisites

```bash
# Connect to tdp-dev
vagrant ssh tdp-dev
# Move into project dir
cd /opt/tdp-dev
# Activate Python virtual env and set environment variables
source ./venv/bin/activate && source .env
# Configure TDP prerequisites
ansible-playbook ansible_collections/tosit/tdp_prerequisites/playbooks/all.yml
```

## Deploy TDP 

You have multiple options to deploy a TDP cluster:

### Option 1: Deploy with TDP lib CLI

```bash
# Connect to tdp-dev
vagrant ssh tdp-dev
# Move into project dir
cd /opt/tdp-dev
# Activate Python virtual env and set environment variables
source ./venv/bin/activate && source .env
# Deploy TDP cluster core and extras services
tdp deploy
```

### Option 2: Deploy with TDP UI 

Access the TDP UI at http://localhost:3000/ on your local machine.

- In the UI, go to "Deployments".
- Select "New deployment", "Deploy from the DAG", and "Preview" (by default all services are deployed).
- Click "Deploy."

You can see the deployment in the "Deployments" page. Wait deployment to complete.

### Option 3: Deploy with TDP server API

You can access the TDP server at http://localhost:8000/ on your local machine.

Run the following command to deploy TDP:

```bash
# Deploy TDP cluster core and extras services
curl -X POST http://localhost:8000/api/v1/deploy/dag
```

To check the deployment status:

```bash
# run in your local machine
while ! curl -s http://localhost:8000/api/v1/deploy/status | grep -q "no deployment on-going"; do sleep 10; done
# Connect to tdp-dev
vagrant ssh tdp-dev
# Check deployment logs
sudo journalctl -u tdp-server.service -f
# Wait for deployment to complete
```

## Post-Installation

After deploying the TDP cluster, perform the following post-installation tasks:

```bash
# Connect to tdp-dev
vagrant ssh tdp-dev
# Move into project dir
cd /opt/tdp-dev
# Activate Python virtual env and set environment variables
source ./venv/bin/activate && source .env
# Configure HDFS user home directories
ansible-playbook ansible_collections/tosit/tdp/playbooks/utils/hdfs_user_homes.yml
# Configure Ranger policies
ansible-playbook ansible_collections/tosit/tdp/playbooks/utils/ranger_policies.yml
```

## Connect to machine

```bash
# Connect to edge
vagrant ssh edge-01
```

## Web UIs Links

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
- [JupyterHub](https://master-03.tdp:8000/)

**Note:** All the WebUIs are Kerberized, you need to have a working Kerberos client on your host, configure the KDC in your `/etc/krb5.conf` file and obtain a valid ticket. 

You can also access the WebUIs through Knox:

- [HDFS NN](https://edge-01.tdp:8443/gateway/tdpldap/hdfs)
- [YARN RM](https://edge-01.tdp:8443/gateway/tdpldap/yarn)
- [MapReduce Job History Server](https://edge-01.tdp:8443/gateway/tdpldap/jobhistory)
- [HBase Master](https://edge-01.tdp:8443/gateway/tdpldap/hbase/webui/master/master-status?host=master-01.tdp&port=16010)
- [Spark History Server](https://edge-01.tdp:8443/gateway/tdpldap/sparkhistory)
- [Spark3 History Server](https://edge-01.tdp:8443/gateway/tdpldap/spark3history)
- [Ranger Admin](https://edge-01.tdp:8443/gateway/tdpldap/ranger)

## Destroy cluster

```bash
vagrant destroy
```

For virtualbox provider the destroy command does not destroy the internal network.
This network use an interface on the host `vboxnet<N>` which need to be delete manually.

```bash
# https://www.virtualbox.org/manual/ch06.html#network_hostonly
VBoxManage hostonlyif remove vboxnet0
```

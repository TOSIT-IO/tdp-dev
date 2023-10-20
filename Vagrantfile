# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'yaml'

vagrantfile_dir = File.dirname(File.realpath(__FILE__))

if File.file?("./vagrant.yml")
  config_file = YAML.load_file("./vagrant.yml")
else 
  config_file = YAML.load_file("#{vagrantfile_dir}/vagrant.yml")
end
settings = config_file

if File.file?("./vagrant.yml")
  tdp_config_file = YAML.load_file("./tdp_config.yml")
else 
  tdp_config_file = YAML.load_file("#{vagrantfile_dir}/tdp_config.yml")
end
project_dir = tdp_config_file["project_dir"]
tdp_server_port = tdp_config_file["tdp_server"]["port"]
tdp_ui_port = tdp_config_file["tdp_ui"]["port"]

# Helper functions
def destructure_host_dict(dict)
  dict.values_at("ip", "hostname", "cpus", "memory", "box")
end

domain = settings["domain"]
all_hosts = settings["hosts"] + settings["tdp_manager_host"]
# define groups and hostvars for ansible provisionner
ansible_configuration = all_hosts.each_with_object({"hostvars": {}, "groups": Hash.new {|hash, key| hash[key] = []}}) do |host, configuration|
  ip, hostname, cpus, memory, box = destructure_host_dict(host)
  configuration[:hostvars][hostname] = {
    :ip     => ip,
    :domain => domain,
  }
  host.fetch("groups", []).each do |group|
    configuration[:groups][group] << host["hostname"]
  end # end group
end # end configuration


Vagrant.configure("2") do |config|
  config.vm.synced_folder "./", "/vagrant", disabled: true

  all_hosts.each do |host|
    ip, hostname, cpus, memory, box = destructure_host_dict(host)
    box ||= settings["box"]
    config.vm.define hostname, autostart: true do |cfg|
      cfg.vm.box = box
      cfg.vm.hostname = hostname
      cfg.vm.network "private_network", ip: ip

      cfg.vm.provider :virtualbox do |vb|
        vb.name = hostname # sets gui name for VM
        vb.customize ["modifyvm", :id, "--memory", memory, "--cpus", cpus, "--hwvirtex", "on"]
        
        if hostname == "tdp-dev"
          # Create synced folder
          config.vm.synced_folder "tdp-dev-sync/", project_dir
          # Forward TDP UI and server port
          cfg.vm.network "forwarded_port", guest: tdp_server_port, host: tdp_server_port, id: 'tdp-server'
          cfg.vm.network "forwarded_port", guest: tdp_ui_port, host: tdp_ui_port, id: 'tdp-ui'
        end # end if 

      end # end provider virtualbox

      cfg.vm.provider :libvirt do |libvirt|
        libvirt.cpus = cpus
        libvirt.memory = memory
        libvirt.qemu_use_session = false
        if hostname == "tdp-dev"
          # Create synced folder
          config.vm.synced_folder "tdp-dev-sync/", project_dir
          # Forward TDP UI and server port
          cfg.vm.network "forwarded_port", guest: tdp_server_port, host: tdp_server_port, id: 'tdp-server'
          cfg.vm.network "forwarded_port", guest: tdp_ui_port, host: tdp_ui_port, id: 'tdp-ui'
        end # end if 
      end # end provider libvirt
    end # end define
  end # end settings

  config.vm.provision :ansible do |ansible|
    ansible.playbook = "#{vagrantfile_dir}/provision/playbooks/all.yml"
    ansible.host_vars = ansible_configuration[:hostvars]
    ansible.groups = ansible_configuration[:groups]
    ansible.config_file = "#{vagrantfile_dir}/ansible.cfg"
  end # end provision
end

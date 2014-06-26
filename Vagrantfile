# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.require_version ">= 1.4.0"

Vagrant.configure("2") do |config|
    config.vm.box = "ubuntu1204"
    config.vm.box_url = "http://cloud-images.ubuntu.com/vagrant/precise/current/precise-server-cloudimg-amd64-vagrant-disk1.box"
    config.vm.hostname = "cirqle-test.vm"

    # Forward Tornado's 9000
    config.vm.network :forwarded_port, guest:8888, host:3456

    config.vm.provider :vmware_fusion do |fusion|
        fusion.vmx["memsize"] = "2048"
        fusion.vmx["numvcpus"] = "1"
    end

    config.vm.provider :virtualbox do |vbox|
        vbox.name = "cirqle"
        vbox.customize ["modifyvm", :id, "--memory", "3048"]
        vbox.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    end

    config.vm.provision :ansible do |ansible|
        ansible.verbose = 'vv'
        ansible.limit = 'all'
        ansible.host_key_checking = false
        ansible.playbook = "vagrant/initial-setup.yaml"
        ansible.extra_vars = {
            project_dir: "/vagrant/"
        }

    end

end

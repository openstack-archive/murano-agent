Murano Agent Elements
=====================

This folder contains necessary DIB elements to build Murano Agent image.


Prerequisites
-------------

1. Install diskimage-builder

.. sourcecode:: bash

    sudo pip install diskimage-builder

2. Install qemu-uils and kpartx

On Ubuntu, Debian:

.. sourcecode:: bash

    sudo apt-get install qemu-utils kpartx


On Centos, Fedora:

.. sourcecode:: bash

    sudo yum install qemu-utils kpartx


Image building
--------------

To build Ubuntu-based image

.. sourcecode:: bash

    sudo ELEMENTS_PATH=${murano_agent_root}/contrib/elements \
        DIB_CLOUD_INIT_DATASOURCES="Ec2, ConfigDrive, OpenStack" disk-image-create \
        vm ubuntu murano-agent -o ubuntu14.04-x64-agent

To build Debian-based image

.. sourcecode:: bash

    sudo ELEMENTS_PATH=${murano_agent_root}/contrib/elements DIB_RELEASE=jessie \
        DIB_CLOUD_INIT_DATASOURCES="Ec2, ConfigDrive, OpenStack" disk-image-create \
        vm debian murano-agent-debian -o debian8-x64-agent

Where ${murano_agent_root} is a path to murano-agent files.

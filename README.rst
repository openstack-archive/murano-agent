========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/murano-agent.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

Murano Agent
============

Murano Agent is a VM-side guest agent that accepts commands from Murano engine
and executes them.

Image building using DiskImage-Builder
--------------------------------------

Folder, named *contrib/elements* contains
`diskimage-builder <https://opendev.org/openstack/diskimage-builder>`_
elements to build an image which contains the Murano Agent required to use Murano.

Ubuntu based image containing the agent can be built and uploaded
to Glance with the following commands:

::

  $ git clone https://opendev.org/openstack/diskimage-builder.git
  $ git clone https://opendev.org/openstack/murano-agent.git
  $ export ELEMENTS_PATH=murano-agent/contrib/elements
  $ export DIB_CLOUD_INIT_DATASOURCES=OpenStack
  $ diskimage-builder/bin/disk-image-create vm ubuntu \
    murano-agent -o ubuntu-murano-agent.qcow2
  $ openstack image create ubuntu-murano --disk-format qcow2
    --container-format bare --file ubuntu-murano-agent.qcow2 \
    --property murano_image_info='{"title": "Ubuntu for Murano", "type": "linux"}'

Project Resources
-----------------

Project status, bugs, and blueprints are tracked on Launchpad:

  https://launchpad.net/murano

Developer documentation can be found here:

  https://docs.openstack.org/murano/latest/

Additional resources are linked from the project wiki page:

  https://wiki.openstack.org/wiki/Murano

License
-------

Apache License Version 2.0 http://www.apache.org/licenses/LICENSE-2.0

Murano Agent
============

Murano Agent is a VM-side guest agent that accepts commands from Murano engine
and executes them.

Image building using dib
------------------------

contrib/elements contains
`diskimage-builder <https://git.openstack.org/cgit/openstack/diskimage-builder>`_
elements to build an image which contains the Murano Agent required to use Murano.

An example Ubuntu based image containing the agent can be built and uploaded
to glance with the following commands:

::

  git clone https://git.openstack.org/openstack/diskimage-builder.git
  git clone https://git.openstack.org/stackforge/murano-agent.git
  export ELEMENTS_PATH=murano-agent/contrib/elements
  diskimage-builder/bin/disk-image-create vm ubuntu \
    murano-agent -o ubuntu-murano-agent.qcow2
  glance image-create --disk-format qcow2 --container-format bare \
    --name ubuntu-murano < ubuntu-murano.qcow2

Project Resources
-----------------

Project status, bugs, and blueprints are tracked on Launchpad:

  https://launchpad.net/murano

Developer documentation can be found here:

  https://murano.readthedocs.org

Additional resources are linked from the project wiki page:

  https://wiki.openstack.org/wiki/Murano

License
-------

Apache License Version 2.0 http://www.apache.org/licenses/LICENSE-2.0
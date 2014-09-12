Murano
======
Murano Project introduces an application catalog, which allows application
developers and cloud administrators to publish various cloud-ready
applications in a browsable‎ categorised catalog, which may be used by the
cloud users (including the inexperienced ones) to pick-up the needed
applications and services and composes the reliable environments out of them
in a "push-the-button" manner.

murano-agent
============
Murano Agent is a VM-side guest agent that accepts commands from
Murano Conductor and executes them. We have two Agent implementations
targeting different platforms, but eventually we going to end up with
Python Agent that works on Linux and uses new execution plan format
described in `Unified Agent <https://wiki.openstack.org/wiki/Murano/UnifiedAgent>`_

Project Resources
-----------------

Project status, bugs, and blueprints are tracked on Launchpad:

  https://launchpad.net/murano

Developer documentation can be found here:

  https://murano.readthedocs.org

Additional resources are linked from the project wiki page:

  https://wiki.openstack.org/wiki/Murano


Image building using dib
------------------------

contrib/elements contains `diskimage-builder <https://github.com/openstack/diskimage-builder>`_
elements to build an image which contains the Murano Agent required to use Murano.

An example ubuntu based image containing the agent can be built and uploaded to glance
with the following commands:

::

  git clone https://git.openstack.org/openstack/diskimage-builder.git
  git clone https://git.openstack.org/stackforge/murano-agent.git
  export ELEMENTS_PATH=murano-agent/contrib/elements
  diskimage-builder/bin/disk-image-create vm ubuntu murano-agent -o ubuntu-murano-agent.qcow2
  glance image-create --disk-format qcow2 --container-format bare --name ubuntu-murano < ubuntu-murano.qcow2


License
-------

Apache License Version 2.0 http://www.apache.org/licenses/LICENSE-2.0

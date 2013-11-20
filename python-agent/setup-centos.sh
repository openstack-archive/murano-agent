#!/bin/sh
#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#   CentOS script
LOGLVL=1
SERVICE_CONTENT_DIRECTORY=`cd $(dirname "$0") && pwd`
PREREQ_PKGS="git wget make gcc python-pip python-iso8601 python-six python-anyjson python-eventlet python-devel python-setuptools"
PIPAPPS="pip python-pip pip-python"
PIPCMD=""
SERVICE_SRV_NAME="murano-agent"
ETC_CFG_DIR="/etc/murano"



# Functions
# Loger function
log()
{
	MSG=$1
	if [ $LOGLVL -gt 0 ]; then
		echo "LOG:> $MSG"
	fi
}

# find pip
find_pip()
{
	for cmd in $PIPAPPS
	do
		_cmd=$(which $cmd 2>/dev/null)
		if [ $? -eq 0 ];then
			break
		fi
	done
	if [ -z $_cmd ];then
		echo "Can't find \"pip\" in system, please install it first, exiting!"
		exit 1
	else
		PIPCMD=$_cmd
	fi
}

# Check or install package
in_sys_pkg()
{
	PKG=$1
	rpm -q $PKG > /dev/null 2>&1
	if [ $? -eq 0 ]; then
	    log "Package \"$PKG\" already installed"
	else
		log "Installing \"$PKG\"..."
		yum install $PKG --assumeyes > /dev/null 2>&1
		if [ $? -ne 0 ];then
		    log "installation fails, exiting!!!"
		    exit
		fi
	fi
}

# install
inst()
{
# Checking packages
	for PKG in $PREREQ_PKGS
	do
		in_sys_pkg $PKG
	done
# Find python pip
	find_pip
	MRN_CND_SPY=$SERVICE_CONTENT_DIRECTORY/setup.py
	if [ -e $MRN_CND_SPY ]; then
		chmod +x $MRN_CND_SPY
		log "$MRN_CND_SPY output:_____________________________________________________________"
## Setup through pip
		# Creating tarball
		rm -rf $SERVICE_CONTENT_DIRECTORY/*.egg-info
		cd $SERVICE_CONTENT_DIRECTORY && python $MRN_CND_SPY egg_info
		if [ $? -ne 0 ];then
			log "\"$MRN_CND_SPY\" egg info creation FAILS, exiting!!!"
			exit 1
		fi
		rm -rf $SERVICE_CONTENT_DIRECTORY/dist/*
		cd $SERVICE_CONTENT_DIRECTORY && $MRN_CND_SPY sdist
		if [ $? -ne 0 ];then
			log "\"$MRN_CND_SPY\" tarball creation FAILS, exiting!!!"
			exit 1
		fi
		# Running tarball install
		TRBL_FILE=$(basename `ls $SERVICE_CONTENT_DIRECTORY/dist/murano-agent*.tar.gz`)
		$PIPCMD install $SERVICE_CONTENT_DIRECTORY/dist/$TRBL_FILE
		if [ $? -ne 0 ];then
			log "$PIPCMD install \"$TRBL_FILE\" FAILS, recreate terball with \"python setup.py sdist\" command, exiting!!!"
			exit 1
		fi
		# Creating etc directory for config files
		if [ ! -d $ETC_CFG_DIR ];then
			log "Creating $ETC_CFG_DIR direcory..."
			mkdir -p $ETC_CFG_DIR
			if [ $? -ne 0 ];then
				log "Can't create $ETC_CFG_DIR, exiting!!!"
				exit 1
			fi
		fi
		log "Making sample configuration file at \"$ETC_CFG_DIR\""
		cp -f "$SERVICE_CONTENT_DIRECTORY/etc/agent.conf" "$ETC_CFG_DIR/agent.conf"
	else
		log "$MRN_CND_SPY not found!"
	fi
}

# searching for service executable in path
get_service_exec_path()
{
	if [ -z "$SERVICE_EXEC_PATH" ]; then
		SERVICE_EXEC_PATH=$(which muranoagent)
		if [ $? -ne 0 ]; then
			log "Can't find \"muranoagent ($SERVICE_SRV_NAME)\", please install the \"$SERVICE_SRV_NAME\" by running \"$(basename "$0") install\" or set variable SERVICE_EXEC_PATH=/path/to/daemon before running setup script, exiting!"
			exit 1
		fi
	else
		if [ ! -x "$SERVICE_EXEC_PATH" ]; then
			log "\"$SERVICE_EXEC_PATH\" in not executable, please install the muranoagent \"($SERVICE_SRV_NAME)\" or set variable SERVICE_EXEC_PATH=/path/to/daemon before running setup script, exiting!"
			exit 1
		fi
	fi
}

# uninstall
uninst()
{
	# Uninstall trough  pip
	find_pip
	# looking up for python package installed
	PYPKG=$SERVICE_SRV_NAME
	_pkg=$($PIPCMD freeze | grep $PYPKG)
	if [ $? -eq 0 ]; then
		log "Removing package \"$PYPKG\" with pip"
		$PIPCMD uninstall $_pkg --yes
	else
		log "Python package \"$PYPKG\" not found"
	fi
}

# inject init
injectinit()
{
	log "Enabling $SERVICE_SRV_NAME in init.d..."
	cp -f "$SERVICE_CONTENT_DIRECTORY/init.d/murano-agent-el6" "/etc/init.d/$SERVICE_SRV_NAME"
	sed -i "s/DAEMON=.*/DAEMON=$(echo $SERVICE_EXEC_PATH | sed -e 's/\//\\\//g')/" /etc/init.d/$SERVICE_SRV_NAME
	chmod 755 /etc/init.d/$SERVICE_SRV_NAME
	chkconfig --add $SERVICE_SRV_NAME
	chkconfig $SERVICE_SRV_NAME on
}

purgeinit()
{
	log "Removing from init.d..."
	chkconfig $SERVICE_SRV_NAME off
	chkconfig --del $SERVICE_SRV_NAME
	rm -f /etc/init.d/$SERVICE_SRV_NAME
	#Fedora compat.
	systemctl --system daemon-reload > /dev/null 2>&1
}

# Command line args'
COMMAND="$1"
case $COMMAND in
	inject-init )
		get_service_exec_path
		log "Injecting \"$SERVICE_SRV_NAME\" to init..."
		injectinit
		postinst
		;;

	install )
		inst
		get_service_exec_path
		injectinit
		;;

	purge-init )
		log "Purging \"$SERVICE_SRV_NAME\" from init..."
		service $SERVICE_SRV_NAME stop
		purgeinit
		;;

	uninstall )
		log "Uninstalling \"$SERVICE_SRV_NAME\" from system..."
		service $SERVICE_SRV_NAME stop
		purgeinit
		uninst
		;;

	* )
		echo -e "Usage: $(basename "$0") command \nCommands:\n\tinstall - Install $SERVICE_SRV_NAME software\n\tuninstall - Uninstall $SERVICE_SRV_NAME software\n\tinject-init - Add $SERVICE_SRV_NAME to the system start-up\n\tpurge-init - Remove $SERVICE_SRV_NAME from the system start-up"
		exit 1
		;;
esac
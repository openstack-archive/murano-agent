Murano Windows Agent
====================

Murano Windows Agent is an initial version of Murano Agent.
Currently, it's outdated and not supported.

The main difference with the new Python agent is support of running PowerShell.
After this support will be added to Python Agent, Windows Agent will be dropped.


How to build
============

Build using Visual Studio
-------------------------
1. Launch Visual Studio
#. Ensure that you have latest ``NuGet`` extension installed (shipped with recent
   versions of VS)
#. Open ``WindowsAgent.sln``
#. Select target configuration (Release or Debug) using drop-down found in VS
   toolbar
#. Build the Solution (Build menu -> Build Solution).


Build from command line
-----------------------
1. CD to where ``WindowsAgent.sln`` is located
#. Download nuget.exe from https://dist.nuget.org/win-x86-commandline/latest/nuget.exe
   to current directory.
#. Run ``nuget.exe restore``
#. Build the solution using msbuild:
   ``C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\MSBuild.exe /p:Configuration=Release``

   The exact path to msbuild may differ on your system and .NET version installed.
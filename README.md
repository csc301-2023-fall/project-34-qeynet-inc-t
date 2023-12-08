​
<h1 align="center">
<img src="logo.png" width="150">
</h1>

# Astra 

## Partner Intro
**Partner:**
* Michael Luciuk
* Primary point of contact
* Github: https://github.com/mrl280

**Organization:**

<p>
 <img width="300" height="160" src="https://images.squarespace-cdn.com/content/v1/5a837cb7d74cffca72977a29/1518672294226-XPZ4FOYONO9PKB0DX8AC/QEYnet+logo_final-+iteration+2.png">
</p>

QEYnet is a startup company aiming to deploy a low-cost microsatellite quantum-key-distribution (QKD) network to facilitate the start a new era of ultra-secure communication systems.

More can be learned about QEYnet and their groundbreaking QKD technologies from their website: https://qeynet.com/

## Description of the project

Astra is a local, GUI-based program that will allow QEYnet employees and customers to read and interact with data from QEYnet satellites and other devices.

Satellites out of view are critical to QEYnet’s mission, hence they need some form of software that allows them and customers to monitor the state of their satellites at all times.

Our application will give employees a convenient and smooth GUI to check satellite data and keep them informed on satellite health through the use of notifications.

## Key Features

* **Read in custom telemetry files**

The user can upload a local file from their computer and have the information accessible to the program. If there are problems with the file, the upload does not go through and the user is shown an error.

* **View telemetry data**

The user can see the data (and additional info on the data) associated with a telemetry frame. The user can move between telemetry frames, constrain the time range for the telemetry frames, and choose which parameters for the telemetry frame are shown and in what order.

* **Display warning messages**

When the telemetry data satisfies certain alarm criteria, alarms are created and shown to the user in a dedicated tab. Alarms can be sorted and filtered based on various criteria, most notably the priority of the alarm.

* **Plot selected parameters against time**

Data from telemetry frames can be plotted on a graph with time as the independent variable and various user-chosen parameters as dependent variables.

## Download and Installation

To acquire the program, one can head to the releases section and simply download `astra-X.Y.Z.zip` under the latest release version X.Y.Z, then extract the zip folder.

Once extracted, running the program simply requires running the `astra.exe` file located in the root of the folder.

## Instructions

Astra starts up on the device selection screen. You can add a device by clicking the appropriate button and selecting a device configuration file (some example files are included in the download). Once added, devices will appear in a table. Double-clicking a row of the table allows you to either delete a device or select it for monitoring.

Once a device is chosen, the main GUI for Astra will open. It consists of three tabs: the telemetry, alarm, and graphing tabs.

The telemetry tab is where you can input and view telemetry data. To start, press the button for adding telemetry data from a file. A file dialog will appear asking for a telemetry file. (Some example telemetry files are also included in the download.) Make sure to select telemetry files that correspond to the appropriate device.

NOTE: telemetry data persists between sessions of the program. If you close and reopen the program, all the read-in telemetry data for a given device will still be there.

The table on the screen will now be filled with data for the first telemetry frame from the file. You can use arrows above the table to change between different telemetry frames, or the time range filter to view only telemetry frames in a certain time range. Clicking on the headers of the table allows you to sort by certain columns, and clicking on the rows allows you to see more data. Finally, which parameters to show can be controlled by the left panel, where parameters can be checked or unchecked to show or hide them from the table. There is a search function for narrowing down the tags in the panel.

The alarm tab displays a table of alarms generated upon reading in a telemetry file that satisifies certain abnormal conditions. Alarms can be filtered according to various options above the table, as well as a parameter-filtering side panel that functions similarly to the one in the telemetry tab. Clicking on the headers allows for sorting by columns just like with the telemetry table. Clicking on rows allows you to view an alarm in more detail and either acknowledge or remove the alarm.

On all three tabs, there is a set of alarm banners showing the most high-priority alarms that have been generated. The banners will generally show a mixture of acknowledged (old) and unacknowledged (new) alarms.

NOTE: alarms, unlike telemetry data, do not persist between sessions.

The final tab is the graphing tab. Another parameter selection side panel allows you to pick which parameters to plot. There is a time range filter to allow for narrowing the graph to a specific range of time. All parameters are plotted according to separate y-axes that can be switched between in a dropdown.

There are also options to export a graph, as well as the raw data that makes up the graph.

 ## Development requirements

Astra is designed to run on Windows, and uses Python 3.12. All required dependencies are listed in `requirements.txt`.
 
 ## Deployment and Github Workflow

Astra was developed in 3 subteams: the data subteam, responsible for file I/O and persistence; the use case subteam, responsible for alarm checking and formatting data from the data subteam into a useful form for the frontend subteam; and the frontend subteam, responsible for the GUI. The subteam division was loosely followed, with members of one subteam often helping out members of another subteam as needed. Some additional information about the architecture is available to QEYnet in [this document](https://docs.google.com/document/d/1Wuo1VQmCnTxxP83IEmn096VleXanofMJPdSxHzJb2K8/edit?usp=sharing).

There is a GitHub workflow for linting with Flake8 and running tests with pytest.

Deployment of the application is manual, using PyInstaller to create an executable from the source code.

 ## Coding Standards and Guidelines

We have the following standards on code style:
* Max line Length: 100 characters
* Strings: Use single quotes for strings by default
* Docstring Format: reST (same as Panoptes, a sister project to automatically generate device configuration and telemetry files)
* Lint with Flake8; no specific autoformatters prescribed
* Follow the PEP 8 Style Guide on other matters

 ## Licenses 

Astra uses the **MIT license**, a simple and popular open-source license that meets all our needs.

With the MIT license in our codebase, it grants any person the right to use, modify, and distribute our codebase as long as they include the same copyright notice in their copies.

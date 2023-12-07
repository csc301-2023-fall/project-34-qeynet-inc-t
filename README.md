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

QEYnet is a startup company aiming to deploy a low-cost microsatellite quantum-key-distribution (QKD) network to facilitate the start a new era of ultra-secure communication systems

More can be learned about QEYnet and their groundbreaking QKD technologies from their website: https://qeynet.com/

## Description of the project

Astra will be a local, GUI-based program that will allow QEYnet employees and customers to read and interact with data from QEYnet satellites and other devices.

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

Data from telemetry frames is plotted on a graph with time as the independent variable and various user-chosen parameters as dependent variables.

* **Emit additional warnings for high-priority alarms (if time permits)**

For sufficiently high-priority alarms, additional methods of notifying staff are deployed such as popups or emails.

## Download and Installation

To acquire the program, one can head to the releases section and simply download `astra-vX.Y.Z.zip` under the latest release version X.Y.Z, then extract the zip folder

Once extracted, running the program simply requires running the `main.exe` file located in the root of the folder.

## Instructions

On startup, a file dialog will appear asking for a device configuration file. Some sample device configuration files are included in the download.

Once a configuration file is chosen, the GUI for Astra will open. There are currently two functioning tabs (screens): the telemetry tab and the alarm tab.

The telemetry tab is where you can input and view telemetry data. To start, press the button for adding telemetry data from a file. A file dialog will appear asking for a telemetry file. Some sample telemetry files are also included in the download. Make sure to select telemetry files that correspond to the appropriate device.

NOTE: telemetry data persists between sessions of the program. If you close and reopen the program, all the read-in telemetry data for a given device will still be there. To reset the state of the program, delete the `astra.db` file that is generated upon the first run of the program. (In the future, there will be more granular ways of managing the state of the program.)

The table on the screen will now be filled with data for the first telemetry frame from the file. You can use arrows above the table to change between different telemetry frames, or the time range filter to view only telemetry frames in a certain time range. The format for the filter is `YYYY-MM-DD hh:mm:ss`; leave a time blank to indicate that there is no bound.

On the left is a parameter filter. Check and uncheck parameter tags to show and hide them from the table. There is a search function to narrow down tags -- enter something into the search box to see only tags that contain the search text as a substring. (Leave the search box empty to see all tags. The search function will be expanded in the future to include parameter descriptions.)

The other tab is the alarm tab. It contains a table of alarms, created based on patterns in the telemetry data and alarm specifications in the chosen configuration file. There are some filters above the table that can be toggled.

NOTE: alarms, unlike telemetry data, do not persist between sessions.

Some columns of the tables for both the telemetry and alarm tabs can be sorted. Click a column header of the table to sort, and click again to sort in the opposite order.

Known issues:
- The telemetry file reading is currently not very robust. Make sure to select the appropriate files for the appropriate device, to add files for a device in order of timestamp (indicated on the filename of all sample telemetry files), and to add each file only once. The program may behave in unpredictable ways otherwise.
 
 ## Development requirements

 Astra can be run on Windows. To install the D3 version, navigate to the D3 release for this repository and download `astra-d3.zip`. Extract the zip, and double-click on `astra-d3.exe` to launch the program. If a Windows Defender popup appears, click "More info" followed by "Run anyway".
 
 ## Deployment and Github Workflow

We still largely work in the subteams established in D2: the data subteam, responsible with interacting with the file system (including persistence); the use case subteam, responsible for alarm checking and turning data from the data subteam into a useful format for the frontend subteam; and the frontend subteam, responsible for the GUI. However, we are not strict with the subteams, and members of one subteam can and do help out members of another subteam as needed.

Ideally, changes are worked on in branches, and when a feature is done, a pull request is made, at least one other team member reviews and provides feedback on the changes to the code, and when the code is deemed ready, the pull request is merged into the main branch. (In practice, deviations from this may occur for various reasons.) There are workflows upon pushing to the repository to run tests and lint the code.

For now, we deploy the application manually, using PyInstaller to create an executable from the source code. In the future, we may switch to a more automatic method of deployment.

 ## Coding Standards and Guidelines

We currently have the following standards on code style:
* Max line Length: 100 characters
* Strings: Use single quotes for strings by default
* Docstring Format: reST (same as Panoptes, a sister project to automatically generate device configuration and telemetry files)
* Lint with Flake8; no specific autoformatters prescribed
* Follow the PEP 8 Style Guide on other matters

 ## Licenses 

We will apply the **MIT license** to our codebase. It’s because we're allowed to share the code under an open-source license and the MIT license is such a simple and popular open-source license that meets all our needs.

With the MIT license in our codebase, it grants any person the right to use, modify, and distribute our codebase as long as they include the same copyright notice in their copies.

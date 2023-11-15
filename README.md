# Astra
​
## Partner Intro
**Partner:**
* Michael Luciuk
* Primary point of contact
* Email: mike.luciuk@mail.utoronto.ca

**Organization:**

<p>
 <img width="300" height="160" src="https://images.squarespace-cdn.com/content/v1/5a837cb7d74cffca72977a29/1518672294226-XPZ4FOYONO9PKB0DX8AC/QEYnet+logo_final-+iteration+2.png">
</p>

[QEYnet](qeynet.com) is a startup company aiming to deploy a quantum key distribution system using satellites, to deal with the approaching quantum threat. 

Our society relies heavily on encryption to keep data safe when communicating, however, it also relies on a mathematical formula which will soon be broken by quantum computers.

QEYnet plans to use the satellite distribution system to streamline our society's switch to "quantum-safe" keys, in a way that traditional distribution systems cannot.

## Description about the project

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

## Instructions
 * Clear instructions for how to use the application from the end-user's perspective
 * How do you access it? For example: Are accounts pre-created or does a user register? Where do you start? etc. 
 * Provide clear steps for using each feature described in the previous section.
 * This section is critical to testing your application and must be done carefully and thoughtfully.

 **_TBA_**
 
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
* Docstring Format: reST (same as Panoptes)
* Lint with Flake8; no specific autoformatters prescribed
* Follow the PEP 8 Style Guide on other matters

 ## Licenses 

We will apply the **MIT license** to our codebase. It’s because we're allowed to share the code under an open-source license and the MIT license is such a simple and popular open-source license that meets all our needs.

With the MIT license in our codebase, it grants any person the right to use, modify, and distribute our codebase as long as they include the same copyright notice in their copies.

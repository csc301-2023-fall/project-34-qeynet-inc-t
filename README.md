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
 * What are the technical requirements for a developer to set up on their machine or server (e.g. OS, libraries, etc.)?
 * Briefly describe instructions for setting up and running the application. You should address this part like how one would expect a README doc of real-world deployed application would be.
 * You can see this [example](https://github.com/alichtman/shallow-backup#readme) to get started.

  **_TBA_**
 
 ## Deployment and Github Workflow
​
Describe your Git/GitHub workflow. Essentially, we want to understand how your team members share codebase, avoid conflicts and deploys the application.
​
 * Be concise, yet precise. For example, "we use pull-requests" is not a precise statement since it leaves too many open questions - Pull-requests from where to where? Who reviews the pull-requests? Who is responsible for merging them? etc.
 * If applicable, specify any naming conventions or standards you decide to adopt.
 * Describe your overall deployment process from writing code to viewing a live application
 * What deployment tool(s) are you using? And how?
 * Don't forget to **briefly justify why** you chose this workflow or particular aspects of it!

  **_TBA_**

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

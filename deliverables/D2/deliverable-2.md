# Team Astra - Deliverable 2

## Software

Astra will be a local, GUI-based program that will allow QEYnet employees and customers to read and interact with data from QEYnet satellites and other devices. QEYnet is a startup company aiming to deploy a quantum key distribution system using satellites. Users will be able to use our app to monitor the health of satellites and other devices by displaying plots of telemetry data over time, and notifying users in case there are any unexpected discrepancies so that they can diagnose and treat any potential problems.

We will be developing Astra from scratch, in Python.

## Divisions for Deliverable 2

The first division into subteams that we considered was a simple frontend/backend/database divide. However, it was clarified in a team-partner meeting that persistence will not be a fundamental aspect of the program – there may be additional features that require saving certain types of files, but no specialized knowledge on databases will be required for this project, so it does not make sense to have a specialized database team.

The next most natural division, then, was a simple frontend/backend split. However, Deliverable 2 requires that the project be split into three distinct sections, so we could not go with this division.

We eventually created three distinct sections of the program by further dividing the backend into two sections: one that dealt with reading (and, if needed, writing) local files, and one that dealt with all other non-UI matters. This gave rise to the three subteams for this deliverable:
Data subteam: Responsible for all file I/O that occurs in the program. Transforms file data into objects that the use case subteam can make use of.
Use case subteam: Transforms the output of the data subteam into various forms that can be conveniently used by the frontend subteam.
Frontend subteam: Responsible for the GUI of the program.

## Scope of Deliverable 2

Due to time constraints, we decided to keep the scope of this deliverable very small. Each subteam was responsible for doing their part to facilitate the following functionality:
Automatically reading configuration data from a fixed configuration file at program startup.
Allowing the user to read telemetry data from telemetry files, conforming to the configuration data.
Displaying information on the most recent telemetry frame across all telemetry data that has been read in.

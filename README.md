# Campuswire Reputation Report
This python script fetches reputation report from Campuswire and stores it to a google sheet.

Two environment variables are needed

- SHEETID: the google sheet database
- SERVICEACCOUNT: a base64 encoded service account json

The token for Campuswire is stored in google sheet directly and updated each time the script is run.
It could be obtained via "inspecting" the Campuswire website in the first place.
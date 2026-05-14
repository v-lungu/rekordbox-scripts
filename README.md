# Rekordbod USB Library Import Fix
## Problem
Importing an entire library from a USB to a Desktop with Rekordbox installed can lead to songs not being able to locate their source file. After some investivation I found that when I pulled all the songs through Rekordbox into a folder, any file over 44 characters in length had its name cut off. This meant that when Rekordbox tries to find the full file name it can't, because the file doesn't exist.
## Solution
I've written a script that will take your local library after importing all your songs and playlists, and rename the actual files on your machine to the correct name. The name is taken from the Rekordbox library XML export.
## How to Use
1. Drag and drop all songs you want to import from your USB to a folder in Windows Explorer
2. Download your library XML file by navigating in Rekordbox to File > Export Collection in XML Format
3. Move the .xml file into this project folder
4. Preview the script using command:  python fix-script.py <Library Name\>.xml <Location of Music Folder\>
5. If everything looks good then run the script and rename all files in the folder using: python fix-script.py <Library Name\>.xml <Location of Music Folder\> --rename
6. $$ Profit ??

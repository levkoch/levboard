# LevBoard (Experimental Version)
A stats.fm integration for building custom charts for your listening history. 

This version is adapted to all of the custom features that I'm (levkoch) am making for myself, which includes added filtering for songs & albums, and so much more.

If you are fine with just having song charts, head over to the `main` branch (click [here](https://github.com/levkoch/levboard/)), and it'll include all of the instructions on how to use the non-experimental version. However, if you are really interested in getting more data, continue for set up.

## Requirements
Just like for the non-experimental version, this version requires stats.fm Plus with files imported and a computer to run these scripts on. Additionally, this version requries a copy of my LevBoard spreadsheet, and a Google service account to collect data from and send data to the spreadsheet.

## Setting Up Service Account
**NOTE**: None of the services we are going to use should require you to pay, so don't add your credit card info to Google Cloud even if it asks you nicely.

Head over to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project. Then head to the service account [creation page](https://console.cloud.google.com/iam-admin/serviceaccounts/create) and connect it to the project. Give it the "Editor" role. After finishing, you should be redirected to the service account [management page](https://console.cloud.google.com/iam-admin/serviceaccounts). Click on the three dots to the right of the newly created service account, and then select "Manage Keys". Click "ADD KEY" and then "Create new key". It will download to your computer, so rename it to something nice and keep it somewhere safe. 

## Setting Up Spreadsheet.
The spreadsheet is where most of the data is stored for easier filtering. Clone it from [here](https://docs.google.com/spreadsheets/d/1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk/copy). Then, click on "Share", and grant the service account "Editor" privedges to the sheet. The service account is now able to edit portions of the spreadsheet.

### Adding Songs & Albums
Songs are stored in "Song Info" sub-spreadsheet. The first column is the **unique** name of the song (has to be unique or else filtering doesn't work correctly,) and the second row is the song's IDs (separated by commas.) The next two columns (for artists & plays) are auto-populated whenever `plays.py` is ran in spreadsheet mode, and the last two columns (for points & units) are Google Sheets functions. Make sure they're copied over for any new song row you add.

Albums are stored in the "Albums" sub-spreadsheet ("Albums Info" is for album images.) If you'd like to add a new album, copy another album, insert some new rows to free up space, and paste it into there. Edit the artist, name, and song name fields (just the leftmost column.) You do not need to add all of the songs into the album if you only listen to a few, but the ones that I've added all of have the album title and artists bolded. The rest of the columns will auto-populate with the current information the sheet holds. Ensure that column G also shows at least one song id, and copy over a function from the above row if the cell is blank.

**NOTE**: Albums MUST be registered in the spreadsheet in order to chart. The "Top Albums" spreadsheet will tell you which songs are orphaned, and once a song reaches 200 units, I add it to an album, even if it's all by itself.

### Deleting & Albums
If you'd like to delete a song because you haven't listened to it and I have, that's also fine. (Deleting songs and albums you haven't listened to will make the system run faster.) Just make sure to delete it from any albums that it's attached to. Deleting Albums works the same way, just select the rows it occupies and remove them. 

**NOTE**: whenever deleting albums or songs, make sure to also wipe `songs.json` and `albums.json` in the data folder by deleting their contents and replacing it with the `{}` characters.

## Editing Config
The config in here is currently set to my information. The fields that need to be edited are `LEVBOARD_SHEET` (set it to the letters between `"spreadsheets/d/"` and `"/edit/"` in the URL of your cloned spreadsheet,) `USER_NAME` (set it to your stats.fm username,) `FIRST_DATE` (to the first stream date, found by comparing with a friend,) and `SERVICE_ACCOUNT_FILE` (to the path to the file Google gave you.)

## Running LevBoard
Now that config is all set up, it's time to boot up LevBoard and have it replace all of my data in your spreadsheet with your data. First, delete the contents of `songs.json` and `albums.json`, replacing them with `{}`. Then, run `main/load.py` to grab all of the songs in the spreadsheet and save them to the program files. Then, run `main/main.py` to load all of the chart weeks in to the program files and into the spreadsheet. Reload the spreadsheet page, and all of the data should pop up for you to explore.

### More LevBoard
All of the additional LevBoard functions are also in the `main/` folder. `flourish.py` will gather all of your listening data to create cumulative charts for flourish.studio. `plays.py` updates plays in the spreadsheet and updates local plays for year-end and month-end charts. `recent.py` will scan your listening history to see if there's any songs that are missing from the spreadsheet, or show any recent updates in song or certification milestones. Lastly, `stats.py` has a bunch of filter functions to explore.

## More Spreadsheet
The spreadsheet contains mostly filtered files that are built upon data the service account sends into the spreadsheet. "BOT_SONGS", "BOT_ALBUMS", "Unordered Storage", and the __-End charts ("Year-End", "Year-End Albums", "Month-End" & "Month-End Albums") are not meant to be edited by anyone other than the service account. "Song Info", "Albums" and "Album Info" are where song, album, and image info are stored, respectively. "Recent" shows the latest top 20 of both song and album charts. "Top Albums" displays best-selling albums of all time. "All Time" and "All Time Albums" display best-performing charting songs & albums. "Artists" and "Albums Artists" dispaly best-performing artists based on total song & album points across all credits. "#1 History" shows all of the #1 songs and albums. "Lev Sheet" provides a organized way to view data if you'd like to create a [Lev Sheet](https://www.figma.com/community/file/1215752424822996037/levboard-lev-sheet). "Raw" shows the most-listened to songs and best-selling songs. "Comped" displays the biggest album & song years & months, while "Year-End", "Year-End Albums", "Month-End" & "Month-End Albums" display all of those charts. "Flourish" displays the chart positions of songs & albums over time, perfect for fitting into a [Flourish Visualization](https://flourish.studio).

## Appendix: Chart Setup
This is how charts are run, in case you're curious. (Do note that I won't be changing this for anyone, but if you'd like to clone LevBoard to change it for yourself, then be my guest.) 

Every week, a song gets 10 charts points for every stream it got that week, and 2 bonus chart points for every stream it got the two weeks prior. The songs are sorted by chart points, and the top 60 songs (counting ties) recieve a linear amount of unit points depending on where they placed. (60 for #1, 59 for #2, and all the way down to 1 unit point for whatever song is at #60.)

Songs also recieve units for all of the unit points they've recieved along with all of their streams. 1 stream counts as 2 unit points. When a song reaches 100 units, it's now certified Gold, 200 units is Platinum, and 2,000 units is Diamond, with intervals every 200 units for an additonal Platinum.

Albums charts operate off of units, with albums sorted by the amount of units songs on them gained that week. Albums do not recieve unit points, and their certifications are based solely off of the total units of their songs. 500 units is the threshold for Gold, 1,000 units is for Platinum, and 10,000 units is Diamond, with albums also recieving an additional Platinum every 1,000 units.

For combining songs, I've been pretty aggressive, combining rereleases, remastered versions, live versions, and remixes. Also, if a song appears on two different albums by the same artist, it's only added to the eariler album. For this reason, I don't have any live albums or remix albums registered in the spreadsheet, as the standard version of the song came before them.

## Contact Me
If you have any questions, feel free to reach out to me on my [Charts Twitter](https://twitter.com/levboard). I am usually avaiable and happy to sort out any issues you may have. Happy charting :) 
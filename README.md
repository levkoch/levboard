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

### Adding Songs
Songs are stored in "Songs" sub-spreadsheet. The first column is the **unique** name of the song (has to be unique or else filtering doesn't work correctly,) the second column is a flag for whether it's a variant or not. The third row is the song's IDs (separated by commas,) then the sheet ID, which is shared by all the song variants and is the lowest value (text wise, so "11" goes before "2") of all the song IDs. The last manually-entered column is the song artists. The next column is stored as plaintext, but is auto-populated whenever `plays.py` is ran in spreadsheet mode, and the last two columns (for points & units) are Google Sheets functions. Make sure they're copied over for any new song row you add.

**NOTE**: For adding variants, which I do whenever there's a remix of a song or a live version that appears on a project separate from the original release, add an "X" in that row, directly following the main version. The system will automatically adjust which version of the song is the "main" version and which one are variants. You can also merge as many songs together as you'd like, just ensure all the variants appear directly below the main version and have an "X" in the second column. If you are unintersted in merging together variants, you can keep the entire "V" column blank.

| Song Title | V | Song ID | Sheet ID | Song Artists | Streams | Points | Units
| --- | --- | --- | --- | --- | --- | --- | --- |
| no tears left to cry | | 78715 | 5443449 | Ariana Grande | 850 | 4451 | 6151
| no tears left to cry - live | X | 5443449 | 5443449 | Ariana Grande | 219 | 603 | 1041
| Scared To Be Lonely | | 533774, 12145872 | 12145872 | Martin Garrix, Dua Lipa | 86 | 18 | 190
| What Was I Made For? | | 74278516 | 74278516 | Billie Eilish | 1234 | 3303 | 5771


### Adding Albums
Albums are stored in the "Albums" sub-spreadsheet ("Images" is for album images.) If you'd like to add a new album, copy another album, insert some new rows to free up space, and paste it into there. Edit the artist, name, and song name fields (just the leftmost column.) You do not need to add all of the songs into the album if you only listen to a few, but the ones that I've added all of have the album title and artists bolded. The rest of the columns will auto-populate with the current information the sheet holds. Ensure that column G also shows at least one song id, and copy over a function from the above row if the cell is blank. Column H is auto-populated by a script, so ensure that you delete any data that might have copied into there.

**NOTE**: Albums MUST be registered in the spreadsheet in order to chart. The "Top Albums" spreadsheet will tell you which songs are orphaned, and once a song reaches 200 units, I add it to an album, even if it's all by itself. Albums can also have multiple artists, which should be comma-separated. I keep the albums sorted in alphabetical order, and albums with all songs registered are bolded, but any sorting that works for you is totally okay.

<table>
  <tr>
    <td colspan="2"><b>dont smile at me</b></td>
    <td>Units:</td>
    <td>27,350</td>
    <td>Cert:</td>
    <td>27x⬥</td>
    <td colspan="2"> </td>
  </tr>
  <tr>
    <td colspan="2"><b>Billie Eilish</b></td>
    <td>Plays:</td>
    <td>5,317</td>
    <td>Points:</td>
    <td>16,716</td>
    <td> </td>
    <td>dont smile at me</td>
  </tr>
  <tr>
    <td>Song Title</td>
    <td>Plays</td>
    <td>Units</td>
    <td>Cert</td>
    <td>Peak</td>
    <td>Weeks</td>
    <td> </td>
    <td>dont smile at me</td>
  </tr>
  <tr>
    <td>COPYCAT</td>
    <td>265</td>
    <td>1,027</td>
    <td>5x▲</td>
    <td>6</td>
    <td>21</td>
    <td>585348</td>
    <td>dont smile at me</td>
  </tr>
  <tr>
    <td>dontwannabeyouanymore</td>
    <td>318</td>
    <td>1,334</td>
    <td>6x▲</td>
    <td>9<sup>3</sup></td>
    <td>26</td>
    <td>585347</td>
    <td>dont smile at me</td>
  </tr>
  <tr>
    <td colspan="8">[...]</td>
  </tr>
  <tr>
    <td>btches broken hearts</td>
    <td>1,087</td>
    <td>6,356</td>
    <td>5x▲</td>
    <td>1<sup>8</sup></td>
    <td>97</td>
    <td>822333</td>
    <td>dont smile at me</td>
  </tr>
</table>

### Deleting Unneeded Content
If you'd like to delete a song because you haven't listened to it and I have, that's also fine. (Deleting songs and albums you haven't listened to will make the system run faster.) Just make sure to delete it from any albums that it's attached to. Deleting Albums works the same way, just select the rows it occupies and remove them. 

**NOTE**: whenever deleting albums or songs, make sure to also wipe `songs.json` and `albums.json` in the data folder by deleting their contents and replacing it with the `{}` characters.

## Editing Config
The config in here is currently set to my information. The fields that need to be edited are `LEVBOARD_SHEET` (set it to the letters between `"spreadsheets/d/"` and `"/edit/"` in the URL of your cloned spreadsheet,) `USER_NAME` (set it to your stats.fm username, this also needs to be updated inside of `main/model/spotistats.py`) `FIRST_DATE` (to the first stream date, found by comparing with a friend,) and `SERVICE_ACCOUNT_FILE` (to the path to the file Google gave you.)

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

For combining songs, there are some straight up stats.fm errors (especially from the Apple Music integration) that crop up. Otherwise, sped-up, slowed-down, and other "versions" I combined into the statndard release. Live tracks that don't appear on a separate project are also conbined into the main release. Otherwise, songs from live albums, like *k bye for now (swt live)*, are listed separately as variants, and count towards their respective album with streams and also with points when the live version is the most popular that week.

## Contact Me
If you have any questions, feel free to reach out to me on my [Charts Twitter](https://twitter.com/levboard). I am usually avaiable and happy to sort out any issues you may have. Happy charting :) 
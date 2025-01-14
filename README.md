# LevBoard
This is a [Spotistats](https://stats.fm/) integration for building customizable song charts. On this version, only creating song charts is available, due to some complications that Spotistats has with album versions. For a more full experience, if you are willing to set up a spreadsheet and a free Google Service Account, then head over to the [experimental version](https://github.com/levkoch/levboard/tree/personal).

__Please Note__: Only accounts with Spotistats Plus __AND__ their files imported work, as all other accounts don't display stream counts, which the system needs to work correctly.

# How To Use (For Anyone)

_This is the explaining to anyone how-to guide, so if you know how to run a program, skip to the other [How to Use section.](#how-to-use-for-programmers)_

## Downloading the Program
__(1)__ This is code that runs on your computer, so to run it, you have to download it first. Click on the green button in the top right corner, and then select "Download ZIP", which will download a compressed copy of the script onto your computer. Find the zipped folder in your file discovery system on your computer and move the inner folder (which should be named "levboard-main") out of the zipped folder.

## Configuring Your Username
__(2)__ Find / update your Spotistats username. They are automatically set to whatever Spotify auto-generates your username to be, but they are unwieldy. Navigate to the [Spotistats account page](https://stats.fm/account), sign into your account, and change your custom url to something nice. You'll need it soon to run the program.

## Downloading Python
__(3)__ In order to run the files, your computer needs to have Python (the language the program is written in) installed. Download it from the [official Python website](https://www.python.org/downloads/), and follow any instructions. Make sure that you download either the version called "Python 3.9" or "Python 3.10", as older versions may not work properly.

## Installing Dependencies
__(4)__ The program requires code from outside the system for it to work, and it's installed using the `pip` program that comes with Python. The first command updates your pip program, and the second will install the outside code needed for the program. Open up Command Prompt (on Windows) or Terminal (on Mac) and type in the first line, hit enter, and then type in the second line and hit enter again. The system should show that it is installing and updating pip and the programs needed for levboard to run.

```console
python -m pip install --upgrade pip
pip install -r requirements.txt  
```

## Executing the Program
__(5a)__ Navigate to where you moved the file inside of your command line tool. I saved the program files to the `Documents` folder, so move to there, and into the `levboard-main` folder as well. The command tool should display `levboard-main` as the last folder in your path on the left, as shown on the second line.

```console
C:\your\path> cd Documents\levboard-main
C:\your\path\Documents\levboard-main>
```
__(5b)__ From there, execute the `main.py` program from the command line tool. When using the program for the first time, you need to specify your Spotistats username from step 2. Afterwards, it's not necessary, as the program will save your username.

```console
C:\your\path\Documents\levboard-main> python main.py lev
```

__(5c)__ The program also accepts a third option, specifying if you want the songs to be lazily named or not. Running the program as `python main.py {username} f` will  prompt you to name all the songs. Running the program later with `python main.py {username} t`(or any other letter at the end) will revert to lazy naming and will not prompt you to name any of the new songs. If you want to configure settings manually, you can change them in the `data/settings.json` file.

```console
C:\your\path\Documents\levboard-main> python main.py lev f
```

## Naming New Songs (Non-Lazy Naming)

__(6a)__ When prompted for a song name, type in the name that you wanted the song to be called at the prompt. 

```text
Song Secret Love Song (feat. Jason Derulo) (283072) not found.
Find the link here -> https://stats.fm/track/283072
What should the song be called in the database? Secret Love Song
```

__(6b)__ If you press enter without giving a name, it will name the song whatever it already has displayed for you (the same as lazy naming the songs.) 

```text
Song Yikes (163325) not found.
Find the link here -> https://stats.fm/track/163325
What should the song be called?
```

__(6c)__ There is also a merge option to merge two track ids together into one song. To merge a new track into an already existing one on the system, type in `merge`. Then, specify the song id of the track to merge into, which you can find by going to the `data\songs.json` file and then searching for the song title using any word processing tool, like Notepad, and they will be merged into one song. (This is helpful if a song has multiple names that are one song, like a remastered and original version.)

```text
Song Bad - 2012 Remastered (1016605) not found.
Find the link here -> https://stats.fm/track/1016605
What should the song be called in the database? merge
Id of the song to merge with: 43009
Sucessfully merged Bad - 2012 Remastered into Bad
```

## Running The Program
__(7)__ While the program is running, it should display your data for your song weeks like this. Don't close the command line terminal, it should take around a minute or two to comb through all your weeks.

```text
(2) Week of 2021-05-26 to 2021-06-09
 MV | Title                                         | Artists                                       | TW | LW | OC | PLS | PK
▲39 | I Would                                       | One Direction                                 | 1  | 40 | 2  | 6   | 1
NEW | We Are Never Ever Getting Back Together       | Taylor Swift                                  | 1  | -  | 1  | 6   | 1
NEW | Domino                                        | Jessie J                                      | 3  | -  | 1  | 5   | 3
NEW | Neon Lights                                   | Demi Lovato                                   | 3  | -  | 1  | 5   | 3
```

## Accessing Your Data
__(8)__ Once it's done, it will create a `songs.csv` file in the root directory of the package. Load them into your favorite spreadsheet processing tool & enjoy your data. (Select "Split Text to Columns" after copy & pasting it if using Google Sheets.)

## To See Extra Stats
__(9)__ Once you have ran the `main.py` program, you can also run the `stats.py` program located in the same directory, and it will display various stats about your songs, including your top songs all time (do this by running the first command.) I suggest sending the output to a text file so you can read it later (by running the second command in the same directory).

```console
python stats.py
python stats.py > info.txt
```

# How To Use (For Programmers)

_This is for people who have done some surface-level programming and understand how running a program works._

## Downloading the Code
__(1)__ Clone the repository onto your machine. (Click on "Clone" and then either "Open in Github Desktop" or "Download ZIP", whichever you like better.) If you downloaded the ZIP folder version, make sure to un-compress it, or else it won't work.

## Configuring Your Username
__(2)__ Find your Spotistats username. They are automatically set to whatever Spotify auto-generates your username to be, but they are unwieldy. Navigate to the [Spotistats account page](https://stats.fm/account), sign into your account, and change your custom url to something nice. Remember it for later on in the process.

## Downloading Python
__(3)__ If you don't have Python downloaded already, install it from the [official Python website](https://www.python.org/downloads/). The program is written in Python 3.9, so it or any later release will work.

## Installing Dependencies
__(4)__ Install dependencies with pip through a command terminal. It's recomended to always upgrade your pip before downloading anything new, and then download the three non-standard library dependencies of levboard from the `requirements.txt` file.

```console
python -m pip install --upgrade pip
pip install -r requirements.txt  
```

## Running the Program
__(5a)__ Navigate to the root directory of this package, and then run the `main.py` file. When using the program for the first time, you will need to specify your Spotistats username that you created in part 2 (example one.) 

```console
python main.py lev
```

__(5b)__ The program also accepts a third argument, specifying if you want the songs to be lazily named or not. Running the program as `python main.py {username} f` will prompt you to name all the songs (example two.) Running the program later with `python main.py {username} t`(or any other letter at the end) will revert to lazy naming and will not prompt you to name any of the new songs. If you want to configure settings manually, you can change them in the `data/settings.json` file.

```console
python main.py lev f
```

## Song Naming (Non-Lazy Naming)
__(6a)__ When prompted for a song name, type in the name that you wanted the song to be called at the prompt.

```text
Song Secret Love Song (feat. Jason Derulo) (283072) not found.
Find the link here -> https://stats.fm/track/283072
What should the song be called in the database? Secret Love Song
```

__(6b)__ If you press enter without giving a name, it will name the song whatever it already has displayed for you (the same as lazy naming the songs.) 

```text
Song Yikes (163325) not found.
Find the link here -> https://stats.fm/track/163325
What should the song be called?
```

__(6c)__ There is also a merge option to merge two track ids together into one song. To merge a new track into an already existing one on the system, type in `merge`. Then, specify the song id of the track to merge into, which you can find by going to the `data\songs.json` file and then searching for the song title using any word processing tool, like Notepad, and they will be merged into one song. (This is helpful if a song has multiple names that are one song, like a remastered and original version.)

```text
Song Bad - 2012 Remastered (1016605) not found.
Find the link here -> https://stats.fm/track/1016605
What should the song be called in the database? merge
Id of the song to merge with: 43009
Sucessfully merged Bad - 2012 Remastered into Bad
```

## Running The Program
__(7)__ While the program is running, it should display your data for your song weeks as shown in the example below. Don't close the command line terminal, it should take around a minute or two to comb through all your weeks. 

```text
(2) Week of 2021-05-26 to 2021-06-09
 MV | Title                                         | Artists                                       | TW | LW | OC | PLS | PK
▲39 | I Would                                       | One Direction                                 | 1  | 40 | 2  | 6   | 1
NEW | We Are Never Ever Getting Back Together       | Taylor Swift                                  | 1  | -  | 1  | 6   | 1
NEW | Domino                                        | Jessie J                                      | 3  | -  | 1  | 5   | 3
NEW | Neon Lights                                   | Demi Lovato                                   | 3  | -  | 1  | 5   | 3
```

## Accessing Your Data
__(8)__ Once it's done, it will create a `songs.csv` file in the root directory of the package. Load them into your favorite spreadsheet processing tool & enjoy your data. (Select "Split Text to Columns" after copy & pasting it if using Google Sheets.)

## To See Extra Stats
__(9)__ Once you have ran the `main.py` program, you can also run the `stats.py` program located in the same directory, and it will display various stats about your songs, including your top songs all time. I suggest sending the output to a text file so you can read it later.

```console
python stats.py
python stats.py > info.txt
```

# Contact Me
If you have any issues with the code, feel free to ask me over on my [charts twitter](https://twitter.com/levboard) where I post the charts created from the experimental version of this program. I love them and am currently working on making albums work for people other than me. If you want to help me crowdsource that data or want to contribute to it let me know, your help would be greatly appreciated.

# levboard
A [Spotstats](stats.fm) integration for building customizable song charts.
Currently, only creating song charts is avaliable, due to some complications 
that Spotistats has with albums. 
Please Note: Only accounts with Spotistats Plus __AND__ their files imported work, 
as other accounts don't display stream counts, and the system needs those.

## How To Use (Not a Programmer)

## How To Use (Done Some Programming)
1. Clone the repository onto your machine. (Click on "Clone" and then 
either "Open in Github Desktop" or "Download ZIP", whichever you like better.) If 
you downloaded the ZIP folder version, make sure to un-compress it, or else it 
won't work.

2. Find your Spotistats username. They are automatically set to whatever Spotify 
auto-generates your username to be, but they are unwieldy. Navigate to the 
[Spotistats account page](https://stats.fm/account) and change your custom 
url to something nice.

3. If you don't have Python downloaded already, install it from the 
[official Python website](https://www.python.org/downloads/). The program is 
written in Python 3.9, but it or any later release will work.

4. Install dependencies with pip through a command terminal. First off, it's best 
to always upgrade your pip before downloading anything new, and then download the 
three non-standard library dependencies of levboard from the `requirements.txt` file.
```console
python -m pip install --upgrade pip
pip install -r requirements.txt  
```

5. Navigate to the root directory of this package, and then run the `main.py` file. 
When using the program for the first time, you will need to specify your Spotistats 
username that you specified in part 2.
```console
python main.py lev
```
The program also accepts a third argument, specifying if you want the songs to be 
lazily named or not. Running the program as `python main.py {username} f` will  prompt 
you to name all the songs. Running the program later with `python main.py {username} t`
(or any other letter at the end) will revert to lazy naming and will not prompt you to 
name any of the new songs. If you want to configure settings manually, you can change 
them in the `data/settings.json` file.

5b. (Optional) Non-lazy naming: When prompted for a song name, type in the name that you 
wanted the song to be called at the prompt. If you press enter, it will name the song 
whatever it already has displayed for you (the same as lazy naming the songs.) There 
is also a merge option, to merge two track ids together into one song. Then, specify 
the song id of the track to merge into, and they will be merged into one song. (This 
is helpful if a song has multiple names that are one song, like a remastered and 
original version.)
```text
Song Secret Love Song (feat. Jason Derulo) (283072) not found.
Find the link here -> https://stats.fm/track/283072
What should the song be called in the database? Secret Love Song
```

6. While the program is running, it should display your data for your song weeks like this:
```text
(2) Week of 2021-05-26 to 2021-06-09
 MV | Title                                         | Artists                                       | TW | LW | OC | PLS | PK
▲39 | I Would                                       | One Direction                                 | 1  | 40 | 2  | 6   | 1
NEW | We Are Never Ever Getting Back Together       | Taylor Swift                                  | 1  | -  | 1  | 6   | 1
NEW | Domino                                        | Jessie J                                      | 3  | -  | 1  | 5   | 3
NEW | Neon Lights                                   | Demi Lovato                                   | 3  | -  | 1  | 5   | 3
```
Don't close the command line terminal, it should take around a minute or two to comb through 
all your weeks. Once it's done, it will create a `songs.csv` file in the root directory of 
the package. You can then use the "Import Data" feature in Excel to import the data into Excel, 
or copy the entire contents of the file, and paste them into Google Sheets. Then select "Split 
Text to Columns" and you now have your data in your favorite spreadsheet program.

7. Once you have ran the `main.py` program, you can also run the `stats.py` program located in 
the same directory, and it will display various stats about your songs, including your top songs 
all time. I suggest sending the output to a text file so you can read it later.
```console
python stats.py
python stats.py > info.txt
```
# LevBoard
This is a [Spotistats](https://stats.fm/) integration for building customizable song charts. Currently, only creating song charts is avaliable, due to some complications that Spotistats has with album versions. 

This is the version for web deployment. To use LevBoard on your computer (which gives you access to a whole lot more data)

__Please Note__: Only accounts with Spotistats Plus __AND__ their files imported work, as all other accounts don't display stream counts, which the system needs to work correctly.

# Running Locally:

_This is the explaining to anyone how-to guide, so if you know how to run a program, skip to the other [How to Use section.](#how-to-use-for-programmers)_

## Downloading the Program
__(1)__ This is code that runs on your computer, so to run it, you have to download it first. Click on the green button in the top right corner, and then select "Download ZIP", which will download a compressed copy of the script onto your computer. Find the zipped folder in your file discovery system on your computer and move the inner folder (which should be named "levboard-main") out of the zipped folder.

## Configuring Your Username
__(2)__ Find / update your Spotistats username. They are automatically set to whatever Spotify auto-generates your username to be, but they are unwieldy. Navigate to the [Spotistats account page](https://stats.fm/account), sign into your account, and change your custom url to something nice. You'll need it soon to run the program.

## Installing Dependencies
__(4)__ All dependencies for the program are in `requirements.txt`, so you can install them with pip, (and upgrade it just in case a new version came out as well.)

```console
python -m pip install --upgrade pip
pip install -r requirements.txt  
```

# Contact Me
If you have any issues with the code, feel free to ask me over on my [twitter](https://twitter.com/levsnasty) where I post the charts created from the experimental version of this program. I am currently working on bringing these charts to the web so you can view them directly in your browser.
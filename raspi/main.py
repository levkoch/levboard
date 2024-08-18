"""
functions for the raspberry pi until i figure out what i'll actaully
be doing with it.

raspberry pi lives at 192.168.5.63

PACKAGES INSTALLED:
- rpi.lgpio (it's some sort of port)
- google-api-python-client
- pillow
- mfrc522

rfid chip connections:
sda    brown    24
sck    red      23
mosi   orange   19
miso   yellow   21
irq    blank    
gnd    green    20  
rst    blue     22
3.3v   purple   17

display connections:
vcc    grey     17 
gnd    brown    20
din    blue     19
clk    yellow   23
cd     orange   24
dc     green    22
rst    white    11
busy   purple   18
"""

import math
import time
import json
import sys
import RPi.GPIO as GPIO

from PIL import Image, ImageDraw, ImageFont

from mfrc import  MFRC
from epd import EPD

from config import COLLECTION_SHEET, LEVBOARD_SHEET, RECORDS_FILE, DATA_DIR

# since the google libraries are a nightmare to install for some reason
from ..main.spreadsheet import Spreadsheet

WHITE = '#FFFFFF'
LGRAY = '#C0C0C0'
DGRAY = '#808080'
BLACK = '#000000'

FONT_8 = ImageFont.truetype(DATA_DIR + '/image/minecraftia.ttf', 8)
FONT_16 = ImageFont.truetype(DATA_DIR + '/image/minecraftia.ttf', 16)
FONT_24 = ImageFont.truetype(DATA_DIR + '/image/minecraftia.ttf', 24)


def _check_peak(peak: str) -> str:
    convert = [
        ('¹', '_1'),
        ('²', '_2'),
        ('³', '_3'),
        ('⁴', '_4'),
        ('⁵', '_5'),
        ('⁶', '_6'),
        ('⁷', '_7'),
        ('⁸', '_8'),
        ('⁹', '_9'),
        ('⁰', '_0'),
    ]

    if any(char in peak for char in '⁰¹²³⁴⁵⁶⁷⁸⁹'):
        for (start, end) in convert:
            peak = peak.replace(start, end)

        peak = peak.split('_')[0] + '(' + ''.join(peak.split('_')[1:]) + ')'

    return peak


def update_records_info():
    collection = Spreadsheet(COLLECTION_SHEET)
    levboard = Spreadsheet(LEVBOARD_SHEET)

    albums_info: dict[str, dict[str, str]] = {}
    for row in levboard.get_range("'Top Albums'!A2:J").get('values'):
        (
            place,
            album,
            _,  # C artist
            _,  # D year
            units,
            _,  # F certification
            plays,
            points,
            weeks,
            peak,
        ) = row

        albums_info[album] = {
            'place': int(place.replace(',', '')),
            'units': int(units.replace(',', '')),
            'plays': int(plays.replace(',', '')),
            'points': int(points.replace(',', '')),
            # the weeks are the one item that shows as "-" when it's 0,
            # so we have to convert that into an numeric value
            'weeks': int(weeks.replace(',', '').replace('-', '0')),
            'peak': _check_peak(peak),
        }

    songs_info = {}
    for row in levboard.get_range("'All Time'!A3:P").get('values'):
        (
            song,
            _,  # B artist
            points,
            place,
            _,  # E sheet id
            _,  # F #1 weeks
            _,  # G top 3 weeks
            _,  # H top 5 weeks
            _,  # I top 10 weeks
            _,  # J top 20 weeks
            _,  # K top 30 weeks
            weeks,
            peak,
            _,  # N chart plays
            plays,
            units,
        ) = row

        # since the all time sheet fills in blank values when there isn't a
        # song specified, we skip all the ones without a song specified
        if not song:
            continue

        songs_info[song] = {
            'place': int(place.replace(',', '')),
            'units': int(units.replace(',', '')),
            'plays': int(plays.replace(',', '')),
            'points': int(points.replace(',', '')),
            # the weeks are the one item that shows as "-" when it's 0,
            # so we have to convert that into an numeric value
            'weeks': int(weeks.replace(',', '').replace('-', '0')),
            'peak': _check_peak(peak),
        }

    chart_rows = [
        row
        for row in levboard.get_range('BOT_ALBUMS!B5:K550').get('values')
        # google sheets returns just a [] for blank rows so filter those out
        # and also filter out all the header rows
        if row and row[2].isnumeric()
    ]
    current_week = int(chart_rows[0][9])  # bot_albums!K5
    current_rows = [row for row in chart_rows if int(row[9]) == current_week]
    current_albums = [row[0] for row in current_rows]
    chart_rows = [
        (int(position), title, int(week))
        for (title, _, position, _, _, _, _, _, _, week) in chart_rows
    ]

    records = {}
    for row in collection.get_range('COLLECTION!A2:K').get('values'):
        (
            rfid,
            artist,
            title,
            format,
            details,
            speed,
            year,
            levboard_type,
            levboard_title,
            discogs,
            upc,
        ) = row
        levboard_info: dict[str, str] = {
            'type': levboard_type,
            'title': levboard_title,
        }

        # albums without a levboard equivalent (like compilations and
        # singles that i bought physical copies of but that didn't chart)
        # are registered as "NONE"
        if levboard_title != 'NONE':
            info_pool = albums_info if levboard_type == 'Album' else songs_info
            info_field = info_pool.get(levboard_title)

            if info_field is None:   # no match so it was merged wrong
                print(f'Unable to find levboard item named {levboard_title}')
            else:
                levboard_info.update(info_field)

            if levboard_title in current_albums:
                album_row = next(
                    row for row in current_rows if row[0] == levboard_title
                )

                positions = []
                for chart_week in range(current_week - 15, current_week + 1):
                    positions.append(
                        next(
                            (
                                row[0]
                                for row in chart_rows
                                if row[1] == levboard_title
                                and row[2] == chart_week
                            ),
                            None,
                        )
                    )

                levboard_info['current'] = {
                    'units': album_row[6],
                    'plays': album_row[7],
                    'points': album_row[8],
                    'positions': positions[::-1],
                }

        records[rfid] = {
            'rfid': rfid,
            'artist': artist,
            'title': title,
            'format': format,
            'details': details,
            'speed': speed,
            'year': year,
            'discogs': discogs,
            'upc': upc,
            'levboard': levboard_info,
        }

    with open(RECORDS_FILE, 'w', encoding='UTF-8') as f:
        json.dump(records, f, indent=4)


def get_record(rfid: str) -> dict:
    with open(RECORDS_FILE, 'r', encoding='UTF-8') as f:
        return json.load(f).get(rfid)


def create_album_image(info: dict) -> Image:
    print(info)

    chart = info['levboard']
    current = chart['current']

    display = Image.open(image_dir + '/blank_display.png')
    draw = ImageDraw.Draw(display)

    draw.rectangle(((12, 12), (38, 38)), fill=BLACK)
    draw.text((18, 9), str(current['positions'][0]), font=FONT_24, fill=WHITE)
    draw.text((44, 9), info['title'].lower(), font=FONT_16, fill=BLACK)
    draw.text((44, 29), info['artist'].lower(), font=FONT_8, fill=BLACK)

    units_offset = 2 - math.floor(math.log10(int(current['units'])))
    plays_offset = 2 - math.floor(math.log10(int(current['plays'])))
    points_offset = 2 - math.floor(math.log10(int(current['points'])))

    draw.text(
        (32 + 12 * units_offset, 44),
        current['units'],
        font=FONT_16,
        fill=BLACK,
    )
    draw.text(
        (106 + 12 * plays_offset, 44),
        current['plays'],
        font=FONT_16,
        fill=BLACK,
    )
    draw.text(
        (196 + 12 * points_offset, 44),
        current['points'],
        font=FONT_16,
        fill=BLACK,
    )

    draw.text((76, 96), f'{chart["units"]:,}', font=FONT_8, fill=BLACK)
    draw.text((76, 106), f'{chart["plays"]:,}', font=FONT_8, fill=BLACK)
    draw.text((170, 96), chart['peak'], font=FONT_8, fill=BLACK)
    draw.text((170, 106), info['year'], font=FONT_8, fill=BLACK)
    draw.text((244, 96), str(chart['weeks']), font=FONT_8, fill=BLACK)
    draw.text((244, 106), str(chart['place']), font=FONT_8, fill=BLACK)

    for offset, position in enumerate(current['positions']):
        if position is None:
            draw.rectangle(
                ((13 + offset * 17, 70), (27 + offset * 17, 84)), outline=LGRAY
            )
            draw.line(
                ((18 + offset * 17, 77), (22 + offset * 17, 77)), fill=LGRAY
            )
            continue

        if position < 4:
            fill = LGRAY
            text = BLACK

            if position == 1:
                fill = BLACK
                text = WHITE

            draw.rectangle(
                ((13 + offset * 17, 70), (27 + offset * 17, 84)), fill=fill
            )
            draw.text(
                (18 + offset * 17, 72), str(position), font=FONT_8, fill=text
            )
            continue

        draw.rectangle(
            ((13 + offset * 17, 70), (27 + offset * 17, 84)), outline=LGRAY
        )
        draw.text(
            ((15 if position > 9 else 18) + offset * 17, 72),
            str(position),
            font=FONT_8,
            fill=BLACK,
        )

    return display

    with open('C:/Users/levpo/Downloads/trial.png', 'wb') as f:
        display.save(f, format='png')


def display_image(image: Image):
    epd = EPD()
    epd.Init_4Gray()
    epd.display_4Gray(epd.getbuffer_4Gray(image))

    time.sleep(10)

    epd.init()
    epd.Clear(0xFF)
    epd.sleep()

def collect_rfid_tag():
    try:
        reader = MFRC()
        print("created reader, awaiting scan")
        tag = reader.read_id()
        print(f'found id: {tag}')
    finally:
        GPIO.cleanup()


if __name__ == '__main__':
    # collect_rfid_tag()
    # update_records_info()
    record = str(sys.argv[1]) if len(sys.argv) > 1 else '30014'
    display_image(create_album_image(get_record(record)))

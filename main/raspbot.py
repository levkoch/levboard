"""functions for the raspberry pi until i figure out what i'll actaully be doing with it."""

import time
import json
# from waveshare.epd import EPD
from PIL import Image, ImageDraw, ImageFont

from config import COLLECTION_SHEET, LEVBOARD_SHEET, RECORDS_FILE, image_dir

# since the google libraries are a nightmare to install for some reason
# from spreadsheet import Spreadsheet


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
            'peak': peak,
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
            'peak': peak,
        }

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


def create_image_trial():
    # epd = EPD()
    # epd.Init_4Gray()

    WHITE = "#FFFFFF"
    LGRAY = "#C0C0C0"
    DGRAY = "#808080"
    BLACK = "#000000"

    """
    example = Image.open(image_dir + '/example_display.png')
    epd.display_4Gray(epd.getbuffer_4Gray(example))
    time.sleep(10)
    """
    # epd.init()
    # epd.Clear(0xFF)

    # epd.Init_4Gray()
    font_8 = ImageFont.truetype(image_dir + '/minecraftia.ttf', 8)
    font_16 = ImageFont.truetype(image_dir + '/minecraftia.ttf', 16)
    font_24 = ImageFont.truetype(image_dir + '/minecraftia.ttf', 24)

    display = Image.open(image_dir + '/blank_display.png')
    # epd.display_4Gray(epd.getbuffer_4Gray(display))

    draw = ImageDraw.Draw(display)
    draw.rectangle(((12, 12), (38, 38)), fill=BLACK)
    draw.text((18, 9), '2', font=font_24, fill=WHITE) #at 18, 13 on figma
    # epd.display_4Gray(epd.getbuffer_4Gray(display))

    draw.text((44, 9), 'hit me hard and soft', font=font_16, fill=BLACK) # at
    draw.text((44, 29), 'billie eilish', font=font_8, fill=BLACK)

    draw.text()

    with open("C:/Users/levpo/Downloads/trial.png", "wb") as f:
        display.save(f, format="png")
    #epd.display_4Gray(epd.getbuffer_4Gray(display))
    # time.sleep(10)

    """
    Limage = Image.new('L', (epd.height, epd.width), 0)  # 255: clear the frame
    draw = ImageDraw.Draw(Limage)
    draw.text((0, 0), '3', font=font35, fill=epd.GRAY1)
    draw.text((20, 105), 'hello world', font=font18, fill=epd.GRAY1)
    draw.line((160, 10, 210, 60), fill=epd.GRAY1)
    draw.line((160, 60, 210, 10), fill=epd.GRAY1)
    draw.rectangle((160, 10, 210, 60), outline=epd.GRAY1)
    draw.line((160, 95, 210, 95), fill=epd.GRAY4)
    draw.line((185, 70, 185, 120), fill=epd.GRAY1)
    draw.arc((160, 70, 210, 120), 0, 360, fill=epd.GRAY1)
    draw.rectangle((220, 10, 270, 60), fill=epd.GRAY1)
    draw.chord((220, 70, 270, 120), 0, 360, fill=epd.GRAY1)

    epd.display_4Gray(epd.getbuffer_4Gray(Limage))
    """

    # epd.init()
    # epd.Clear(0xFF)

    # epd.sleep()


if __name__ == '__main__':
    # update_records_info()
    create_image_trial()

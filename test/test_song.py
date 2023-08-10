import pytest

from ..main.src.model import Song


def test_song_image_link_single_image():
    # no tears left to cry single link from spotify
    expected_link = (
        'https://i.scdn.co/image/ab67616d0000b27365d28ba9f50b2eba46ffc55c'
    )
    ntltc = Song('78715', 'no tears left to cry')
    assert ntltc.image == expected_link


def test_song_image_links_album_image():
    # positions album link from spotify
    expected_link = (
        'https://i.scdn.co/image/ab67616d0000b2736484dfce3cc12e68d8aa2e55'
    )
    nasty = Song('533701', 'nasty')
    assert nasty.image == expected_link

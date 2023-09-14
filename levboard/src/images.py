"""
Collects the song images from the yaml file so that they can be used
to create song instances later on.

class:
* SongImage: A dataclass containing information about a song skeleton.

functions:
* load_song_images(): Loads all the song images from the file for use.
"""

import yaml

from pydantic import BaseModel, validator
from typing import Any, Literal, Union
from model import Credits


class _SongImageVersion(BaseModel):
    name: str
    id: str
    artists: Credits
    type: Literal['alternate', 'remix']


class SongImage(BaseModel):
    name: str
    standard: str   # main id
    artists: Credits
    ids: set[str]
    image: str = 'MISSING'
    versions: list[_SongImageVersion] = []

    @validator('artists')
    def turn_credits_into_models(cls, artists: Union[list[dict], list[tuple], Credits]):
        if isinstance(artists, Credits):
            return artists
        return Credits(artists)

    @validator('versions', each_item=True)
    def turn_versions_into_models(
        cls, version: Union[dict, _SongImageVersion]
    ):
        if isinstance(version, _SongImageVersion):
            return version
        if not 'artists' in version:
            version['artists'] = cls.artists
        return _SongImageVersion(**version)


DEFAULT_FILE_PATH = 'levboard/data/songs.yml'


def load_song_images(file: str = DEFAULT_FILE_PATH) -> dict[str, SongImage]:
    """
    Collects song images from the yaml file and converts them into song
    images for usage.

    What the yaml is supposed to look like to declare a song image:
    ```yaml
    '5748569': # same as "standard" main id
      artists:
      - name: 19716 Tyga
        type: main
      - name: 11619 Nicki Minaj
        type: main
      ids:
      - '10020996'
      - '5748569'
      image: https://i.imgur.com/IaNzbEh.png
      name: Dip
      standard: '5748569'
      versions:
      - id: '10020996'
          name: Dip
          type: alternate
    ```
    """

    collection: dict[str, SongImage] = {}

    with open(file, 'r') as fp:
        images: dict[str, dict[str, Any]] = yaml.safe_load(fp)

    for (main_id, image_dict) in images.items():
        image = SongImage(**image_dict)
        collection[main_id] = image
        for alternate_id in image.ids ^ {main_id}:
            collection[alternate_id] = image

    return collection

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

    class Config:
        arbitrary_types_allowed = True

    @validator('artists', pre=True)
    def turn_credits_into_models(
        cls, artists: Union[list[dict], list[tuple], Credits]
    ):
        if isinstance(artists, Credits):
            return artists
        return Credits(artists)

    def to_dict(self):
        return {
            'name': self.name,
            'id': self.id,
            'artists': self.artists.to_list(),
            'type': self.type,
        }


class SongImage(BaseModel):
    name: str
    standard: str   # main id
    artists: Credits
    ids: set[str]
    image: str = 'MISSING'
    versions: list[_SongImageVersion] = []

    class Config:
        arbitrary_types_allowed = True

    @validator('artists', pre=True)
    def turn_credits_into_models(
        cls, artists: Union[list[dict], list[tuple], Credits]
    ):
        if isinstance(artists, Credits):
            return artists
        credits = Credits(artists)
        cls.latest_credits = credits
        return credits

    @validator('versions', pre=True, each_item=True)
    def turn_versions_into_models(
        cls, version: Union[dict, _SongImageVersion]
    ):
        if isinstance(version, _SongImageVersion):
            return version
        if not 'artists' in version:
            version['artists'] = cls.latest_credits
        return _SongImageVersion(**version)

    def to_dict(self):
        info = {
            'name': self.name,
            'standard': self.standard,
            'artists': self.artists.to_list(),
            'ids': list(self.ids),
            'image': self.image,
        }
        if self.versions:
            info['versions'] = [v.to_dict() for v in self.versions]
        return info


DEFAULT_FILE_PATH = 'levboard/data/songs.yml'
PARSED_FILE_PATH = 'levboard/data/parsedsongs.yml'


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


def ingest_song_images():
    """
    Collect any images from the songs file and then process them into the
    nicest machine form and dump them into the parsedsongs file.
    """
    
    images = load_song_images()
    info = {image.standard: image.to_dict() for image in images.values()}
    with open(PARSED_FILE_PATH, 'w') as f:
        yaml.dump(info, f)

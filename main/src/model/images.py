"""
Collects the song images from the yaml file so that they can be used
to create song instances later on.
"""

import yaml

from pydantic import BaseModel, validator
from typing import Any, Literal, Union


class _SongImageVersion(BaseModel):
    name: str
    id: str
    artists: list[str]
    type: Literal['alternate', 'remix']


class SongImage(BaseModel):
    name: str
    standard: str   # main id
    ids: set[str]
    image: str = 'MISSING'
    versions: list[_SongImageVersion] = []

    @validator('versions', each_item=True)
    def turn_versions_into_models(version: Union[dict, _SongImageVersion]):
        if isinstance(version, _SongImageVersion):
            return version
        return _SongImageVersion(**version)


def load_song_images() -> dict[str, SongImage]:
    """
    Collects song images from the yaml file and converts them into song
    images for usage.

    What the yaml is supposed to look like to declare a song image:
    ```yaml
    '10020996': # same as "standard" main id
        artists:
        - Tyga
        - Nicki Minaj
        ids:
        - '10020996'
        - '5748569'
        image: https://i.imgur.com/IaNzbEh.png
        name: Dip
        standard: '10020996' # main id
        versions:
        - artists:
          - Tyga
          - Nicki Minaj
          id: '5748569'
          name: Dip (feat. Nicki Minaj)
          type: alternate
    ```
    """

    collection: dict[str, SongImage] = {}

    with open('data/songimages.py', 'r') as fp:
        images: dict[str, dict[str, Any]] = yaml.load(fp)

    for (main_id, image_dict) in images.values():
        image = SongImage(**image_dict)
        collection[main_id] = image
        for alternate_id in image.ids ^ {main_id}:
            collection[alternate_id] = image

    return collection

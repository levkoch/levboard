import pathlib
from typing import Final

# where my google sheet is located at
LEVBOARD_SHEET: Final[str] = '1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk'
# where my collection sheet is located at
COLLECTION_SHEET: Final[str] = '1RG6msaBX0Ysfx72yvdJ-Q14x-YZP_0YQpQYZThObJrA'

# find path of where the __main__ program was run
data_dir = pathlib.Path().resolve().as_posix()

# so if someone ran that program inside of levboard/raspi
if data_dir.endswith('/raspi'):
    data_dir = data_dir[:-6]  # remove "/raspi"
data_dir += '/data'

DATA_DIR: Final[str] = data_dir

RECORDS_FILE: Final[str] = data_dir + '/records.json'
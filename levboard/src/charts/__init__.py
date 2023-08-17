# overall chart things that we need for all
from datetime import datetime

from ..storage import Process
from .chart_util import SONG_ROW_HEADERS
from .original_charts import original_charts
from .points_charts import points_charts


def clear_entries(process: Process) -> None:
    print('Clearing previous entries.')
    for song in process.songs:
        song._entries.clear()


def create_song_chart(process: Process) -> list:
    username = process.config.username
    print(f'Finding song data for {username}.')
    clear_entries(process)

    start_time = datetime.now()

    if process.config.use_points:
        info = points_charts(process)
    else:
        info = original_charts(process)

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')

    return SONG_ROW_HEADERS + [['']] + info

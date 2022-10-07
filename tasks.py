"""
This is our Makefile type of thing, allowing programs to be
executed in simplified ways through the terminal.
"""

import invoke


@invoke.task
def load(c):
    """
    Load songs and albums from spreadsheet into system.
    """
    result = c.run('python main/load.py')
    print(result)
    # c.run("python main/load_album.py")

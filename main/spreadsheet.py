"""
main/spreadsheet.py

A class to manipulate Google Sheets data.

Class:
* `Spreadsheet`: A Google Sheets spreadsheet.
"""

from typing import Any
from google.oauth2 import service_account
from googleapiclient import discovery

from config import SERVICE_ACCOUNT_FILE


class Spreadsheet:
    """
    A google sheets access class, to be able to send data to files from python directly.

    Arguments:
    * sheet_id (`str`): The ID of the sheet the instance should manipulate.
    * cred_file (optional `str`): Path to the google_token.json file. Defaults
        to the one that it should be right now but who knows.
    """

    __slots__ = ['sheet', '_sheet_id', '_credentials']

    def __init__(self, sheet_id: str, cred_file: str = SERVICE_ACCOUNT_FILE):
        self._sheet_id = sheet_id
        self._get_credentials(cred_file)
        self._attach_sheet()

    def _get_credentials(self, cred_file: str) -> None:
        """Internal method to bind google sheets credentials to the instance from the file."""

        self._credentials = (
            service_account.Credentials.from_service_account_file(
                cred_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets'],
            )
        )

    def _attach_sheet(self) -> None:
        """
        Internal method to grant the instance access to the google sheets
        resource.
        """

        service: discovery.Resource = discovery.build(
            'sheets',
            'v4',
            credentials=self._credentials,
            cache_discovery=False,
        )
        self.sheet: discovery.Resource = service.spreadsheets().values()

    def delete_range(self, range: str) -> dict[str, Any]:
        """
        Clears the specified range in the sheet.

        Argument:
        * range (`str`): The *FULL* range name, with the sheet name,
            to be cleared.

        Returns:
        * response (`dict`): The google API response dictionary.
        """

        response = self.sheet.clear(
            spreadsheetId=self._sheet_id, range=range, body={}
        ).execute()

        return response

    def get_range(self, range: str) -> dict[str, Any]:
        """
        Finds the specified range in the sheet.

        Argument:
        * range (`str`): The *FULL* range name, with the sheet name, to be found.

        Returns:
        * response (`dict`): The google API response dictionary. The 'values'
            field contains the fields (in list of lists) form that were requested
            if the request was sucessful.
        """

        result = self.sheet.get(
            spreadsheetId=self._sheet_id, range=range
        ).execute()

        return result

    def update_range(
        self, range_: str, values: list[list], chunk_size: int = 4000
    ) -> list[dict[str, Any]]:
        """
        Updates the specified range in the sheet, chunking large writes to
        avoid oversized requests that can trigger SSL/connection errors.

        Arguments:
        * range (`str`): The *FULL* range name, with the sheet name, to be found.
        * values (`list[list]`): The values to insert in the specified range.
        * chunk_size (`int`): Max rows per request. Defaults to 4000.

        Returns:
        * responses (`list[dict]`): One google API response dict per chunk.
        """

        sheet_name, cell_range = range_.split('!')
        start_cell, end_cell = cell_range.split(':')
        start_letters = ''.join(c for c in start_cell if c.isalpha())
        end_letters = ''.join(c for c in end_cell if c.isalpha())
        start_row = int(''.join(c for c in start_cell if c.isdigit()))

        responses = []
        for i in range(0, len(values), chunk_size):
            chunk = values[i : i + chunk_size]
            chunk_start = start_row + i
            chunk_end = chunk_start + len(chunk) - 1
            chunk_range = (f'{sheet_name}!{start_letters}{chunk_start}' 
                           f':{end_letters}{chunk_end}')

            result = self.sheet.update(
                spreadsheetId=self._sheet_id,
                range=chunk_range,
                valueInputOption='USER_ENTERED',
                body={'values': chunk},
            ).execute()
            responses.append(result)

        return responses

    def append_range(self, range: str, values: list[list]) -> dict[str, Any]:
        """
        Appends the values to the specified range in the sheet.

        Arguments:
        * range (`str`): The *FULL* range name, with the sheet name, to be found.
        * values (`list[list]`): The values to insert in the specified range.

        Returns:
        * response (`dict`): The google API response dictionary.
        """

        result = self.sheet.append(
            spreadsheetId=self._sheet_id,
            range=range,
            valueInputOption='USER_ENTERED',
            body={'values': values},
        ).execute()

        return result

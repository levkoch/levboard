from typing import Any

from google.oauth2 import service_account
from googleapiclient import discovery

SERVICE_ACCOUNT_FILE: str = (
    # r'C:\Users\vasil\Documents\GitHub\levboard\data\google_token.json' # on desktop
    'C:/Users/levpo/Documents/GitHub/lev-bot/extras/google_token.json'  # on laptop
)


class Spreadsheet:
    """
    A google sheets access class, to be able to send data to files from python directly.

    Arguments:
    * sheet_id (`str`): The ID of the sheet the instance should manipulate.
    * cred_file (optional `str`): Path to the google_token.json file. Defaults to the one
        that it should be right now but who knows.
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
        """Internal method to grant the instance access to the google sheets resource."""

        service = discovery.build(
            'sheets', 'v4', credentials=self._credentials
        )
        self.sheet = service.spreadsheets().values()

    def delete_range(self, range: str) -> dict[str, Any]:
        """
        Clears the specified range in the sheet.

        Argument:
        * range (`str`): The *FULL* range name, with the sheet name, to be cleared.

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

    def update_range(self, range: str, values: list[list]) -> dict[str, Any]:
        """
        Updates the specified range in the sheet.

        Arguments:
        * range (`str`): The *FULL* range name, with the sheet name, to be found.
        * values (`list[list]`): The values to insert in the specified range.

        Returns:
        * response (`dict`): The google API response dictionary.
        """

        result = self.sheet.update(
            spreadsheetId=self._sheet_id,
            range=range,
            valueInputOption='USER_ENTERED',
            body={'values': values},
        ).execute()

        return result

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

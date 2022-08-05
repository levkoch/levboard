from spreadsheet import Spreadsheet
from model import config

sheet = Spreadsheet(config.LEVBOARD_SHEET)
request = sheet.get_range('Flourish!A1:BD100')
data = request.get('values')

trimmed_data = [['Song Title', 'Song Image']]
trimmed_data[0].extend(i for i in range(1, len(data[0]) - 1))

for row in data[1:]:
    trimmed_row = []
    for item in row:
        if item != '-':
            trimmed_row.append(item)
    trimmed_data.append(trimmed_row)

sheet.update_range('Flourish!A101:BD200', trimmed_data)

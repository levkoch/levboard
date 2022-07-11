from main.spreadsheet import Spreadsheet

sheet = Spreadsheet('1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk')
request = sheet.get_range('Flourish Visualization!A1:BD100')
data = request.get('values')
print(data)

trimmed_data = [['Song Title', 'Song Image']]
trimmed_data[0].extend(i for i in range(1, len(data[0]) - 1))
print(len(trimmed_data[0]))
print(len(data[0]))

for row in data[1:]:
    trimmed_row = []
    for item in row:
        if item != '-':
            trimmed_row.append(item)
    trimmed_data.append(trimmed_row)

sheet.update_range('Flourish Visualization!A101:BD200', trimmed_data)

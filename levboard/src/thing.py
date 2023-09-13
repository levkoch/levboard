import yaml

with open('levboard/data/songs.yml', 'r+') as fp:
    data = yaml.safe_load(fp)
    good_images = (
        value for value in data.values() if value['image'] != 'MISSING'
    )
    yaml.dump({value['standard']: value for value in good_images}, fp)

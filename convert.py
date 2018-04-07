import itertools
import csv
import os
import glob
import re
import tarfile


def unzip_files():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    pattern = os.path.join(path, '*.tar.gz')
    files = glob.glob(pattern)

    extract_path = os.path.join(path, 'unzipped')

    for fname in files:
        tar = tarfile.open(fname, "r:gz")
        tar.extractall(path=extract_path)
        tar.close()


def load_file_content(filepath):
    fname = os.path.basename(filepath)
    num, metric, _, _ = fname.split('.')
    year, month = int(num[:4]), int(num[-2:])

    with open(filepath, 'r') as f:
        for line in f.readlines():
            lat, long, val = re.split(r'\s+', line.strip())
            record = {
                'lat': lat,
                'long': long,
                'measurement': val,
                'month': month,
                'year': year,
                'metric': metric
            }
            yield record


def load_all_file_contents():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data', 'unzipped')
    pattern = os.path.join(path, '*.pnt')
    files = glob.glob(pattern)

    return map(lambda fname: load_file_content(fname), files)


if __name__ == '__main__':
    unzip_files()

    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data', 'data.csv')

    with open(path, 'w') as f:
        fieldnames = ['lat', 'long', 'measurement', 'year', 'month', 'metric']
        writer = csv.DictWriter(f, delimiter=',', fieldnames=fieldnames)
        writer.writeheader()

        for line in itertools.chain.from_iterable(load_all_file_contents()):
            print(line)
            writer.writerow(line)

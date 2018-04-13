import glob
import os

import pandas as pd

DATA_PATH = os.getenv('DATA_PATH')


def load_host_file_to_df(filepath: str) -> pd.DataFrame:
    """Loads pnt file contents into pandas dataframe

    :param filepath: path to pnt file on localhost
    """
    fname = os.path.basename(filepath)
    num, metric, region, _ = fname.split('.')
    year, month = int(num[:4]), int(num[-2:])

    if year not in range(1992, 2017 + 1):
        print('Skipping year out of range {}'.format(year))
        return

    print("Loading file to dataframe: {}".format(os.path.basename(filepath)))
    df = pd.read_csv(
        filepath,
        header=None,
        delim_whitespace=True,
        names=['lat', 'long', 'measurement'])
    df['month'] = month
    df['year'] = year
    df['metric'] = metric
    df['region'] = region
    return df


def list_pnts():
    path = os.path.join(DATA_PATH, 'pnts')

    pattern = os.path.join(path, '*.pnt')
    files = glob.glob(pattern)
    for f in files:
        yield f


if __name__ == '__main__':
    fpath = os.path.join(DATA_PATH, '1972_2017.csv')
    max_count = 2
    count = 0
    with open(fpath, 'a') as f:
        for pnt in list_pnts():
            df = load_host_file_to_df(pnt)
            if df is not None:
                count += 1
                print('Writing [year={}, month={}, metric={}, region={}] to {}'
                      .format(df['year'][0], df['month'][0], df['metric'][0],
                              df['region'][0], fpath))
                df.to_csv(
                    f,
                    mode='a',
                    header=False,
                    index=False,
                    columns=[
                        'year', 'month', 'metric', 'region', 'lat', 'long',
                        'measurement'
                    ])

                if count >= max_count:
                    break

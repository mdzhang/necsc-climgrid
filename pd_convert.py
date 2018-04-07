import os
import glob
import tarfile

from celery import Celery
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

db_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'data', 'data.db')

SQLALCHEMY_DB_URI = os.getenv('SQLALCHEMY_DB_URI',
                              'sqlite:///{}'.format(db_path))
CELERY_RESULTS_BACKEND = os.getenv('CELERY_BROKER_BACKEND',
                                   'redis://localhost:6379/0')
CELERY_BROKER_BACKEND = os.getenv('CELERY_BROKER_BACKEND',
                                  CELERY_RESULTS_BACKEND)
engine = sa.create_engine(SQLALCHEMY_DB_URI)

app = Celery(
    'pd_convert',
    broker=CELERY_BROKER_BACKEND,
    result_backend=CELERY_RESULTS_BACKEND)


def db_setup():
    """Creates database if it does not already exist"""
    Base = declarative_base()

    class Precipitation(Base):
        __tablename__ = "precipitation"

        lat = sa.Column(sa.Float, primary_key=True)
        long = sa.Column(sa.Float, primary_key=True)
        measurement = sa.Column(sa.Float)
        month = sa.Column(sa.Integer, primary_key=True)
        year = sa.Column(sa.Integer, primary_key=True)
        metric = sa.Column(sa.String, primary_key=True)

    try:
        Base.metadata.create_all(engine)
    except ValueError as e:
        if str(e) == "Table 'precipitation' already exists.":
            pass


def unzip_files():
    """Unzip tarballs in ./data dir to ./data/unzipped"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    pattern = os.path.join(path, '*.tar.gz')
    files = glob.glob(pattern)

    extract_path = os.path.join(path, 'unzipped')

    for fname in files:
        tar = tarfile.open(fname, "r:gz")
        tar.extractall(path=extract_path)
        tar.close()


def load_file_content(filepath):
    """Loads file contents into pandas dataframe"""
    fname = os.path.basename(filepath)
    num, metric, _, _ = fname.split('.')
    year, month = int(num[:4]), int(num[-2:])

    df = pd.read_csv(
        filepath,
        header=None,
        delim_whitespace=True,
        names=['lat', 'long', 'measurement'])
    df['month'] = month
    df['year'] = year
    df['metric'] = metric
    return df


def write_to_store(df):
    """Write pandas dataframe to a sql db"""
    return df.to_sql(
        name='precipitation', con=engine, if_exists='append', index=False)


@app.task
def load_to_store(filepath):
    return write_to_store(load_file_content(filepath))


def load_all_file_contents():
    """List out and enqueue files to load to db"""
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data', 'unzipped')
    pattern = os.path.join(path, '*.pnt')
    files = glob.glob(pattern)

    for fname in files:
        load_to_store.apply_async((fname, ))


if __name__ == '__main__':
    unzip_files()

    db_setup()

    load_all_file_contents()

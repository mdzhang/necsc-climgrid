from typing import Iterator
from urllib.parse import urlparse, urljoin
from urllib.request import urlretrieve
import ftplib
import glob
import io
import os
import tarfile

from celery import Celery
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from google.cloud import storage

##############################################################################
# Global configuration and initialization
##############################################################################

# uri to tarballs
TARBALL_URI = os.getenv('TARBALL_URI', 'file://{}'.format(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')))
# where to put pnt files
DATA_URI = os.getenv('DATA_URI', os.path.join(TARBALL_URI, 'unzipped'))
# where to store tarballs and pnt files temporarily
TMP_DIR = os.getenv('TMP_DIR', os.path.expanduser('~/tmp/climgrid'))
# pnt data will ultimately go to this postgres instance
POSTGRESQL_URI = ('postgresql+psycopg2://climgrid:climgrid'
                  '@localhost:5432/precipitation')
# for task queue
REDIS_URI = os.getenv('REDIS_URI', 'redis://localhost:6379/0')

SQLALCHEMY_DB_URI = os.getenv('SQLALCHEMY_DB_URI', POSTGRESQL_URI)
CELERY_RESULTS_BACKEND = os.getenv('CELERY_BROKER_BACKEND', REDIS_URI)
CELERY_BROKER_BACKEND = os.getenv('CELERY_BROKER_BACKEND', REDIS_URI)

engine = sa.create_engine(SQLALCHEMY_DB_URI)

app = Celery(
    'climgrid',
    broker=CELERY_BROKER_BACKEND,
    result_backend=CELERY_RESULTS_BACKEND)

##############################################################################
# Worker task helper functions
##############################################################################


def download_file_from_gcs(src_uri: str, target_path: str) -> str:
    """See download_uri_to_host.

    This is just Google Cloud Storage specific.
    """
    uri = urlparse(src_uri)
    bucket_name = uri.netloc
    blob_name = uri.path.lstrip('/')
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    blob = bucket.blob(blob_name)
    blob.download_to_filename(target_path)
    return target_path


def download_uri_to_host(uri: str, download_subdir: str = None) -> str:
    """Downloads file at uri to localhost and returns its location

    :param uri: uri to (potentially remote) pnt file
    :returns: path to local pnt file
    """
    # ensure download directory exists
    download_dir = TMP_DIR
    if download_subdir is not None:
        download_dir = os.path.join(download_dir, download_subdir)

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    parsed = urlparse(uri)
    name = os.path.basename(parsed.path)
    local_file_path = os.path.join(download_dir, name)

    # don't download if the file already exists
    if os.path.exists(local_file_path):
        print('{} already existed locally and was not overwritten.'
              .format(local_file_path))
        return local_file_path

    # download file
    if parsed.scheme in ['ftp', 'http']:
        print('Downloading "{}" to "{}"...'.format(uri, local_file_path))
        urlretrieve(uri, filename=local_file_path)
    elif parsed.scheme == 'gs':
        download_file_from_gcs(uri, local_file_path)
    else:
        raise ValueError('Cannot download file from uri: "{}"'.format(uri))

    return local_file_path


def upload_file_to_gcs(src_path: str, target_uri: str) -> str:
    """See upload_host_file_to_store.

    This is just Google Cloud Storage specific.
    """
    uri = urlparse(target_uri)
    bucket_name = uri.netloc
    blob_name = uri.path.lstrip('/')
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    try:
        blob = bucket.get_blob(blob_name)
        print('{} already existed and was not overwritten.'.format(target_uri))
    except Exception as e:
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(src_path)
    return target_uri


def upload_host_file_to_store(path: str) -> str:
    """Uploads file on localhost to DATA_URI

    :param path: absolute path to file on localhost
    :returns: uri file was uploaded to
    """
    filename = os.path.basename(path)

    remote_path = DATA_URI
    uri = urlparse(remote_path)
    src = path

    if uri.scheme == 'gs':
        target = remote_path
        if target.endswith('/'):
            target = target.rstrip('/')
        target = '{}/{}'.format(target, filename)
        print('Uploading {} to {}...'.format(src, target))
        return upload_file_to_gcs(src, target)
    elif uri.scheme == 'file':
        # TODO
        pass
    else:
        raise ValueError('Cannot upload file to uri: "{}"'.format(uri))


def load_host_file_to_df(filepath: str) -> pd.DataFrame:
    """Loads pnt file contents into pandas dataframe

    :param filepath: path to pnt file on localhost
    """
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


def copy_df_to_sql_store(df: pd.DataFrame) -> None:
    """Write pandas dataframe to a sql db

    :param df: as returned by `load_host_file_to_df`; dataframe with
        month/year/metric/lat/long/measurement columns
    """
    print('Writing dataframe to db...')
    # to_sql is slow so stream csv
    output = io.StringIO()
    df.to_csv(output, sep='\t', header=False, index=False)
    output.seek(0)

    connection = engine.raw_connection()
    try:
        cur = connection.cursor()
        cur.copy_from(output, 'precipitation', null="")
        connection.commit()
    finally:
        cur.close()


def extract_tarball(tarball_uri: str) -> Iterator[str]:
    """Download (if necessary) and unzip a tarball to a tmp dir on localhost,
    then upload the resulting files to the specified uri with their same names

    :returns: path to extracted files
    """
    uri = urlparse(tarball_uri)
    path = uri.path
    local_tarball_path = None

    if uri.scheme == 'ftp':
        local_tarball_path = download_uri_to_host(
            tarball_uri, download_subdir='tarballs')
    elif uri.scheme == 'file':
        local_tarball_path = path
    else:
        raise ValueError('Cannot unzip tarball with uri: "{}"'.format(uri))

    # extract to tmpdir
    extract_path = os.path.join(TMP_DIR, 'unzipped')
    tar = tarfile.open(local_tarball_path, "r:gz")
    print('Extracting "{}" to "{}"...'.format(local_tarball_path,
                                              extract_path))
    tar.extractall(path=extract_path)

    for m in tar.getmembers():
        full_path = os.path.join(extract_path, m.path)
        yield upload_host_file_to_store(full_path)

    tar.close()


##############################################################################
# Worker tasks
##############################################################################


@app.task
def etl_pnt(uri: str) -> None:
    """Load the pnt file at the given uri to localhost, then stream to sql db

    :param uri: uri to pnt file
    """
    path = download_uri_to_host(uri)
    copy_df_to_sql_store(load_host_file_to_df(path))


@app.task
def etl_tarball(uri: str) -> None:
    """Download and unzip tarball, and enqueue resulting files for further
    processing.

    :param uri: uri to tarball
    """
    extracted_uris = extract_tarball(uri)
    for uri in extracted_uris:
        etl_pnt.apply_async((uri, ))


##############################################################################
# Used by main process
##############################################################################


def db_setup() -> None:
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


def list_tarballs() -> Iterator[str]:
    """List tarballs at TARBALL_URI
    Supports TARBALL_URIs that are URIs using file or ftp scheme

    :yields: URIs to tarballs
    """
    path = TARBALL_URI
    uri = urlparse(path)
    if uri.scheme == 'ftp':
        ftp = ftplib.FTP(uri.netloc)
        ftp.login()  # user anonymous, passwd anonymous@
        for f in ftp.nlst(uri.path):
            if f.endswith('.tar.gz'):
                yield urljoin('{}://{}'.format(uri.scheme, uri.netloc), f)
    elif uri.scheme == 'file':
        pattern = os.path.join(uri.path, '*.tar.gz')
        files = glob.glob(pattern)
        for f in files:
            yield urljoin('{}://{}'.format(uri.scheme, uri.netloc), f)
    else:
        raise ValueError('Cannot list tarballs at uri: "{}"'.format(uri))


def main():
    """Main process for enqueuing of tasks"""
    print('Setting up database...')
    db_setup()

    max_count = 1
    count = 0
    print('Listing tarballs...')
    for tarball in list_tarballs():
        print('Enqueuing tarball {}...'.format(tarball))
        for uri in extract_tarball(tarball):
            path = download_uri_to_host(uri)
            copy_df_to_sql_store(load_host_file_to_df(path))
        count += 1
        if count >= max_count:
            break

    print('Enqueueing process finished. See workers for data processing '
          'progress.')


if __name__ == '__main__':
    """Invoke with python climgrid.py"""
    main()

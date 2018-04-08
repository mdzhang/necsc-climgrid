# [NE CSC climgrid][climgrid]

Scripts for taking [climgrid data][climgrid] (tarballed `.pnt` files containing geolocated precipitation data) and putting them into a Postgres DB with added columns for data encoded in the file name.

#### What this does

- Running `python climgrid.py` will connect to the FTP server, list all tarballs, and enqueue a celery task `etl_tarball` with the URI of the tarball as its only argument
- `etl_tarball` will download the tarball, unzip it, copy the extracted files to the configured uri, and enqueue an `etl_pnt` task for each extracted file
- `etl_pnt` will download copy the extracted file to localhost, load it into a `pandas` dataframe, inject columns whose values are derived from the file name, and stream the contents of the dataframe into a postgres `COPY` command

#### Some data notes

There is a tarball for each month over the 120 years from 1895-2015. Each tarball contains 4-8 files, each named: `[year][month].[metric].[region].pnt`. More recent years have data for the `alaska` as well as `conus` (contiguous US), thus the range in files per tarball. Each file has about 13MB of data / ~470k observations.

The entirety of the dataset as of 2018-04 is about ~75 GB of data, distributed over 120 * 12 * 4 = ~6k files. That's about 6k * 470k = ~2.8b records.

[climgrid]: ftp://ftp.ncdc.noaa.gov/pub/data/climgrid/

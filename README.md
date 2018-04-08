# [NE CSC climgrid][climgrid]

Scripts for taking [climgrid data][climgrid] (tarballed `.pnt` files) and putting them into a Postgres DB with added columns for data encoded in the file name.

#### What this does

- Running `python climgrid.py` will connect to the FTP server, list all tarballs, and enqueue a celery task to process each one
- The celery task will unzip the tarball, note the path the extracted contents, and for each extracted file enqueue a different celery task to process the individual files
- The final celery task will open each file, load it into a `pandas` dataframe, inject columns whose values are derived from the file name, and stream the contents of the dataframe into a postgres `COPY` command

#### Some data notes

There is a tarball for each month over the 120 years from 1895-2015. Each tarball contains 4-8 files, each named: `[year][month].[metric].[region].pnt`. More recent years have data for the `alaska` as well as `conus` (contiguous US), thus the range in files per tarball. Each file has about 13MB of data / ~470k observations.

The entirety of the dataset as of 2018-04 is about ~75 GB of data, distributed over 120 * 12 * 4 = ~6k files. That's about 6k * 470k = ~2.8b records.

#### Some performance notes

Running on my personal MBP w/ 4 CPUs, 8G mem, I found that:

| # Tarballs | # pnt files | # workers | # procs | threads per proc | time to queue | time for all tasks to finish |
| -- | -- | -- | -- | -- | -- | -- |
| 1 | 4 | 4 | 15,3 (24) | 10 | 1.37s | 17s |
| 2 | 16 | 4 | 15,3 (24) | 10 | 1.81s | 54.03s |
| 3 | 20 | 4 | 15,3 (24) | 10 | 2.58s | 83.05s |
| 3 | 20 | 5 | 15,3 (24) | 10 | 1.95s | 61s |
| 3 | 20 | 8 | 15,3 (24) | 10 | 2s | 60s |
| 3 | 20 | 4 | 15,3 (24) | 20 | 1.95s | 56.98s |

All of these peg my cpu and take about 5GB mem max at any given point, with higher mem loosely correlated to having more workers.

[climgrid]: ftp://ftp.ncdc.noaa.gov/pub/data/climgrid/

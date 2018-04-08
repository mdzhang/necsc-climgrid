# [NE CSC climgrid][climgrid]

Scripts for taking [climgrid data][climgrid] (tarballed `.pnt` files) and putting them into a Postgres DB with added columns for data encoded in the file name.

#### What this does

I wrote this as a one-off, so admittedly it's not the most performant thing. Assuming you have the tarballs at the given FTP server path on disk, `pd_convert` will:

- untar them to a subdirectory called `unzipped`
- for each resulting `.pnt` file, queue a celery task to
  - parse that `.pnt` file to a dataframe with the 3 columns from the file + 3 more from the file name, and approximately 500k observations per dataframe
  - use that dataframe to generate a postgres copy command to populate a postgres database that has a unique index on month/year/metric/lat/long

#### Some data notes

There are 120 years worth of data, each with 12 months, each with 4-8 files each about 13MB of data and ~470k lines. Aka 120 x 12 x 4 x 13 ~= 75k MB ~= 75 GB of data. (4 files for alaska, 8 for alaska + continuous us)

Running with local redis/celery/postgres/data files, it takes 1 worker task about 15-30s to process 1 `.pnt` file. Bump that to about 1m for a hosted postgres instance.

So, 120 x 12 x 4 = 5760 `.pnt` files

#### Some perf notes

On my 4 CPU MBP, that's 1 celery worker, p processes, each using c threads. The Makefile target is set to c = 10; I find that it offers a few seconds improvement per parallel batch of pnt files relative to c = 4 or c = 20.

| # Tarballs | # pnt files | # workers | # procs | threads per proc | time to queue | time for all tasks to finish |
| -- | -- | -- | -- | -- | -- | -- |
| 1 | 4 | 4 | 15,3 (24) | 10 | 1.37s | 17s |
| 2 | 16 | 4 | 15,3 (24) | 10 | 1.81s | 54.03s |
| 3 | 20 | 4 | 15,3 (24) | 10 | 2.58s | 83.05s |
| 3 | 20 | 5 | 15,3 (24) | 10 | 1.95s | 61s |
| 3 | 20 | 8 | 15,3 (24) | 10 | 2s | 60s |
| 3 | 20 | 4 | 15,3 (24) | 20 | 1.95s | 56.98s |

All of these peg my cpu and take about 5GB mem max at any given point, with higher mem for more workers


[climgrid]: ftp://ftp.ncdc.noaa.gov/pub/data/climgrid/

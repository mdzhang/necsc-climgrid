FROM python:3.6

RUN mkdir -p /opt/climgrid
WORKDIR /opt/climgrid

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY . ./

LABEL maintainer="Michelle D Zhang <zhang.michelle.d@gmail.com>"
LABEL source="https://github.com/mdzhang/necsc-climgrid"
ARG commit
LABEL commit="$commit"

ENV PYTHONPATH /opt/climgrid

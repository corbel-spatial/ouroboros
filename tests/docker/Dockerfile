# syntax=docker/dockerfile:1
FROM ubuntu:noble AS builder
ENV HOME="/root"
WORKDIR $HOME
RUN apt update && apt upgrade -y

# install system dependencies
FROM builder AS build1
RUN apt install -y git build-essential libbz2-dev libffi-dev liblzma-dev libncursesw5-dev libreadline-dev  \
    libsqlite3-dev libssl-dev libstdc++-11-dev libxml2-dev libxmlsec1-dev make tk-dev xz-utils zlib1g-dev

# clone Python source
FROM build1 AS build2
ARG TEST_VERSION
RUN git clone https://github.com/python/cpython.git --branch "v$TEST_VERSION"

# make install Python as python3
FROM build2 AS build3
RUN cd cpython && \
    ./configure && \
    make && \
    make test && \
    make install

# upgrade pip
FROM build3 AS build4
RUN pip3 install --upgrade pip --root-user-action ignore

# install GDAL binaries
FROM build4 AS build5
RUN apt install -y gdal-bin libgdal-dev python3-gdal

# install Python packages
FROM build5 AS build6
RUN python3 -m pip install uv
RUN GDAL_VERSION=$(apt info gdal-bin | grep -oE "Version: .*\+" | grep -oE "[0-9\.]{5,}") && \
    uv pip install gdal==$GDAL_VERSION --system

# copy install/test script
FROM build6 AS build7
COPY test.sh test.sh
RUN chmod +x test.sh

# on docker run: clone ouroboros and run tests
CMD ["./test.sh"]

# to test:
# docker pull corbelspatial/ouroboros:py3.14 && docker run -it --rm --name ouroboros-test corbelspatial/ouroboros:py3.14

#!/bin/bash

set -e

mkdir -p /tmp/minio/data

docker run -p 9000:9000 -p 9090:9090 \
    --user $(id -u):$(id -g) \
    -v /tmp/minio/data:/data \
    quay.io/minio/minio server /data --console-address ":9090"

rm -R /tmp/minio/data
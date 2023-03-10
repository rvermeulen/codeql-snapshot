#!/bin/bash

echo "Building params: language=$1 source-root=$2  db-path=$3"
codeql database create --language=$1 --source-root=$2 $3
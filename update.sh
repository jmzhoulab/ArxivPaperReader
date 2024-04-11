#!/bin/bash

set -e

python src/main.py

git add docs data latest.date

git commit -m "Auto Update"

git push

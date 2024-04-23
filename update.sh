#!/bin/bash

python src/main.py

cd datasets

git add .

git_status=$(git status -s | grep "^[AM]")
if [ -z "$git_status" ]; then
    echo "datasets没有发现新增或者变更文件"
else
    echo "datasets有已暂存的变更，准备提交："
    git commit -m "$(git status -s)"
    git pull --rebase
    git push
fi

cd ..

git add docs datasets latest.date update.sh

git_status=$(git status -s | grep "^[AM]")

if [ -z "$git_status" ]; then
    echo "没有发现新增或者变更文件"
    exit 0
else
    echo "有已暂存的变更，准备提交："
    echo "$git_status"
    git commit -m "Auto Update"
    git push
fi

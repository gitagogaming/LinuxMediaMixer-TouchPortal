#!/bin/sh

prog="$1"

if [ ! -x "$prog" ]; then
    echo "Error: $prog is not an executable file or does not exist."
    exit 1
fi

chmod +x "$prog"

pid=$(ps -ef | grep -v grep | grep -i "\./${prog}" | awk '{print $2}')

if [ "x$pid" != "x" ] && [ "$pid" -gt 0 ]; then
    echo "$(date +"%F %T%Z"): ${prog} already running, killing it to start again"
    kill -9 "$pid"
    sleep 1
fi

./"$prog" -l log.tx

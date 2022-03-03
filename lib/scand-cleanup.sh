#!/bin/sh
#
# Clean-up scan session directories
#
[ $# -eq 0 ] && exit 1
scanqueue="$1"
if [ ! -d "$scanqueue" ] ; then
  exit 2
fi

now=$(date +%s)

find "$scanqueue" -maxdepth 1 -mindepth 1 -type d -print0 \
	| xargs -0 stat -c '%Y %n' | while read ts fn
do
  age=$(expr $now - $ts)
  if [ $age -gt 3600 ] ; then
    rm -rf "$fn"
  fi
done


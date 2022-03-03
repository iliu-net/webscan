#!/bin/sh
#
# Read output of hp-scan and create a suitable status file
#
status="$1"
msgs="$2"
lock="$3"
rcfile="$4"
cmdfile="$5"

cmd="$(cat "$cmdfile")"
#~ cmd="/www/faker.sh"

prev="_"
secs=0
write_status() {
  if [ x"$1" = x"-r" ] ; then
    rate_limit=true
    shift
  else
    rate_limit=false
    secs=0
  fi

  local cur="$*"
  [ x"$prev" = x"$cur" ] && return
  prev="$cur"

  if $rate_limit ; then
    if [ $(date +%s) -eq $secs ] ; then
      return
    fi
    secs=$(date +%s)
  fi

  #~ clear ; echo "$cur"

  exec 4>>$lock
  echo -n 'L'
  flock -x 4
  echo "$cur" > $status
  echo -n 'U'
  flock -u 4
  exec 4>&-
}

rm -f "$rcfile"
(
  exec 2>&1
  $cmd
  rc=$?
  echo $rc >$rcfile
) | tr '\010' '\n' | (
  state="starting"
  write_status "$state"
  while read L
  do
    [ -z "$L" ] && continue
    if (echo "$L" | grep -q 'Reading data:') ; then
      state="finishing"
      write_status -r "$L"
    else
      echo -n 'M'
      echo $L >> $msgs
      write_status "$state"
    fi
  done
)
count=0
while [ ! -f "$rcfile" ]
do
  sleep 1
  count=$(expr $count + 1)
done
echo -n 'X'
write_status $(cat $rcfile)
echo '..DONE'
cat $rcfile

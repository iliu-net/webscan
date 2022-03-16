#!/usr/bin/haserl
<%
set -euf
scanqueue="scan.d"

./lib/scand-cleanup.sh "$scanqueue"

header() {
  local title="$1"
%>Content-type: text/html

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title><%= $title %></title>
    <style>
      /* Forms alignment */
      form  { display: table;      }
      p     { display: table-row;  }
      label { display: table-cell; }
      input { display: table-cell; }
      select { display: table-cell; }
    </style>
  </head>
  <body>
    <h1><%= $title %></h1>
<%
}
footer() {
  #echo '<pre>'
  #env | sort
  #echo '</pre>'
  %>
  </body>
</html>
<%
}

fm_select() {
  local fname="$1" i; shift
  eval local value=\"\${FORM_${fname}:-}\"
  if [ x"$1" = x"-d" ] ; then
    if [ -z "$value" ] ; then
      value="$2"
    fi
    shift 2
  fi
  echo "<select name=\"$fname\" id=\"$fname\">"
  for i in "$@"
  do
    echo -n "<option value=\"$i\""
    if [ x"$i" = x"$value" ] ; then
      echo -n " selected"
    fi
    echo ">$i</option>"
  done
  echo "</select>"
}


begin_wf() {
  if [ $# -gt 0 ] ; then
    echo '<div class="msg">'
    echo "$*"
    echo '</div>'
  fi
  %>
<form method="POST">
  <p>
    <label for="mode">Mode: </label>
    <% fm_select mode -d color gray color lineart %>
  </p>
  <p>
    <label for="res">Resolution (DPI): </label>
    <input type="text" name="res" id="res" value="<%= ${FORM_res:-100} %>"/>
  </p>
  <p>
    <label for="comp">Compression: </label>
    <% fm_select comp -d jpeg none jpeg %>
  </p>
  <%
  if [ -n "${FORM_posturl:-}" ] && [ -n "${HTTP_REFERER:-}" ] ; then
    posturl=$(echo $FORM_posturl | sed -e 's|^/*||')
    referer=$(echo $HTTP_REFERER | sed -e 's|/*$||')
  %>
    <p>
      <label for="posturl">Post URL: </label>
      <input type="text" name="posturl" id="posturl" value="<%= $referer/$posturl %>" readonly/>
    </p>
  <%
  fi
  %>
  <p>
    <label for="convert">Conversion: </label>
    <% fm_select convert -d none none monochrome grayscale 256-colors 64-colors %>
  </p>
  <div class="control-group">
    <input type="submit" name="submit" value="Begin Scan"/>
  </div>
</form>
<hr/>
<%
}

gen_pdf() {
  local session="$1" output="$2"

  if [ -f "$scanqueue/$session/convert.txt" ] ; then
    case "$(cat $scanqueue/$session/convert.txt)" in
      monochrome) convert=-monochrome ;;
      grayscale) convert="-type Grayscale" ;;
      256-colors) convert="-colors 256" ;;
      64-colors) convert="-colors 64" ;;
      *) convert="" ;;
    esac
  fi
  convert -page A4 \
    $(find "$scanqueue/$session" -name "hpscan*" -type f) \
    $convert \
    $output
}

download_pdf() {
  #echo 'Content-type: text/plain'
  #echo ''
  #exec 2>&1

  local session="$1"
  local output="$scanqueue/$session/scan-$(date +%Y-%m-%d_%H%M -r $scanqueue/$session/scan.txt).pdf"
  gen_pdf "$session" "$output"
  echo Location: "$output"
  echo ''
}

post_pdf() {
  #echo 'Content-type: text/plain'
  #echo ''
  #exec 2>&1
  local session="$1"
  local output="$scanqueue/$session/scan-$(date +%Y-%m-%d_%H%M -r $scanqueue/$session/scan.txt).pdf"
  gen_pdf "$session" "$output"
  local posturl="$(cat $scanqueue/$session/posturl.txt)"

  local post_data="$(curl "$posturl" \
	-F uploadFile=@"$output;type=application/pdf;filename=$(basename $output)" \
	-F create=scanned 2>/dev/null)"
  if (echo "$post_data" | grep -q NEXT-URL:) ; then
    local next_url="$(echo "$post_data" | grep NEXT-URL: | cut -d: -f2-)"
    echo "Refresh: 5;url=$(echo $posturl | cut -d/ -f-3)$next_url"
    echo "Content-type: text/html"
    echo ''
    echo "<a href=\"$(echo $posturl | cut -d/ -f-3)$next_url\">Created record</a>"
  else
    echo 'Content-type: text/html'
    echo ''
    echo '<h1>Error></h1>'
    local myurl="$SCRIPT_NAME"'?'"session=$session"
    %>
      <a href="<%= $myurl %>&cmd=preview">Back to preview</a> :
    <%
    echo "$post_data"
  fi

}



scan_page() {
  local session="$1"
  header "Webscan: --scanning--"
  echo '<div id="topdiv"></div>'
  echo '<pre id="status"></pre>'
  echo '<hr/>'
  echo '<pre id="msgs"></pre>'
  echo "<pre>"
  echo "$scanqueue/$session"
  echo "</pre>"
  js_url="$SCRIPT_NAME"'?'"session=$session"
  %>
  <script src="scan.js"></script>
  <script>
    next_url="<%= $js_url %>&cmd=preview";
    poll_url="<%= $js_url %>&cmd=status";
    getStatus();
  </script>
  <%
  footer
  # Run the scan job...
  (
    exec >&- 2>&- <&-
    msgr=$(readlink -f lib/msg-filter.sh)
    cd "$scanqueue/$session"
    exec > log.txt 2>&1
    sh "$msgr" \
	status.txt \
	msgs.txt \
	lock \
	rc.txt \
	scan.txt
  ) &
  echo $! > "$scanqueue/$session/pid.txt"
}

preview_pages() {
  local session="$1"
  local myurl="$SCRIPT_NAME"'?'"session=$session"
  %>
  <a href="<%= $myurl %>&cmd=scanpg">Add Page</a> :
  <%
    if [ -f "$scanqueue/$session/posturl.txt" ] ; then
    %> <a href="<%= $myurl %>&cmd=post">Post document</a> <%
    else
    %> <a href="<%= $myurl %>&cmd=download">Download</a> <%
    fi
  %>
  : (<% (cd $scanqueue ; du -sh $session) %>)
  <hr/>
  <%
  find "$scanqueue/$session" -name "hpscan*" -type f | while read f
  do
    %>
    <a href="<%= $f %>"><img src="<%= $f %>" width=300 height=400></a>
    <%
  done
  echo "<hr/>"
}


if [ -n "${FORM_submit:-}" ] ; then
  # This is a new session!
  session=$(mktemp -d -p $scanqueue sess.XXXXXXXXXX)
  chmod 777 "$session"
  echo "$FORM_convert" > $session/convert.txt
  if [ -n "${FORM_posturl:-}" ] ; then
    echo "$FORM_posturl" > $session/posturl.txt
  fi
  dpi=$(echo $FORM_res | tr -dc 0-9)
  [ -z "$dpi" ] && dpi=150
  echo "hp-scan -i -linfo -sfile -m${FORM_mode} -r$dpi -x$FORM_comp" > $session/scan.txt
  scan_page "$(basename "$session")"
elif [ -n "${FORM_session:-}" ] ; then
  session=$(echo "$FORM_session" | tr -dc .A-Za-z0-9)
  [ -z "$session" ] && session=____
  if [ ! -d "$scanqueue/$session" ] ; then
    header "Webscan: error"
    begin_wf "Session error ($session)"
    footer
  elif [ x"${FORM_cmd:-}" = x"preview" ] ; then
    header "Webscan: preview"
    preview_pages "$session"
    footer
  elif [ x"${FORM_cmd:-}" = x"scanpg" ] ; then
    scan_page "$session"
  elif [ x"${FORM_cmd:-}" = x"download" ] ; then
    download_pdf "$session"
  elif [ x"${FORM_cmd:-}" = x"post" ] ; then
    post_pdf "$session"
  elif [ x"${FORM_cmd:-}" = x"status" ] ; then
    echo 'Content-type: text/plain'
    echo ''
    if [ -d "$scanqueue/$session" ] ; then
      exec 4>>$scanqueue/$session/lock
      flock -x 4
      echo $(xargs < "$scanqueue/$session/status.txt")
      flock -u 4
      cat "$scanqueue/$session/msgs.txt"
    else
      echo 'ERROR: Missing session'
    fi
  fi
else
  header "Webscan"
  begin_wf
  footer
fi

#
# 1st Form: tweak settings
# 2nd Scan: one page
# - add to scan
# - POST fo pergamino
#   curl [URL] -F file=@filename1 -F field=this
%>

/*
 * handle status changes
 */
const xhttp = new XMLHttpRequest();

//~ next_url="<%= $js_url %>&cmd=preview";
//~ poll_url="<%= $js_url %>&cmd=status";
function getStatus() {
  xhttp.open("GET", poll_url);
  xhttp.send();
}

xhttp.onload = function() {
  var topdiv = document.getElementById("topdiv");
  var status = document.getElementById("status");
  var msgs = document.getElementById("msgs");
  const regex = /^[0-9]+$/;

  var rtext = this.responseText;
  var lines = rtext.split("\n");

  var rc = lines.shift();
  status.innerHTML = rc;

  msgs.innerHTML = lines.join("\n");

  if (rc.match(regex)) {
    topdiv.innerHTML = "Done.  <a href=\""+next_url+"\">Continue</a>";
    window.location.replace(next_url);
  } else {
    topdiv.innerHTML = "In-progress";
  }

  setTimeout(getStatus,500);
}


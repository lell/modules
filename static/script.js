function setCookie(key, value, expiry) {
  var expires = new Date();
  expires.setTime(expires.getTime() + (expiry * 24 * 60 * 60 * 1000));
  document.cookie = key + '=' + value + ';path=/;expires=' + expires.toUTCString();
}

function getCookie(key) {
  var keyValue = document.cookie.match('(^|;) ?' + key + '=([^;]*)(;|$)');
  return keyValue ? keyValue[2] : null;
}

function eraseCookie(key) {
  var keyValue = getCookie(key);
  setCookie(key, keyValue, '-1');
}

var working = 0;
setup = function() {
  $("#button").button();
  $("#button-icon").button({
    icon: "ui-icon-gear",
    showLabel: false
  });

  $("#radioset").buttonset();

  $("#controlgroup").controlgroup();

  $("#dialog-link, #icons li").hover(
    function() {
      $(this).addClass("ui-state-hover");
    },
    function() {
      $(this).removeClass("ui-state-hover");
    }
  );

  $(':input').addClass("ui-corner-all");

  $(':input').addClass("ui-widget ui-widget-content ui-corner-all");

  $(':input:enabled:visible:first').focus();
  $(document).on('keydown', 'input', function(e) {
    if (e.which == 13) {
      if (working == 0) {
        click();
        working = 1;
      }
      return false;
    }
  });
}

function logout() {
  eraseCookie('sid');
  sid = '';
  window.location.replace('/');
}


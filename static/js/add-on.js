$(document).on("click", function(e) {
  if ($(e.target).is(".share-toggle i, #share-menu, .search-toggle, .search-toggle i, #search-input") === false) {
    $("#search").css("display", "none");
  } else if ($(e.target).is(".share-toggle i, #share-menu, .search-toggle, .search-toggle i, #search-input") === true) {
    $("#search").css("display", "flex");
  } else {
    $("#search").css("display", "none");
  }
});

var deadline = new Date("2021-05-06T23:59:59.000+10:00");
var timeUntilDeadline = countdown(deadline).toString();

var timerId = countdown(
    deadline,
    function(ts) {
      $('#deadlineTimer').html(ts.toHTML("b"));
    },
    countdown.DAYS|countdown.HOURS|countdown.MINUTES|countdown.SECONDS,
);


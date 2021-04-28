$(document).on("click", function(e) {
  if ($(e.target).is(".share-toggle i, #share-menu, .search-toggle, .search-toggle i, #search-input") === false) {
    $("#search").css("display", "none");
  } else if ($(e.target).is(".share-toggle i, #share-menu, .search-toggle, .search-toggle i, #search-input") === true) {
    $("#search").css("display", "flex");
  } else {
    $("#search").css("display", "none");
  }
});

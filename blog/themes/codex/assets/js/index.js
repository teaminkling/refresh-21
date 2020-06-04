/**
 * Event listener to activate the mobile nav menu.
 */
function toggleMobileNavState() {
  const body = document.querySelector("body");
  body.classList.toggle("nav--active");
}

/**
 * Initialise the burger by adding an event listener on click.
 */
function initBurger() {
  const burger = document.querySelector(".burger");

  burger.addEventListener("click", toggleMobileNavState);
}

initBurger();

document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll(".alert").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400);
    }, 5000);
  });

  // Active nav link highlighting
  var currentPath = window.location.pathname;
  document.querySelectorAll(".navbar-nav a").forEach(function (link) {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });

  // AJAX subcategory filter in question form
  var catSelect = document.querySelector('select[name="subcategory"]');
  if (catSelect) {
    catSelect.addEventListener("change", function () {
      // Enhancement: could load subcategories dynamically
    });
  }
});
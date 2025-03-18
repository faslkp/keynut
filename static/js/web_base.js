// Check the active link and apply it on page load
const navLinks = document.querySelectorAll('.navbar-nav .nav-link')
const currentUrl = window.location.pathname
navLinks.forEach(link => {
    if (link.getAttribute('href') === currentUrl) {
        link.classList.add('active');
    }
});
// Custom Script for Sidebar Toggle
document.addEventListener('DOMContentLoaded', function() {
    // Script for mark active sidebar link
    const navLinks = document.querySelectorAll('.sidebar .nav-link')

    navLinks.forEach(link => {
        link.addEventListener('click', function(e){
            // Remove active class from all links
            navLinks.forEach(item => {
                item.classList.remove('active');
            })

            // Add active class to the clicked item
            this.classList.add('active');
        });
    });

    // Check the active link and apply it on page load
    const currentUrl = window.location.pathname
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentUrl) {
            link.classList.add('active');
        }
    });
    

    // Script for Sidbar Toggle
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.querySelector('.sidebar-backdrop');
    const body = document.body;
    
    function toggleSidebar() {
        sidebar.classList.toggle('show');
        body.classList.toggle('sidebar-open');
    }
    
    sidebarToggle.addEventListener('click', toggleSidebar);
    backdrop.addEventListener('click', toggleSidebar);
    
    // Close sidebar when window resizes to large screen
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 992 && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            body.classList.remove('sidebar-open');
        }
    });
});
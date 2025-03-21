

document.addEventListener('DOMContentLoaded', function () {

    // Check the active navbar link and apply it on page load
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link')
    const currentUrl = window.location.pathname
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentUrl) {
            link.classList.add('active');
        }
    });


    // Handling wishlist button on product card
    const wishlistButtons = document.querySelectorAll('.wish-badge-icon');
    
    if (wishlistButtons.length === 0) {
        return; // Exit if there are no wishlist buttons on the page
    }

    async function toggleWishlist(productId, csrftoken) {
        const url = `/wishlist/${productId}/toggle/`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                },
            });

            const data = await response.json();

            if (response.ok) {
                if (window.location.pathname === '/wishlist/') {
                    window.location.reload(); // Reload only on wishlist page
                } else {
                    const icon = document.getElementById(`wishlist-icon-${productId}`);
                    icon.classList.toggle('bi-heart-fill');
                    icon.classList.toggle('bi-heart');
                    icon.classList.toggle('text-danger');
                }
            } else {
                alert(data.error || 'Something went wrong');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    wishlistButtons.forEach(button => {
        button.addEventListener('click', function () {
            const productId = this.dataset.productId;
            const csrftoken = this.dataset.csrfToken;
            toggleWishlist(productId, csrftoken);
        });
    });
});

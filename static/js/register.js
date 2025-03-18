document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("registerForm").addEventListener("submit", function(event) {
        let isValid = true;
        let firstName = document.getElementById("first_name");
        let lastName = document.getElementById("last_name");
        let email = document.getElementById("email");
        let password1 = document.getElementById("password1");
        let password2 = document.getElementById("password2");
    
        // Clear previous error messages
        document.querySelectorAll(".error-message").forEach(el => el.innerText = "");
    
        // Name validation (only letters allowed)
        let nameRegex = /^[A-Za-z]+$/;
        if (!nameRegex.test(firstName.value.trim())) {
            firstName.nextElementSibling.innerText = "First name can only contain letters.";
            isValid = false;
        }
        if (!nameRegex.test(lastName.value.trim())) {
            lastName.nextElementSibling.innerText = "Last name can only contain letters.";
            isValid = false;
        }
    
        // Email validation
        let emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value.trim())) {
            email.nextElementSibling.innerText = "Enter a valid email address.";
            isValid = false;
        }
    
        // Password validation
        if (password1.value.length < 8) {
            password1.nextElementSibling.innerText = "Password must be at least 8 characters long.";
            isValid = false;
        }
        if (password1.value !== password2.value) {
            password2.nextElementSibling.innerText = "Passwords do not match.";
            isValid = false;
        }
    
        // Prevent form submission if validation fails
        if (!isValid) {
            event.preventDefault();
        }
    });
});

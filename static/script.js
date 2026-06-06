document.addEventListener('DOMContentLoaded', () => {
    const htmlElement = document.documentElement;

    // 1. ALWAYS apply the saved theme immediately on EVERY page
    const savedTheme = localStorage.getItem('appTheme') || 'light';
    htmlElement.setAttribute('data-bs-theme', savedTheme);

    // 2. Handle the toggle button (only if it exists on the current page)
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');

    if (themeToggle && themeIcon) {
        // Set the correct icon on load
        updateIcon(savedTheme);

        // Listen for clicks
        themeToggle.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            // Apply and save
            htmlElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('appTheme', newTheme);
            updateIcon(newTheme);
        });

        function updateIcon(theme) {
            if (theme === 'dark') {
                themeIcon.classList.remove('bi-moon-fill');
                themeIcon.classList.add('bi-sun-fill');
                themeIcon.style.color = "#ffc107"; // Yellow sun
            } else {
                themeIcon.classList.remove('bi-sun-fill');
                themeIcon.classList.add('bi-moon-fill');
                themeIcon.style.color = "inherit"; // Normal moon
            }
        }
    }
});
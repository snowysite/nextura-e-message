const toggleBtn = document.getElementById('theme-toggle');
toggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('light-mode');

    // Change button icon
    if(document.body.classList.contains('dark-mode')){
        toggleBtn.textContent = '🌙';
    } else {
        toggleBtn.textContent = '☀️';
    }
});

// Initialize mode
if (!document.body.classList.contains('dark-mode') && !document.body.classList.contains('light-mode')) {
    document.body.classList.add('dark-mode'); // default
}

document.getElementById('open-ruby').addEventListener('click', () => {
    window.open('http://localhost:5001', '_blank');
});

document.getElementById('talk-ruby').addEventListener('click', async () => {
    // Try to send a wake command or similar to the backend
    alert("Ruby is listening! You can talk to her now.");
    window.open('http://localhost:5001', '_blank');
});

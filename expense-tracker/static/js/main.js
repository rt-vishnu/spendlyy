// main.js — students will add JavaScript here as features are built

// Video Modal Functionality
(function() {
    const modal = document.getElementById('video-modal');
    const openBtn = document.getElementById('open-modal-btn');
    const closeBtn = document.getElementById('modal-close-btn');
    const video = document.getElementById('modal-video');

    // Placeholder YouTube URL (replace with actual video ID later)
    const videoUrl = 'https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1';

    // Open modal
    openBtn.addEventListener('click', function() {
        modal.classList.add('active');
        video.src = videoUrl;
        document.body.style.overflow = 'hidden';
    });

    // Close modal
    function closeModal() {
        modal.classList.remove('active');
        video.src = '';
        document.body.style.overflow = '';
    }

    closeBtn.addEventListener('click', closeModal);

    // Close on overlay click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
})();

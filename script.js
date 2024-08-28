document.addEventListener('DOMContentLoaded', () => {
    const wheel = document.getElementById('wheel');
    const spinButton = document.getElementById('spinButton');
    const numberOfSegments = 10; // You can change this number to add more segments

    // Create segments with numbers
    for (let i = 1; i <= numberOfSegments; i++) {
        const segment = document.createElement('div');
        segment.classList.add('number');
        segment.innerText = i;
        const angle = (i - 1) * (360 / numberOfSegments);
        segment.style.transform = `rotate(${angle}deg) translate(0, -50%)`;
        wheel.appendChild(segment);
    }

    spinButton.addEventListener('click', () => {
        const spinDuration = 3000; // Spin duration in milliseconds
        const randomAngle = Math.floor(Math.random() * 360) + 360 * 5; // Random spin angle + multiple full spins
        wheel.style.transition = `transform ${spinDuration}ms cubic-bezier(0.33, 1, 0.68, 1)`;
        wheel.style.transform = `rotate(${randomAngle}deg)`;
    });
});

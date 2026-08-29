// 1. Entrance Animations (Global state to only run once)
function initEntranceAnimations() {
    const cards = document.querySelectorAll('.analytics-card, .glass-card');
    cards.forEach((card, index) => {
        // Only animate if not already processed
        if (card.dataset.animated) return;
        
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        // Trigger animation
        setTimeout(() => {
            card.classList.add('animate-in');
            card.dataset.animated = "true";
        }, index * 100);
    });
}

// 2. Sidebar Link Interactivity
function initSidebarInteractivity() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.dataset.bound) return;
        link.addEventListener('mousedown', () => {
            link.style.transform = 'scale(0.95)';
        });
        link.addEventListener('mouseup', () => {
            link.style.transform = '';
        });
        link.addEventListener('mouseleave', () => {
            link.style.transform = '';
        });
        link.dataset.bound = "true";
    });
}

// 3. Dynamic Progress Bar Animation
function initProgressBars() {
    const progressFills = document.querySelectorAll('.progress-bar-fill');
    progressFills.forEach(fill => {
        // Skip if already animated and width matches
        const targetWidth = fill.style.width;
        if (fill.dataset.lastWidth === targetWidth) return;
        
        // If it's a new fill or width changed
        const currentWidth = fill.style.width;
        fill.style.width = '0';
        setTimeout(() => {
            fill.style.transition = 'width 1.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
            fill.style.width = targetWidth;
            fill.dataset.lastWidth = targetWidth;
        }, 100);
    });
}

// 5. Button Hover Glow Effect
function initButtonGlow() {
    const primaryBtns = document.querySelectorAll('.btn-primary');
    primaryBtns.forEach(btn => {
        if (btn.dataset.bound) return;
        btn.addEventListener('mouseenter', () => {
            btn.style.boxShadow = '0 0 20px rgba(0, 117, 255, 0.6)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.boxShadow = '';
        });
        btn.dataset.bound = "true";
    });
}

// Function to call after DOM updates
window.initDashboardContent = function() {
    initEntranceAnimations();
    initProgressBars();
    initButtonGlow();
};

// Sidebar Toggle Functionality
function initSidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (!toggleBtn) return;

    // Check saved state
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        document.body.classList.add('sidebar-collapsed');
    }

    toggleBtn.addEventListener('click', () => {
        const currentlyCollapsed = document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', currentlyCollapsed);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initSidebarToggle();
    initSidebarInteractivity();
    window.initDashboardContent();

    // 4. VISION INTERACTIVE BACKGROUND (Particles)
    const canvas = document.getElementById('vision-bg');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let particles = [];
        let mouse = { x: null, y: null, radius: 150 };

        window.addEventListener('mousemove', (e) => {
            mouse.x = e.x;
            mouse.y = e.y;
            // Subtle Parallax for Body Background
            const xShift = (e.clientX / window.innerWidth) * 20;
            const yShift = (e.clientY / window.innerHeight) * 20;
            document.body.style.backgroundPosition = `${xShift}px ${yShift}px`;
        });

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            init();
        }

        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 0.5 - 0.25;
                this.speedY = Math.random() * 0.5 - 0.25;
                this.color = 'rgba(0, 117, 255, 0.3)';
            }
            update() {
                this.x += this.speedX;
                this.y += this.speedY;

                if (this.x > canvas.width) this.x = 0;
                else if (this.x < 0) this.x = canvas.width;
                if (this.y > canvas.height) this.y = 0;
                else if (this.y < 0) this.y = canvas.height;

                // Mouse interaction
                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < mouse.radius) {
                    const force = (mouse.radius - distance) / mouse.radius;
                    this.x -= dx * force * 0.02;
                    this.y -= dy * force * 0.02;
                }
            }
            draw() {
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        function init() {
            particles = [];
            const count = (canvas.width * canvas.height) / 15000;
            for (let i = 0; i < count; i++) {
                particles.push(new Particle());
            }
        }

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (let i = 0; i < particles.length; i++) {
                particles[i].update();
                particles[i].draw();

                for (let j = i; j < particles.length; j++) {
                    let dx = particles[i].x - particles[j].x;
                    let dy = particles[i].y - particles[j].y;
                    let distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < 150) {
                        ctx.strokeStyle = `rgba(0, 117, 255, ${0.1 * (1 - distance / 150)})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }
            requestAnimationFrame(animate);
        }

        window.addEventListener('resize', resize);
        resize();
        animate();
    }
});

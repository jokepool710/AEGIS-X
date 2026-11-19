/**
 * AEGIS-X Landing Page Logic
 * Particle canvas, scroll reveals, navbar effects, and counter animations.
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavbarScroll();
  initParticles();
  initScrollReveal();
  initCountUp();
});

// ========================================
// Navbar scroll effect
// ========================================
function initNavbarScroll() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const updateNavbar = () => {
    if (window.scrollY > 60) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };

  window.addEventListener('scroll', updateNavbar, { passive: true });
  updateNavbar();
}

// ========================================
// Hero particle canvas
// ========================================
function initParticles() {
  const canvas = document.getElementById('heroParticles');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let particles = [];
  let animationFrameId = null;
  let isHeroVisible = true;
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  const PARTICLE_COUNT = 50;

  function resize() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
  }

  function createParticle() {
    return {
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 2 + 0.5,
      opacity: Math.random() * 0.5 + 0.2,
    };
  }

  function initParticleArray() {
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(createParticle());
    }
  }

  function shouldAnimate() {
    return !motionQuery.matches && isHeroVisible && document.visibilityState === 'visible';
  }

  function draw(advance = false) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach((p, i) => {
      // Update position
      if (advance) {
        p.x += p.vx;
        p.y += p.vy;
      }

      // Wrap around
      if (p.x < 0) p.x = canvas.width;
      if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height;
      if (p.y > canvas.height) p.y = 0;

      // Draw particle
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(59, 130, 246, ' + p.opacity + ')';
      ctx.fill();

      // Draw connections to nearby particles
      for (let j = i + 1; j < particles.length; j++) {
        const dx = p.x - particles[j].x;
        const dy = p.y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = 'rgba(59, 130, 246, ' + (0.08 * (1 - dist / 150)) + ')';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    });

  }

  function animateParticles() {
    animationFrameId = null;
    if (!shouldAnimate()) return;

    draw(true);
    animationFrameId = requestAnimationFrame(animateParticles);
  }

  function syncAnimation() {
    if (shouldAnimate()) {
      if (animationFrameId === null) {
        animationFrameId = requestAnimationFrame(animateParticles);
      }
    } else if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
      draw(false);
    }
  }

  window.addEventListener('resize', () => {
    resize();
    initParticleArray();
    draw(false);
    syncAnimation();
  }, { passive: true });

  document.addEventListener('visibilitychange', syncAnimation);
  if (motionQuery.addEventListener) {
    motionQuery.addEventListener('change', syncAnimation);
  } else {
    motionQuery.addListener(syncAnimation);
  }

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      isHeroVisible = entries.some(entry => entry.isIntersecting);
      syncAnimation();
    });
    observer.observe(canvas.parentElement);
  }

  resize();
  initParticleArray();
  draw(false);
  syncAnimation();
}

// ========================================
// Scroll reveal animation
// ========================================
function initScrollReveal() {
  // Add reveal class to sections and cards
  const revealTargets = document.querySelectorAll(
    '.capability-card, .timeline-item, .stack-card, .benchmark-panel, .section-header, .cta-content'
  );

  revealTargets.forEach(el => el.classList.add('reveal'));
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (motionQuery.matches || !('IntersectionObserver' in window)) {
    revealTargets.forEach(el => el.classList.add('visible'));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
  );

  revealTargets.forEach(el => observer.observe(el));
  if (motionQuery.addEventListener) {
    motionQuery.addEventListener('change', (event) => {
      if (event.matches) {
        revealTargets.forEach(el => el.classList.add('visible'));
        observer.disconnect();
      }
    });
  }
}

// ========================================
// Count-up animation for metric values
// ========================================
function initCountUp() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const counters = document.querySelectorAll('.count-up');

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseFloat(el.textContent);
          const isFloat = el.textContent.includes('.');
          const duration = 900;
          const startTime = performance.now();

          function animate(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic

            const current = eased * target;
            el.textContent = isFloat ? current.toFixed(1) : Math.round(current);

            if (progress < 1) {
              requestAnimationFrame(animate);
            } else {
              el.textContent = isFloat ? target.toFixed(1) : target;
            }
          }

          requestAnimationFrame(animate);
          observer.unobserve(el);
        }
      });
    },
    { threshold: 0.5 }
  );

  counters.forEach(el => observer.observe(el));
}

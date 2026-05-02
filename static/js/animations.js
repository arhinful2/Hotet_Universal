// 734 Hotel - Animation Functions

// Scroll Reveal Animations
function initScrollReveal() {
  if (typeof ScrollReveal !== "undefined") {
    const motionLevel = ANIMATION_SETTINGS.motionLevel || "balanced";
    const motionProfiles = {
      soft: { distance: 38, interval: 200, baseScale: 0.98 },
      balanced: { distance: 60, interval: 160, baseScale: 0.95 },
      strong: { distance: 75, interval: 120, baseScale: 0.92 },
    };
    const profile = motionProfiles[motionLevel] || motionProfiles.balanced;

    const sr = ScrollReveal({
      duration: 1200,
      distance: `${profile.distance}px`,
      easing: "cubic-bezier(0.22, 1, 0.36, 1)",
      interval: profile.interval,
      reset: false,
    });

    // Configure based on animation speed
    const speed = ANIMATION_SETTINGS.speed || "normal";
    const durations = {
      slow: 1800,
      normal: 1200,
      fast: 800,
    };

    sr.reveal(".animate-on-scroll", {
      duration: durations[speed] || 1000,
      origin: "bottom",
      distance: `${Math.max(20, profile.distance - 30)}px`,
      opacity: 0,
      scale: profile.baseScale,
      interval: 100,
    });

    // Staggered animations
    sr.reveal(".room-card", {
      duration: durations[speed] || 1000,
      origin: "bottom",
      distance: `${Math.max(24, profile.distance - 20)}px`,
      opacity: 0,
      interval: 150,
      scale: profile.baseScale - 0.02,
    });

    sr.reveal(".polaroid", {
      duration: durations[speed] || 1000,
      origin: "bottom",
      distance: `${Math.max(28, profile.distance - 10)}px`,
      opacity: 0,
      rotate: { x: 0, y: 0, z: 10 },
      interval: 200,
    });

    sr.reveal(".sticky-note", {
      duration: durations[speed] || 1000,
      origin: "bottom",
      distance: `${Math.max(20, profile.distance - 35)}px`,
      opacity: 0,
      rotate: { x: 0, y: 0, z: 5 },
      interval: 100,
    });

    sr.reveal(
      ".section-title, .booking-widget, .contact-form, .footer-content > div",
      {
        duration: durations[speed] || 1200,
        origin: "bottom",
        distance: "28px",
        opacity: 0,
        interval: 120,
        scale: 0.98,
      },
    );

    sr.reveal(".map-point, .room-buttons .btn, .hero-actions .btn", {
      duration: durations[speed] || 1200,
      origin: "bottom",
      distance: "22px",
      opacity: 0,
      interval: 80,
      scale: 0.97,
    });
  }
}

// Hover animations
function initHoverAnimations() {
  if (!window.matchMedia("(hover: hover)").matches) {
    return;
  }

  const motionLevel = ANIMATION_SETTINGS.motionLevel || "balanced";
  const hoverProfiles = {
    soft: {
      buttonTransform: "translateY(-3px) scale(1.03)",
      buttonShadow: "0 10px 20px rgba(0,0,0,0.16)",
      cardLift: "-6px",
      cardScale: "1.02",
      cardRotate: "1deg",
      cardShadow: "0 14px 28px rgba(0,0,0,0.14)",
    },
    balanced: {
      buttonTransform: "translateY(-5px) scale(1.06)",
      buttonShadow: "0 14px 28px rgba(0,0,0,0.22)",
      cardLift: "-8px",
      cardScale: "1.04",
      cardRotate: "1.5deg",
      cardShadow: "0 20px 40px rgba(0,0,0,0.18)",
    },
    strong: {
      buttonTransform: "translateY(-7px) scale(1.08)",
      buttonShadow: "0 18px 36px rgba(0,0,0,0.24)",
      cardLift: "-12px",
      cardScale: "1.06",
      cardRotate: "2deg",
      cardShadow: "0 24px 44px rgba(0,0,0,0.2)",
    },
  };
  const hover = hoverProfiles[motionLevel] || hoverProfiles.balanced;

  // Button hover effects
  const buttons = document.querySelectorAll(".btn");
  buttons.forEach((btn) => {
    btn.addEventListener("mouseenter", function () {
      this.style.transform = hover.buttonTransform;
      this.style.boxShadow = hover.buttonShadow;
    });

    btn.addEventListener("mouseleave", function () {
      this.style.transform = "";
      this.style.boxShadow = "";
    });
  });

  // Card hover effects
  const cards = document.querySelectorAll(".room-card, .map-point");
  cards.forEach((card) => {
    card.addEventListener("mouseenter", function () {
      if (this.classList.contains("hover-lift")) {
        this.style.transform = `translateY(${hover.cardLift})`;
      } else if (this.classList.contains("hover-scale")) {
        this.style.transform = `translateY(${hover.cardLift}) scale(${hover.cardScale})`;
      } else if (this.classList.contains("hover-rotate")) {
        this.style.transform = `translateY(${hover.cardLift}) rotate(${hover.cardRotate})`;
      } else {
        this.style.transform = `translateY(${hover.cardLift})`;
      }
      this.style.boxShadow = hover.cardShadow;
    });

    card.addEventListener("mouseleave", function () {
      this.style.transform = "";
      this.style.boxShadow = "";
    });
  });
}

// Typewriter effect for hero text
function initTypewriter() {
  const heroTitle = document.querySelector(".hero-content h1");
  if (heroTitle && !heroTitle.dataset.animated) {
    const text = heroTitle.textContent;
    heroTitle.textContent = "";
    heroTitle.dataset.animated = "true";

    let i = 0;
    function typeWriter() {
      if (i < text.length) {
        heroTitle.textContent += text.charAt(i);
        i++;
        setTimeout(typeWriter, 50);
      }
    }

    // Start typing after a delay
    setTimeout(typeWriter, 500);
  }
}

// Floating animation for elements
function initFloatingAnimations() {
  // Create floating particles
  if (document.querySelector(".section-title")) {
    const particles = document.createElement("div");
    particles.className = "floating-particles";
    particles.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1;
            overflow: hidden;
        `;

    // Add some particles
    for (let i = 0; i < 15; i++) {
      const particle = document.createElement("div");
      particle.style.cssText = `
                position: absolute;
                width: ${Math.random() * 10 + 5}px;
                height: ${Math.random() * 10 + 5}px;
                background: rgba(231, 111, 81, ${Math.random() * 0.3 + 0.1});
                border-radius: 50%;
                top: ${Math.random() * 100}%;
                left: ${Math.random() * 100}%;
                animation: float ${Math.random() * 20 + 10}s infinite linear;
            `;
      particles.appendChild(particle);
    }

    document.querySelector(".section-title").style.position = "relative";
    document.querySelector(".section-title").appendChild(particles);
  }

  // Add CSS for floating animation
  const style = document.createElement("style");
  style.textContent = `
        @keyframes float {
            0% {
                transform: translateY(0) rotate(0deg);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(-100vh) rotate(360deg);
                opacity: 0;
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 0 0 0 rgba(231, 111, 81, 0.7);
            }
            50% {
                transform: scale(1.05);
                box-shadow: 0 0 0 10px rgba(231, 111, 81, 0);
            }
        }
        
        @keyframes hammockSway {
            0%, 100% { transform: rotate(-5deg); }
            50% { transform: rotate(5deg); }
        }
        
        @keyframes steamRise {
            0% {
                opacity: 0;
                transform: translateY(0) scale(0.8);
            }
            50% {
                opacity: 1;
            }
            100% {
                opacity: 0;
                transform: translateY(-50px) scale(1.2);
            }
        }
        
        .btn-pulse {
            animation: pulse 2s infinite;
        }
    `;
  document.head.appendChild(style);
}

// Parallax scrolling effect
function initParallax() {
  window.addEventListener("scroll", function () {
    const scrolled = window.pageYOffset;
    const parallaxElements = document.querySelectorAll(".parallax");

    parallaxElements.forEach((element) => {
      const speed = element.dataset.speed || 0.5;
      element.style.transform = `translateY(${scrolled * speed}px)`;
    });
  });
}

// Initialize all animations when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  if (ANIMATION_SETTINGS.enabled) {
    initScrollReveal();
    initHoverAnimations();
    initTypewriter();
    initFloatingAnimations();
    initParallax();
  }
});

// Coffee steam animation (for fun)
function createCoffeeSteam() {
  const coffeeElements = document.querySelectorAll(".fa-coffee, .coffee-icon");

  coffeeElements.forEach((coffee) => {
    const steam = document.createElement("div");
    steam.className = "coffee-steam";
    steam.style.cssText = `
            position: absolute;
            top: -20px;
            left: 50%;
            width: 20px;
            height: 40px;
            background: rgba(255,255,255,0.8);
            border-radius: 50%;
            filter: blur(5px);
            opacity: 0;
            transform: translateX(-50%);
        `;

    coffee.style.position = "relative";
    coffee.appendChild(steam);

    // Animate steam periodically
    setInterval(() => {
      steam.style.animation = "steamRise 3s ease-in-out";
      setTimeout(() => {
        steam.style.animation = "";
      }, 3000);
    }, 5000);
  });
}

// Call coffee steam on page load
window.addEventListener("load", createCoffeeSteam);

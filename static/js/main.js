// 734 Hotel - Main JavaScript File
document.addEventListener("DOMContentLoaded", function () {
  console.log("734 Hotel Website Loaded");

  // Initialize all features
  initNavigation();
  initVibeCheck();
  initGuestbook();
  initBookingForm();
  initContactForm();
  initAnimations();
  initMap();
  initEasterEgg();
  initBackpackCursor();
  initRoomBooking();

  // Admin notifications (if on admin page)
  if (window.location.pathname.includes("admin")) {
    initAdminNotifications();
  }
});

function smoothScrollToPosition(targetY, duration = 900) {
  const smoothness = ANIMATION_SETTINGS?.scrollSmoothness || "normal";
  const durationMultiplier =
    smoothness === "gentle" ? 1.15 : smoothness === "enhanced" ? 0.85 : 1;

  const startY = window.scrollY || window.pageYOffset;
  const distance = targetY - startY;

  if (Math.abs(distance) < 2) return;

  const easeInOutCubic = (t) =>
    t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

  let startTime = null;

  function animate(currentTime) {
    if (!startTime) startTime = currentTime;

    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / (duration * durationMultiplier), 1);
    const easedProgress = easeInOutCubic(progress);

    window.scrollTo(0, startY + distance * easedProgress);

    if (progress < 1) {
      window.requestAnimationFrame(animate);
    }
  }

  window.requestAnimationFrame(animate);
}

function smoothScrollToElement(targetElement, offset = 20, duration = 900) {
  if (!targetElement) return;

  const targetTop =
    targetElement.getBoundingClientRect().top + window.pageYOffset - offset;
  smoothScrollToPosition(targetTop, duration);
}

// Navigation functionality
function initNavigation() {
  const navToggle = document.getElementById("nav-toggle");
  const navLinks = document.getElementById("nav-links");
  const mainNav = document.querySelector(".main-nav");

  // Mobile menu toggle
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", function () {
      navToggle.classList.toggle("active");
      navLinks.classList.toggle("active");
    });

    // Close mobile menu when clicking a link
    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", function () {
        navToggle.classList.remove("active");
        navLinks.classList.remove("active");
      });
    });
  }

  // Smooth scrolling for navigation links
  document.querySelectorAll('a[href*="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const href = this.getAttribute("href");
      if (!href || href === "#") return;

      let targetUrl;
      try {
        targetUrl = new URL(href, window.location.origin);
      } catch (error) {
        return;
      }

      if (!targetUrl.hash) return;

      const isSamePageLink =
        targetUrl.origin === window.location.origin &&
        targetUrl.pathname === window.location.pathname;

      if (!isSamePageLink) return;

      const target = document.querySelector(targetUrl.hash);
      if (!target) return;

      e.preventDefault();

      const headerOffset = mainNav ? mainNav.offsetHeight : 0;
      smoothScrollToElement(target, headerOffset + 20, 850);

      // Update active link
      document.querySelectorAll(".nav-links a").forEach((link) => {
        link.classList.remove("active");
      });
      this.classList.add("active");
    });
  });

  // Update active navigation link on scroll
  function updateActiveNavLink() {
    const sections = document.querySelectorAll("section[id]");
    const scrollPosition = window.scrollY + 100;

    sections.forEach((section) => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      const sectionId = section.getAttribute("id");

      if (
        scrollPosition >= sectionTop &&
        scrollPosition < sectionTop + sectionHeight
      ) {
        document.querySelectorAll(".nav-links a").forEach((link) => {
          link.classList.remove("active");
          const linkHref = link.getAttribute("href") || "";
          if (linkHref.endsWith(`#${sectionId}`)) {
            link.classList.add("active");
          }
        });
      }
    });
  }

  // Add scroll event listener for active link updates
  window.addEventListener("scroll", updateActiveNavLink);
  updateActiveNavLink(); // Call once on load

  // Add scrolled class to navigation on scroll
  window.addEventListener("scroll", function () {
    if (window.scrollY > 50) {
      mainNav.classList.add("scrolled");
    } else {
      mainNav.classList.remove("scrolled");
    }
  });
}

// Vibe Check functionality
function initVibeCheck() {
  const polaroids = document.querySelectorAll(".polaroid");
  const audioPlayer = document.getElementById("vibe-audio-player");

  polaroids.forEach((polaroid) => {
    polaroid.addEventListener("click", function () {
      const itemId = this.dataset.itemId;

      if (!itemId) return;

      // Remove active class from all polaroids
      polaroids.forEach((p) => p.classList.remove("active"));

      // Add active class to clicked polaroid
      this.classList.add("active");

      // Show loading
      const guestNote = document.getElementById("guest-note");
      const guestInfo = document.getElementById("guest-info");
      guestNote.textContent = "Loading experience...";
      guestInfo.textContent = "";
      document.getElementById("guest-note-container").style.opacity = "1";

      // Fetch audio and guest note
      fetch(`/api/vibe-check/${itemId}/`)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          if (data.audio_url) {
            audioPlayer.src = data.audio_url;
            audioPlayer.style.display = "block";
            audioPlayer.play().catch((e) => {
              console.log("Autoplay prevented:", e);
              // Show play button
              audioPlayer.controls = true;
            });
          }

          if (data.guest_note) {
            guestNote.textContent = data.guest_note;
            guestInfo.textContent = `- ${data.guest_name}, ${data.guest_country}`;
          } else {
            guestNote.textContent =
              "Click another polaroid to experience our vibe!";
          }
        })
        .catch((error) => {
          console.error("Error loading vibe check:", error);
          guestNote.textContent = "Unable to load audio. Please try again.";
          guestInfo.textContent = "";
        });
    });
  });
}

// Guestbook functionality
function initGuestbook() {
  const guestbookForm = document.getElementById("guestbook-form");

  if (guestbookForm) {
    guestbookForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = new FormData(this);
      const submitBtn = this.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;

      // Show loading
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Pinning...';

      fetch("/api/guestbook/submit/", {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            showNotification(
              "Your note has been pinned to the wall!",
              "success",
            );
            guestbookForm.reset();

            // Reload guestbook entries after 2 seconds
            setTimeout(() => {
              loadGuestbookEntries();
            }, 2000);
          } else {
            showNotification(
              "Could not submit your note. Please try again.",
              "error",
            );
            console.error("Guestbook error:", data.errors);
          }

          // Reset button
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        })
        .catch((error) => {
          console.error("Guestbook submission error:", error);
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
          showNotification(
            "Network error. Please check your connection.",
            "error",
          );
        });
    });
  }

  // Add hover effects to sticky notes
  const stickyNotes = document.querySelectorAll(".sticky-note");
  stickyNotes.forEach((note) => {
    note.addEventListener("mouseenter", function () {
      this.style.transform = `translateY(-10px) rotate(${
        parseInt(this.style.getPropertyValue("--rotate") || 0) + 2
      }deg)`;
      this.style.boxShadow = "0 20px 40px rgba(0,0,0,0.15)";
      this.style.zIndex = "10";
    });

    note.addEventListener("mouseleave", function () {
      this.style.transform = "";
      this.style.boxShadow = "";
      this.style.zIndex = "";
    });
  });
}

// Booking form functionality
function initBookingForm() {
  const bookingForm = document.getElementById("booking-form");

  if (bookingForm) {
    const datepickerEnabled = FEATURES?.datepicker !== false;
    // Set min dates
    const today = new Date().toISOString().split("T")[0];
    const roomInput = bookingForm.querySelector(
      'select[name="room"], input[name="room"]',
    );
    const checkInInput = bookingForm.querySelector('input[name="check_in"]');
    const checkOutInput = bookingForm.querySelector('input[name="check_out"]');
    const legendNote = bookingForm.querySelector(".booking-date-legend-note");

    let availabilityMessage = bookingForm.querySelector(
      ".booking-availability-message",
    );
    if (!availabilityMessage && roomInput && roomInput.parentElement) {
      availabilityMessage = document.createElement("small");
      availabilityMessage.className = "booking-availability-message";
      availabilityMessage.style.display = "block";
      availabilityMessage.style.marginTop = "0.5rem";
      availabilityMessage.style.fontWeight = "500";
      roomInput.parentElement.appendChild(availabilityMessage);
    }

    function setAvailabilityMessage(message, type = "neutral") {
      if (!availabilityMessage) return;
      availabilityMessage.textContent = message || "";

      if (!message) {
        availabilityMessage.style.color = "";
        return;
      }

      if (type === "error") {
        availabilityMessage.style.color = "#E76F51";
      } else if (type === "success") {
        availabilityMessage.style.color = "#2A9D8F";
      } else {
        availabilityMessage.style.color = "#666";
      }
    }

    let checkInPicker = null;
    let checkOutPicker = null;

    function parseDateValue(value) {
      if (!value) return null;
      const [year, month, day] = value.split("-").map(Number);
      return new Date(year, month - 1, day);
    }

    function formatDateValue(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    }

    function shiftDate(value, days) {
      const date = parseDateValue(value);
      if (!date) return value;
      date.setDate(date.getDate() + days);
      return formatDateValue(date);
    }

    function buildDisabledRanges(unavailableRanges) {
      return (unavailableRanges || [])
        .filter((range) => range.check_in && range.check_out)
        .map((range) => ({
          from: range.check_in,
          to: shiftDate(range.check_out, -1),
        }));
    }

    async function loadRoomUnavailableRanges() {
      const roomId = roomInput ? roomInput.value : "";
      if (!roomId) return [];

      try {
        const query = new URLSearchParams({ room_id: roomId }).toString();
        const response = await fetch(`/api/bookings/availability/?${query}`);
        const data = await response.json();

        if (!response.ok || !data.success) {
          return [];
        }

        return buildDisabledRanges(data.unavailable_ranges);
      } catch (error) {
        console.error("Could not load unavailable ranges:", error);
        return [];
      }
    }

    async function refreshDatepickerAvailability() {
      if (!datepickerEnabled || typeof flatpickr === "undefined") return;

      const disabledRanges = await loadRoomUnavailableRanges();

      if (legendNote) {
        if (!roomInput || !roomInput.value) {
          legendNote.textContent = "Select a room to load blocked dates.";
        } else if (disabledRanges.length === 0) {
          legendNote.textContent = "No blocked dates for selected room.";
        } else {
          legendNote.textContent = `${disabledRanges.length} blocked date range(s) loaded.`;
        }
      }

      if (checkInPicker) {
        checkInPicker.set("disable", disabledRanges);
      }
      if (checkOutPicker) {
        checkOutPicker.set("disable", disabledRanges);
      }
    }

    function initBookingDatepicker() {
      if (!datepickerEnabled || typeof flatpickr === "undefined") {
        if (legendNote && !datepickerEnabled) {
          legendNote.textContent =
            "Datepicker is disabled from admin settings. Manual date entry is active.";
        }
        return;
      }
      if (!checkInInput || !checkOutInput) return;

      const baseOptions = {
        dateFormat: "Y-m-d",
        minDate: today,
        disableMobile: true,
      };

      checkInPicker = flatpickr(checkInInput, {
        ...baseOptions,
        onChange: function (selectedDates) {
          if (selectedDates[0]) {
            const nextDate = new Date(selectedDates[0]);
            nextDate.setDate(nextDate.getDate() + 1);
            if (checkOutPicker) {
              checkOutPicker.set("minDate", nextDate);
              if (
                checkOutInput.value &&
                parseDateValue(checkOutInput.value) <= selectedDates[0]
              ) {
                checkOutPicker.clear();
              }
            }
          } else if (checkOutPicker) {
            checkOutPicker.set("minDate", today);
          }

          checkAvailability(false);
        },
      });

      checkOutPicker = flatpickr(checkOutInput, {
        ...baseOptions,
        onChange: function () {
          checkAvailability(false);
        },
      });

      refreshDatepickerAvailability();
    }

    async function checkAvailability(showErrors = false) {
      const roomId = roomInput ? roomInput.value : "";
      const checkIn = checkInInput ? checkInInput.value : "";
      const checkOut = checkOutInput ? checkOutInput.value : "";

      if (!roomId || !checkIn || !checkOut) {
        setAvailabilityMessage("Select room and dates to check availability.");
        return true;
      }

      try {
        const query = new URLSearchParams({
          room_id: roomId,
          check_in: checkIn,
          check_out: checkOut,
        }).toString();

        const response = await fetch(`/api/bookings/availability/?${query}`);
        const data = await response.json();

        if (!response.ok || !data.success) {
          setAvailabilityMessage(
            data.error || "Could not verify availability right now.",
            "error",
          );
          if (showErrors) {
            showNotification(
              data.error || "Could not verify room availability.",
              "error",
            );
          }
          return false;
        }

        if (data.available) {
          setAvailabilityMessage(
            "Room is available for selected dates.",
            "success",
          );
          return true;
        }

        setAvailabilityMessage(
          "Selected dates are unavailable for this room.",
          "error",
        );
        if (showErrors) {
          showNotification(
            "Selected dates are unavailable. Please choose different dates.",
            "error",
          );
        }
        return false;
      } catch (error) {
        console.error("Availability check error:", error);
        setAvailabilityMessage(
          "Availability check failed. Try again.",
          "error",
        );
        if (showErrors) {
          showNotification("Could not check availability. Try again.", "error");
        }
        return false;
      }
    }

    if (checkInInput) checkInInput.min = today;
    if (checkOutInput) checkOutInput.min = today;

    initBookingDatepicker();

    [roomInput, checkInInput, checkOutInput].forEach((field) => {
      if (field) {
        field.addEventListener("change", () => {
          if (field === roomInput) {
            refreshDatepickerAvailability();
          }
          checkAvailability(false);
        });
      }
    });

    setAvailabilityMessage("Select room and dates to check availability.");

    bookingForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      // Basic validation
      const checkIn = checkInInput.value;
      const checkOut = checkOutInput.value;

      if (checkIn && checkOut) {
        if (new Date(checkOut) <= new Date(checkIn)) {
          showNotification(
            "Check-out date must be after check-in date.",
            "error",
          );
          return;
        }
      }

      const isAvailable = await checkAvailability(true);
      if (!isAvailable) {
        return;
      }

      const formData = new FormData(this);
      const submitBtn = this.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;

      // Show loading
      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Processing...';

      fetch("/api/bookings/submit/", {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            const message = data.manage_url
              ? `Booking submitted! Manage your booking here: ${data.manage_url}`
              : "Booking submitted! We'll contact you soon.";
            showNotification(message, "success");
            bookingForm.reset();

            // Show confirmation animation
            const bookingWidget = document.querySelector(".booking-widget");
            const checkmark = document.createElement("div");
            checkmark.className = "confirmation-checkmark";
            checkmark.innerHTML = '<i class="fas fa-check"></i>';
            checkmark.style.position = "absolute";
            checkmark.style.top = "50%";
            checkmark.style.left = "50%";
            checkmark.style.transform = "translate(-50%, -50%) scale(0)";
            checkmark.style.width = "80px";
            checkmark.style.height = "80px";
            checkmark.style.background = "#2A9D8F";
            checkmark.style.borderRadius = "50%";
            checkmark.style.display = "flex";
            checkmark.style.alignItems = "center";
            checkmark.style.justifyContent = "center";
            checkmark.style.fontSize = "2.5rem";
            checkmark.style.color = "white";
            checkmark.style.zIndex = "1000";

            bookingWidget.style.position = "relative";
            bookingWidget.appendChild(checkmark);

            // Animate
            setTimeout(() => {
              checkmark.style.transition = "all 0.5s ease";
              checkmark.style.transform = "translate(-50%, -50%) scale(1)";
            }, 10);

            setTimeout(() => {
              checkmark.style.transform = "translate(-50%, -50%) scale(0)";
              setTimeout(() => checkmark.remove(), 500);
            }, 1500);

            if (data.manage_url) {
              setTimeout(() => {
                window.location.href = data.manage_url;
              }, 1200);
            }
          } else {
            showNotification("Please check your information.", "error");
            console.error("Booking error:", data.errors);
          }

          // Reset button
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        })
        .catch((error) => {
          console.error("Booking submission error:", error);
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
          showNotification("Network error. Please try again.", "error");
        });
    });
  }
}

// Contact form functionality
function initContactForm() {
  const contactForm = document.getElementById("contact-form");

  if (contactForm) {
    contactForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = new FormData(this);
      const submitBtn = this.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;

      // Show loading
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

      fetch("/api/contact/submit/", {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            showNotification("Message sent! We'll reply soon.", "success");
            contactForm.reset();
          } else {
            showNotification("Could not send message.", "error");
          }

          // Reset button
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        })
        .catch((error) => {
          console.error("Contact submission error:", error);
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
          showNotification("Network error.", "error");
        });
    });
  }
}

// Animation initialization
function initAnimations() {
  // Scroll animations
  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.1,
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    });
  }, observerOptions);

  // Observe all animate-on-scroll elements
  document.querySelectorAll(".animate-on-scroll").forEach((el) => {
    observer.observe(el);
  });

  // Add hover effects to room cards
  const roomCards = document.querySelectorAll(".room-card");
  roomCards.forEach((card) => {
    card.addEventListener("mouseenter", function () {
      const effect = this.classList.contains("hover-scale")
        ? "scale(1.05)"
        : this.classList.contains("hover-slide")
          ? "translateY(-10px)"
          : this.classList.contains("hover-rotate")
            ? "rotate(2deg)"
            : "none";

      if (effect !== "none") {
        this.style.transform = effect;
      }
    });

    card.addEventListener("mouseleave", function () {
      this.style.transform = "";
    });
  });
}

// Map functionality
function initMap() {
  const mapElement = document.getElementById("neighborhood-map");

  if (mapElement && typeof L !== "undefined") {
    // Initialize map with Ghana-friendly default view
    const defaultCenter = [6.6885, -1.6244];
    const map = L.map("neighborhood-map", {
      zoomSnap: 0.5,
      zoomDelta: 0.5,
      minZoom: 5,
      maxZoom: 17,
      scrollWheelZoom: true,
      wheelDebounceTime: 80,
      wheelPxPerZoomLevel: 100,
      zoomControl: false,
    }).setView(defaultCenter, 12);

    // Add cleaner zoom control placement
    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Add "my location" button
    const locationControl = L.control({ position: "bottomright" });
    locationControl.onAdd = function () {
      const control = L.DomUtil.create(
        "button",
        "leaflet-bar map-location-btn",
      );
      control.type = "button";
      control.title = "Zoom to my location";
      control.setAttribute("aria-label", "Zoom to my location");
      control.innerHTML = '<i class="fas fa-location-arrow"></i>';

      L.DomEvent.disableClickPropagation(control);
      L.DomEvent.on(control, "click", function (e) {
        L.DomEvent.stop(e);
        map.locate({ setView: true, maxZoom: 14, enableHighAccuracy: true });
      });

      return control;
    };
    locationControl.addTo(map);

    map.on("locationerror", () => {
      showNotification("Could not access your location.", "error");
    });

    let fittedBounds = null;
    let fittedPad = 0.18;
    let fittedMaxZoom = 14;

    const refreshMapLayout = () => {
      map.invalidateSize();
      if (fittedBounds) {
        map.fitBounds(fittedBounds.pad(fittedPad), {
          maxZoom: fittedMaxZoom,
          animate: false,
        });
      }
    };

    // Add tile layer with proper attribution and CORS support
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
      minZoom: 0,
      crossOrigin: true,
      referrerPolicy: 'no-referrer'
    }).addTo(map);

    // Load points from API
    fetch("/api/neighborhood/points/")
      .then((response) => response.json())
      .then((data) => {
        if (data.points && data.points.length > 0) {
          const latLngs = [];

          data.points.forEach((point) => {
            const lat = Number.parseFloat(point.lat);
            const lng = Number.parseFloat(point.lng);

            if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
              return;
            }

            latLngs.push([lat, lng]);

            // Create custom icon
            const icon = L.divIcon({
              className: "custom-marker",
              html: `<div style="background-color: ${
                point.color
              }; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px;">
                                <i class="fas fa-${
                                  point.icon || "map-marker-alt"
                                }"></i>
                            </div>`,
              iconSize: [30, 30],
              iconAnchor: [15, 15],
            });

            // Add marker
            const marker = L.marker([lat, lng], {
              icon: icon,
            }).addTo(map);

            // Add popup
            marker.bindPopup(`
                            <div class="map-popup">
                                <h4>${point.title}</h4>
                                <p>${point.description}</p>
                                <span class="badge">${point.type}</span>
                            </div>
                        `);
          });

          // Fit bounds to show all markers
          if (latLngs.length > 0) {
            const bounds = L.latLngBounds(latLngs);
            fittedBounds = bounds;
            fittedPad = 0.18;
            fittedMaxZoom = 14;
            map.fitBounds(bounds.pad(0.18), { maxZoom: 14, animate: false });

            // Ensure proper fit after layout settles
            setTimeout(() => {
              refreshMapLayout();
            }, 250);
          }
        } else {
          // Add default markers if none exist
          const defaultPoints = [
            {
              lat: 6.6885,
              lng: -1.6244,
              title: "734 Hotel",
              description: "Your home away from home",
              color: "#E76F51",
              icon: "home",
            },
            {
              lat: 6.7009,
              lng: -1.6155,
              title: "New Dubai Restaurant",
              description: "Popular local food spot",
              color: "#2A9D8F",
              icon: "coffee",
            },
            {
              lat: 6.7044,
              lng: -1.6202,
              title: "Rattray Park",
              description: "Great place to relax",
              color: "#E9C46A",
              icon: "tree",
            },
          ];

          defaultPoints.forEach((point) => {
            const icon = L.divIcon({
              className: "custom-marker",
              html: `<div style="background-color: ${point.color}; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px;">
                                <i class="fas fa-${point.icon}"></i>
                            </div>`,
            });

            L.marker([point.lat, point.lng], { icon: icon })
              .addTo(map)
              .bindPopup(`<b>${point.title}</b><br>${point.description}`);
          });

          const defaultBounds = L.latLngBounds(
            defaultPoints.map((point) => [point.lat, point.lng]),
          );
          fittedBounds = defaultBounds;
          fittedPad = 0.2;
          fittedMaxZoom = 13;
          map.fitBounds(defaultBounds.pad(0.2), {
            maxZoom: 13,
            animate: false,
          });
        }
      })
      .catch((error) => {
        console.error("Error loading map points:", error);
      });

    // Keep map correctly sized when layout changes or viewport resizes
    setTimeout(() => {
      refreshMapLayout();
    }, 300);

    window.addEventListener("load", () => {
      setTimeout(() => {
        refreshMapLayout();
      }, 120);
    });

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setTimeout(() => {
                refreshMapLayout();
              }, 80);
            }
          });
        },
        { threshold: 0.2 },
      );
      observer.observe(mapElement);
    }

    window.addEventListener("resize", () => {
      refreshMapLayout();
    });
  }
}

// Room booking buttons
function initRoomBooking() {
  const bookButtons = document.querySelectorAll(".book-room-btn");

  bookButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const roomId = this.dataset.roomId;
      const roomName = this.dataset.roomName;

      // Scroll to booking section
      const bookingSection = document.getElementById("booking");
      if (bookingSection) {
        bookingSection.scrollIntoView({ behavior: "smooth" });

        // Auto-select the room in booking form
        const roomSelect = document.querySelector('select[name="room"]');
        if (roomSelect && roomId) {
          roomSelect.value = roomId;
          roomSelect.dispatchEvent(new Event("change", { bubbles: true }));
          showNotification(`Selected: ${roomName}`, "success");
        }
      }
    });
  });
}

// Easter Egg: Type "734" to light up string lights
function initEasterEgg() {
  let typedSequence = "";
  const stringLights = document.querySelectorAll(".string-light");

  // Create string lights if they don't exist
  if (stringLights.length === 0) {
    const lightsContainer = document.createElement("div");
    lightsContainer.className = "string-lights";
    lightsContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9998;
        `;

    for (let i = 0; i < 20; i++) {
      const light = document.createElement("div");
      light.className = "string-light";
      light.style.cssText = `
                position: absolute;
                top: 20px;
                left: ${(i + 1) * 5}%;
                width: 15px;
                height: 15px;
                background: #E9C46A;
                border-radius: 50%;
                opacity: 0.3;
                box-shadow: 0 0 5px #E9C46A;
                transition: all 0.3s ease;
            `;
      lightsContainer.appendChild(light);
    }

    document.body.appendChild(lightsContainer);
  }

  document.addEventListener("keydown", function (e) {
    typedSequence += e.key;

    // Keep only last 3 characters
    if (typedSequence.length > 3) {
      typedSequence = typedSequence.slice(-3);
    }

    // Check for "734"
    if (typedSequence === "734") {
      const lights = document.querySelectorAll(".string-light");

      // Light up string lights
      lights.forEach((light, index) => {
        setTimeout(() => {
          light.style.opacity = "1";
          light.style.boxShadow = "0 0 20px #E9C46A, 0 0 40px #E9C46A";
          light.style.transform = "scale(1.5)";

          setTimeout(() => {
            light.style.opacity = "0.3";
            light.style.boxShadow = "0 0 5px #E9C46A";
            light.style.transform = "scale(1)";
          }, 1000);
        }, index * 100);
      });

      // Play subtle sound (optional)
      try {
        const audio = new Audio("/static/audio/sparkle.mp3");
        audio.volume = 0.3;
        audio.play();
      } catch (e) {
        console.log("Audio not available");
      }

      // Show notification
      showNotification("✨ Secret code activated! ✨", "success");

      // Reset sequence
      typedSequence = "";
    }
  });
}

// Backpack cursor
function initBackpackCursor() {
  const links = document.querySelectorAll("a");

  // Create backpack cursor element
  const cursor = document.createElement("div");
  cursor.id = "backpack-cursor";
  cursor.style.cssText = `
        position: fixed;
        width: 32px;
        height: 32px;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23E76F51"><path d="M20 8v12c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2V8c0-1.86 1.28-3.41 3-3.86V2h3v2h4V2h3v2.14c1.72.45 3 2 3 3.86zM6 12v2h10v2h2v-4H6z"/></svg>');
        background-size: contain;
        pointer-events: none;
        z-index: 9999;
        opacity: 0;
        transition: opacity 0.3s;
        transform: translate(-50%, -50%);
    `;
  document.body.appendChild(cursor);

  links.forEach((link) => {
    link.addEventListener("mouseenter", function () {
      cursor.style.opacity = "1";
    });

    link.addEventListener("mouseleave", function () {
      cursor.style.opacity = "0";
    });
  });

  // Move cursor with mouse
  document.addEventListener("mousemove", function (e) {
    cursor.style.left = e.clientX + "px";
    cursor.style.top = e.clientY + "px";
  });
}

// Admin notifications
function initAdminNotifications() {
  const notificationBell = document.getElementById("notification-bell");

  if (notificationBell) {
    // Load notifications every 30 seconds
    loadAdminNotifications();
    setInterval(loadAdminNotifications, 30000);

    // Toggle dropdown
    notificationBell.addEventListener("click", function (e) {
      const dropdown = document.getElementById("notification-dropdown");
      dropdown.style.display =
        dropdown.style.display === "block" ? "none" : "block";
      e.stopPropagation();
    });

    // Mark as read when clicking notification
    document.addEventListener("click", function (e) {
      const dropdown = document.getElementById("notification-dropdown");
      if (!notificationBell.contains(e.target)) {
        dropdown.style.display = "none";
      }

      // Mark notification as read
      const notificationItem = e.target.closest(".notification-item");
      if (notificationItem && notificationItem.dataset.notificationId) {
        markNotificationAsRead(notificationItem.dataset.notificationId);
        notificationItem.classList.remove("unread");
      }
    });
  }
}

function loadAdminNotifications() {
  fetch("/api/admin/notifications/")
    .then((response) => response.json())
    .then((data) => {
      if (data.notifications) {
        updateNotificationDisplay(data.notifications);
      }
    })
    .catch((error) => console.error("Error loading notifications:", error));
}

function markNotificationAsRead(notificationId) {
  fetch(`/api/admin/notifications/${notificationId}/read/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
      "Content-Type": "application/json",
    },
  }).catch((error) =>
    console.error("Error marking notification as read:", error),
  );
}

function updateNotificationDisplay(notifications) {
  const notificationBell = document.getElementById("notification-bell");
  const badge = notificationBell.querySelector(".notification-badge");
  const dropdown = document.getElementById("notification-dropdown");
  const itemsContainer = dropdown.querySelector(".notification-items");

  // Update badge
  const unreadCount = notifications.filter((n) => !n.isRead).length;
  if (badge) {
    badge.textContent = unreadCount;
    badge.style.display = unreadCount > 0 ? "block" : "none";
  }

  // Update dropdown content
  itemsContainer.innerHTML = "";
  notifications.forEach((notification) => {
    const item = document.createElement("div");
    item.className = `notification-item ${notification.isRead ? "" : "unread"}`;
    item.dataset.notificationId = notification.id;
    item.innerHTML = `
            <div class="notification-type">${notification.type}</div>
            <div class="notification-message">${notification.message}</div>
            <div class="notification-time">${notification.created_at}</div>
        `;
    itemsContainer.appendChild(item);
  });

  if (notifications.length === 0) {
    itemsContainer.innerHTML =
      '<div class="notification-item empty">No new notifications</div>';
  }
}

// Utility functions
function showNotification(message, type = "info") {
  // Remove existing notifications
  document.querySelectorAll(".notification").forEach((n) => n.remove());

  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${
              type === "success"
                ? "check-circle"
                : type === "error"
                  ? "exclamation-circle"
                  : "info-circle"
            }"></i>
            <span>${message}</span>
        </div>
    `;

  notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${
          type === "success"
            ? "#2A9D8F"
            : type === "error"
              ? "#E76F51"
              : "#264653"
        };
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        transform: translateX(150%);
        transition: transform 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        max-width: 300px;
    `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.transform = "translateX(0)";
  }, 10);

  setTimeout(() => {
    notification.style.transform = "translateX(150%)";
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function loadGuestbookEntries() {
  fetch("/api/guestbook/entries/")
    .then((response) => response.json())
    .then((data) => {
      if (data.entries) {
        const wall = document.querySelector(".guestbook-wall");
        if (wall) {
          // Clear existing entries (except maybe first few default ones)
          wall.innerHTML = "";

          // Add new entries
          data.entries.forEach((entry) => {
            const note = document.createElement("div");
            note.className = "sticky-note";
            note.style.cssText = `
                            background-color: ${entry.color || "#E9C46A"};
                            transform: rotate(${Math.random() * 4 - 2}deg);
                        `;
            note.innerHTML = `
                            <h4>${entry.name}</h4>
                            <div class="hometown">${entry.hometown}</div>
                            <div class="message">${entry.message}</div>
                            <div class="date">${entry.created_at}</div>
                        `;
            wall.appendChild(note);
          });
        }
      }
    })
    .catch((error) => console.error("Error loading guestbook entries:", error));
}

// Smooth scrolling for anchor links
document.addEventListener("click", function (e) {
  if (e.defaultPrevented) return;

  const anchor = e.target.closest('a[href^="#"]');
  if (anchor) {
    e.preventDefault();
    const targetId = anchor.getAttribute("href");
    if (targetId === "#") return;

    const targetElement = document.querySelector(targetId);
    if (targetElement) {
      smoothScrollToElement(targetElement, 80, 900);
    }
  }
});

// Page load animation
window.addEventListener("load", function () {
  document.body.style.opacity = "0";
  document.body.style.transition = "opacity 0.5s ease";

  setTimeout(() => {
    document.body.style.opacity = "1";
  }, 100);
});

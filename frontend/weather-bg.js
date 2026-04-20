// Animated weather backgrounds via canvas.
// Weather codes: WMO (https://open-meteo.com/en/docs)

const CATEGORIES = {
  clear: [0],
  partly: [1, 2],
  overcast: [3],
  fog: [45, 48],
  drizzle: [51, 53, 55],
  rain: [61, 63, 65, 80, 81, 82],
  snow: [71, 73, 75, 77, 85, 86],
  storm: [95, 96, 99],
};

function categoryFor(code) {
  for (const [cat, codes] of Object.entries(CATEGORIES)) {
    if (codes.includes(code)) return cat;
  }
  return "overcast";
}

function isNight() {
  const h = new Date().getHours();
  return h < 6 || h >= 20;
}

export function startWeatherBg(canvas, weatherCode) {
  const ctx = canvas.getContext("2d");
  let width, height, dpr;
  let animId = 0;
  let particles = [];
  const cat = categoryFor(weatherCode);
  const night = isNight();

  function resize() {
    dpr = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function initParticles() {
    particles = [];
    if (cat === "rain" || cat === "drizzle" || cat === "storm") {
      const count = cat === "drizzle" ? 60 : cat === "storm" ? 180 : 130;
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          len: 10 + Math.random() * (cat === "drizzle" ? 8 : 18),
          speed: 4 + Math.random() * (cat === "drizzle" ? 4 : 10),
          opacity: 0.2 + Math.random() * 0.4,
        });
      }
    } else if (cat === "snow") {
      for (let i = 0; i < 90; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          r: 1 + Math.random() * 2.5,
          speed: 0.5 + Math.random() * 1.2,
          drift: (Math.random() - 0.5) * 0.6,
          opacity: 0.5 + Math.random() * 0.4,
        });
      }
    } else if (cat === "clear" && !night) {
      // no particles, sun rendered directly
    } else if (cat === "clear" && night) {
      // stars
      for (let i = 0; i < 80; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height * 0.7,
          r: Math.random() * 1.2,
          twinkle: Math.random() * Math.PI * 2,
        });
      }
    } else if (cat === "partly" || cat === "overcast" || cat === "fog") {
      // floating clouds — simple blobs
      const count = cat === "partly" ? 4 : cat === "overcast" ? 6 : 8;
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * width,
          y: 30 + Math.random() * (height * 0.5),
          w: 120 + Math.random() * 200,
          speed: 0.15 + Math.random() * 0.3,
          opacity: 0.12 + Math.random() * 0.18,
        });
      }
    }
  }

  // Base gradient per category
  function drawBase() {
    let grad;
    if (night) {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#020617");
      grad.addColorStop(1, "#0f172a");
    } else if (cat === "clear") {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#0c4a6e");
      grad.addColorStop(0.5, "#0369a1");
      grad.addColorStop(1, "#0f172a");
    } else if (cat === "rain" || cat === "drizzle") {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#1e293b");
      grad.addColorStop(1, "#0f172a");
    } else if (cat === "storm") {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#1e1b4b");
      grad.addColorStop(1, "#0f172a");
    } else if (cat === "snow") {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#334155");
      grad.addColorStop(1, "#0f172a");
    } else if (cat === "fog") {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#475569");
      grad.addColorStop(1, "#0f172a");
    } else {
      grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#1e293b");
      grad.addColorStop(1, "#0f172a");
    }
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);
  }

  function drawSun() {
    const cx = width * 0.8, cy = height * 0.2, r = 60;
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 3);
    g.addColorStop(0, "rgba(251, 191, 36, 0.7)");
    g.addColorStop(0.3, "rgba(251, 191, 36, 0.25)");
    g.addColorStop(1, "rgba(251, 191, 36, 0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(253, 224, 71, 0.9)";
    ctx.fill();
  }

  function drawMoon() {
    const cx = width * 0.8, cy = height * 0.18, r = 36;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(226, 232, 240, 0.85)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx + 12, cy - 4, r, 0, Math.PI * 2);
    ctx.fillStyle = "#0f172a";
    ctx.fill();
  }

  let lightningTimer = 0;
  function render() {
    drawBase();

    if (cat === "clear" && !night) drawSun();
    if (cat === "clear" && night) drawMoon();

    if (cat === "rain" || cat === "drizzle" || cat === "storm") {
      ctx.strokeStyle = "rgba(148, 197, 255, 0.6)";
      ctx.lineWidth = 1;
      for (const p of particles) {
        ctx.globalAlpha = p.opacity;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x - 1, p.y + p.len);
        ctx.stroke();
        p.y += p.speed;
        p.x -= 0.5;
        if (p.y > height) { p.y = -p.len; p.x = Math.random() * width; }
      }
      ctx.globalAlpha = 1;
      if (cat === "storm") {
        lightningTimer++;
        if (lightningTimer > 200 && Math.random() < 0.02) {
          ctx.fillStyle = "rgba(255,255,255,0.6)";
          ctx.fillRect(0, 0, width, height);
          lightningTimer = 0;
        }
      }
    } else if (cat === "snow") {
      ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
      for (const p of particles) {
        ctx.globalAlpha = p.opacity;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
        p.y += p.speed;
        p.x += p.drift;
        if (p.y > height) { p.y = -5; p.x = Math.random() * width; }
        if (p.x < 0) p.x = width; else if (p.x > width) p.x = 0;
      }
      ctx.globalAlpha = 1;
    } else if (cat === "clear" && night) {
      for (const p of particles) {
        p.twinkle += 0.05;
        const a = 0.4 + Math.sin(p.twinkle) * 0.3;
        ctx.globalAlpha = a;
        ctx.fillStyle = "#e2e8f0";
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    } else if (cat === "partly" || cat === "overcast" || cat === "fog") {
      for (const p of particles) {
        ctx.globalAlpha = p.opacity;
        ctx.fillStyle = cat === "fog" ? "#cbd5e1" : "#e2e8f0";
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, p.w / 2, p.w / 5, 0, 0, Math.PI * 2);
        ctx.fill();
        p.x += p.speed;
        if (p.x - p.w > width) p.x = -p.w;
      }
      ctx.globalAlpha = 1;
    }

    animId = requestAnimationFrame(render);
  }

  resize();
  initParticles();
  render();

  window.addEventListener("resize", () => {
    resize();
    initParticles();
  });

  return () => cancelAnimationFrame(animId);
}

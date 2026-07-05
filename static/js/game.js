/**
 * game.js
 * -------
 * منطق واجهة اللعبة: إرسال الضغطات، مزامنة الإنتاج التلقائي دوريًا، شراء التطويرات.
 * كل طلب يحمل رمز CSRF في الهيدر X-CSRF-Token.
 */

(function () {
  const wrapper = document.querySelector(".game-wrapper");
  if (!wrapper) return; // لسنا في صفحة اللعبة

  const csrfToken = wrapper.dataset.csrf;
  const collectBtn = document.getElementById("collect-btn");
  const floatingLayer = document.getElementById("floating-numbers");
  const balanceW = document.getElementById("balance-w");
  const balanceGems = document.getElementById("balance-gems");
  const balanceCrowns = document.getElementById("balance-crowns");

  function fmt(n) {
    return Math.floor(n).toLocaleString("en-US");
  }

  function setBalance(balance) {
    if (!balance) return;
    balanceW.textContent = fmt(balance.w);
    balanceGems.textContent = fmt(balance.gems);
    balanceCrowns.textContent = fmt(balance.crowns);
  }

  function spawnFloatingNumber(text, isCritical) {
    const el = document.createElement("div");
    el.className = "float-num" + (isCritical ? " critical" : "");
    el.textContent = text;
    const x = 40 + Math.random() * 20; // نسبة مئوية تقريبية داخل منطقة الزر
    el.style.left = x + "%";
    el.style.top = "35%";
    floatingLayer.appendChild(el);
    setTimeout(() => el.remove(), 950);
  }

  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  // ---------- الضغط اليدوي ----------
  let clickInFlight = false;
  collectBtn.addEventListener("click", async () => {
    // تأثير بصري فوري (تفاؤلي) قبل رد السيرفر لسلاسة أكبر
    collectBtn.style.transform = "scale(0.92)";
    setTimeout(() => (collectBtn.style.transform = ""), 90);

    if (clickInFlight) return;
    clickInFlight = true;
    try {
      const data = await apiPost("/api/click", {});
      if (data.success) {
        let text = "+" + fmt(data.gained_w) + " W";
        if (data.is_critical) text = "💥 " + text;
        spawnFloatingNumber(text, data.is_critical);
        if (data.gems_won > 0) {
          spawnFloatingNumber("+" + data.gems_won + " 💎", false);
        }
        setBalance(data.balance);
      }
    } catch (e) {
      console.error("click error", e);
    } finally {
      clickInFlight = false;
    }
  });

  // ---------- مزامنة الإنتاج التلقائي (روبوت / جمجمة / auto-click) ----------
  const SYNC_INTERVAL_MS = 5000;
  async function syncProduction() {
    try {
      const data = await apiPost("/api/sync", {});
      if (data.success) {
        setBalance(data.balance);
      }
    } catch (e) {
      console.error("sync error", e);
    }
  }
  setInterval(syncProduction, SYNC_INTERVAL_MS);

  // ---------- شراء التطويرات ----------
  document.querySelectorAll(".btn-upgrade").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const key = btn.dataset.key;
      btn.disabled = true;
      try {
        const data = await apiPost("/api/upgrade", { building_key: key });
        if (data.success) {
          const card = document.querySelector(`.building-card[data-key="${key}"]`);
          card.querySelector(".level-value").textContent = data.new_level;
          // تحديث الرصيد محليًا (خصم السعر المدفوع) فورًا، ثم مزامنة كاملة لضبط كل الأسعار الجديدة
          const currentW = parseFloat(balanceW.textContent.replace(/,/g, "")) - data.paid;
          balanceW.textContent = fmt(currentW);
          refreshState();
        } else {
          alert(data.error || "تعذر الشراء");
        }
      } catch (e) {
        console.error("upgrade error", e);
      } finally {
        btn.disabled = false;
      }
    });
  });

  // ---------- إعادة تحميل حالة المباني (الأسعار والمستويات) بعد أي تطوير ----------
  async function refreshState() {
    try {
      const res = await fetch("/api/state");
      const data = await res.json();
      if (!data.success) return;
      setBalance(data.balance);
      data.buildings.forEach((b) => {
        const card = document.querySelector(`.building-card[data-key="${b.key_name}"]`);
        if (!card) return;
        card.querySelector(".level-value").textContent = b.level;
        card.querySelector(".price-value").textContent = fmt(b.next_price);
        card.dataset.price = b.next_price;
      });
    } catch (e) {
      console.error("state refresh error", e);
    }
  }
})();

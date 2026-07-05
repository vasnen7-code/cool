/**
 * auth.js
 * -------
 * زر "إرسال الرمز" في صفحتي التسجيل واستعادة كلمة المرور.
 * يطلب من السيرفر توليد رمز OTP جديد (السيرفر لا يُعيد الرمز أبدًا في الاستجابة؛
 * المستخدم يستلمه فقط من داخل بوت تيليجرام بعد الضغط على زر OTP هناك).
 */

(function () {
  const btn = document.getElementById("send-otp-btn");
  if (!btn) return;

  const statusEl = document.getElementById("otp-status");
  const purpose = btn.dataset.purpose; // "register" أو "reset"
  const form = btn.closest("form");
  const csrfToken = form.querySelector('input[name="csrf_token"]').value;

  const COOLDOWN_SECONDS = 45;
  let cooldownRemaining = 0;
  let cooldownTimer = null;

  function startCooldown() {
    cooldownRemaining = COOLDOWN_SECONDS;
    btn.disabled = true;
    updateBtnText();
    cooldownTimer = setInterval(() => {
      cooldownRemaining -= 1;
      if (cooldownRemaining <= 0) {
        clearInterval(cooldownTimer);
        btn.disabled = false;
        btn.textContent = "إعادة إرسال الرمز";
      } else {
        updateBtnText();
      }
    }, 1000);
  }

  function updateBtnText() {
    btn.textContent = `إعادة الإرسال بعد ${cooldownRemaining}ث`;
  }

  btn.addEventListener("click", async () => {
    let endpoint, payload;

    if (purpose === "register") {
      const telegramId = document.getElementById("telegram_id").value.trim();
      if (!/^\d{5,15}$/.test(telegramId)) {
        statusEl.textContent = "أدخل آيدي تيليجرام صحيح (أرقام فقط) قبل طلب الرمز";
        statusEl.className = "otp-status error";
        return;
      }
      endpoint = "/api/otp/request-register";
      payload = { csrf_token: csrfToken, telegram_id: telegramId };
    } else {
      const username = document.getElementById("username").value.trim();
      if (!username) {
        statusEl.textContent = "أدخل اسم المستخدم قبل طلب الرمز";
        statusEl.className = "otp-status error";
        return;
      }
      endpoint = "/api/otp/request-reset";
      payload = { csrf_token: csrfToken, username: username };
    }

    btn.disabled = true;
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (data.success) {
        statusEl.textContent = "✅ تم إرسال الرمز، افتح بوت OTP واضغط زر OTP لاستلامه";
        statusEl.className = "otp-status success";
        startCooldown();
      } else {
        statusEl.textContent = "❌ " + (data.error || "تعذر إرسال الرمز");
        statusEl.className = "otp-status error";
        btn.disabled = false;
      }
    } catch (e) {
      statusEl.textContent = "❌ خطأ في الاتصال، حاول مرة أخرى";
      statusEl.className = "otp-status error";
      btn.disabled = false;
    }
  });
})();

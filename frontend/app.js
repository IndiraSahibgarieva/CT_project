function resolveApiBase() {
  // Способ 1 — window.location.origin (самый надёжный в Telegram WebView)
  try {
    const origin = window.location.origin;
    if (origin && origin !== "null" && origin !== "about:blank" && !origin.includes("telegram.org")) {
      const base = origin + "/api";
      console.log("API_BASE from location.origin:", base);
      return base;
    }
  } catch (e) { console.warn("location.origin failed:", e); }

  // Способ 2 — window.location.href
  try {
    const href = window.location.href;
    if (href && !href.includes("telegram.org")) {
      const base = new URL("/api", href).href.replace(/\/$/, "");
      console.log("API_BASE from location.href:", base);
      return base;
    }
  } catch (e) { console.warn("location.href failed:", e); }

  // Способ 3 — из src скрипта, только если не telegram.org
  try {
    const script = document.querySelector('script[src*="app.js"]');
    if (script && script.src && script.src.startsWith("http") && !script.src.includes("telegram.org")) {
      const base = new URL("/api", script.src).href.replace(/\/$/, "");
      console.log("API_BASE from script.src:", base);
      return base;
    }
  } catch (e) { console.warn("script.src failed:", e); }

  // Fallback — относительный путь
  console.log("API_BASE fallback: /api");
  return "/api";
}
const API_BASE = resolveApiBase();

let accessToken = "";
let connectedWallet = "";

const authForm = document.getElementById("authForm");
const nonceBox = document.getElementById("nonceBox");
const authStatus = document.getElementById("authStatus");
const initDataInput = document.getElementById("initDataInput");
const telegramLoginBtn = document.getElementById("telegramLoginBtn");
const connectMetamaskBtn = document.getElementById("connectMetamaskBtn");
const getNonceBtn = document.getElementById("getNonceBtn");
const signMetamaskBtn = document.getElementById("signMetamaskBtn");
const verifyBtn = document.getElementById("verifyBtn");
const signatureLabel = document.getElementById("signatureLabel");
const balanceValue = document.getElementById("balanceValue");
const badgesList = document.getElementById("badgesList");
const notificationsList = document.getElementById("notificationsList");
const broadcastForm = document.getElementById("broadcastForm");
const broadcastStatus = document.getElementById("broadcastStatus");
const adminCard = document.querySelector(".admin-card");
const transferCard = document.getElementById("transferCard");
const transferForm = document.getElementById("transferForm");
const transferStatus = document.getElementById("transferStatus");
const transferBtn = document.getElementById("transferBtn");

async function postJSON(url, body) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "API error");
  }
  return res.json();
}

async function getJSON(url) {
  const headers = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "API error");
  }
  return res.json();
}

function getTelegramInitData() {
  try {
    if (window.Telegram && window.Telegram.WebApp) {
      return window.Telegram.WebApp.initData || "";
    }
  } catch (e) {
    console.error("getTelegramInitData error:", e);
  }
  return "";
}

async function telegramLogin() {
  const initData = initDataInput.value.trim() || getTelegramInitData();
  console.log("API_BASE:", API_BASE);
  console.log("initData length:", initData.length);
  if (!initData) {
    authStatus.textContent = "Откройте приложение в Telegram WebApp или вставьте initData.";
    return;
  }
  const result = await postJSON(`${API_BASE}/auth/telegram`, { init_data: initData });
  accessToken = result.access_token || "";
  localStorage.setItem("twa_token", accessToken);
  authStatus.textContent = `Telegram auth успешен. Роль: ${result.role}.`;
  const me = await getJSON(`${API_BASE}/auth/me`);
  document.getElementById("telegramId").value = me.telegram_id;
  adminCard.style.display = me.role === "admin" ? "block" : "none";
}

function renderDashboard(data) {
  balanceValue.textContent = `${data.balance_fa} FA`;
  badgesList.innerHTML = "";
  data.badges.forEach((badge) => {
    const li = document.createElement("li");
    li.textContent = badge;
    badgesList.appendChild(li);
  });
  notificationsList.innerHTML = "";
  data.notifications.forEach((n) => {
    const li = document.createElement("li");
    li.textContent = n;
    notificationsList.appendChild(li);
  });
  transferCard.style.display = "block";
}

// ── Подключить MetaMask ───────────────────────────────────────────────────
connectMetamaskBtn.addEventListener("click", async () => {
  authStatus.textContent = "";

  if (!window.ethereum) {
    // Передаём Telegram данные через URL-параметры
    const tgId = document.getElementById("telegramId").value || "";
    const initData = initDataInput.value.trim() || getTelegramInitData();
    const params = new URLSearchParams();
    if (tgId) params.set("tg_id", tgId);
    if (initData) params.set("init_data", encodeURIComponent(initData));
    const appUrl = `${window.location.host}${window.location.pathname}?${params.toString()}`;
    const metamaskUrl = `https://metamask.app.link/dapp/${appUrl}`;
    window.location.href = metamaskUrl;
    return;
  }

  try {
    connectMetamaskBtn.textContent = "Подключение...";
    connectMetamaskBtn.disabled = true;

    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    connectedWallet = accounts[0];
    document.getElementById("walletAddress").value = connectedWallet;

    connectMetamaskBtn.textContent = `✓ ${connectedWallet.slice(0, 6)}...${connectedWallet.slice(-4)}`;
    authStatus.textContent = "Кошелёк подключён. Нажмите «Шаг 1» для получения сообщения.";
  } catch (error) {
    authStatus.textContent = `Ошибка подключения: ${error.message}`;
    connectMetamaskBtn.textContent = "🦊 Подключить MetaMask";
    connectMetamaskBtn.disabled = false;
  }
});

// ── Шаг 1 — получить nonce ────────────────────────────────────────────────
getNonceBtn.addEventListener("click", async () => {
  authStatus.textContent = "";
  if (!accessToken) {
    authStatus.textContent = "Сначала выполните вход через Telegram.";
    return;
  }
  const telegram_id = Number(document.getElementById("telegramId").value);
  const wallet_address = document.getElementById("walletAddress").value.trim();
  if (!telegram_id) {
    authStatus.textContent = "Заполните поле Telegram ID.";
    return;
  }
  if (!wallet_address || wallet_address.length !== 42) {
    authStatus.textContent = "Введите корректный адрес кошелька (42 символа, начинается с 0x). Или нажмите «Подключить MetaMask».";
    return;
  }
  try {
    getNonceBtn.textContent = "Загрузка...";
    getNonceBtn.disabled = true;
    const nonceData = await postJSON(`${API_BASE}/auth/nonce`, { telegram_id, wallet_address });
    nonceBox.textContent = "Сообщение для подписи:\n\n" + nonceData.challenge_message;
    nonceBox.style.display = "block";
    nonceBox.dataset.message = nonceData.challenge_message;

    // Показываем кнопку MetaMask если он доступен, иначе ручное поле
    if (window.ethereum) {
      signMetamaskBtn.style.display = "block";
      signatureLabel.style.display = "none";
      verifyBtn.style.display = "none";
    } else {
      signMetamaskBtn.style.display = "none";
      signatureLabel.style.display = "grid";
      verifyBtn.style.display = "block";
    }

    authStatus.textContent = window.ethereum
      ? "Нажмите «Подписать через MetaMask» — MetaMask откроется автоматически."
      : "Скопируйте сообщение, подпишите в MetaMask и вставьте подпись ниже.";
  } catch (error) {
    authStatus.textContent = `Ошибка: ${error.message}`;
  } finally {
    getNonceBtn.textContent = "Шаг 1 — Получить сообщение для подписи";
    getNonceBtn.disabled = false;
  }
});

// ── Подписать через MetaMask автоматически ────────────────────────────────
signMetamaskBtn.addEventListener("click", async () => {
  authStatus.textContent = "";
  const wallet_address = document.getElementById("walletAddress").value.trim();
  const message = nonceBox.dataset.message;

  if (!message) {
    authStatus.textContent = "Сначала получите сообщение (Шаг 1).";
    return;
  }

  try {
    signMetamaskBtn.textContent = "Ожидание подписи...";
    signMetamaskBtn.disabled = true;

    const signature = await window.ethereum.request({
      method: "personal_sign",
      params: [message, wallet_address],
    });

    // Автоматически верифицируем
    authStatus.textContent = "Подпись получена, проверяем...";
    const telegram_id = Number(document.getElementById("telegramId").value);
    await postJSON(`${API_BASE}/auth/verify`, { telegram_id, wallet_address, signature });

    authStatus.textContent = "✓ Кошелёк успешно привязан!";
    nonceBox.style.display = "none";
    signMetamaskBtn.style.display = "none";

    const dashboard = await getJSON(`${API_BASE}/dashboard/me`);
    renderDashboard(dashboard);
  } catch (error) {
    authStatus.textContent = `Ошибка: ${error.message}`;
    signMetamaskBtn.textContent = "Подписать через MetaMask";
    signMetamaskBtn.disabled = false;
  }
});

// ── Шаг 2 — ручная верификация (fallback) ────────────────────────────────
authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authStatus.textContent = "";
  if (!accessToken) {
    authStatus.textContent = "Сначала выполните вход через Telegram.";
    return;
  }
  const telegram_id = Number(document.getElementById("telegramId").value);
  const wallet_address = document.getElementById("walletAddress").value.trim();
  const signature = document.getElementById("signature").value.trim();
  if (!signature) {
    authStatus.textContent = "Вставьте подпись из MetaMask в поле Signature.";
    return;
  }
  try {
    verifyBtn.textContent = "Проверка...";
    verifyBtn.disabled = true;
    await postJSON(`${API_BASE}/auth/verify`, { telegram_id, wallet_address, signature });
    authStatus.textContent = "✓ Кошелёк успешно привязан!";
    nonceBox.style.display = "none";
    signatureLabel.style.display = "none";
    verifyBtn.style.display = "none";
    document.getElementById("signature").value = "";
    const dashboard = await getJSON(`${API_BASE}/dashboard/me`);
    renderDashboard(dashboard);
  } catch (error) {
    authStatus.textContent = `Ошибка: ${error.message}`;
  } finally {
    verifyBtn.textContent = "Шаг 2 — Подключить кошелёк";
    verifyBtn.disabled = false;
  }
});

broadcastForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  broadcastStatus.textContent = "";
  const message = document.getElementById("broadcastMessage").value.trim();
  if (!message) {
    broadcastStatus.textContent = "Введите текст рассылки.";
    return;
  }
  try {
    const result = await postJSON(`${API_BASE}/admin/broadcast`, { message, audience: "all" });
    broadcastStatus.textContent = `Поставлено в очередь. Получателей: ${result.delivered}.`;
  } catch (error) {
    broadcastStatus.textContent = `Ошибка: ${error.message}`;
  }
});

transferForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  transferStatus.textContent = "";
  const to_wallet = document.getElementById("transferTo").value.trim();
  const amount = parseFloat(document.getElementById("transferAmount").value);

  if (!to_wallet || to_wallet.length !== 42 || !to_wallet.startsWith("0x")) {
    transferStatus.textContent = "Введите корректный адрес получателя (0x..., 42 символа).";
    return;
  }
  if (!amount || amount <= 0) {
    transferStatus.textContent = "Введите сумму больше нуля.";
    return;
  }

  try {
    transferBtn.textContent = "Отправка...";
    transferBtn.disabled = true;
    const result = await postJSON(`${API_BASE}/transfer`, { to_wallet, amount });
    transferStatus.textContent = result.message;
    if (result.new_balance !== null && result.new_balance !== undefined) {
      balanceValue.textContent = `${result.new_balance} FA`;
    }
    document.getElementById("transferTo").value = "";
    document.getElementById("transferAmount").value = "";
  } catch (error) {
    transferStatus.textContent = `Ошибка: ${error.message}`;
  } finally {
    transferBtn.textContent = "Отправить FA токены";
    transferBtn.disabled = false;
  }
});

telegramLoginBtn.addEventListener("click", async () => {
  try {
    await telegramLogin();
  } catch (error) {
    console.error("telegramLogin error:", error);
    authStatus.textContent = `Ошибка Telegram auth: ${error.message}`;
  }
});

window.addEventListener("DOMContentLoaded", async () => {
  if (window.Telegram && window.Telegram.WebApp) {
    try {
      window.Telegram.WebApp.ready();
      initDataInput.value = window.Telegram.WebApp.initData || "";
    } catch (e) {
      console.error("Telegram WebApp init error:", e);
    }
  }

  // Показать кнопку MetaMask всегда
  connectMetamaskBtn.style.display = "block";

  // Подхватываем данные из URL-параметров (после редиректа в MetaMask)
  const urlParams = new URLSearchParams(window.location.search);
  const urlTgId = urlParams.get("tg_id");
  const urlInitData = urlParams.get("init_data");

  if (urlTgId) {
    document.getElementById("telegramId").value = urlTgId;
    authStatus.textContent = "Telegram ID загружен из URL.";
  }
  if (urlInitData) {
    initDataInput.value = decodeURIComponent(urlInitData);
  }

  // Если есть init_data в URL — автоматически логинимся
  if (urlInitData && !localStorage.getItem("twa_token")) {
    try {
      authStatus.textContent = "Выполняем вход через Telegram...";
      await telegramLogin();
      authStatus.textContent = "✓ Вход выполнен. Теперь подключите MetaMask.";
    } catch (e) {
      authStatus.textContent = "Ошибка автовхода: " + e.message;
    }
    return;
  }

  accessToken = localStorage.getItem("twa_token") || "";
  adminCard.style.display = "none";
  if (!accessToken) return;
  try {
    const me = await getJSON(`${API_BASE}/auth/me`);
    document.getElementById("telegramId").value = me.telegram_id;
    adminCard.style.display = me.role === "admin" ? "block" : "none";
    const dashboard = await getJSON(`${API_BASE}/dashboard/me`);
    renderDashboard(dashboard);
    authStatus.textContent = "Сессия восстановлена.";
  } catch {
    localStorage.removeItem("twa_token");
    accessToken = "";
  }
});

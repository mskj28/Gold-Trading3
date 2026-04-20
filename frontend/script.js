// ================= ELEMENT =================
const signalEl = document.getElementById("signal");
const reasonEl = document.getElementById("reason");
const timerEl = document.getElementById("timer");
const historyEl = document.getElementById("history");
const dateEl = document.getElementById("date");
const newsContainer = document.getElementById("newsContainer");

dateEl.innerText = new Date().toLocaleDateString("th-TH");

// ================= API =================
async function getDashboard() {
    try {
        // Use new AI proxy endpoint
        const res = await fetch("/api/ai/status");
        const data = await res.json();
        return data;
    } catch (err) {
        return null;
    }
}

// ================= HISTORY =================
function saveHistory(signal, reason) {
    let history = JSON.parse(localStorage.getItem("history")) || [];

    const now = new Date();
    const minutes = Math.floor(now.getMinutes() / 15) * 15;

    const t = new Date(now);
    t.setMinutes(minutes);
    t.setSeconds(0);
    t.setMilliseconds(0);

    const newTime = t.getTime();

    if (history.some(h => h.time === newTime)) return;

    history.push({ signal, reason, time: newTime });

    if (history.length > 5) {
        history = history.slice(-5);
    }

    localStorage.setItem("history", JSON.stringify(history));
}

function getSignalIcon(signal) {
    if (signal === "BUY") return "▲";
    if (signal === "SELL") return "▼";
    return "●";
}

function loadHistory() {
    let history = JSON.parse(localStorage.getItem("history")) || [];

    historyEl.innerHTML = "";

    history
        .sort((a, b) => b.time - a.time)
        .forEach(h => {
            let div = document.createElement("div");

            // เพิม class เรื่องสี
            div.classList.add("history-item", h.signal.toLowerCase());

            let date = new Date(h.time);

            div.innerHTML = `
                <b>${getSignalIcon(h.signal)} ${h.signal}</b><br>
                ${h.reason}<br>
                เวลา ${date.toLocaleTimeString("th-TH")} 
                วันที่ ${date.toLocaleDateString("th-TH")}
            `;

            historyEl.appendChild(div);
        });
}

// ================= NEWS =================
function renderNews(newsList) {
    newsContainer.innerHTML = "";

    newsList.slice(0, 5).forEach(news => {

        let keyword = encodeURIComponent(
            (news.title || "gold finance").split(" ").slice(0, 3).join(" ")
        );

        let img = `https://source.unsplash.com/400x250/?${keyword}`;

        let color = "gray";
        if (news.sentiment === "positive") color = "green";
        if (news.sentiment === "negative") color = "red";

        const div = document.createElement("div");
        div.classList.add("news-card");

        // 🔥 ทำให้ทั้ง block คลิกได้
        div.style.cursor = "pointer";
        div.onclick = () => {
            window.open(news.url, "_blank");
        };

        div.innerHTML = `
            <div class="news-image">
                <img src="${img}">
                <div class="news-title">
                    ${news.title}
                </div>
            </div>

            <div class="news-content">
                <p>${news.summary || ""}</p>
                <span style="color:${color}">
                    ● ${news.sentiment || "neutral"}
                </span>
            </div>
        `;

        newsContainer.appendChild(div);
    });
}

// ================= ANALYZE =================
let lastSavedTime = null;

async function analyze() {
    const now = new Date();
    const minutes = Math.floor(now.getMinutes() / 15) * 15;
    const t = new Date(now);
    t.setMinutes(minutes);
    t.setSeconds(0);
    t.setMilliseconds(0);
    const currentRound = t.getTime();
    if (lastSavedTime === currentRound) return;
    lastSavedTime = currentRound;
    // Use new AI analyze endpoint
    let res = await fetch("/api/ai/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    let data = await res.json();
    if (!data || data.error) {
        signalEl.innerText = "ERROR";
        reasonEl.innerText = "ไม่สามารถดึงข้อมูลได้";
        return;
    }
    let signal = data.ai_action || "HOLD";
    let confidence = data.confidence || 0;
    let reason = `AI Signal<br>Confidence: ${(confidence * 100).toFixed(2)}%<br>${data.ai_reason || ""}`;
    signalEl.innerText = signal;
    signalEl.className = "signal-btn " + signal.toLowerCase();
    reasonEl.innerHTML = reason;
    saveHistory(signal, reason);
    loadHistory();
    // ✅ NEWS (if available)
    if (Array.isArray(data.raw_reports)) {
        renderNews(data.raw_reports);
    }
}

// ================= TIMER =================
function getSecondsToNextInterval() {
    const now = new Date();

    const nextMinute = Math.ceil(now.getMinutes() / 15) * 15;

    let target = new Date(now);
    target.setMinutes(nextMinute);
    target.setSeconds(0);

    if (nextMinute === 60) {
        target.setHours(now.getHours() + 1);
        target.setMinutes(0);
    }

    return Math.floor((target - now) / 1000);
}

function formatTime(sec) {
    let m = Math.floor(sec / 60);
    let s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
}

function startTimer() {
    let timeLeft = getSecondsToNextInterval();

    timerEl.innerText = formatTime(timeLeft);

    setInterval(() => {
        timeLeft--;

        if (timeLeft <= 0) {
            analyze();
            timeLeft = getSecondsToNextInterval(); // recalc for real 15-min interval
        }

        timerEl.innerText = formatTime(timeLeft);
    }, 1000);
}

// ================= INIT =================
async function init() {
    loadHistory();

    let data = await getDashboard();

    // โหลดข่าวทันทีตอนเปิด
    if (data && Array.isArray(data.news)) {
        renderNews(data.news);
    }

    analyze();
    startTimer();
}

init();
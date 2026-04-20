import React, { useEffect, useState, useRef } from "react";
import ThaiGoldChart from "./ThaiGoldChart";
import "./style.css";

function getSignalIcon(signal) {
  if (signal === "BUY") return "▲";
  if (signal === "SELL") return "▼";
  return "●";
}

function formatTime(sec) {
  if (sec < 0) sec = 0;
  let m = Math.floor(sec / 60);
  let s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

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

const HISTORY_KEY = "history";

export default function App() {
  const [date, setDate] = useState("");
  const [timer, setTimer] = useState("5:00");
  const [signal, setSignal] = useState("WAIT...");
  const [signalClass, setSignalClass] = useState("signal-btn hold");
  const [reason, setReason] = useState("รอการวิเคราะห์...");
  const [history, setHistory] = useState([]);
  const [news, setNews] = useState([]);
  const [thaiGoldPrice, setThaiGoldPrice] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [aiData, setAiData] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [executionResult, setExecutionResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const lastSavedTime = useRef(null);
  const timerInterval = useRef(null);

  // Set date on mount
  useEffect(() => {
    setDate(new Date().toLocaleDateString("th-TH"));
  }, []);

  // API fetch
  async function getDashboard() {
    try {
      const res = await fetch("/api/ai/status");
      if (!res.ok) {
        return null;
      }
      const data = await res.json();
      setDashboard(data);
      if (data?.market?.HSH_Sell) {
        setThaiGoldPrice(data.market.HSH_Sell);
      }
      return data;
    } catch (err) {
      return null;
    }
  }

  async function runAiAnalysis() {
    setIsAnalyzing(true);
    setExecutionResult(null);
    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!data || data.error) {
        setSignal("ERROR");
        setSignalClass("signal-btn hold");
        setReason("ไม่สามารถดึงข้อมูลได้");
        setAiData(null);
        setTimeLeft(0);
      } else {
        setAiData(data);
        setTimeLeft(15);
        setSignal(data.ai_action || "HOLD");
        setSignalClass("signal-btn " + (data.ai_action || "HOLD").toLowerCase());
        const confidence = data.confidence || 0;
        setReason(`AI Signal<br>Confidence: ${(confidence * 100).toFixed(2)}%<br>${data.ai_reason || ""}`);
        saveHistory(data.ai_action || "HOLD", `AI Signal<br>Confidence: ${(confidence * 100).toFixed(2)}%<br>${data.ai_reason || ""}`);
        loadHistory();
        if (Array.isArray(data.raw_reports)) {
          renderNews(data.raw_reports);
        }
      }
    } catch (error) {
      setSignal("ERROR");
      setSignalClass("signal-btn hold");
      setReason("ไม่สามารถติดต่อ AI ได้");
      setAiData(null);
      setTimeLeft(0);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function submitDecision(userAction) {
    if (!aiData) return;
    const payload = {
      ai_action: aiData.ai_action,
      ai_reason: aiData.ai_reason,
      ai_amount_thb: aiData.ai_amount_thb,
      user_action: userAction,
    };

    setAiData(null);
    setTimeLeft(0);

    try {
      const res = await fetch("/api/ai/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      setExecutionResult(result);
      await getDashboard();
    } catch (error) {
      setExecutionResult({ status: "error", reason: "ไม่สามารถเชื่อมต่อกับระบบได้" });
    }
  }

  // Save history
  function saveHistory(signal, reason) {
    let historyArr = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    const now = new Date();
    const minutes = Math.floor(now.getMinutes() / 15) * 15;
    const t = new Date(now);
    t.setMinutes(minutes);
    t.setSeconds(0);
    t.setMilliseconds(0);
    const newTime = t.getTime();
    if (historyArr.some((h) => h.time === newTime)) return;
    historyArr.push({ signal, reason, time: newTime });
    if (historyArr.length > 5) {
      historyArr = historyArr.slice(-5);
    }
    localStorage.setItem(HISTORY_KEY, JSON.stringify(historyArr));
  }

  // Load history
  function loadHistory() {
    let historyArr = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    setHistory(
      historyArr.sort((a, b) => b.time - a.time)
    );
  }

  // News rendering
  function renderNews(newsList) {
    setNews(newsList.slice(0, 5));
  }

  // Main analyze logic
  async function analyze() {
    const now = new Date();
    const minutes = Math.floor(now.getMinutes() / 15) * 15;
    const t = new Date(now);
    t.setMinutes(minutes);
    t.setSeconds(0);
    t.setMilliseconds(0);
    const currentRound = t.getTime();
    if (lastSavedTime.current === currentRound) return;
    lastSavedTime.current = currentRound;
    // Use new AI analyze endpoint
    let res = await fetch("/api/ai/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    let data = await res.json();
    if (!data || data.error) {
      setSignal("ERROR");
      setSignalClass("signal-btn hold");
      setReason("ไม่สามารถดึงข้อมูลได้");
      return;
    }
    let signalVal = data.ai_action || "HOLD";
    let confidence = data.confidence || 0;
    let reasonVal = `AI Signal<br>Confidence: ${(confidence * 100).toFixed(2)}%<br>${data.ai_reason || ""}`;
    setSignal(signalVal);
    setSignalClass("signal-btn " + signalVal.toLowerCase());
    setReason(reasonVal);
    saveHistory(signalVal, reasonVal);
    loadHistory();
    if (Array.isArray(data.raw_reports)) {
      renderNews(data.raw_reports);
    }
  }

  // Timer logic
  useEffect(() => {
    setTimer(formatTime(getSecondsToNextInterval()));
    timerInterval.current = setInterval(() => {
      const timeLeft = getSecondsToNextInterval();
      setTimer(formatTime(timeLeft));
      if (timeLeft <= 0) {
        analyze();
      }
    }, 1000);
    return () => clearInterval(timerInterval.current);
    // eslint-disable-next-line
  }, []);

  // Initial API call
  useEffect(() => {
    analyze();
    getDashboard();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (timeLeft > 0 && aiData) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    }

    if (timeLeft === 0 && aiData) {
      submitDecision("TIMEOUT");
    }
  }, [timeLeft, aiData]);

  // --- Render ---
  return (
    <div className="container">
      <div className="header">
        <div>
          <p>เทรดทองพารวย</p>
          <p>วันที่ <span>{date}</span></p>
        </div>
        <div className="timer">
          <p>เวลาที่วิเคราะห์ถัดไป</p>
          <h1>{timer}</h1>
        </div>
      </div>
      <h1 className="title">ราคาทอง</h1>
      <div className="gold-price">{thaiGoldPrice ? thaiGoldPrice.toLocaleString() : "..."} บาท</div>
      <div className="chart-box">
        <ThaiGoldChart onPriceUpdate={setThaiGoldPrice} />
      </div>

      {dashboard && (
        <div className="portfolio-summary">
          <div className="portfolio-card">
            <p>Cash Balance</p>
            <strong>{dashboard.portfolio.THB_Balance.toLocaleString(undefined, { minimumFractionDigits: 2 })} THB</strong>
          </div>
          <div className="portfolio-card">
            <p>Gold Holdings</p>
            <strong>{dashboard.portfolio.Gold_Gram.toFixed(4)} g</strong>
          </div>
          <div className="portfolio-card">
            <p>Net Asset Value</p>
            <strong>{dashboard.net_asset_value.toLocaleString(undefined, { minimumFractionDigits: 2 })} THB</strong>
          </div>
        </div>
      )}

      <div className="signal-section">
        <div className="signal-left">
          <p className={signalClass}>{signal}</p>
        </div>
        <div className="signal-right">
          <p dangerouslySetInnerHTML={{ __html: reason }} />
        </div>
      </div>

      <div className="action-section">
        <button className="primary-button" onClick={runAiAnalysis} disabled={isAnalyzing || aiData !== null}>
          {isAnalyzing ? "Analyzing..." : "Trigger AI Analysis"}
        </button>
      </div>

      {aiData && (
        <div className="decision-modal">
          <div className="decision-header">
            <h3>AI RECOMMENDS: {aiData.ai_action}</h3>
            <p>Amount: {aiData.ai_amount_thb}</p>
            <p>{aiData.ai_reason}</p>
            <p>Decision Timeout in {timeLeft}s</p>
          </div>
          <div className="decision-buttons">
            <button className="decision-button buy" onClick={() => submitDecision("BUY")}>Force BUY</button>
            <button className="decision-button sell" onClick={() => submitDecision("SELL")}>Force SELL</button>
            <button className="decision-button hold" onClick={() => submitDecision("HOLD")}>Force HOLD</button>
          </div>
        </div>
      )}

      {executionResult && (
        <div className="execution-result">
          <h2>Execution Result</h2>
          <p><strong>Action:</strong> {executionResult.executed_action || executionResult.status}</p>
          <p><strong>Reason:</strong> {executionResult.reason}</p>
          {executionResult.executed_amount && <p><strong>Amount:</strong> {executionResult.executed_amount}</p>}
          {executionResult.net_asset_value !== undefined && (
            <p><strong>NAV:</strong> {Number(executionResult.net_asset_value).toLocaleString(undefined, { minimumFractionDigits: 2 })} THB</p>
          )}
        </div>
      )}

      <hr />
      <div className="history-section">
        <h2>ประวัติ</h2>
        <div className="history">
          {history.map((h, i) => {
            const dateObj = new Date(h.time);
            return (
              <div
                key={h.time}
                className={"history-item " + h.signal.toLowerCase()}
              >
                <b>{getSignalIcon(h.signal)} {h.signal}</b><br />
                <span dangerouslySetInnerHTML={{ __html: h.reason }} /><br />
                เวลา {dateObj.toLocaleTimeString("th-TH")} วันที่ {dateObj.toLocaleDateString("th-TH")}
              </div>
            );
          })}
        </div>
      </div>
      <div className="news-section">
        <h2>Related News</h2>
        <div id="newsContainer">
          {news.map((newsItem, idx) => {
            let keyword = encodeURIComponent(
              (newsItem.title || "gold finance").split(" ").slice(0, 3).join(" ")
            );
            let img = `https://source.unsplash.com/400x250/?${keyword}`;
            let color = "gray";
            if (newsItem.sentiment === "positive") color = "green";
            if (newsItem.sentiment === "negative") color = "red";
            return (
              <div
                className="news-card"
                style={{ cursor: "pointer" }}
                key={newsItem.url || idx}
                onClick={() => window.open(newsItem.url, "_blank")}
              >
                <div className="news-image">
                  <img src={img} alt="news" />
                  <div className="news-title">{newsItem.title}</div>
                </div>
                <div className="news-content">
                  <p>{newsItem.summary || ""}</p>
                  <span style={{ color }}>
                    ● {newsItem.sentiment || "neutral"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
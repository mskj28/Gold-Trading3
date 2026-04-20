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

  // States สำหรับการตัดสินใจเทรดอัตโนมัติ
  const [aiData, setAiData] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [executionResult, setExecutionResult] = useState(null);

  // States สำหรับแก้ไข Portfolio
  const [isEditingPortfolio, setIsEditingPortfolio] = useState(false);
  const [editCash, setEditCash] = useState("");
  const [editGold, setEditGold] = useState("");

  const lastSavedTime = useRef(null);
  const timerInterval = useRef(null);

  useEffect(() => {
    setDate(new Date().toLocaleDateString("th-TH"));
  }, []);

  async function getDashboard() {
    try {
      const res = await fetch("/api/ai/status");
      if (!res.ok) return null;
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

  function loadHistory() {
    let historyArr = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    setHistory(historyArr.sort((a, b) => b.time - a.time));
  }

  function renderNews(newsList) {
    setNews(newsList.slice(0, 5));
  }

  async function analyze() {
    const now = new Date();
    const minutes = Math.floor(now.getMinutes() / 15) * 15;
    const t = new Date(now);
    t.setMinutes(minutes);
    t.setSeconds(0);
    t.setMilliseconds(0);
    const currentRound = t.getTime();

    // ป้องกันการยิง API ซ้ำซ้อนในรอบ 15 นาทีเดียวกัน
    if (lastSavedTime.current === currentRound) return;
    lastSavedTime.current = currentRound;

    try {
      let res = await fetch("/api/ai/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
      let data = await res.json();

      if (!data || data.error) {
        setSignal("ERROR");
        setSignalClass("signal-btn hold");
        setReason("ไม่สามารถดึงข้อมูลได้");
        return;
      }

      let signalVal = data.ai_action || "HOLD";
      let reasonVal = data.ai_reason ? `<strong>เหตุผลจาก AI:</strong><br/>${data.ai_reason}` : "AI ไม่ได้ระบุเหตุผล";

      // แสดง Popup ตัดสินใจ และเริ่มนับถอยหลัง 15 วิ
      setAiData(data);
      setTimeLeft(15);
      setExecutionResult(null); // เคลียร์ผลการเทรดรอบเก่า

      setSignal(signalVal);
      setSignalClass("signal-btn " + signalVal.toLowerCase());
      setReason(reasonVal);

      saveHistory(signalVal, reasonVal);
      loadHistory();

      if (Array.isArray(data.raw_reports)) {
        renderNews(data.raw_reports);
      }
    } catch (error) {
      console.error(error);
      setSignal("ERROR");
      setSignalClass("signal-btn hold");
      setReason("ระบบขัดข้อง ไม่สามารถวิเคราะห์ได้");
    }
  }

  // --- Portfolio Editing Functions ---
  const openEditPortfolio = () => {
    if (dashboard && dashboard.portfolio) {
      setEditCash(dashboard.portfolio.THB_Balance);
      setEditGold(dashboard.portfolio.Gold_Gram);
    }
    setIsEditingPortfolio(true);
  };

  const savePortfolio = async () => {
    // บังคับแปลงค่าให้เป็นตัวเลขเสมอ เพื่อป้องกัน Error NaN หรือ String
    const safeCash = parseFloat(editCash) || 0;
    const safeGold = parseFloat(editGold) || 0;

    try {
      const response = await fetch("/api/ai/portfolio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          THB_Balance: safeCash,
          Gold_Gram: safeGold
        })
      });

      if (!response.ok) {
        throw new Error("Backend rejected the portfolio update.");
      }

      setIsEditingPortfolio(false);
      await getDashboard(); // ดึงข้อมูลใหม่มาโชว์ทันที
    } catch (error) {
      console.error(error);
      alert("เกิดข้อผิดพลาดในการบันทึกข้อมูลพอร์ต กรุณาลองใหม่อีกครั้ง");
    }
  };

  // --- Effect: นาฬิกานับถอยหลัง 15 นาที ---
  useEffect(() => {
    setTimer(formatTime(getSecondsToNextInterval()));
    timerInterval.current = setInterval(() => {
      const timeLeftToNext = getSecondsToNextInterval();
      setTimer(formatTime(timeLeftToNext));
      if (timeLeftToNext <= 0) {
        analyze();
      }
    }, 1000);
    return () => clearInterval(timerInterval.current);
  }, []);

  // --- Effect: โหลดข้อมูลครั้งแรกเมื่อเปิดเว็บ ---
  useEffect(() => {
    analyze();
    getDashboard();
  }, []);

  // --- Effect: นาฬิกานับถอยหลังสำหรับการ Force Action (15 วิ) ---
  useEffect(() => {
    if (timeLeft > 0 && aiData) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    }
    if (timeLeft === 0 && aiData) {
      submitDecision("TIMEOUT");
    }
  }, [timeLeft, aiData]);

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
        <div className="portfolio-summary" style={{ position: "relative" }}>
          {/* ปุ่มแก้ไข Portfolio */}
          <button
            onClick={openEditPortfolio}
            style={{ position: "absolute", top: "-15px", right: "0", background: "#f57c00", color: "#fff", border: "none", padding: "5px 12px", borderRadius: "5px", cursor: "pointer", fontSize: "14px", fontWeight: "bold" }}
          >
            ⚙️ แก้ไขพอร์ต
          </button>

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

      {/* Modal แก้ไข Portfolio */}
      {isEditingPortfolio && (
        <div className="decision-modal" style={{ border: "3px solid #f57c00" }}>
          <div className="decision-header">
            <h3>⚙️ ตั้งค่า Portfolio</h3>
          </div>
          <div style={{ marginBottom: "15px", textAlign: "left" }}>
            <label style={{ fontWeight: "bold", color: "#555" }}>Cash Balance (THB):</label>
            <input
              type="number"
              value={editCash}
              onChange={(e) => setEditCash(e.target.value)}
              style={{ width: "100%", padding: "10px", marginTop: "5px", borderRadius: "8px", border: "1px solid #ccc", fontSize: "16px", boxSizing: "border-box" }}
            />
          </div>
          <div style={{ marginBottom: "15px", textAlign: "left" }}>
            <label style={{ fontWeight: "bold", color: "#555" }}>Gold Holdings (Grams):</label>
            <input
              type="number"
              value={editGold}
              onChange={(e) => setEditGold(e.target.value)}
              style={{ width: "100%", padding: "10px", marginTop: "5px", borderRadius: "8px", border: "1px solid #ccc", fontSize: "16px", boxSizing: "border-box" }}
            />
          </div>
          <div className="decision-buttons">
            <button className="decision-button buy" onClick={savePortfolio} style={{ background: "#f57c00" }}>บันทึกข้อมูล</button>
            <button className="decision-button hold" onClick={() => setIsEditingPortfolio(false)}>ยกเลิก</button>
          </div>
        </div>
      )}

      {/* ข้อมูลสัญญาณและเหตุผล */}
      <div className="signal-section">
        <div className="signal-left">
          <p className={signalClass}>{signal}</p>
        </div>
        <div className="signal-right">
          <p dangerouslySetInnerHTML={{ __html: reason }} />
        </div>
      </div>

      {/* Popup ให้ผู้ใช้ตัดสินใจ Force Action ก่อนหมดเวลา (จะเด้งขึ้นมาตอนที่ระบบวิเคราะห์เสร็จ) */}
      {aiData && (
        <div className="decision-modal">
          <div className="decision-header">
            <h3>AI RECOMMENDS: {aiData.ai_action}</h3>
            <p>Amount: {aiData.ai_amount_thb}</p>
            <p>{aiData.ai_reason}</p>
            <p style={{ color: "#d32f2f", fontWeight: "bold" }}>Decision Timeout in {timeLeft}s</p>
          </div>
          <div className="decision-buttons">
            <button className="decision-button buy" onClick={() => submitDecision("BUY")}>Force BUY</button>
            <button className="decision-button sell" onClick={() => submitDecision("SELL")}>Force SELL</button>
            <button className="decision-button hold" onClick={() => submitDecision("HOLD")}>Force HOLD</button>
          </div>
        </div>
      )}

      {/* โชว์ผลลัพธ์หลังจากทำการเทรดแล้ว */}
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
              <div key={h.time} className={"history-item " + h.signal.toLowerCase()}>
                <b>{getSignalIcon(h.signal)} {h.signal}</b><br />
                <span dangerouslySetInnerHTML={{ __html: h.reason }} /><br />
                <small style={{ color: "#777" }}>เวลา {dateObj.toLocaleTimeString("th-TH")} วันที่ {dateObj.toLocaleDateString("th-TH")}</small>
              </div>
            );
          })}
        </div>
      </div>

      <div className="news-section">
        <h2>Related News</h2>
        <div id="newsContainer">
          {news.map((newsItem, idx) => {
            let keyword = encodeURIComponent((newsItem.title || "gold finance").split(" ").slice(0, 3).join(" "));
            let img = `https://source.unsplash.com/400x250/?${keyword}`;
            let color = "gray";
            if (newsItem.sentiment === "positive") color = "green";
            if (newsItem.sentiment === "negative") color = "red";
            return (
              <div className="news-card" style={{ cursor: "pointer" }} key={newsItem.url || idx} onClick={() => window.open(newsItem.url, "_blank")}>
                <div className="news-image">
                  <img src={img} alt="news" />
                  <div className="news-title">{newsItem.title}</div>
                </div>
                <div className="news-content">
                  <p>{newsItem.summary || ""}</p>
                  <span style={{ color }}>● {newsItem.sentiment || "neutral"}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
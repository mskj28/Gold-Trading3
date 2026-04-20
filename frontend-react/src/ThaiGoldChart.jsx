import React, { useState, useEffect, useMemo, useRef } from "react";
import { Line } from "react-chartjs-2";
import Chart from "chart.js/auto";
import 'chartjs-adapter-date-fns';

// --- Configurable constants ---
const GOLD_API = "/api/market-data?symbol=XAUUSD&period=1d&interval=15m";
const FX_API = "/api/usdthb";
const OUNCE_TO_THAI = 0.4729;

// --- Data Fetching Hooks ---
function useGoldData() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetch(GOLD_API)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((json) => {
            throw new Error(json.detail || json.error || `Market API error ${res.status}`);
          });
        }
        return res.json();
      })
      .then((json) => {
        if (isMounted && json.data) setData(json.data);
        else if (isMounted) throw new Error("Market API returned no data");
      })
      .catch((e) => isMounted && setError(e))
      .finally(() => isMounted && setLoading(false));
    return () => { isMounted = false; };
  }, []);

  return { data, loading, error };
}

function useUsdThb() {
  const [rate, setRate] = useState(null);
  const [timestamp, setTimestamp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetch(FX_API)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((json) => {
            throw new Error(json.detail || json.error || `FX API error ${res.status}`);
          });
        }
        return res.json();
      })
      .then((json) => {
        if (isMounted && json.rate) {
          setRate(json.rate);
          setTimestamp(json.timestamp);
        } else if (isMounted) {
          throw new Error("FX API returned no rate");
        }
      })
      .catch((e) => isMounted && setError(e))
      .finally(() => isMounted && setLoading(false));
    return () => { isMounted = false; };
  }, []);

  return { rate, timestamp, loading, error };
}

// --- Transformation Logic ---
function useThaiGoldData({ goldData, fxRate, premium = 0, fee = 0 }) {
  return useMemo(() => {
    if (!goldData || !fxRate) return [];

    const parsed = goldData
      .map((d) => {
        const timestamp = d.timestamp ? new Date(d.timestamp) : null;
        const goldSpot = Number(d.Close);
        const thaiGold = ((goldSpot + Number(premium)) * OUNCE_TO_THAI * Number(fxRate)) + Number(fee);
        return {
          ...d,
          timestamp,
          thaiGold: Math.round(thaiGold * 100) / 100,
        };
      })
      .filter((d) => d.timestamp instanceof Date && !Number.isNaN(d.timestamp.getTime()));

    const windowStart = new Date(Date.now() - 180 * 60 * 1000); // 3 hour - minutes ago
    const recentData = parsed.filter((d) => d.timestamp >= windowStart);
    return recentData.length > 0 ? recentData : parsed;
  }, [goldData, fxRate, premium, fee]);
}

// --- Main Component ---
export default function ThaiGoldChart({ onPriceUpdate }) {
  const chartRef = useRef();

  // Data fetching
  const { data: goldData, loading: goldLoading, error: goldError } = useGoldData();
  const { rate: fxRate, timestamp: fxTimestamp, loading: fxLoading, error: fxError } = useUsdThb();

  // Data transformation (NO premium/fee controls)
  const thaiGoldData = useThaiGoldData({ goldData, fxRate });

  // Notify parent of latest price
  React.useEffect(() => {
    if (!thaiGoldData || thaiGoldData.length === 0) return;
    const latest = thaiGoldData[thaiGoldData.length - 1];
    if (onPriceUpdate && latest && latest.thaiGold) {
      onPriceUpdate(latest.thaiGold);
    }
  }, [thaiGoldData, onPriceUpdate]);

    // --- UTC-aligned 15-min tick logic and strict 4h30m window ---
    function roundTo15UTC(date) {
      const d = new Date(date);
      d.setUTCSeconds(0, 0);
      d.setUTCMinutes(Math.floor(d.getUTCMinutes() / 15) * 15);
      return d;
    }

    // --- Auto refresh every 15 minutes ---
    const [refreshKey, setRefreshKey] = useState(0);
    useEffect(() => {
      function msToNext15() {
        const now = new Date();
        const min = now.getUTCMinutes();
        const next = Math.ceil((min + 1) / 15) * 15;
        let nextDate = new Date(now);
        nextDate.setUTCSeconds(0, 0);
        if (next >= 60) {
          nextDate.setUTCHours(nextDate.getUTCHours() + 1);
          nextDate.setUTCMinutes(0);
        } else {
          nextDate.setUTCMinutes(next);
        }
        return nextDate - now;
      }
      let timer = null;
      let interval = null;
      timer = setTimeout(() => {
        setRefreshKey((k) => k + 1);
        interval = setInterval(() => {
          setRefreshKey((k) => k + 1);
        }, 15 * 60 * 1000);
      }, msToNext15());
      return () => {
        if (timer) clearTimeout(timer);
        if (interval) clearInterval(interval);
      };
    }, []);

    // --- Strict 4h30m sliding window, always 15-min UTC ticks ---
    const endTime = useMemo(() => roundTo15UTC(new Date()), [refreshKey]);
    const startTime = useMemo(() => new Date(endTime.getTime() - 270 * 60 * 1000), [endTime]);
    const xTicks = useMemo(() => {
      const arr = [];
      for (let t = new Date(startTime); t <= endTime; t = new Date(t.getTime() + 15 * 60 * 1000)) {
        arr.push(new Date(t));
      }
      return arr;
    }, [startTime, endTime]);

    // Align data to ticks (carry forward last known value)
    let lastGold = null;
    const goldByTime = {};
    thaiGoldData.forEach((d) => {
      const tick = roundTo15UTC(d.timestamp).getTime();
      goldByTime[tick] = d.thaiGold;
    });
    const yData = xTicks.map((tick) => {
      const t = tick.getTime();
      if (goldByTime[t] !== undefined) {
        lastGold = goldByTime[t];
        return lastGold;
      } else {
        return lastGold;
      }
    });

    // Chart data
    const chartData = useMemo(() => ({
      labels: xTicks,
      datasets: [
        {
          label: "Thai Gold Price (THB)",
          data: yData,
          borderColor: "#eab308",
          backgroundColor: "rgba(234,179,8,0.1)",
          pointRadius: 2,
          spanGaps: true,
          tension: 0.2,
        },
      ],
    }), [xTicks, yData]);

    // Chart options (tick ทุก 15 นาที, min/max ตามช่วงเวลา)
    const chartOptions = useMemo(() => ({
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `ราคา: ${ctx.parsed.y?.toLocaleString() ?? '-'} บาท`,
            title: (ctx) => {
              const label = ctx[0].label;
              if (!label) return '';
              // format H:mm
              const d = new Date(label);
              return `เวลา: ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: "time",
          time: {
            unit: 'minute',
            stepSize: 15,
            displayFormats: {
              minute: 'H:mm',
              hour: 'H:mm',
            },
            tooltipFormat: "yyyy-MM-dd HH:mm"
          },
          min: startTime,
          max: endTime,
          ticks: {
            autoSkip: false,
            stepSize: 15,
            maxTicksLimit: 100,
          },
          title: { display: true, text: "เวลา" },
        },
        y: {
          title: { display: true, text: "ราคาทอง (บาท)" },
          ticks: { callback: (v) => v.toLocaleString() },
        },
      },
    }), [startTime, endTime, xTicks.length]);
  // Latest price (not rendered, but available if needed)
  // const latest = thaiGoldData.length > 0 ? thaiGoldData[thaiGoldData.length - 1] : null;

  // Chart.js instance cleanup (fix canvas reuse error)
  useEffect(() => {
    return () => {
      if (chartRef.current && chartRef.current.chartInstance) {
        chartRef.current.chartInstance.destroy();
      }
    };
  }, []);

  // Loading/Error handling
  if (goldLoading || fxLoading) return <div style={{textAlign:'center',color:'#888'}}>กำลังโหลดข้อมูล...</div>;
  if (goldError || fxError) return <div style={{textAlign:'center',color:'red'}}>เกิดข้อผิดพลาดในการโหลดข้อมูลกราฟทอง</div>;

  if (!thaiGoldData || thaiGoldData.length === 0) {
    return <div style={{textAlign:'center',color:'#888'}}>ไม่มีข้อมูลราคาทองไทยสำหรับแสดงกราฟ</div>;
  }

  // Render chart to fill parent .chart-box with small padding
  return (
    <div style={{ width: "100%", height: "100%", padding: "6px" }}>
      <Line
        ref={chartRef}
        data={chartData}
        options={{
          ...chartOptions,
          maintainAspectRatio: false,
        }}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
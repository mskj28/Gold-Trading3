import React, { useState, useEffect, useMemo, useRef } from "react";
import { Line } from "react-chartjs-2";
import Chart from "chart.js/auto";
import 'chartjs-adapter-date-fns';

const HSH_API = "/hsh-api/api/Values/GetPriceSeacon";
const CHART_STORAGE_KEY = "hsh_realtime_chart";

export default function ThaiGoldChart({ onPriceUpdate }) {
  const chartRef = useRef();
  const [dataPoints, setDataPoints] = useState([]);
  const [loading, setLoading] = useState(true);

  // 1. Load saved graph data from localStorage when component mounts
  useEffect(() => {
    const savedData = localStorage.getItem(CHART_STORAGE_KEY);
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        // Convert the string timestamps back into actual Date objects for Chart.js
        const restoredData = parsed.map(d => ({
          timestamp: new Date(d.timestamp),
          price: d.price
        }));
        setDataPoints(restoredData);
      } catch (e) {
        console.error("Failed to parse saved chart data", e);
      }
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const fetchHshPrice = async () => {
      try {
        // CACHE BUSTER: Adding ?t=... forces the browser to get the freshest price
        const freshUrl = `${HSH_API}?t=${new Date().getTime()}`;
        const res = await fetch(freshUrl);

        if (!res.ok) throw new Error("Failed to fetch HSH API");
        const json = await res.json();

        if (isMounted && json && json.Ask965) {
          const currentPrice = parseFloat(json.Ask965);
          const now = new Date();

          setDataPoints((prev) => {
            const newData = [...prev, { timestamp: now, price: currentPrice }];
            // Keep the last 60 points (1 hour of data if polling every minute)
            const trimmedData = newData.slice(-60);

            // 2. Save the updated graph to localStorage
            localStorage.setItem(CHART_STORAGE_KEY, JSON.stringify(trimmedData));
            return trimmedData;
          });

          if (onPriceUpdate) {
            onPriceUpdate(currentPrice);
          }
          setLoading(false);
        }
      } catch (err) {
        console.error("HSH API Error:", err);
      }
    };

    fetchHshPrice();
    const intervalId = setInterval(fetchHshPrice, 60000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [onPriceUpdate]);

  useEffect(() => {
    return () => {
      if (chartRef.current && chartRef.current.chartInstance) {
        chartRef.current.chartInstance.destroy();
      }
    };
  }, []);

  const chartData = useMemo(() => {
    return {
      labels: dataPoints.map((d) => d.timestamp),
      datasets: [
        {
          label: "ราคาทองฮั่วเซ่งเฮง (ขายออก)",
          data: dataPoints.map((d) => d.price),
          borderColor: "#eab308",
          backgroundColor: "rgba(234,179,8,0.15)",
          pointRadius: 4,
          pointHoverRadius: 6,
          spanGaps: true,
          tension: 0.2,
          fill: true,
        },
      ],
    };
  }, [dataPoints]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `ราคา: ${ctx.parsed.y?.toLocaleString() ?? '-'} บาท`,
          title: (ctx) => {
            const d = new Date(ctx[0].parsed.x);
            return `เวลา: ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')} น.`;
          },
        },
      },
    },
    scales: {
      x: {
        type: "time",
        time: { unit: 'minute', displayFormats: { minute: 'HH:mm' } },
        title: { display: true, text: "เวลา" },
      },
      y: {
        title: { display: true, text: "ราคาทอง (บาท)" },
        ticks: { callback: (v) => v.toLocaleString() },
        grace: '5%'
      },
    },
  }), []);

  if (loading && dataPoints.length === 0) {
    return <div style={{textAlign:'center', color:'#888', marginTop: '40px'}}>กำลังดึงข้อมูล...</div>;
  }

  return (
    <div style={{ width: "100%", height: "100%", padding: "10px", boxSizing: "border-box" }}>
      <Line ref={chartRef} data={chartData} options={chartOptions} />
    </div>
  );
}
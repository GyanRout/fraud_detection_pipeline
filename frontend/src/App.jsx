import React, { useState, useEffect, useRef } from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle, Activity } from 'lucide-react';

export default function App() {
  // 1. State Management for Real-Time Data
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({ total: 0, blocked: 0, reviewed: 0 });
  const [connectionStatus, setConnectionStatus] = useState('Connecting...');
  
  // Use a ref to maintain the WebSocket instance across re-renders
  const ws = useRef(null);

  // 2. WebSocket Lifecycle Hook
  useEffect(() => {
    // Connect to the FastAPI backend WebSocket endpoint
    ws.current = new WebSocket('ws://127.0.0.1:8000/ws/alerts');

    ws.current.onopen = () => {
      setConnectionStatus('Live & Secure');
    };

    ws.current.onmessage = (event) => {
      const incomingData = JSON.parse(event.data);
      
      // Update the ledger (Keep only the latest 50 to prevent DOM memory bloat)
      setAlerts((prevAlerts) => [incomingData, ...prevAlerts].slice(0, 50));
      
      // Update aggregate statistics dynamically
      setStats((prevStats) => ({
        total: prevStats.total + 1,
        blocked: incomingData.action === 'BLOCK' ? prevStats.blocked + 1 : prevStats.blocked,
        reviewed: incomingData.action === 'REVIEW' ? prevStats.reviewed + 1 : prevStats.reviewed,
      }));
    };

    ws.current.onclose = () => {
      setConnectionStatus('Disconnected. Reconnecting...');
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket routing error:", error);
      setConnectionStatus('Connection Error');
    };

    // Cleanup function: Close socket if the component unmounts
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  // 3. Dynamic Styling Helpers
  const getActionStyles = (action) => {
    switch (action) {
      case 'BLOCK':
        return 'bg-red-900/50 text-red-400 border-red-500/50';
      case 'REVIEW':
        return 'bg-yellow-900/50 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-gray-800 text-gray-400 border-gray-700';
    }
  };

  // 4. UI Rendering
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-sans">
      
      {/* Header Section */}
      <header className="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <ShieldCheck className="text-emerald-500" size={32} />
            Fintech Fraud Operations
          </h1>
          <p className="text-gray-400 mt-1">High-Throughput ML Inference Gateway</p>
        </div>
        <div className={`flex items-center gap-2 px-4 py-2 rounded-full border ${connectionStatus === 'Live & Secure' ? 'bg-emerald-900/30 border-emerald-500 text-emerald-400' : 'bg-red-900/30 border-red-500 text-red-400'}`}>
          <Activity size={18} className={connectionStatus === 'Live & Secure' ? 'animate-pulse' : ''} />
          <span className="text-sm font-medium">{connectionStatus}</span>
        </div>
      </header>

      {/* Analytics KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gray-900 border border-gray-800 p-6 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm font-medium">Session Alerts Caught</p>
            <p className="text-3xl font-bold mt-2">{stats.total}</p>
          </div>
          <Activity className="text-blue-500 opacity-50" size={48} />
        </div>
        <div className="bg-gray-900 border border-red-900/50 p-6 rounded-xl flex items-center justify-between shadow-[0_0_15px_rgba(239,68,68,0.1)]">
          <div>
            <p className="text-red-400 text-sm font-medium">Auto-Blocked</p>
            <p className="text-3xl font-bold mt-2 text-red-50">{stats.blocked}</p>
          </div>
          <ShieldAlert className="text-red-500 opacity-50" size={48} />
        </div>
        <div className="bg-gray-900 border border-yellow-900/50 p-6 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-yellow-400 text-sm font-medium">Manual Review Required</p>
            <p className="text-3xl font-bold mt-2 text-yellow-50">{stats.reviewed}</p>
          </div>
          <AlertTriangle className="text-yellow-500 opacity-50" size={48} />
        </div>
      </div>

      {/* Real-Time Alert Ledger */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800 bg-gray-900/50">
          <h2 className="text-lg font-semibold">Live Threat Ledger</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-950 text-gray-400 text-sm">
                <th className="p-4 font-medium">Timestamp (UTC)</th>
                <th className="p-4 font-medium">Transaction ID</th>
                <th className="p-4 font-medium">Amount</th>
                <th className="p-4 font-medium">ML Risk Score</th>
                <th className="p-4 font-medium">System Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {alerts.length === 0 ? (
                <tr>
                  <td colSpan="5" className="p-8 text-center text-gray-500">
                    Listening for anomalous transactions...
                  </td>
                </tr>
              ) : (
                alerts.map((alert, index) => (
                  <tr key={index} className="hover:bg-gray-800/50 transition-colors animate-in fade-in slide-in-from-top-4 duration-300">
                    <td className="p-4 text-sm text-gray-400">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="p-4 font-mono text-sm">{alert.transaction_id}</td>
                    <td className="p-4 font-medium">${alert.amount.toFixed(2)}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="w-full bg-gray-800 rounded-full h-2 max-w-[100px]">
                          <div 
                            className={`h-2 rounded-full ${alert.risk_score >= 0.8 ? 'bg-red-500' : 'bg-yellow-500'}`}
                            style={{ width: `${alert.risk_score * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-mono text-gray-300">
                          {alert.risk_score.toFixed(3)}
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getActionStyles(alert.action)}`}>
                        {alert.action}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
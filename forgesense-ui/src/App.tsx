import React, { useState, useEffect } from 'react';
import './App.css'; 
import Login from './Login';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// --- TypeScript Interfaces ---
interface TelemetryData {
  id?: number;
  machine_id: string;
  temperature: number;
  vibration: number;
  pressure: number;
  rpm: number;
  power_consumption: number;
  timestamp?: string; // From history API
  time?: string; // For live charts
}

interface AlertData {
  id: number;
  machine_id: string;
  message: string;
  timestamp?: string;
}

interface MetricCardProps {
  title: string;
  value?: number;
  unit: string;
  alertThreshold?: number;
}

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [userRole, setUserRole] = useState<string | null>(null);
  
  // Navigation & Filtering State
  const [activeTab, setActiveTab] = useState<'live' | 'history'>('live');
  const [selectedMachine, setSelectedMachine] = useState<string>('CNC-001');
  
  // Live Data State
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [telemetryChartData, setTelemetryChartData] = useState<TelemetryData[]>([]);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [status, setStatus] = useState<string>("Healthy");

  // Historical Data State
  const [historyData, setHistoryData] = useState<TelemetryData[]>([]);

  // 1. Decode Token
  useEffect(() => {
    if (token) {
      try {
        const payloadBase64 = token.split('.')[1];
        const decodedPayload = JSON.parse(atob(payloadBase64));
        setUserRole(decodedPayload.role);
      } catch (e) {
        console.error("Failed to decode token", e);
      }
    } else {
      setUserRole(null);
    }
  }, [token]);

  // 2. Fetch Active Alerts & Connect WebSocket
  useEffect(() => {
    if (!token) return;

    // Fetch alerts
    fetch("http://127.0.0.1:8000/alerts/", {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) {
          if (res.status === 401) handleLogout();
          throw new Error("Failed to fetch alerts");
        }
        return res.json();
      })
      .then((data: AlertData[]) => {
        setAlerts(data);
        if (data.filter(a => a.machine_id === selectedMachine).length > 0) {
          setStatus("Critical");
        } else {
          setStatus("Healthy");
        }
      })
      .catch(err => console.error("Failed to fetch alerts:", err));

    // Connect WebSocket
    const ws = new WebSocket("ws://127.0.0.1:8000/ws");
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === "TELEMETRY") {
        // Only update live stats if it matches the selected machine
        if (message.data.machine_id === selectedMachine) {
          const newData = {
            ...message.data,
            time: new Date().toLocaleTimeString('en-US', { hour12: false, hour: "numeric", minute: "numeric", second: "numeric" })
          };
          
          setTelemetry(newData);
          setTelemetryChartData(prev => {
            const newHistory = [...prev, newData];
            return newHistory.length > 20 ? newHistory.slice(newHistory.length - 20) : newHistory;
          });
        }
      } else if (message.type === "ALERT") {
        setAlerts(prev => [message.data, ...prev]);
        if (message.data.machine_id === selectedMachine) setStatus("Critical");
      }
    };

    return () => ws.close();
  }, [token, selectedMachine]);

  // 3. Fetch Historical Data when switching to History Tab
  useEffect(() => {
    if (activeTab === 'history' && token) {
      fetch(`http://127.0.0.1:8000/telemetry/?machine_id=${selectedMachine}&limit=15`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      .then(res => res.json())
      .then(data => setHistoryData(data))
      .catch(err => console.error("Failed to fetch history:", err));
    }
  }, [activeTab, selectedMachine, token]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/alerts/${alertId}/acknowledge`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        setAlerts(prev => {
          const updatedAlerts = prev.filter(a => a.id !== alertId);
          if (updatedAlerts.filter(a => a.machine_id === selectedMachine).length === 0) {
            setStatus("Healthy");
          }
          return updatedAlerts;
        });
      }
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
    }
  };

  if (!token) {
    return <Login onLoginSuccess={(newToken) => setToken(newToken)} />;
  }

  const canResolve = userRole === 'admin' || userRole === 'engineer';
  const machineAlerts = alerts.filter(a => a.machine_id === selectedMachine || !a.machine_id);

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, sans-serif', backgroundColor: '#1e1e1e', color: '#fff', minHeight: '100vh' }}>
      
      {/* Top Navigation */}
      <header style={{ borderBottom: '1px solid #333', paddingBottom: '15px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <h1 style={{ margin: 0 }}>ForgeSense</h1>
          {userRole && (
            <span style={{ backgroundColor: '#3b82f6', color: 'white', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}>
              {userRole}
            </span>
          )}
          
          {/* Tab Navigation */}
          <div style={{ display: 'flex', gap: '10px', marginLeft: '20px' }}>
            <button 
              onClick={() => setActiveTab('live')}
              style={{ padding: '8px 16px', backgroundColor: activeTab === 'live' ? '#4ade80' : '#333', color: activeTab === 'live' ? '#1e1e1e' : 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              Live Dashboard
            </button>
            <button 
              onClick={() => setActiveTab('history')}
              style={{ padding: '8px 16px', backgroundColor: activeTab === 'history' ? '#4ade80' : '#333', color: activeTab === 'history' ? '#1e1e1e' : 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              Historical Data
            </button>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          {/* Machine Selector */}
          <select 
            value={selectedMachine} 
            onChange={(e) => setSelectedMachine(e.target.value)}
            style={{ padding: '8px', borderRadius: '4px', backgroundColor: '#333', color: 'white', border: '1px solid #444', outline: 'none' }}>
            <option value="CNC-001">CNC-001</option>
            <option value="CNC-002">CNC-002</option>
            <option value="MILL-001">MILL-001</option>
          </select>

          <button 
            onClick={handleLogout}
            style={{ padding: '8px 16px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
            Logout
          </button>
        </div>
      </header>

      {/* Conditional Rendering based on Active Tab */}
      {activeTab === 'live' ? (
        <div style={{ display: 'flex', gap: '20px' }}>
          {/* Left Column: Machine Status, Metrics & Charts */}
          <div style={{ flex: 2 }}>
            <div style={{ backgroundColor: '#2a2a2a', padding: '20px', borderRadius: '8px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between' }}>
              <h2>Machine: {selectedMachine}</h2>
              <h3 style={{ color: status === 'Healthy' ? '#4ade80' : '#f87171' }}>
                Status: {status === 'Healthy' ? '🟢 Healthy' : '🔴 Critical'}
              </h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginBottom: '20px' }}>
              <MetricCard title="Temperature" value={telemetry?.temperature} unit="°C" alertThreshold={85} />
              <MetricCard title="Vibration" value={telemetry?.vibration} unit="mm/s" alertThreshold={8} />
              <MetricCard title="Pressure" value={telemetry?.pressure} unit="PSI" />
              <MetricCard title="RPM" value={telemetry?.rpm} unit="rev/min" />
              <MetricCard title="Power" value={telemetry?.power_consumption} unit="kW" />
            </div>

            <div style={{ backgroundColor: '#2a2a2a', padding: '20px', borderRadius: '8px' }}>
              <h3 style={{ marginTop: 0, marginBottom: '20px', color: '#aaa' }}>Live Telemetry Streams</h3>
              <div style={{ height: '300px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={telemetryChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                    <XAxis dataKey="time" stroke="#aaa" />
                    <YAxis yAxisId="left" stroke="#f87171" domain={['dataMin - 5', 'dataMax + 5']} />
                    <YAxis yAxisId="right" orientation="right" stroke="#4ade80" domain={[0, 'dataMax + 2']} />
                    <Tooltip contentStyle={{ backgroundColor: '#1e1e1e', border: '1px solid #444', borderRadius: '4px' }} />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="temperature" stroke="#f87171" name="Temp (°C)" strokeWidth={2} dot={false} isAnimationActive={false} />
                    <Line yAxisId="right" type="monotone" dataKey="vibration" stroke="#4ade80" name="Vibration (mm/s)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Right Column: Persistent Alerts */}
          <div style={{ flex: 1, backgroundColor: '#2a2a2a', padding: '20px', borderRadius: '8px' }}>
            <h2>Active Alerts</h2>
            {machineAlerts.length === 0 ? (
              <p style={{ color: '#aaa' }}>No active alerts for this machine.</p>
            ) : (
              <ul style={{ listStyleType: 'none', padding: 0 }}>
                {machineAlerts.map((alert, index) => (
                  <li key={index} style={{ backgroundColor: '#3f2c2c', borderLeft: '4px solid #f87171', padding: '10px', marginBottom: '10px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>{alert.machine_id}:</strong> {alert.message}
                    </div>
                    {canResolve && (
                      <button 
                        onClick={() => handleAcknowledge(alert.id)}
                        style={{ padding: '4px 8px', backgroundColor: '#4ade80', color: '#1e1e1e', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}>
                        Resolve
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : (
        /* History Tab View */
        <div style={{ backgroundColor: '#2a2a2a', padding: '20px', borderRadius: '8px' }}>
          <h2>Historical Telemetry for {selectedMachine}</h2>
          {historyData.length === 0 ? (
            <p style={{ color: '#aaa' }}>No historical data found. Is the simulator running?</p>
          ) : (
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #444' }}>
                  <th style={{ padding: '10px' }}>Timestamp</th>
                  <th style={{ padding: '10px' }}>Temp (°C)</th>
                  <th style={{ padding: '10px' }}>Vibration</th>
                  <th style={{ padding: '10px' }}>Pressure</th>
                  <th style={{ padding: '10px' }}>RPM</th>
                  <th style={{ padding: '10px' }}>Power (kW)</th>
                </tr>
              </thead>
              <tbody>
                {historyData.map((row) => (
                  <tr key={row.id} style={{ borderBottom: '1px solid #333' }}>
                    <td style={{ padding: '10px' }}>{new Date(row.timestamp || '').toLocaleString()}</td>
                    <td style={{ padding: '10px', color: row.temperature > 85 ? '#f87171' : 'white' }}>{row.temperature.toFixed(2)}</td>
                    <td style={{ padding: '10px', color: row.vibration > 8 ? '#f87171' : 'white' }}>{row.vibration.toFixed(2)}</td>
                    <td style={{ padding: '10px' }}>{row.pressure.toFixed(1)}</td>
                    <td style={{ padding: '10px' }}>{row.rpm.toFixed(0)}</td>
                    <td style={{ padding: '10px' }}>{row.power_consumption.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, unit, alertThreshold }: MetricCardProps) {
  const isAnomalous = alertThreshold && value && value > alertThreshold;
  return (
    <div style={{ backgroundColor: '#2a2a2a', padding: '15px', borderRadius: '8px', border: isAnomalous ? '1px solid #f87171' : '1px solid #444' }}>
      <h4 style={{ margin: '0 0 10px 0', color: '#aaa' }}>{title}</h4>
      <div style={{ fontSize: '24px', fontWeight: 'bold', color: isAnomalous ? '#f87171' : '#fff' }}>
        {value ? value.toFixed(2) : '--'} <span style={{ fontSize: '14px', color: '#aaa' }}>{unit}</span>
      </div>
    </div>
  );
}

export default App;
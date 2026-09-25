import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, CheckCircle, Bell, Check } from 'lucide-react';

interface Telemetry {
  id: number;
  machine_id: string;
  temperature: number;
  status: string;
}

interface Alert {
  id: number;
  machine_id: string;
  message: string;
  time: string;
}

function App() {
  const [data, setData] = useState<Telemetry[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/telemetry/')
      .then(res => res.json())
      .then(initialData => setData(initialData.reverse()))
      .catch(err => console.error(err));

    const ws = new WebSocket('ws://127.0.0.1:8000/ws');

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      
      if (payload.type === 'telemetry') {
        setData((prev) => {
          const updated = [...prev, payload.data];
          return updated.length > 50 ? updated.slice(updated.length - 50) : updated;
        });
      }
      
      if (payload.type === 'alert') {
        const machineIdMatch = payload.message.match(/ANOMALY:\s(.*?)\sspiked/);
        const machineId = machineIdMatch ? machineIdMatch[1] : "Unknown";

        setAlerts((prev) => {
          if (prev.some(a => a.machine_id === machineId)) return prev;
          const newAlert = { id: Date.now(), machine_id: machineId, message: payload.message, time: new Date().toLocaleTimeString() };
          const updated = [newAlert, ...prev];
          return updated.length > 5 ? updated.slice(0, 5) : updated;
        });
      }

      if (payload.type === 'clear_alert') {
        setAlerts((prev) => prev.filter(alert => alert.machine_id !== payload.machine_id));
      }
    };

    return () => ws.close();
  }, []);

  const handleAcknowledge = async (machineId: string) => {
    try {
      await fetch(`http://127.0.0.1:8000/acknowledge/${machineId}`, { method: 'POST' });
    } catch (error) {
      console.error("Failed to acknowledge alert", error);
    }
  };

  const totalMachines = new Set(data.map(d => d.machine_id)).size;
  const criticalAlerts = data.filter(d => d.status === 'Critical').length;
  const healthyMachines = data.filter(d => d.status === 'Healthy').length;

  return (
    <div style={{ backgroundColor: '#0f172a', minHeight: '100vh', padding: '32px', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{ fontSize: '28px', fontWeight: 'bold', color: '#f8fafc', margin: 0 }}>ForgeSense</h1>
          <p style={{ color: '#94a3b8', margin: '4px 0 0 0' }}>Industrial Asset Monitoring & Predictive Maintenance</p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '24px', marginBottom: '32px' }}>
          <div style={{ backgroundColor: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#94a3b8', marginBottom: '8px' }}><Activity size={20} color="#38bdf8" /> <span>Active Machines</span></div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#f8fafc' }}>{totalMachines}</div>
          </div>
          <div style={{ backgroundColor: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#94a3b8', marginBottom: '8px' }}><AlertTriangle size={20} color="#ef4444" /> <span>Critical Logs</span></div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#f8fafc' }}>{criticalAlerts}</div>
          </div>
          <div style={{ backgroundColor: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#94a3b8', marginBottom: '8px' }}><CheckCircle size={20} color="#10b981" /> <span>Healthy Logs</span></div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#f8fafc' }}>{healthyMachines}</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          
          <div style={{ flex: '3 1 600px', backgroundColor: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155' }}>
            <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#f8fafc', marginBottom: '20px' }}>Real-Time Temperature Telemetry</h2>
            <div style={{ height: '400px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                  <XAxis dataKey="id" tick={{ fill: '#94a3b8' }} />
                  <YAxis domain={['auto', 'auto']} tick={{ fill: '#94a3b8' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', border: '1px solid #334155', color: '#f8fafc' }} />
                  <Line type="monotone" dataKey="temperature" stroke="#22d3ee" strokeWidth={3} dot={false} activeDot={{ r: 8, fill: '#22d3ee' }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ flex: '1 1 300px', backgroundColor: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#f8fafc', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bell size={20} color="#ef4444" /> Live Anomaly Alerts
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
              {alerts.length === 0 ? (
                <p style={{ color: '#64748b', fontStyle: 'italic' }}>System operating normally. No anomalies detected.</p>
              ) : (
                alerts.map(alert => (
                  <div key={alert.id} style={{ padding: '16px', backgroundColor: '#451a1e', border: '1px solid #7f1d1d', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div>
                      <p style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: '#fca5a5' }}>{alert.message}</p>
                      <span style={{ fontSize: '12px', color: '#f87171' }}>{alert.time}</span>
                    </div>
                    <button 
                      onClick={() => handleAcknowledge(alert.machine_id)}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', width: '100%', padding: '8px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '14px' }}
                    >
                      <Check size={16} /> Acknowledge
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import VoiceAgent from './VoiceAgent';
import './App.css';

// Backend port may vary (e.g., :5000 can be taken by macOS AirPlay/AirTunes),
// so allow override via REACT_APP_API_URL.
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

function App() {
  const [activeTab, setActiveTab] = useState('pricing');
  const [inputs, setInputs] = useState({
    spot: 100,
    strike: 100,
    maturity: 0.25,
    rate: 0.05,
    volatility: 0.20,
    option_type: 'call'
  });

  const [result, setResult] = useState(null);
  const [payoffData, setPayoffData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendConnected, setBackendConnected] = useState(false);

  useEffect(() => {
    // Check if backend is running on component mount
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_URL}/api/health`, {
          method: 'GET',
          mode: 'cors'
        });
        if (response.ok) {
          setBackendConnected(true);
          setError(null);
        } else {
          setBackendConnected(false);
        }
      } catch (err) {
        setBackendConnected(false);
      }
    };
    checkBackend();
    
    // Check backend connection every 5 seconds
    const interval = setInterval(checkBackend, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setInputs(prev => ({
      ...prev,
      [name]: name === 'option_type' ? value : parseFloat(value)
    }));
  };

  const calculatePrice = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(inputs),
        mode: 'cors'
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(`Backend error (${response.status}): ${errorData.error || response.statusText}`);
      }
      
      const data = await response.json();
      setResult(data);
      
      const payoffResponse = await fetch(`${API_URL}/api/payoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strike: inputs.strike,
          premium: data.price,
          option_type: inputs.option_type
        }),
        mode: 'cors'
      });
      
      if (!payoffResponse.ok) {
        const errorData = await payoffResponse.json().catch(() => ({ error: payoffResponse.statusText }));
        throw new Error(`Backend error (${payoffResponse.status}): ${errorData.error || payoffResponse.statusText}`);
      }
      
      const payoffResult = await payoffResponse.json();
      setPayoffData(payoffResult.payoffs);
    } catch (error) {
      console.error('Error:', error);
      let errorMessage = error.message;
      
      // Provide more helpful error messages
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMessage = 'Cannot connect to backend. Please ensure:\n1. Flask server is running (python app.py)\n2. Server is on http://localhost:5000\n3. No firewall is blocking the connection';
      }
      
      setError(errorMessage);
      setResult(null);
      setPayoffData([]);
    }
    setLoading(false);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Black-Scholes Option Pricing Platform</h1>
        <p>Real-time European option pricing with Greeks analysis</p>
        <nav className="app-nav">
          <button
            type="button"
            className={activeTab === 'pricing' ? 'active' : ''}
            onClick={() => setActiveTab('pricing')}
          >
            Option Pricing
          </button>
          <button
            type="button"
            className={activeTab === 'voice' ? 'active' : ''}
            onClick={() => setActiveTab('voice')}
          >
            AI Voice Agent
          </button>
        </nav>
      </header>

      {activeTab === 'voice' ? (
        <VoiceAgent />
      ) : (
      <div className="container">
        <div className="input-section">
          <h2>Input Parameters</h2>
          
          <div className="input-group">
            <label>Option Type</label>
            <select name="option_type" value={inputs.option_type} onChange={handleInputChange}>
              <option value="call">Call</option>
              <option value="put">Put</option>
            </select>
          </div>

          <div className="input-group">
            <label>Spot Price ($)</label>
            <input type="number" name="spot" value={inputs.spot} onChange={handleInputChange} />
          </div>

          <div className="input-group">
            <label>Strike Price ($)</label>
            <input type="number" name="strike" value={inputs.strike} onChange={handleInputChange} />
          </div>

          <div className="input-group">
            <label>Time to Maturity (Years)</label>
            <input type="number" name="maturity" value={inputs.maturity} onChange={handleInputChange} step="0.01" />
            <small>{(inputs.maturity * 365).toFixed(0)} days</small>
          </div>

          <div className="input-group">
            <label>Risk-Free Rate (%)</label>
            <input
              type="number"
              value={inputs.rate * 100}
              onChange={(e) => setInputs(prev => ({ ...prev, rate: parseFloat(e.target.value) / 100 }))}
              step="0.1"
            />
          </div>

          <div className="input-group">
            <label>Volatility (%)</label>
            <input
              type="number"
              value={inputs.volatility * 100}
              onChange={(e) => setInputs(prev => ({ ...prev, volatility: parseFloat(e.target.value) / 100 }))}
              step="1"
            />
          </div>

          <button onClick={calculatePrice} disabled={loading} className="calculate-btn">
            {loading ? 'Calculating...' : 'Calculate Price'}
          </button>
          
          <div style={{ 
            marginTop: '1rem', 
            padding: '0.75rem', 
            background: backendConnected ? '#efe' : '#fee', 
            border: `1px solid ${backendConnected ? '#cfc' : '#fcc'}`, 
            borderRadius: '5px', 
            color: backendConnected ? '#3c3' : '#c33',
            fontSize: '0.9rem'
          }}>
            <strong>Backend Status:</strong> {backendConnected ? '✓ Connected' : '✗ Not Connected'}
            {!backendConnected && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                Run: <code>python app.py</code> in the project root
              </div>
            )}
          </div>
          
          {error && (
            <div style={{ 
              marginTop: '1rem', 
              padding: '1rem', 
              background: '#fee', 
              border: '1px solid #fcc', 
              borderRadius: '5px', 
              color: '#c33' 
            }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {result && (
          <>
            <div className="results-section">
              <h2>Results</h2>
              <div className="result-card">
                <h3>Option Price</h3>
                <div className="price">${result.price.toFixed(4)}</div>
                <small>Response time: {result.response_time_ms.toFixed(2)}ms</small>
              </div>

              <div className="greeks-grid">
                <div className="greek-card">
                  <h4>Delta (Δ)</h4>
                  <div className="greek-value">{result.greeks.delta.toFixed(4)}</div>
                  <small>Price sensitivity</small>
                </div>
                <div className="greek-card">
                  <h4>Gamma (Γ)</h4>
                  <div className="greek-value">{result.greeks.gamma.toFixed(4)}</div>
                  <small>Delta sensitivity</small>
                </div>
                <div className="greek-card">
                  <h4>Theta (Θ)</h4>
                  <div className="greek-value">{result.greeks.theta.toFixed(4)}</div>
                  <small>Time decay</small>
                </div>
                <div className="greek-card">
                  <h4>Vega (ν)</h4>
                  <div className="greek-value">{result.greeks.vega.toFixed(4)}</div>
                  <small>Volatility sensitivity</small>
                </div>
                <div className="greek-card">
                  <h4>Rho (ρ)</h4>
                  <div className="greek-value">{result.greeks.rho.toFixed(4)}</div>
                  <small>Rate sensitivity</small>
                </div>
              </div>
            </div>

            <div className="charts-section">
              <h2>Profit/Loss Diagram</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={payoffData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="spot" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="payoff" stroke="#8884d8" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
      )}
    </div>
  );
}

export default App;
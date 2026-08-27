import React, { useState, useEffect, useRef, useCallback } from 'react';
import './VoiceAgent.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

function VoiceAgent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [speakReplies, setSpeakReplies] = useState(true);
  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/voice/status`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
          setMessages([
            {
              role: 'assistant',
              content: data.greeting,
            },
          ]);
        }
      } catch {
        setError('Cannot connect to voice agent backend.');
      }
    };
    fetchStatus();
  }, []);

  const playTts = useCallback(async (text) => {
    if (!speakReplies || !status?.openai_configured) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/voice/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // Fallback to browser speech synthesis
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
      }
    }
  }, [speakReplies, status]);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    setLoading(true);
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');

    try {
      const res = await fetch(`${API_URL}/api/v1/voice/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, session_id: sessionId }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || 'Request failed');
      }

      setSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
      await playTts(data.reply);

      if (data.escalate) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'system',
            content: 'This issue would be escalated to a human agent on a live call.',
          },
        ]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const startListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Speech recognition is not supported in this browser. Use Chrome.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(transcript);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    setListening(false);
  };

  const resetChat = async () => {
    if (sessionId) {
      await fetch(`${API_URL}/api/v1/voice/chat/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
    }
    setSessionId(null);
    setMessages([{ role: 'assistant', content: status?.greeting || 'Hello! How can I help you?' }]);
    setError(null);
  };

  return (
    <div className="voice-agent">
      <div className="voice-agent-layout">
        <aside className="voice-sidebar">
          <h2>Voice Agent</h2>
          <p className="voice-subtitle">
            AI customer service — test the same agent that answers phone calls.
          </p>

          <div className={`status-badge ${status?.openai_configured ? 'ok' : 'warn'}`}>
            OpenAI: {status?.openai_configured ? 'Connected' : 'Not configured'}
          </div>
          <div className={`status-badge ${status?.twilio_configured ? 'ok' : 'neutral'}`}>
            Twilio: {status?.twilio_configured ? 'Ready for calls' : 'Phone not configured'}
          </div>

          <div className="voice-info">
            <h3>Try asking about</h3>
            <ul>
              <li>&quot;What&apos;s the status of order ORD-1001?&quot;</li>
              <li>&quot;I need help with billing&quot;</li>
              <li>&quot;What&apos;s your refund policy?&quot;</li>
              <li>&quot;Look up jane@example.com&quot;</li>
            </ul>
          </div>

          <label className="toggle-label">
            <input
              type="checkbox"
              checked={speakReplies}
              onChange={(e) => setSpeakReplies(e.target.checked)}
            />
            Speak agent replies
          </label>

          <button type="button" className="reset-btn" onClick={resetChat}>
            New conversation
          </button>
        </aside>

        <main className="voice-main">
          <div className="chat-window">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-bubble ${msg.role}`}>
                <span className="bubble-role">
                  {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? status?.agent_name || 'Agent' : 'System'}
                </span>
                <p>{msg.content}</p>
              </div>
            ))}
            {loading && (
              <div className="chat-bubble assistant loading">
                <span className="bubble-role">{status?.agent_name || 'Agent'}</span>
                <p className="typing">Thinking...</p>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {error && <div className="voice-error">{error}</div>}

          <form className="chat-input-row" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message or use the microphone..."
              disabled={loading || !status?.openai_configured}
            />
            <button
              type="button"
              className={`mic-btn ${listening ? 'active' : ''}`}
              onClick={listening ? stopListening : startListening}
              disabled={loading || !status?.openai_configured}
              title={listening ? 'Stop listening' : 'Start voice input'}
            >
              {listening ? '⏹' : '🎤'}
            </button>
            <button type="submit" disabled={loading || !input.trim() || !status?.openai_configured}>
              Send
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

export default VoiceAgent;

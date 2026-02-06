import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Loader2, Bot, User } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';

const GROQ_API_KEY = import.meta.env.VITE_GROQ_API_KEY;
const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';

const SYSTEM_PROMPT = `You are CloudSense Assistant, an AI specialized in tropical cloud detection and meteorology. 
Your expertise includes:
- Tropical Cloud Clusters (TCC) detection using satellite data
- INSAT-3D IRBT (Infrared Brightness Temperature) data analysis
- Deep learning architectures like U-Net for cloud segmentation
- DBSCAN clustering algorithms for cloud pattern analysis
- Monsoon systems and tropical weather patterns
- Satellite meteorology and remote sensing

Provide accurate, helpful responses about cloud patterns, weather systems, and the science behind tropical cloud detection.
Keep responses concise but informative.`;

export default function ChatBot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const [initialized, setInitialized] = useState(false);
  const [apiKeyMissing, setApiKeyMissing] = useState(false);

  useEffect(() => {
    if (!initialized) {
      setMessages([
        {
          id: '0',
          type: 'bot',
          content: 'Hello! I\'m CloudSense Assistant. I can help you analyze cloud patterns and answer questions about tropical cloud systems. What would you like to know?',
          timestamp: new Date(),
        },
      ]);
      setInitialized(true);
      
      // Check if API key is available
      if (!GROQ_API_KEY) {
        setApiKeyMissing(true);
        console.warn('Groq API key not found. Set VITE_GROQ_API_KEY in .env file.');
      }
    }
  }, [initialized]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // If no API key, use fallback response
      if (!GROQ_API_KEY) {
        setTimeout(() => {
          const botMessage = {
            id: (Date.now() + 1).toString(),
            type: 'bot',
            content: `You asked about "${input}". I'm CloudSense Assistant, but my AI brain (Groq API) isn't connected yet. Please ask your administrator to add the VITE_GROQ_API_KEY to the .env file.`,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, botMessage]);
          setLoading(false);
        }, 1000);
        return;
      }

      // Build conversation history for context
      const conversationHistory = messages.map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content
      }));

      const response = await fetch(GROQ_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${GROQ_API_KEY}`,
        },
        body: JSON.stringify({
          model: 'llama-3.1-8b-instant',
          messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            ...conversationHistory,
            { role: 'user', content: input }
          ],
          temperature: 0.7,
          max_tokens: 1024,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      const botResponse = data.choices[0]?.message?.content || 'I apologize, I could not generate a response.';

      const botMessage = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: botResponse,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
      setLoading(false);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        id: Date.now().toString(),
        type: 'bot',
        content: `Sorry, I encountered an error: ${error.message}. Please check your API key or try again later.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        {/* Header */}
        <div className="bg-slate-900 border-b border-slate-800 p-4">
          <h2 className="text-lg font-semibold text-slate-50">CloudSense AI Assistant</h2>
          <p className="text-sm text-slate-400">Ask questions about cloud patterns and tropical systems</p>
        </div>

        {/* Chat Container */}
        <div className="flex-1 overflow-auto flex flex-col bg-slate-950">
          {/* Messages Area */}
          <div className="flex-1 p-6 space-y-4 overflow-y-auto">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.type === 'bot' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/50">
                      <Bot className="w-4 h-4 text-cyan-400" />
                    </div>
                  </div>
                )}

                <div
                  className={`max-w-lg rounded-lg p-4 ${
                    message.type === 'user'
                      ? 'bg-cyan-600 text-white shadow-lg'
                      : 'bg-slate-800 text-slate-100 border border-slate-700'
                  }`}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  <p
                    className={`text-xs mt-2 ${
                      message.type === 'user'
                        ? 'text-white/60'
                        : 'text-slate-400'
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>

                {message.type === 'user' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-cyan-600 flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/50">
                  <Bot className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="flex items-center gap-2 p-4 bg-slate-800 rounded-lg border border-slate-700">
                  <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                  <span className="text-sm text-slate-300">AI is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="bg-slate-900 border-t border-slate-800 p-4">
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about cloud patterns..."
                disabled={loading}
                className="flex-1 bg-slate-800 border-slate-700 text-slate-100 placeholder-slate-500 focus:border-cyan-400"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-700 text-white rounded-lg transition-colors flex items-center justify-center"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

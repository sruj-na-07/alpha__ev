import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Bot, User, BookOpen } from 'lucide-react';
import Alphi from '../components/Alphi';
import { sendChatMessage, type ChatMessage } from '../api';

export default function ChatbotPage() {
  const { id } = useParams<{ id: string }>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!id || !input.trim() || loading) return;
    const userMsg: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(id, input);
      setMessages(prev => [...prev, response]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error processing your question. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    'What are the top complaints?',
    'How is the overall sentiment?',
    'Which aspects get the most negative feedback?',
    'What do people say about charging speed?',
    'How many reviews mention payment issues?',
    'Show me the most positive reviews',
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Ask Alphi</h2>
          <p className="text-gray-500 mt-1">Chat about your review data</p>
        </div>
        <Alphi mood={loading ? 'thinking' : 'happy'} size="sm" />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-white rounded-2xl border border-gray-100">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Alphi mood="happy" size="md" message="Ask me anything about your dataset! I answer from your actual data, never making things up." />
            <div className="mt-8 grid grid-cols-2 gap-2 max-w-lg mx-auto">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="text-left text-sm p-3 rounded-xl border border-gray-200 hover:border-teal-300 hover:bg-teal-50 transition-colors text-gray-600"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0">
                <Bot size={16} className="text-teal-600" />
              </div>
            )}
            <div className={`max-w-[75%] ${msg.role === 'user' ? 'bg-teal-600 text-white rounded-2xl rounded-br-md' : 'bg-gray-50 text-gray-800 rounded-2xl rounded-bl-md'} px-4 py-3`}>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              
              {/* Evidence */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="mt-3 border-t border-gray-200 pt-2">
                  <p className="text-xs font-medium text-gray-500 flex items-center gap-1 mb-1">
                    <BookOpen size={12} /> Supporting Evidence
                  </p>
                  {msg.evidence.map((e, j) => (
                    <div key={j} className="text-xs bg-white rounded-lg p-2 mt-1 border border-gray-100">
                      <span className="font-mono text-gray-400">#{e.review_id}</span>
                      <p className="text-gray-600 mt-0.5 italic">"{e.text}"</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Stats */}
              {msg.stats && Object.keys(msg.stats).length > 0 && (
                <div className="mt-3 border-t border-gray-200 pt-2">
                  <div className="grid grid-cols-2 gap-1">
                    {Object.entries(msg.stats).map(([k, v]) => (
                      <div key={k} className="text-xs">
                        <span className="text-gray-500">{k}: </span>
                        <span className="font-medium">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0">
              <Bot size={16} className="text-teal-600" />
            </div>
            <div className="bg-gray-50 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask about your reviews..."
          className="input-field flex-1"
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()} className="btn-primary flex items-center gap-2 disabled:opacity-50">
          <Send size={16} /> Send
        </button>
      </div>
    </div>
  );
}

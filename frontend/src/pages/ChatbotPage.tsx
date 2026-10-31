import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Bot, User, BookOpen, Database, Sparkles, Star } from 'lucide-react';
import Alpha from '../components/Alphi';
import { sendChatMessage, type ChatMessage, type ChatEvidenceItem } from '../api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatbotPage() {
  const { id } = useParams<{ id: string }>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState<Record<number, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async () => {
    if (!id || !input.trim() || loading) return;
    const queryText = input.trim();
    const userMsg: ChatMessage = { role: 'user', content: queryText };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(id, queryText);
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: response.answer,
        intent: response.intent,
        sql_or_search: response.sql_or_search,
        total_matched: response.total_matched,
        evidence: response.evidence || [],
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content:
            err.response?.data?.detail ||
            'Sorry, I encountered an error processing your question. Please ensure your dataset has been cleaned and classified, then try again.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSql = (msgIndex: number) => {
    setShowSql(prev => ({ ...prev, [msgIndex]: !prev[msgIndex] }));
  };

  const suggestedQuestions = [
    'What are the top complaints?',
    'What is the overall sentiment breakdown?',
    'What do customers say about charging and battery?',
    'Which aspects get the most negative feedback?',
    'What is the average rating of usable reviews?',
    'Show me reviews mentioning software and app usability',
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Ask Alpha</h2>
          <p className="text-gray-500 mt-1">
            Explainable AI chat grounded strictly on your EV reviews & database evidence
          </p>
        </div>
        <Alpha mood={loading ? 'thinking' : 'happy'} size="sm" />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-white rounded-2xl border border-gray-100 shadow-sm">
        {messages.length === 0 && (
          <div className="text-center py-10 max-w-xl mx-auto">
            <Alpha
              mood="happy"
              size="md"
              message="Ask me anything about your dataset! I query your actual reviews and never hallucinate answers."
            />
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="text-left text-xs sm:text-sm p-3 rounded-xl border border-gray-200 hover:border-teal-400 hover:bg-teal-50/60 transition-colors text-gray-700 font-medium"
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
              <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0 mt-1">
                <Bot size={16} className="text-teal-700" />
              </div>
            )}

            <div
              className={`max-w-[85%] sm:max-w-[75%] ${
                msg.role === 'user'
                  ? 'bg-teal-600 text-white rounded-2xl rounded-br-md px-4 py-3'
                  : 'bg-gray-50 text-gray-800 rounded-2xl rounded-bl-md px-4 py-3 border border-gray-100 shadow-sm'
              }`}
            >
              {/* Answer content */}
              {/* Formatted AI Answer */}
<div
  className="
    text-sm leading-relaxed
    [&_h1]:text-lg [&_h1]:font-bold [&_h1]:my-3
    [&_h2]:text-base [&_h2]:font-bold [&_h2]:my-3
    [&_h3]:font-semibold [&_h3]:my-2
    [&_p]:my-2
    [&_strong]:font-bold
    [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:my-2
    [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:my-2
    [&_li]:my-1
    [&_table]:w-full [&_table]:border-collapse [&_table]:my-3
    [&_th]:bg-teal-50 [&_th]:font-semibold [&_th]:text-left
    [&_th]:border [&_th]:border-gray-200 [&_th]:p-2
    [&_td]:border [&_td]:border-gray-200 [&_td]:p-2
    [&_blockquote]:border-l-4 [&_blockquote]:border-teal-400
    [&_blockquote]:pl-3 [&_blockquote]:my-2
  "
>
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {msg.content.replace(/<br\s*\/?>/gi, ' ')}
  </ReactMarkdown>
</div>

              {/* Metadata badges for assistant message */}
              {msg.role === 'assistant' && (msg.intent || msg.total_matched !== undefined) && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200/60 flex-wrap">
                  {msg.intent && (
                    <span className="badge bg-teal-50 text-teal-700 border border-teal-200 text-[10px]">
                      Intent: {msg.intent}
                    </span>
                  )}
                  {msg.total_matched !== undefined && msg.total_matched > 0 && (
                    <span className="badge bg-blue-50 text-blue-700 border border-blue-200 text-[10px]">
                      {msg.total_matched} matching reviews found
                    </span>
                  )}
                  {msg.sql_or_search && (
                    <button
                      onClick={() => toggleSql(i)}
                      className="text-[10px] text-gray-500 hover:text-teal-700 font-mono inline-flex items-center gap-1 ml-auto"
                    >
                      <Database size={10} />
                      {showSql[i] ? 'Hide Logic' : 'View Query Logic'}
                    </button>
                  )}
                </div>
              )}

              {/* Expandable SQL / Search Logic */}
              {msg.role === 'assistant' && showSql[i] && msg.sql_or_search && (
                <div className="mt-2 p-2 bg-navy-950 text-teal-300 rounded-lg text-[11px] font-mono overflow-x-auto">
                  {msg.sql_or_search}
                </div>
              )}

              {/* Evidence cards */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="mt-3 border-t border-gray-200/80 pt-2 space-y-2">
                  <p className="text-xs font-semibold text-gray-600 flex items-center gap-1.5">
                    <BookOpen size={13} className="text-teal-600" /> Grounded Evidence ({msg.evidence.length})
                  </p>
                  <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                    {msg.evidence.map((e, j) => (
                      <div
                        key={j}
                        className="text-xs bg-white rounded-lg p-2.5 border border-gray-200/70 shadow-2xs"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
                          <span className="font-mono text-[10px] text-gray-400">Review #{e.review_id}</span>
                          <div className="flex items-center gap-1.5">
                            {e.rating !== null && (
                              <span className="text-amber-600 text-[11px] font-semibold flex items-center gap-0.5">
                                <Star size={10} className="fill-amber-400" />
                                {e.rating}
                              </span>
                            )}
                            {e.sentiment && (
                              <span
                                className={`badge text-[10px] ${
                                  e.sentiment === 'positive'
                                    ? 'badge-positive'
                                    : e.sentiment === 'negative'
                                    ? 'badge-negative'
                                    : 'bg-gray-100 text-gray-600'
                                }`}
                              >
                                {e.sentiment}
                              </span>
                            )}
                          </div>
                        </div>

                        <p className="text-gray-700 italic leading-relaxed">"{e.text}"</p>

                        {e.aspects && e.aspects.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {e.aspects.map((asp, k) => (
                              <span key={k} className="badge bg-teal-50 text-teal-700 text-[9px]">
                                {asp}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-1">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0">
              <Bot size={16} className="text-teal-700" />
            </div>
            <div className="bg-gray-50 rounded-2xl rounded-bl-md px-4 py-3 border border-gray-100">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs text-gray-400 ml-1">Alpha is analyzing reviews...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask a question about your EV reviews (e.g. 'What are the main battery complaints?')..."
          className="input-field flex-1 text-sm"
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="btn-primary flex items-center gap-1.5 disabled:opacity-50 px-5"
        >
          <Send size={15} /> Send
        </button>
      </div>
    </div>
  );
}

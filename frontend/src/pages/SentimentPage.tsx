import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Zap, ArrowRight, Heart, Frown, Smile, Meh } from 'lucide-react';
import toast from 'react-hot-toast';
import Alphi from '../components/Alphi';
import { startSentimentAnalysis, getSentiments, updateSentiment, getReviews, type SentimentResult, type Review } from '../api';

const SENTIMENTS = ['positive', 'negative', 'neutral'];
const EMOTIONS = ['happy', 'sad', 'frustrated', 'satisfaction', 'neutral'];

const sentimentIcons: Record<string, any> = {
  positive: Smile,
  negative: Frown,
  neutral: Meh,
};

const sentimentColors: Record<string, string> = {
  positive: 'text-emerald-600 bg-emerald-50',
  negative: 'text-red-600 bg-red-50',
  neutral: 'text-gray-600 bg-gray-50',
};

const emotionEmojis: Record<string, string> = {
  happy: '😊', sad: '😢', frustrated: '😤', satisfaction: '😌', neutral: '😐',
};

export default function SentimentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [sentiments, setSentiments] = useState<SentimentResult[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);

  useEffect(() => {
    if (!id) return;
    getSentiments(id).then(s => {
      if (s.length > 0) { setSentiments(s); setStatus('done'); }
    }).catch(() => {});
    getReviews(id, { limit: 100 }).then(d => setReviews(d.reviews)).catch(() => {});
  }, [id]);

  const handleAnalyze = async () => {
    if (!id) return;
    setStatus('running');
    try {
      await startSentimentAnalysis(id);
      const poll = setInterval(async () => {
        try {
          const s = await getSentiments(id);
          if (s.length > 0) {
            clearInterval(poll);
            setSentiments(s);
            setStatus('done');
            toast.success('Sentiment analysis complete!');
          }
        } catch {
          clearInterval(poll);
          setStatus('error');
        }
      }, 2000);
    } catch (err: any) {
      setStatus('error');
      toast.error(err.response?.data?.detail || 'Analysis failed');
    }
  };

  const handleUpdate = async (sentId: number, field: string, value: string) => {
    try {
      const updates: any = { is_human_corrected: true };
      updates[field] = value;
      const updated = await updateSentiment(sentId, updates);
      setSentiments(prev => prev.map(s => s.id === sentId ? updated : s));
      toast.success('Updated');
    } catch {
      toast.error('Update failed');
    }
  };

  const sentimentDist = SENTIMENTS.reduce((acc, s) => {
    acc[s] = sentiments.filter(x => x.overall_sentiment === s).length;
    return acc;
  }, {} as Record<string, number>);

  const emotionDist = EMOTIONS.reduce((acc, e) => {
    acc[e] = sentiments.filter(x => x.emotion === e).length;
    return acc;
  }, {} as Record<string, number>);

  const reviewMap = reviews.reduce((acc, r) => { acc[r.id] = r; return acc; }, {} as Record<string, Review>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Sentiment & Emotion</h2>
          <p className="text-gray-500 mt-1">How do your customers feel?</p>
        </div>
        <Alphi mood={status === 'running' ? 'thinking' : status === 'done' ? 'happy' : 'idle'} size="sm" />
      </div>

      {status === 'idle' && (
        <div className="card text-center py-10">
          <Alphi mood="idle" size="md" message="Ready to analyze sentiment and emotion in your reviews!" />
          <button onClick={handleAnalyze} className="btn-primary mt-6 inline-flex items-center gap-2">
            <Zap size={18} /> Analyze Sentiment
          </button>
        </div>
      )}

      {status === 'running' && (
        <div className="card text-center py-10">
          <Alphi mood="thinking" size="md" message="Alphi is feeling the vibes... 💭" />
          <div className="w-48 mx-auto mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-teal-500 rounded-full animate-pulse" style={{ width: '50%' }} />
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="card text-center py-10">
          <Alphi mood="error" size="md" message="Something went wrong" />
          <button onClick={handleAnalyze} className="btn-primary mt-4">Retry</button>
        </div>
      )}

      {status === 'done' && (
        <>
          {/* Distribution */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Sentiment Distribution</h3>
              <div className="space-y-3">
                {SENTIMENTS.map(s => {
                  const count = sentimentDist[s];
                  const pct = sentiments.length > 0 ? (count / sentiments.length * 100) : 0;
                  return (
                    <div key={s} className="flex items-center gap-3">
                      <span className={`w-24 text-sm font-medium capitalize ${sentimentColors[s].split(' ')[0]}`}>{s}</span>
                      <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${s === 'positive' ? 'bg-emerald-400' : s === 'negative' ? 'bg-red-400' : 'bg-gray-300'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 w-16 text-right">{count} ({pct.toFixed(0)}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Emotion Distribution</h3>
              <div className="space-y-3">
                {EMOTIONS.map(e => {
                  const count = emotionDist[e];
                  const pct = sentiments.length > 0 ? (count / sentiments.length * 100) : 0;
                  return (
                    <div key={e} className="flex items-center gap-3">
                      <span className="w-24 text-sm font-medium capitalize">{emotionEmojis[e]} {e}</span>
                      <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-teal-400 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-sm text-gray-500 w-16 text-right">{count} ({pct.toFixed(0)}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Per-review sentiments */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Review Sentiments</h3>
            <div className="space-y-2">
              {sentiments.map(sent => {
                const review = reviewMap[sent.review_id];
                if (!review) return null;
                return (
                  <div key={sent.id} className="border border-gray-100 rounded-xl p-4">
                    <p className="text-sm text-gray-700 mb-2">{review.cleaned_text || review.original_text}</p>
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-gray-500">Sentiment:</span>
                        <select
                          value={sent.overall_sentiment}
                          onChange={e => handleUpdate(sent.id, 'overall_sentiment', e.target.value)}
                          className={`text-xs font-medium border rounded px-2 py-1 ${sentimentColors[sent.overall_sentiment]}`}
                        >
                          {SENTIMENTS.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <span className="text-xs text-gray-400">({(sent.sentiment_confidence * 100).toFixed(0)}%)</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-gray-500">Emotion:</span>
                        <select
                          value={sent.emotion}
                          onChange={e => handleUpdate(sent.id, 'emotion', e.target.value)}
                          className="text-xs font-medium border rounded px-2 py-1"
                        >
                          {EMOTIONS.map(e => <option key={e} value={e}>{emotionEmojis[e]} {e}</option>)}
                        </select>
                        <span className="text-xs text-gray-400">({(sent.emotion_confidence * 100).toFixed(0)}%)</span>
                      </div>
                      {sent.is_human_corrected && <span className="badge bg-blue-100 text-blue-700">Edited</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end">
            <button onClick={() => navigate(`/dataset/${id}/dashboard`)} className="btn-primary flex items-center gap-2">
              View Dashboard <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

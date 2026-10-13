import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Brain, ArrowRight, ChevronDown, Save, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import Alphi from '../components/Alphi';
import { startClassification, getPredictions, updatePrediction, getReviews, getExplanation, type Prediction, type Review } from '../api';

const ASPECTS = [
  'pricing', 'payment_issues', 'charging_speed', 'reliability', 'waiting_time',
  'app_usability', 'availability', 'location_convenience', 'customer_support',
  'improvement_suggestion', 'overall_experience'
];

const ASPECT_LABELS: Record<string, string> = {
  pricing: 'Pricing', payment_issues: 'Payment Issues', charging_speed: 'Charging Speed',
  reliability: 'Reliability', waiting_time: 'Waiting Time', app_usability: 'App Usability',
  availability: 'Availability', location_convenience: 'Location Convenience',
  customer_support: 'Customer Support', improvement_suggestion: 'Improvement Suggestion',
  overall_experience: 'Overall Experience',
};

export default function ClassificationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [explanation, setExplanation] = useState<any>(null);
  const [selectedReview, setSelectedReview] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    // Check if predictions already exist
    getPredictions(id).then(preds => {
      if (preds.length > 0) {
        setPredictions(preds);
        setStatus('done');
      }
    }).catch(() => {});
    getReviews(id, { limit: 100 }).then(data => setReviews(data.reviews)).catch(() => {});
  }, [id]);

  const handleClassify = async () => {
    if (!id) return;
    setStatus('running');
    try {
      await startClassification(id);
      // Poll
      const poll = setInterval(async () => {
        try {
          const preds = await getPredictions(id);
          if (preds.length > 0) {
            clearInterval(poll);
            setPredictions(preds);
            setStatus('done');
            toast.success('Classification complete!');
          }
        } catch {
          clearInterval(poll);
          setStatus('error');
        }
      }, 2000);
    } catch (err: any) {
      setStatus('error');
      toast.error(err.response?.data?.detail || 'Classification failed');
    }
  };

  const handleUpdatePrediction = async (predId: number, aspect: string, polarity: string) => {
    try {
      const updated = await updatePrediction(predId, { aspect, polarity, is_human_corrected: true });
      setPredictions(prev => prev.map(p => p.id === predId ? updated : p));
      toast.success('Prediction updated');
    } catch {
      toast.error('Failed to update');
    }
  };

  const handleExplain = async (reviewId: string) => {
    setSelectedReview(reviewId);
    try {
      const exp = await getExplanation(reviewId);
      setExplanation(exp);
    } catch {
      setExplanation({ error: 'Explanation not available for this model type' });
    }
  };

  // Group predictions by review
  const predsByReview = predictions.reduce((acc, p) => {
    if (!acc[p.review_id]) acc[p.review_id] = [];
    acc[p.review_id].push(p);
    return acc;
  }, {} as Record<string, Prediction[]>);

  // Aspect summary counts
  const aspectCounts = ASPECTS.reduce((acc, a) => {
    acc[a] = { positive: 0, negative: 0 };
    predictions.forEach(p => {
      if (p.aspect === a) {
        if (p.polarity === 'positive') acc[a].positive++;
        else if (p.polarity === 'negative') acc[a].negative++;
      }
    });
    return acc;
  }, {} as Record<string, { positive: number; negative: number }>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Aspect Classification</h2>
          <p className="text-gray-500 mt-1">Alphi detects what customers are talking about</p>
        </div>
        <Alphi mood={status === 'running' ? 'detective' : status === 'done' ? 'happy' : 'idle'} size="sm" />
      </div>

      {/* Model info */}
      <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-xl text-sm text-blue-700">
        <Info size={16} className="mt-0.5 shrink-0" />
        <p>Using keyword-based baseline classifier. For improved accuracy, train a TF-IDF + LogisticRegression model with labeled data using the provided training script.</p>
      </div>

      {status === 'idle' && (
        <div className="card text-center py-10">
          <Alphi mood="detective" size="md" message="Ready to classify your reviews into 11 EV charging aspects with positive/negative polarity!" />
          <button onClick={handleClassify} className="btn-primary mt-6 inline-flex items-center gap-2">
            <Brain size={18} /> Start Classification
          </button>
        </div>
      )}

      {status === 'running' && (
        <div className="card text-center py-10">
          <Alphi mood="detective" size="md" message="Alphi is inspecting each review... 🔍" />
          <div className="w-48 mx-auto mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-teal-500 rounded-full animate-pulse" style={{ width: '50%' }} />
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="card text-center py-10">
          <Alphi mood="error" size="md" message="Classification encountered an error" />
          <button onClick={handleClassify} className="btn-primary mt-4">Retry</button>
        </div>
      )}

      {/* Aspect Summary */}
      {status === 'done' && (
        <>
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Aspect Overview</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {ASPECTS.map(aspect => (
                <div key={aspect} className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs font-medium text-gray-500 mb-2">{ASPECT_LABELS[aspect]}</p>
                  <div className="flex items-center gap-3">
                    <span className="badge badge-positive">+{aspectCounts[aspect].positive}</span>
                    <span className="badge badge-negative">-{aspectCounts[aspect].negative}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Per-review predictions */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Review Classifications</h3>
            <div className="space-y-3">
              {reviews.map(review => {
                const preds = predsByReview[review.id] || [];
                if (preds.length === 0) return null;
                return (
                  <div key={review.id} className="border border-gray-100 rounded-xl p-4">
                    <p className="text-sm text-gray-700 mb-3">{review.cleaned_text || review.original_text}</p>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {preds.map(pred => (
                        <div key={pred.id} className="flex items-center gap-1">
                          <span className={`badge ${pred.polarity === 'positive' ? 'badge-positive' : 'badge-negative'} ${pred.is_human_corrected ? 'ring-2 ring-blue-300' : ''}`}>
                            {ASPECT_LABELS[pred.aspect]} ({(pred.confidence * 100).toFixed(0)}%)
                          </span>
                          <select
                            className="text-xs border rounded px-1 py-0.5"
                            value={`${pred.aspect}_${pred.polarity}`}
                            onChange={e => {
                              const [a, p] = e.target.value.split(/_(?=[^_]+$)/);
                              handleUpdatePrediction(pred.id, a, p);
                            }}
                          >
                            {ASPECTS.flatMap(a => [
                              <option key={`${a}_positive`} value={`${a}_positive`}>{ASPECT_LABELS[a]} (+)</option>,
                              <option key={`${a}_negative`} value={`${a}_negative`}>{ASPECT_LABELS[a]} (-)</option>,
                            ])}
                          </select>
                        </div>
                      ))}
                    </div>
                    <button onClick={() => handleExplain(review.id)} className="text-xs text-teal-600 hover:text-teal-700 font-medium">
                      Show Explanation
                    </button>
                    {selectedReview === review.id && explanation && (
                      <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs">
                        {explanation.error ? (
                          <p className="text-gray-500">{explanation.error}</p>
                        ) : (
                          <div>
                            <p className="font-medium text-gray-700 mb-1">Key words influencing classification:</p>
                            <div className="flex flex-wrap gap-1">
                              {(explanation.keywords || []).map((kw: any, i: number) => (
                                <span key={i} className={`px-1.5 py-0.5 rounded text-xs ${kw.weight > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                  {kw.word} ({kw.weight > 0 ? '+' : ''}{kw.weight.toFixed(2)})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end">
            <button onClick={() => navigate(`/dataset/${id}/sentiment`)} className="btn-primary flex items-center gap-2">
              Continue to Sentiment Analysis <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

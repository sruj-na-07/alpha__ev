import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, AlertTriangle, Check, Search, Download, Edit3, X, Save, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import Alphi from '../components/Alphi';
import { startCleaning, getCleaningStatus, getCleaningReport, getReviews, updateReview, exportResults, type Review } from '../api';

export default function CleaningPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [report, setReport] = useState<any>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [totalReviews, setTotalReviews] = useState(0);
  const [page, setPage] = useState(1);
  const [flagsOnly, setFlagsOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [showComparison, setShowComparison] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getReviews(id, { page, limit: 20, flags_only: flagsOnly, search: search || undefined });
      setReviews(data.reviews);
      setTotalReviews(data.total);
    } catch { /* reviews may not be ready yet */ }
  }, [id, page, flagsOnly, search]);

  useEffect(() => { fetchReviews(); }, [fetchReviews]);

  const handleStartCleaning = async () => {
    if (!id) return;
    setStatus('cleaning');
    try {
      await startCleaning(id);
      // Poll for status
      const poll = setInterval(async () => {
        try {
          const s = await getCleaningStatus(id);
          setProgress(s.progress);
          if (s.status === 'cleaned' || s.status === 'complete') {
            clearInterval(poll);
            setStatus('done');
            setProgress(100);
            const rep = await getCleaningReport(id);
            setReport(rep);
            fetchReviews();
            toast.success('Cleaning complete!');
          } else if (s.status === 'error') {
            clearInterval(poll);
            setStatus('error');
            toast.error('Cleaning failed');
          }
        } catch {
          clearInterval(poll);
          setStatus('error');
        }
      }, 1500);
    } catch (err: any) {
      setStatus('error');
      toast.error(err.response?.data?.detail || 'Failed to start cleaning');
    }
  };

  const handleSaveEdit = async (reviewId: string) => {
    try {
      await updateReview(reviewId, { cleaned_text: editText });
      setEditingId(null);
      fetchReviews();
      toast.success('Review updated');
    } catch {
      toast.error('Failed to update');
    }
  };

  const handleExport = async () => {
    if (!id) return;
    try {
      const blob = await exportResults(id, 'csv');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cleaned_reviews_${id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Export failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Data Cleaning</h2>
          <p className="text-gray-500 mt-1">Alphi sweeps your data clean</p>
        </div>
        <Alphi mood={status === 'cleaning' ? 'cleaning' : status === 'done' ? 'happy' : status === 'error' ? 'error' : 'idle'} size="sm" />
      </div>

      {/* Start cleaning */}
      {status === 'idle' && (
        <div className="card text-center py-10">
          <Alphi mood="cleaning" size="md" message="Ready to clean your dataset! This includes encoding fixes, HTML removal, duplicate detection, language identification, and more." />
          <button onClick={handleStartCleaning} className="btn-primary mt-6 inline-flex items-center gap-2">
            <Sparkles size={18} /> Start Cleaning
          </button>
        </div>
      )}

      {/* Progress */}
      {status === 'cleaning' && (
        <div className="card text-center py-10">
          <Alphi mood="cleaning" size="md" message="Alphi is sweeping through your reviews... 🧹" />
          <div className="w-64 mx-auto mt-6">
            <div className="flex justify-between text-sm text-gray-500 mb-1">
              <span>Cleaning</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-teal-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="card text-center py-10">
          <Alphi mood="error" size="md" message="Oops! Something went wrong during cleaning." />
          <button onClick={handleStartCleaning} className="btn-primary mt-4">Retry</button>
        </div>
      )}

      {/* Cleaning Report */}
      {report && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Check size={18} className="text-teal-600" /> Cleaning Report
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Reviews', value: report.total_reviews ?? totalReviews, color: 'text-gray-900' },
              { label: 'HTML Cleaned', value: report.html_cleaned ?? 0, color: 'text-blue-600' },
              { label: 'Duplicates Found', value: report.duplicates_found ?? 0, color: 'text-amber-600' },
              { label: 'Near-Duplicates', value: report.near_duplicates ?? 0, color: 'text-orange-600' },
              { label: 'Encoding Fixed', value: report.encoding_fixed ?? 0, color: 'text-purple-600' },
              { label: 'Low Information', value: report.low_info ?? 0, color: 'text-red-600' },
              { label: 'Languages Detected', value: report.languages_detected ?? 0, color: 'text-teal-600' },
              { label: 'Whitespace Fixed', value: report.whitespace_fixed ?? 0, color: 'text-indigo-600' },
            ].map(stat => (
              <div key={stat.label} className="bg-gray-50 rounded-xl p-3">
                <p className="text-xs text-gray-500 font-medium">{stat.label}</p>
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reviews table */}
      {(status === 'done' || reviews.length > 0) && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Reviews ({totalReviews})</h3>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search reviews..."
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1); }}
                  className="input-field pl-9 text-sm w-56"
                />
              </div>
              <button
                onClick={() => { setFlagsOnly(!flagsOnly); setPage(1); }}
                className={`text-sm px-3 py-1.5 rounded-lg transition-colors ${flagsOnly ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                <AlertTriangle size={14} className="inline mr-1" />
                {flagsOnly ? 'Showing Flagged' : 'Show Flagged'}
              </button>
              <button onClick={handleExport} className="btn-ghost text-sm flex items-center gap-1">
                <Download size={14} /> Export
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {reviews.map(review => (
              <div key={review.id} className={`border rounded-xl p-4 transition-colors ${review.flags.length > 0 || review.is_duplicate || review.is_low_info ? 'border-amber-200 bg-amber-50/50' : 'border-gray-100'}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs text-gray-400 font-mono">#{review.row_index}</span>
                      {review.is_duplicate && <span className="badge badge-negative">Duplicate</span>}
                      {review.is_low_info && <span className="badge bg-amber-100 text-amber-700">Low Info</span>}
                      {review.language && review.language !== 'en' && <span className="badge bg-blue-100 text-blue-700">{review.language}</span>}
                      {review.rating !== null && (
                        <span className="text-xs text-gray-400">★ {review.rating}</span>
                      )}
                      {review.flags.map((f, i) => (
                        <span key={i} className="badge bg-gray-100 text-gray-500 text-[10px]">{f.type}</span>
                      ))}
                    </div>

                    {editingId === review.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={editText}
                          onChange={e => setEditText(e.target.value)}
                          className="input-field text-sm min-h-[80px]"
                        />
                        <div className="flex gap-2">
                          <button onClick={() => handleSaveEdit(review.id)} className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1">
                            <Save size={12} /> Save
                          </button>
                          <button onClick={() => setEditingId(null)} className="btn-ghost text-xs py-1.5 px-3">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-700">{review.cleaned_text || review.original_text}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {review.cleaned_text && review.original_text !== review.cleaned_text && (
                      <button
                        onClick={() => setShowComparison(showComparison === review.id ? null : review.id)}
                        className="btn-ghost p-1.5"
                        title="Compare original/cleaned"
                      >
                        <Eye size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => { setEditingId(review.id); setEditText(review.cleaned_text || review.original_text); }}
                      className="btn-ghost p-1.5"
                      title="Edit"
                    >
                      <Edit3 size={14} />
                    </button>
                  </div>
                </div>

                {showComparison === review.id && (
                  <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-red-50 rounded-lg p-2">
                      <p className="font-medium text-red-700 mb-1">Original</p>
                      <p className="text-gray-600">{review.original_text}</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-2">
                      <p className="font-medium text-green-700 mb-1">Cleaned</p>
                      <p className="text-gray-600">{review.cleaned_text}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex justify-center gap-2 mt-4">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="btn-ghost text-sm disabled:opacity-30">Previous</button>
            <span className="text-sm text-gray-400 py-2">Page {page}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={reviews.length < 20} className="btn-ghost text-sm disabled:opacity-30">Next</button>
          </div>
        </div>
      )}

      {/* Next step */}
      {status === 'done' && (
        <div className="flex justify-end">
          <button onClick={() => navigate(`/dataset/${id}/classify`)} className="btn-primary flex items-center gap-2">
            Continue to Classification <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

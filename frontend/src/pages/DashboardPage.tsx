import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { BarChart3, Download, Search, MessageSquare, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend } from 'recharts';
import toast from 'react-hot-toast';
import Alphi from '../components/Alphi';
import { getDashboard, exportResults, getReviews, type DashboardData, type Review } from '../api';

const COLORS = ['#10b981', '#ef4444', '#6b7280', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'];

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Review[]>([]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getDashboard(id)
      .then(d => setData(d))
      .catch(() => toast.error('Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSearch = async () => {
    if (!id || !searchQuery.trim()) return;
    try {
      const res = await getReviews(id, { search: searchQuery, limit: 20 });
      setSearchResults(res.reviews);
    } catch {
      toast.error('Search failed');
    }
  };

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (!id) return;
    try {
      const blob = await exportResults(id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `alphaev_results_${id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Exported!');
    } catch {
      toast.error('Export failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Alphi mood="thinking" size="md" message="Loading dashboard..." />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card text-center py-10">
        <Alphi mood="error" size="md" message="No data available. Complete the analysis pipeline first." />
      </div>
    );
  }

  const sentimentChartData = Object.entries(data.sentiment_distribution).map(([name, value]) => ({ name, value }));
  const emotionChartData = Object.entries(data.emotion_distribution).map(([name, value]) => ({ name, value }));
  const aspectChartData = Object.entries(data.aspect_counts).map(([name, counts]) => ({
    name: name.replace(/_/g, ' '),
    positive: counts.positive,
    negative: counts.negative,
  }));
  const ratingChartData = Object.entries(data.rating_distribution).map(([rating, count]) => ({
    rating: `★${rating}`,
    count,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-500 mt-1">Your complete review intelligence overview</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => handleExport('csv')} className="btn-secondary text-sm flex items-center gap-1">
            <Download size={14} /> CSV
          </button>
          <button onClick={() => handleExport('xlsx')} className="btn-secondary text-sm flex items-center gap-1">
            <Download size={14} /> XLSX
          </button>
          <button onClick={() => navigate(`/dataset/${id}/chat`)} className="btn-primary text-sm flex items-center gap-1">
            <MessageSquare size={14} /> Chat
          </button>
        </div>
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Total Reviews', value: data.total_reviews, color: 'text-gray-900' },
          { label: 'Cleaned', value: data.cleaned_reviews, color: 'text-teal-600' },
          { label: 'Flagged', value: data.flagged_reviews, color: 'text-amber-600' },
          { label: 'Duplicates', value: data.duplicate_reviews, color: 'text-orange-600' },
          { label: 'Low Info', value: data.low_info_reviews, color: 'text-red-600' },
        ].map(stat => (
          <div key={stat.label} className="card text-center">
            <p className="text-xs text-gray-500 font-medium">{stat.label}</p>
            <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sentiment Pie */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Sentiment Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={sentimentChartData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {sentimentChartData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Rating Distribution */}
        {ratingChartData.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Rating Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={ratingChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="rating" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Aspect Chart */}
      <div className="card">
        <h3 className="font-semibold text-gray-900 mb-4">Aspect-Level Analysis</h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={aspectChartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={130} />
            <Tooltip />
            <Legend />
            <Bar dataKey="positive" fill="#10b981" name="Positive" radius={[0, 4, 4, 0]} />
            <Bar dataKey="negative" fill="#ef4444" name="Negative" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Emotion Chart */}
      <div className="card">
        <h3 className="font-semibold text-gray-900 mb-4">Emotion Distribution</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={emotionChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Time Trends */}
      {data.time_trends.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Sentiment Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.time_trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="positive" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="negative" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="neutral" stroke="#6b7280" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Priority Issues */}
      {data.priority_issues.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle size={18} className="text-red-500" /> Priority Issues
          </h3>
          <div className="space-y-3">
            {data.priority_issues.map((issue, i) => (
              <div key={i} className="border border-red-100 bg-red-50/50 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900 capitalize">{issue.aspect.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-2">
                    <span className="badge badge-negative">{issue.count} negative reviews</span>
                    <span className={`badge ${issue.severity === 'high' ? 'bg-red-100 text-red-700' : issue.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>
                      {issue.severity}
                    </span>
                  </div>
                </div>
                {issue.sample_reviews.length > 0 && (
                  <div className="space-y-1 mt-2">
                    {issue.sample_reviews.slice(0, 2).map((r, j) => (
                      <p key={j} className="text-xs text-gray-600 italic">"{r}"</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-teal-600" /> Recommendations
          </h3>
          <div className="space-y-3">
            {data.recommendations.map((rec, i) => (
              <div key={i} className="border border-teal-100 bg-teal-50/30 rounded-xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-gray-900">{rec.title}</span>
                  <span className={`badge ${rec.priority === 'high' ? 'bg-red-100 text-red-700' : rec.priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-teal-100 text-teal-700'}`}>
                    {rec.priority} priority
                  </span>
                </div>
                <p className="text-sm text-gray-600">{rec.description}</p>
                {rec.evidence.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {rec.evidence.slice(0, 2).map((e, j) => (
                      <p key={j} className="text-xs text-gray-500 italic">"{e}"</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Explorer */}
      <div className="card">
        <h3 className="font-semibold text-gray-900 mb-4">Review Explorer</h3>
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search reviews by keyword..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              className="input-field pl-9"
            />
          </div>
          <button onClick={handleSearch} className="btn-primary">Search</button>
        </div>
        {searchResults.length > 0 && (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {searchResults.map(r => (
              <div key={r.id} className="border border-gray-100 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400">#{r.row_index}</span>
                  {r.rating !== null && <span className="text-xs text-gray-400">★ {r.rating}</span>}
                  {r.source && <span className="badge bg-gray-100 text-gray-500 text-[10px]">{r.source}</span>}
                </div>
                <p className="text-sm text-gray-700">{r.cleaned_text || r.original_text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

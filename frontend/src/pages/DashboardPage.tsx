import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Download,
  Search,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  Sparkles,
  Star,
  Copy,
  FilterX,
  Languages,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Lightbulb,
  ShieldAlert,
  ShieldCheck,
  Flame,
  Radio,
  X,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ArrowUpRight,
  Zap,
} from 'lucide-react';
import {
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';
import toast from 'react-hot-toast';
import Alpha from '../components/Alphi';
import {
  getDashboard,
  exportResults,
  getReviews,
  getIngestionStatus,
  ingestReviews,
  type DashboardData,
  type Review,
  type IngestionStatusResponse,
  type FeaturedProblem,
  type CriticalFlagItem,
} from '../api';

const SENTIMENT_COLORS: Record<string, string> = {
  Positive: '#10b981',
  Negative: '#ef4444',
  Neutral: '#94a3b8',
};

const EMOTION_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4'];

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Review[]>([]);
  const [searching, setSearching] = useState(false);

  // Severity & Critical Flags State
  const [showCriticalModal, setShowCriticalModal] = useState(false);
  const [selectedFeaturedProblem, setSelectedFeaturedProblem] = useState<FeaturedProblem | null>(null);
  // Priority and recommendation carousel/detail state
  const [priorityPage, setPriorityPage] = useState(0);
  const [recommendationPage, setRecommendationPage] = useState(0);
  const [selectedPriorityIssue, setSelectedPriorityIssue] = useState<any>(null);
  const [selectedRecommendation, setSelectedRecommendation] = useState<any>(null);


  // Dynamic Ingestion Telemetry State
  const [ingestionTelemetry, setIngestionTelemetry] = useState<IngestionStatusResponse | null>(null);
  const [showWebhookModal, setShowWebhookModal] = useState(false);
  const [webhookText, setWebhookText] = useState(
    'Warning! Sparks erupted from the CCS2 charging coupler during fast charging and plastic pins started melting!'
  );
  const [webhookRating, setWebhookRating] = useState<number>(1);
  const [webhookSource, setWebhookSource] = useState('ev_network_live');
  const [submittingWebhook, setSubmittingWebhook] = useState(false);

  const loadDashboard = (datasetId: string) => {
    setLoading(true);
    getDashboard(datasetId)
      .then(d => setData(d))
      .catch(err => toast.error(err.response?.data?.detail || 'Failed to load dashboard data'))
      .finally(() => setLoading(false));
  };

  const loadTelemetry = () => {
    getIngestionStatus()
      .then(telemetry => setIngestionTelemetry(telemetry))
      .catch(() => {
        // Telemetry endpoint optional if running offline
      });
  };

  useEffect(() => {
    if (!id) return;
    loadDashboard(id);
    loadTelemetry();
  }, [id]);

  const handleSearch = async () => {
    if (!id || !searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await getReviews(id, { search: searchQuery.trim(), page_size: 20 });
      setSearchResults(res.reviews || []);
      if (!res.reviews || res.reviews.length === 0) {
        toast('No reviews matched your search', { icon: '🔍' });
      }
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (!id) return;
    try {
      const blob = await exportResults(id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${data?.dataset_name || 'alphaev'}_report_${id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch {
      toast.error('Export failed');
    }
  };

  const handleSimulateWebhook = async (presetType?: 'safety' | 'queue') => {
    if (!id) return;
    let textToSend = webhookText;
    let ratingToSend = webhookRating;

    if (presetType === 'safety') {
      textToSend =
        'Emergency stop triggered! Visible electrical sparking and smoke at dispenser 4, coupler pins charred and melted.';
      ratingToSend = 1;
      setWebhookText(textToSend);
      setWebhookRating(ratingToSend);
    } else if (presetType === 'queue') {
      textToSend =
        'Waited in queue for 45 minutes because 2 chargers were occupied. Need more charging bays here.';
      ratingToSend = 3;
      setWebhookText(textToSend);
      setWebhookRating(ratingToSend);
    }

    setSubmittingWebhook(true);
    try {
      const extId = `webhook_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      const res = await ingestReviews(
        [
          {
            external_review_id: extId,
            text: textToSend,
            rating: ratingToSend,
            source: webhookSource,
            review_date: new Date().toISOString().split('T')[0],
          },
        ],
        'alphaev-authorized-ingest-key',
        webhookSource,
        id
      );

      toast.success(
        `Webhook received! ${res.total_inserted} review(s) processed through NLP & severity pipeline.`
      );
      setShowWebhookModal(false);
      // Reload dashboard and telemetry immediately
      loadDashboard(id);
      loadTelemetry();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to simulate webhook ingestion');
    } finally {
      setSubmittingWebhook(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Alpha mood="thinking" size="md" message="Loading dashboard intelligence..." />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card text-center py-12">
        <Alpha mood="error" size="md" message="Dashboard data not found." />
        <button onClick={() => navigate('/upload')} className="btn-primary mt-4">
          Upload Dataset
        </button>
      </div>
    );
  }

  const sentimentChartData = (data.sentiment_distribution || []).map(s => ({
    name: s.sentiment.charAt(0).toUpperCase() + s.sentiment.slice(1),
    value: s.count,
    percentage: s.percentage,
  }));

  const emotionChartData = (data.emotion_distribution || []).map(e => ({
    name: e.emotion.charAt(0).toUpperCase() + e.emotion.slice(1),
    count: e.count,
    percentage: e.percentage,
  }));

  const aspectChartData = (data.aspect_metrics || []).map(a => {
    const aspectTotal = a.positive_count + a.negative_count;
    return {
      name: a.aspect_display,
      positive: a.positive_count,
      negative: a.negative_count,
      ratio: a.sentiment_ratio,
      // Display-only proportions for the radar shape; raw counts remain intact for tooltips.
      positiveShare: aspectTotal ? (a.positive_count / aspectTotal) * 100 : 0,
      negativeShare: aspectTotal ? (a.negative_count / aspectTotal) * 100 : 0,
    };
  });
  // Presentation-only totals for chart centre labels; source values remain unchanged.
  const sentimentTotal = sentimentChartData.reduce((sum, item) => sum + item.value, 0);
  const emotionTotal = emotionChartData.reduce((sum, item) => sum + item.count, 0);

  const priorityIssues = data.priority_issues || [];
  const recommendations = data.recommendations || [];

  return (
    <div className="space-y-12 pb-10">
      {/* Dashboard Top Header */}
      <div className="card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{data.dataset_name}</h1>
            <span className="badge badge-neutral text-xs">v{data.version || 1}</span>
            {data.is_stale && (
              <span className="badge badge-warning text-xs flex items-center gap-1">
                <RefreshCw size={10} className="animate-spin" />
                Stale Analysis
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400">
            {data.total_reviews} total reviews analyzed
            {data.average_rating !== null && (
              <span className="ml-2 font-medium text-amber-600">
                ★ {data.average_rating.toFixed(2)} / 5.0 Average Rating
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowWebhookModal(true)}
            className="btn-secondary text-xs flex items-center gap-1.5 border-teal-200 text-teal-800 bg-teal-50 hover:bg-teal-100"
          >
            <Radio size={14} className="text-teal-600 animate-pulse" />
            Live Webhook
          </button>
          <button
            onClick={() => navigate(`/chat/${id}`)}
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            <MessageSquare size={14} />
            Chatbot
          </button>
          <button
            onClick={() => handleExport('csv')}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <Download size={14} />
            CSV
          </button>
          <button
            onClick={() => handleExport('xlsx')}
            className="btn-primary text-xs flex items-center gap-1"
          >
            <Download size={14} />
            Excel Report
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* REQUIREMENT 1: SEVERITY-FIRST CRITICAL ISSUE PRIORITIZATION */}
      {/* ------------------------------------------------------------- */}
      <div className="card border-2 border-rose-300 bg-gradient-to-r from-rose-50/50 via-white to-amber-50/30 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-rose-100">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-rose-100 text-rose-700 rounded-lg">
                <ShieldAlert size={20} className="text-rose-600" />
              </span>
              <h2 className="text-base font-bold text-gray-900 tracking-tight">
                Severity-First Critical Issue Prioritization
              </h2>
              <span className="badge bg-rose-100 text-rose-800 border-rose-200 text-[11px] font-bold">
                Deterministically Ranked
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Safety hazards, electrical faults, and customer entrapment outrank high-frequency minor complaints.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCriticalModal(true)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 shadow-sm transition-all flex items-center gap-1.5"
            >
              <Flame size={14} />
              All Critical Flags ({(data.critical_flags || []).length})
            </button>
          </div>
        </div>

        {/* Featured Distinct Problems (Top 2 Highest Priority) */}
        {data.featured_problems && data.featured_problems.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.featured_problems.map((prob: FeaturedProblem, idx: number) => {
              const isCritical = prob.severity === 'Critical';
              const scoreWidth = Math.min(Math.max(prob.priority_score, 0), 100);

              return (
                <article
                  key={idx}
                  className={`group relative overflow-hidden rounded-2xl border p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${
                    isCritical
                      ? 'border-rose-300 bg-gradient-to-br from-rose-50 via-white to-rose-50/70 hover:border-rose-400'
                      : 'border-orange-300 bg-gradient-to-br from-orange-50 via-white to-amber-50/70 hover:border-orange-400'
                  }`}
                >
                  <div
                    className={`absolute inset-y-0 left-0 w-1 ${
                      isCritical ? 'bg-rose-500' : 'bg-orange-500'
                    }`}
                  />

                  <div className="pl-2">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${
                              isCritical
                                ? 'bg-rose-100 text-rose-700'
                                : 'bg-orange-100 text-orange-700'
                            }`}
                          >
                            {isCritical ? <ShieldAlert size={17} /> : <AlertTriangle size={17} />}
                          </span>
                          <span
                            className={`text-[10px] font-bold uppercase tracking-[0.14em] ${
                              isCritical ? 'text-rose-700' : 'text-orange-700'
                            }`}
                          >
                            {prob.category}
                          </span>
                        </div>
                        <h3 className="text-[15px] font-bold leading-snug text-gray-900">
                          {prob.title}
                        </h3>
                      </div>

                      <span
                        className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide ${
                          isCritical
                            ? 'bg-rose-600 text-white shadow-sm shadow-rose-200'
                            : 'bg-orange-500 text-white shadow-sm shadow-orange-200'
                        }`}
                      >
                        {prob.severity}
                      </span>
                    </div>

                    <div className="mb-3 rounded-xl border border-white/90 bg-white/80 p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                          Priority risk score
                        </span>
                        <span
                          className={`font-mono text-lg font-extrabold tabular-nums ${
                            isCritical ? 'text-rose-700' : 'text-orange-700'
                          }`}
                        >
                          {prob.priority_score.toFixed(1)}
                          <span className="ml-1 text-[10px] font-semibold text-gray-400">/ 100</span>
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isCritical ? 'bg-rose-500' : 'bg-orange-500'
                          }`}
                          style={{ width: `${scoreWidth}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-gray-600">
                        <ShieldCheck
                          size={13}
                          className={isCritical ? 'text-rose-600' : 'text-orange-600'}
                        />
                        Unverified · Pending inspection
                      </span>

                      <button
                        type="button"
                        onClick={() => setSelectedFeaturedProblem(prob)}
                        className={`inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold text-white shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                          isCritical
                            ? 'bg-rose-600 shadow-rose-200 hover:bg-rose-700 focus:ring-rose-400'
                            : 'bg-orange-500 shadow-orange-200 hover:bg-orange-600 focus:ring-orange-400'
                        }`}
                      >
                        View incident details
                        <ExternalLink size={13} />
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-gray-200 bg-white p-5 text-center text-xs text-gray-500">
            No critical safety hazards detected in the current dataset. Regular operational metrics apply.
          </div>
        )}
      </div>

      {/* Featured incident detail drawer */}
      {selectedFeaturedProblem && (
        <div
          className="fixed inset-0 z-[70] bg-slate-950/40 backdrop-blur-[2px]"
          onClick={() => setSelectedFeaturedProblem(null)}
          role="presentation"
        >
          <aside
            className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col overflow-hidden bg-white shadow-2xl animate-fadeIn"
            onClick={event => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="featured-incident-title"
          >
            {(() => {
              const prob = selectedFeaturedProblem;
              const isCritical = prob.severity === 'Critical';
              const scoreWidth = Math.min(Math.max(prob.priority_score, 0), 100);

              return (
                <>
                  <div
                    className={`border-b px-5 py-5 sm:px-6 ${
                      isCritical
                        ? 'border-rose-100 bg-gradient-to-br from-rose-50 to-white'
                        : 'border-orange-100 bg-gradient-to-br from-orange-50 to-white'
                    }`}
                  >
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex h-9 w-9 items-center justify-center rounded-xl ${
                            isCritical
                              ? 'bg-rose-100 text-rose-700'
                              : 'bg-orange-100 text-orange-700'
                          }`}
                        >
                          {isCritical ? <ShieldAlert size={19} /> : <AlertTriangle size={19} />}
                        </span>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-500">
                            Incident intelligence
                          </p>
                          <p className="text-xs font-semibold text-gray-700">Priority assessment</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedFeaturedProblem(null)}
                        className="rounded-lg p-2 text-gray-400 transition hover:bg-white hover:text-gray-800"
                        aria-label="Close incident details"
                      >
                        <X size={19} />
                      </button>
                    </div>

                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide ${
                          isCritical ? 'bg-rose-600 text-white' : 'bg-orange-500 text-white'
                        }`}
                      >
                        {prob.severity} priority
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                        {prob.category}
                      </span>
                    </div>
                    <h2
                      id="featured-incident-title"
                      className="text-xl font-extrabold leading-tight tracking-tight text-gray-900"
                    >
                      {prob.title}
                    </h2>

                    <div className="mt-4 rounded-xl border border-white bg-white/90 p-3.5 shadow-sm">
                      <div className="mb-2 flex items-end justify-between gap-3">
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                            Priority risk score
                          </p>
                          <p
                            className={`mt-0.5 text-3xl font-extrabold tabular-nums ${
                              isCritical ? 'text-rose-700' : 'text-orange-700'
                            }`}
                          >
                            {prob.priority_score.toFixed(1)}
                            <span className="ml-1 text-xs font-semibold text-gray-400">/ 100</span>
                          </p>
                        </div>
                        <span
                          className={`rounded-lg px-2.5 py-1.5 text-[10px] font-bold ${
                            isCritical
                              ? 'bg-rose-50 text-rose-700'
                              : 'bg-orange-50 text-orange-700'
                          }`}
                        >
                          {isCritical ? 'High risk' : 'Moderate priority'}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className={`h-full rounded-full ${
                            isCritical ? 'bg-rose-500' : 'bg-orange-500'
                          }`}
                          style={{ width: `${scoreWidth}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5 sm:px-6">
                    <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3">
                      <ShieldCheck size={16} className="mt-0.5 shrink-0 text-amber-700" />
                      <div>
                        <p className="text-xs font-bold text-amber-900">
                          Unverified customer complaint
                        </p>
                        <p className="mt-0.5 text-[11px] leading-relaxed text-amber-800">
                          Pending technical inspection. This report preserves the customer's claim without presenting it as a confirmed fault.
                        </p>
                      </div>
                    </div>

                    <section>
                      <div className="mb-2 flex items-center gap-2">
                        <span className="h-5 w-1 rounded-full bg-slate-400" />
                        <h3 className="text-xs font-extrabold uppercase tracking-wider text-gray-800">
                          Harm assessment
                        </h3>
                      </div>
                      <p className="rounded-xl border border-gray-100 bg-gray-50 p-3.5 text-sm leading-relaxed text-gray-700">
                        {prob.potential_harm}
                      </p>
                    </section>

                    <section>
                      <div className="mb-2 flex items-center gap-2">
                        <span className="h-5 w-1 rounded-full bg-blue-400" />
                        <h3 className="text-xs font-extrabold uppercase tracking-wider text-gray-800">
                          Verbatim customer evidence
                        </h3>
                      </div>
                      <blockquote className="rounded-xl border border-blue-100 bg-blue-50/50 p-3.5 text-sm italic leading-relaxed text-gray-700">
                        “{prob.top_evidence_quote || 'Direct customer evidence recorded in telemetry.'}”
                      </blockquote>
                    </section>

                    <section>
                      <div className="mb-2 flex items-center gap-2">
                        <span className="h-5 w-1 rounded-full bg-emerald-500" />
                        <h3 className="text-xs font-extrabold uppercase tracking-wider text-gray-800">
                          Recommended action
                        </h3>
                      </div>
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3.5">
                        <div className="mb-1.5 flex items-center gap-2 text-emerald-800">
                          <ShieldCheck size={15} />
                          <span className="text-xs font-bold">Suggested response</span>
                        </div>
                        <p className="text-sm leading-relaxed text-emerald-950">
                          {prob.recommended_action}
                        </p>
                      </div>
                    </section>

                    <section>
                      <div className="mb-2 flex items-center gap-2">
                        <span className="h-5 w-1 rounded-full bg-violet-400" />
                        <h3 className="text-xs font-extrabold uppercase tracking-wider text-gray-800">
                          Evidence & complaint metadata
                        </h3>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                            Evidence credibility
                          </p>
                          <p className="mt-1 text-xl font-extrabold text-gray-900">
                            {(prob.evidence_confidence * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                            Complaints detected
                          </p>
                          <p className="mt-1 text-xl font-extrabold text-gray-900">
                            {prob.complaint_count}
                          </p>
                        </div>
                      </div>
                      <div className="mt-2 rounded-xl border border-gray-100 bg-white p-3">
                        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-gray-500">
                          Supporting review IDs
                        </p>
                        <p className="break-all font-mono text-[11px] leading-relaxed text-gray-600">
                          {prob.supporting_review_ids?.length
                            ? prob.supporting_review_ids.join(', ')
                            : 'No supporting review IDs available.'}
                        </p>
                      </div>
                    </section>
                  </div>

                  <div className="border-t border-gray-100 bg-white px-5 py-4 sm:px-6">
                    <button
                      type="button"
                      onClick={() => setSelectedFeaturedProblem(null)}
                      className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-bold text-gray-700 transition hover:bg-gray-50"
                    >
                      Close incident details
                    </button>
                  </div>
                </>
              );
            })()}
          </aside>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
            {/* REQUIREMENT 2: DYNAMIC INGESTION TELEMETRY & SYNC CARD */}
      {/* ------------------------------------------------------------- */}
      {ingestionTelemetry && (
        <div className="card border border-teal-200 bg-teal-50/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <h3 className="font-bold text-sm text-gray-900 flex items-center gap-1.5">
                <Radio size={16} className="text-teal-600" />
                Dynamic Review Ingestion & API Telemetry
              </h3>
              <span className="badge bg-emerald-100 text-emerald-800 border-emerald-200 text-[10px] font-semibold">
                Listening & Idempotent
              </span>
            </div>
            <button
              onClick={() => setShowWebhookModal(true)}
              className="text-xs font-semibold text-teal-700 hover:text-teal-900 underline flex items-center gap-1"
            >
              Simulate Webhook Trigger
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="bg-white p-2.5 rounded-lg border border-teal-100">
              <p className="text-[10px] font-bold uppercase text-gray-400">Total Received</p>
              <p className="text-lg font-bold text-gray-800">{ingestionTelemetry.total_received}</p>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-teal-100">
              <p className="text-[10px] font-bold uppercase text-emerald-600">Processed & Ingested</p>
              <p className="text-lg font-bold text-emerald-700">{ingestionTelemetry.total_processed}</p>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-teal-100">
              <p className="text-[10px] font-bold uppercase text-amber-600">Duplicates Skipped</p>
              <p className="text-lg font-bold text-amber-700">{ingestionTelemetry.total_duplicates}</p>
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-teal-100">
              <p className="text-[10px] font-bold uppercase text-gray-400">Last Sync</p>
              <p className="text-xs font-semibold text-gray-700 mt-1">
                {ingestionTelemetry.last_sync_time
                  ? new Date(ingestionTelemetry.last_sync_time).toLocaleTimeString()
                  : 'Awaiting sync'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Brand Strengths & Pain Points */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card border border-emerald-100 bg-emerald-50/20">
          <h3 className="font-semibold text-emerald-950 mb-3 flex items-center gap-2">
            <TrendingUp size={18} className="text-emerald-600" />
            Key Brand Strengths
          </h3>
          {data.top_strengths && data.top_strengths.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.top_strengths.map((str, idx) => (
                <div
                  key={idx}
                  className="px-3 py-1.5 rounded-lg bg-emerald-100/80 border border-emerald-200 text-emerald-800 text-sm font-semibold flex items-center gap-1.5"
                >
                  <Sparkles size={14} className="text-emerald-600" />
                  {str}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">No predominant positive aspects recorded yet</p>
          )}
        </div>

        <div className="card border border-red-100 bg-red-50/20">
          <h3 className="font-semibold text-red-950 mb-3 flex items-center gap-2">
            <TrendingDown size={18} className="text-red-600" />
            Primary Customer Pain Points
          </h3>
          {data.top_complaints && data.top_complaints.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.top_complaints.map((cmp, idx) => (
                <div
                  key={idx}
                  className="px-3 py-1.5 rounded-lg bg-red-100/80 border border-red-200 text-red-800 text-sm font-semibold flex items-center gap-1.5"
                >
                  <TrendingDown size={14} className="text-red-600" />
                  {cmp}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">No predominant complaint areas recorded yet</p>
          )}
        </div>
      </div>

      {/* Priority Issues & Actionable Recommendations */}
      {(priorityIssues.length > 0 || recommendations.length > 0) && (
        <div className="space-y-10">
          {/* Ranked Priority Issues */}
          {priorityIssues.length > 0 && (
            <section className="rounded-2xl border border-rose-100 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg sm:p-7">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-600 ring-1 ring-rose-100">
                    <AlertTriangle size={19} />
                  </span>
                  <div>
                    <h3 className="text-base font-bold tracking-tight text-slate-900">
                      Ranked Priority Issues
                    </h3>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {priorityIssues.length} issues ranked by impact
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <span className="rounded-full bg-rose-50 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-rose-700">
                    Impact scored
                  </span>
                  {priorityIssues.length > 5 && (
                    <div className="flex items-center gap-2">
                      <span className="min-w-[58px] text-center text-[11px] font-medium tabular-nums text-slate-500">
                        {priorityPage + 1} / {Math.ceil(priorityIssues.length / 5)}
                      </span>
                      <button
                        type="button"
                        onClick={() => setPriorityPage(page => Math.max(0, page - 1))}
                        disabled={priorityPage === 0}
                        aria-label="Previous priority issues"
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-all duration-200 hover:-translate-y-0.5 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                      >
                        <ChevronLeft size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setPriorityPage(page =>
                            Math.min(Math.ceil(priorityIssues.length / 5) - 1, page + 1)
                          )
                        }
                        disabled={priorityPage >= Math.ceil(priorityIssues.length / 5) - 1}
                        aria-label="Next priority issues"
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-all duration-200 hover:-translate-y-0.5 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div
                key={`priority-page-${priorityPage}`}
                className="grid grid-cols-1 gap-5 animate-fadeIn sm:grid-cols-2 xl:grid-cols-5"
              >
                {priorityIssues.slice(priorityPage * 5, priorityPage * 5 + 5).map((issue, localIdx) => {
                  const idx = priorityPage * 5 + localIdx;
                  const severity = (issue.severity || '').toLowerCase();
                  const tone =
                    severity === 'critical'
                      ? {
                          border: 'border-rose-200 hover:border-rose-300',
                          accent: 'bg-rose-500',
                          badge: 'bg-rose-50 text-rose-700 ring-rose-100',
                          score: 'text-rose-700',
                          icon: 'bg-rose-50 text-rose-600 ring-rose-100',
                          glow: 'group-hover:shadow-rose-100/80',
                        }
                      : severity === 'high'
                      ? {
                          border: 'border-orange-200 hover:border-orange-300',
                          accent: 'bg-orange-500',
                          badge: 'bg-orange-50 text-orange-700 ring-orange-100',
                          score: 'text-orange-700',
                          icon: 'bg-orange-50 text-orange-600 ring-orange-100',
                          glow: 'group-hover:shadow-orange-100/80',
                        }
                      : {
                          border: 'border-amber-200 hover:border-amber-300',
                          accent: 'bg-amber-500',
                          badge: 'bg-amber-50 text-amber-700 ring-amber-100',
                          score: 'text-amber-700',
                          icon: 'bg-amber-50 text-amber-600 ring-amber-100',
                          glow: 'group-hover:shadow-amber-100/80',
                        };

                  return (
                    <button
                      key={`${issue.aspect_display}-${idx}`}
                      type="button"
                      onClick={() => setSelectedPriorityIssue(issue)}
                      className={`group relative flex min-h-[286px] flex-col items-center overflow-hidden rounded-2xl border bg-gradient-to-b from-white to-slate-50/70 px-4 py-5 text-center shadow-sm transition-all duration-300 ease-out hover:-translate-y-2 hover:shadow-xl ${tone.border} ${tone.glow} focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 focus-visible:ring-offset-2`}
                    >
                      <span className={`absolute inset-x-0 top-0 h-1 ${tone.accent}`} />
                      <div className="flex w-full items-center justify-between gap-2">
                        <span className="font-mono text-[11px] font-bold tracking-wider text-slate-400">
                          #{String(idx + 1).padStart(2, '0')}
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-[9px] font-bold uppercase tracking-wide ring-1 ring-inset ${tone.badge}`}>
                          {issue.severity}
                        </span>
                      </div>

                      <span className={`mt-6 flex h-14 w-14 items-center justify-center rounded-2xl ring-1 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3 ${tone.icon}`}>
                        <AlertTriangle size={25} />
                      </span>

                      <h4 className="mt-4 min-h-[44px] w-full line-clamp-2 text-[14px] font-bold leading-snug text-slate-900 transition-colors duration-200 group-hover:text-slate-700">
                        {issue.aspect_display}
                      </h4>

                      <div className="mt-auto w-full border-t border-slate-100 pt-4">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">Impact score</p>
                        <p className={`mt-1 font-mono text-2xl font-extrabold tabular-nums transition-transform duration-300 group-hover:scale-105 ${tone.score}`}>
                          {issue.impact_score.toFixed(1)}
                        </p>
                        <span className="mt-2 inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 transition-colors group-hover:text-rose-600">
                          View issue details <ArrowUpRight size={12} />
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {priorityIssues.length > 5 && (
                <div className="mt-4 flex items-center justify-center gap-1.5">
                  {Array.from({ length: Math.ceil(priorityIssues.length / 5) }).map((_, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setPriorityPage(idx)}
                      aria-label={`Go to priority issues page ${idx + 1}`}
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        priorityPage === idx ? 'w-6 bg-rose-500' : 'w-1.5 bg-slate-200 hover:bg-rose-300'
                      }`}
                    />
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Actionable Engineering & Ops Recommendations */}
          {recommendations.length > 0 && (
            <section className="rounded-2xl border border-teal-100 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg sm:p-7">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700 ring-1 ring-teal-100">
                    <Lightbulb size={19} />
                  </span>
                  <div>
                    <h3 className="text-base font-bold tracking-tight text-slate-900">
                      Actionable Engineering &amp; Ops Recommendations
                    </h3>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {recommendations.length} targeted actions for operational improvement
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <span className="rounded-full bg-teal-50 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-teal-700">
                    Prescriptive AI
                  </span>
                  {recommendations.length > 5 && (
                    <div className="flex items-center gap-2">
                      <span className="min-w-[58px] text-center text-[11px] font-medium tabular-nums text-slate-500">
                        {recommendationPage + 1} / {Math.ceil(recommendations.length / 5)}
                      </span>
                      <button
                        type="button"
                        onClick={() => setRecommendationPage(page => Math.max(0, page - 1))}
                        disabled={recommendationPage === 0}
                        aria-label="Previous recommendations"
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-all duration-200 hover:-translate-y-0.5 hover:border-teal-200 hover:bg-teal-50 hover:text-teal-700 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                      >
                        <ChevronLeft size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setRecommendationPage(page =>
                            Math.min(Math.ceil(recommendations.length / 5) - 1, page + 1)
                          )
                        }
                        disabled={recommendationPage >= Math.ceil(recommendations.length / 5) - 1}
                        aria-label="Next recommendations"
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-all duration-200 hover:-translate-y-0.5 hover:border-teal-200 hover:bg-teal-50 hover:text-teal-700 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:translate-y-0 disabled:hover:shadow-none"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div
                key={`recommendation-page-${recommendationPage}`}
                className="grid grid-cols-1 gap-5 animate-fadeIn sm:grid-cols-2 xl:grid-cols-5"
              >
                {recommendations.slice(recommendationPage * 5, recommendationPage * 5 + 5).map((rec, localIdx) => {
                  const idx = recommendationPage * 5 + localIdx;
                  const isHigh = (rec.priority || '').toLowerCase().includes('high');

                  return (
                    <button
                      key={`${rec.title}-${idx}`}
                      type="button"
                      onClick={() => setSelectedRecommendation(rec)}
                      className="group relative flex min-h-[286px] flex-col items-center overflow-hidden rounded-2xl border border-teal-100 bg-gradient-to-b from-white via-white to-teal-50/60 px-4 py-5 text-center shadow-sm transition-all duration-300 ease-out hover:-translate-y-2 hover:border-teal-300 hover:shadow-xl hover:shadow-teal-100/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2"
                    >
                      <span className="absolute inset-x-0 top-0 h-1 bg-teal-500 transition-all duration-300 group-hover:h-1.5" />
                      <div className="flex w-full items-center justify-between gap-2">
                        <span className="font-mono text-[11px] font-bold tracking-wider text-slate-400">
                          #{String(idx + 1).padStart(2, '0')}
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-[9px] font-bold ring-1 ring-inset ${
                          isHigh
                            ? 'bg-teal-50 text-teal-700 ring-teal-100'
                            : 'bg-amber-50 text-amber-700 ring-amber-100'
                        }`}>
                          {rec.priority}
                        </span>
                      </div>
                      <span className="mt-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 ring-1 ring-teal-100 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3 group-hover:bg-teal-100">
                        <Lightbulb size={25} />
                      </span>
                      <h4 className="mt-4 min-h-[52px] w-full line-clamp-3 text-[14px] font-bold leading-snug text-slate-900 transition-colors duration-200 group-hover:text-teal-800">
                        {rec.title}
                      </h4>
                      <div className="mt-auto w-full border-t border-teal-100/80 pt-4">
                        <p className="line-clamp-2 min-h-[30px] text-[11px] font-medium leading-relaxed text-slate-500">
                          {rec.category}
                        </p>
                        <span className="mt-2 inline-flex items-center gap-1 text-[10px] font-semibold text-teal-700 transition-all group-hover:gap-2">
                          View recommendation <ArrowUpRight size={12} />
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {recommendations.length > 5 && (
                <div className="mt-4 flex items-center justify-center gap-1.5">
                  {Array.from({ length: Math.ceil(recommendations.length / 5) }).map((_, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setRecommendationPage(idx)}
                      aria-label={`Go to recommendations page ${idx + 1}`}
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        recommendationPage === idx ? 'w-6 bg-teal-500' : 'w-1.5 bg-slate-200 hover:bg-teal-300'
                      }`}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      )}

      {/* Priority issue detail drawer */}
      {selectedPriorityIssue && (
        <div
          className="fixed inset-0 z-[75] bg-slate-950/40 backdrop-blur-sm animate-fadeIn"
          onClick={() => setSelectedPriorityIssue(null)}
          role="presentation"
        >
          <aside
            className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col overflow-hidden bg-white shadow-2xl animate-fadeIn"
            onClick={event => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="priority-issue-detail-title"
          >
            <div className="flex items-center justify-between border-b border-rose-100 bg-gradient-to-br from-rose-50 to-white px-5 py-5 sm:px-6">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-100 text-rose-700">
                  <AlertTriangle size={19} />
                </span>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-rose-600">Priority intelligence</p>
                  <p className="text-xs font-medium text-slate-500">Issue details</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedPriorityIssue(null)}
                aria-label="Close priority issue details"
                className="rounded-lg p-2 text-slate-400 transition-all duration-200 hover:rotate-90 hover:bg-white hover:text-slate-800"
              >
                <X size={19} />
              </button>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5 sm:px-6">
              <div>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${
                    selectedPriorityIssue.severity === 'Critical'
                      ? 'bg-rose-100 text-rose-700'
                      : selectedPriorityIssue.severity === 'High'
                      ? 'bg-orange-100 text-orange-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}>
                    {selectedPriorityIssue.severity} severity
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    {selectedPriorityIssue.aspect_display}
                  </span>
                </div>
                <h2 id="priority-issue-detail-title" className="text-xl font-extrabold leading-tight text-slate-900">
                  {selectedPriorityIssue.aspect_display}
                </h2>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Impact score</p>
                  <p className="mt-1 text-2xl font-extrabold tabular-nums text-slate-900">
                    {selectedPriorityIssue.impact_score.toFixed(1)}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Complaints</p>
                  <p className="mt-1 text-2xl font-extrabold tabular-nums text-slate-900">
                    {selectedPriorityIssue.complaint_count}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Frustrated</p>
                  <p className="mt-1 text-2xl font-extrabold tabular-nums text-slate-900">
                    {selectedPriorityIssue.frustration_count}
                  </p>
                </div>
              </div>

              {selectedPriorityIssue.average_rating !== null && selectedPriorityIssue.average_rating !== undefined && (
                <div className="rounded-xl border border-amber-100 bg-amber-50/70 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700">Average rating</p>
                  <p className="mt-1 text-lg font-extrabold text-amber-800">
                    ★ {selectedPriorityIssue.average_rating.toFixed(1)} / 5
                  </p>
                </div>
              )}

              {selectedPriorityIssue.sample_evidence && (
                <section>
                  <h3 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-700">Customer evidence</h3>
                  <blockquote className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-sm italic leading-relaxed text-slate-700">
                    “{selectedPriorityIssue.sample_evidence}”
                  </blockquote>
                </section>
              )}

              {selectedPriorityIssue.key_drivers?.length > 0 && (
                <section>
                  <h3 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-700">Key drivers</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedPriorityIssue.key_drivers.map((driver: string, idx: number) => (
                      <span key={`${driver}-${idx}`} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600">
                        {driver}
                      </span>
                    ))}
                  </div>
                </section>
              )}
            </div>

            <div className="border-t border-slate-100 bg-white px-5 py-4 sm:px-6">
              <button
                type="button"
                onClick={() => setSelectedPriorityIssue(null)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-all duration-200 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
              >
                Close details
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Recommendation detail drawer */}
      {selectedRecommendation && (
        <div
          className="fixed inset-0 z-[75] bg-slate-950/40 backdrop-blur-sm animate-fadeIn"
          onClick={() => setSelectedRecommendation(null)}
          role="presentation"
        >
          <aside
            className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col overflow-hidden bg-white shadow-2xl animate-fadeIn"
            onClick={event => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="recommendation-detail-title"
          >
            <div className="flex items-center justify-between border-b border-teal-100 bg-gradient-to-br from-teal-50 to-white px-5 py-5 sm:px-6">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 text-teal-700">
                  <Lightbulb size={19} />
                </span>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-teal-700">Prescriptive intelligence</p>
                  <p className="text-xs font-medium text-slate-500">Engineering &amp; operations action</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedRecommendation(null)}
                aria-label="Close recommendation details"
                className="rounded-lg p-2 text-slate-400 transition-all duration-200 hover:rotate-90 hover:bg-white hover:text-slate-800"
              >
                <X size={19} />
              </button>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5 sm:px-6">
              <div>
                <span className="inline-flex rounded-full bg-teal-50 px-2.5 py-1 text-[10px] font-bold text-teal-700 ring-1 ring-inset ring-teal-100">
                  {selectedRecommendation.priority}
                </span>
                <h2 id="recommendation-detail-title" className="mt-3 text-xl font-extrabold leading-tight text-slate-900">
                  {selectedRecommendation.title}
                </h2>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Department</p>
                  <p className="mt-1 text-sm font-bold text-slate-800">{selectedRecommendation.category}</p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Focus area</p>
                  <p className="mt-1 text-sm font-bold text-slate-800">{selectedRecommendation.target_aspect}</p>
                </div>
              </div>

              <section>
                <h3 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-700">Recommended action</h3>
                <div className="rounded-xl border border-teal-100 bg-teal-50/60 p-4">
                  <p className="text-sm leading-relaxed text-slate-700">{selectedRecommendation.suggested_action}</p>
                </div>
              </section>

              <section>
                <h3 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-700">Expected impact</h3>
                <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
                  <p className="text-sm leading-relaxed text-emerald-900">{selectedRecommendation.expected_impact}</p>
                </div>
              </section>

              <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Supporting reviews</p>
                <p className="mt-1 text-xl font-extrabold tabular-nums text-slate-900">
                  {selectedRecommendation.supporting_review_count}
                </p>
              </div>
            </div>

            <div className="border-t border-slate-100 bg-white px-5 py-4 sm:px-6">
              <button
                type="button"
                onClick={() => setSelectedRecommendation(null)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-all duration-200 hover:border-teal-200 hover:bg-teal-50 hover:text-teal-800"
              >
                Close details
              </button>
            </div>
          </aside>
        </div>
      )}

            {/* Sentiment & Emotion Charts — Premium Analytics */}
      <section className="space-y-8 pt-2">
        <div className="flex flex-col gap-1 px-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-600">Customer intelligence</p>
          <h2 className="text-lg font-extrabold tracking-tight text-slate-900">Sentiment & Emotion Analytics</h2>
          <p className="text-sm text-slate-500">Explore how customers feel across the analysed reviews.</p>
        </div>

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
          {/* Sentiment Distribution */}
          <div className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm transition-all duration-500 hover:-translate-y-1 hover:border-emerald-200 hover:shadow-xl hover:shadow-emerald-100/50 sm:p-7">
            <div className="absolute right-0 top-0 h-32 w-32 rounded-full bg-emerald-100/40 blur-3xl transition-opacity duration-500 group-hover:opacity-100" />
            <div className="relative mb-2 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Overall Customer Sentiment</h3>
                <p className="mt-1 text-xs text-slate-500">Distribution across all analysed reviews</p>
              </div>
              <span className="rounded-xl bg-emerald-50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-700 ring-1 ring-emerald-100">Sentiment</span>
            </div>
            <div className="relative">
              <div className="mb-1 flex justify-center">
                <span className="rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-[11px] font-semibold text-emerald-800">
                  {sentimentTotal.toLocaleString()} total reviews
                </span>
              </div>
              <ResponsiveContainer width="100%" height={276}>
                <PieChart>
                  <Pie
                    data={sentimentChartData}
                    cx="50%"
                    cy="48%"
                    innerRadius={0}
                    outerRadius={112}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="white"
                    strokeWidth={4}
                    label={({ percent }: any) => `${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                    isAnimationActive
                    animationDuration={1250}
                    animationEasing="ease-out"
                  >
                    {sentimentChartData.map(entry => (
                      <Cell
                        key={entry.name}
                        fill={SENTIMENT_COLORS[entry.name] || '#94a3b8'}
                        className="transition-opacity duration-300 hover:opacity-75"
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: 14, border: '1px solid #e2e8f0', boxShadow: '0 12px 30px rgba(15,23,42,.10)', padding: '10px 14px' }}
                    formatter={(val: any, _name: any, item: any) => [
                      `${val} reviews (${item.payload.percentage}%)`,
                      item.payload.name,
                    ]}
                  />
                  <Legend verticalAlign="bottom" iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Emotion Distribution — animated multi-segment doughnut */}
          <div className="group relative overflow-hidden rounded-3xl border border-violet-100 bg-gradient-to-br from-white via-white to-violet-50/60 p-6 shadow-sm transition-all duration-500 hover:-translate-y-1 hover:border-violet-200 hover:shadow-2xl hover:shadow-violet-100/70 sm:p-7">
            <div className="pointer-events-none absolute -right-12 -top-12 h-44 w-44 rounded-full bg-violet-200/30 blur-3xl transition-transform duration-700 group-hover:scale-125" />
            <div className="relative mb-1 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Customer Emotion Distribution</h3>
                <p className="mt-1 text-xs text-slate-500">A closer look at the emotions expressed in customer feedback</p>
              </div>
              <span className="rounded-xl bg-violet-50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-700 ring-1 ring-violet-100">Emotions</span>
            </div>
            <div className="relative mx-auto mt-1 h-[330px] w-full max-w-[520px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={emotionChartData}
                    cx="50%"
                    cy="46%"
                    innerRadius={82}
                    outerRadius={124}
                    paddingAngle={4}
                    cornerRadius={8}
                    dataKey="count"
                    nameKey="name"
                    stroke="#ffffff"
                    strokeWidth={4}
                    isAnimationActive
                    animationBegin={120}
                    animationDuration={1500}
                    animationEasing="ease-out"
                  >
                    {emotionChartData.map((entry, i) => (
                      <Cell
                        key={entry.name}
                        fill={EMOTION_COLORS[i % EMOTION_COLORS.length]}
                        className="cursor-pointer transition-all duration-300 hover:opacity-80"
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: 16, border: '1px solid #ede9fe', boxShadow: '0 16px 36px rgba(76,29,149,.12)', padding: '11px 14px' }}
                    formatter={(val: any, _name: any, item: any) => [
                      `${Number(val).toLocaleString()} reviews · ${item.payload.percentage}%`,
                      item.payload.name,
                    ]}
                  />
                  <Legend
                    verticalAlign="bottom"
                    align="center"
                    iconType="circle"
                    iconSize={9}
                    formatter={(value: string) => <span className="px-1 text-[11px] font-medium text-slate-600">{value}</span>}
                    wrapperStyle={{ paddingTop: 8 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute left-1/2 top-[40%] flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center">
                <span className="text-3xl font-extrabold tracking-tight text-slate-900">{emotionTotal.toLocaleString()}</span>
                <span className="mt-1 text-[9px] font-bold uppercase tracking-[0.16em] text-slate-400">Emotion tags</span>
                <span className="mt-2 h-1 w-8 rounded-full bg-gradient-to-r from-violet-400 to-fuchsia-400" />
              </div>
            </div>
            <p className="relative -mt-1 text-center text-[10px] font-medium text-slate-400">Hover over any segment to inspect its count and share</p>
          </div>
        </div>
      </section>

      {/* Aspect-Level Sentiment Breakdown — dual-layer radar */}
      <section className="pt-2">
        <div className="group relative overflow-hidden rounded-3xl border border-slate-200/80 bg-gradient-to-br from-white via-white to-sky-50/50 p-6 shadow-sm transition-all duration-500 hover:border-sky-200 hover:shadow-xl hover:shadow-sky-100/60 sm:p-8">
          <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-sky-100/50 blur-3xl transition-transform duration-700 group-hover:scale-110" />
          <div className="relative mb-2 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-600">Aspect intelligence</p>
              <h3 className="mt-1 text-base font-bold text-slate-900">Aspect-Level Sentiment Breakdown</h3>
              <p className="mt-1 text-xs text-slate-500">Compare the positive and negative balance across all 11 key EV areas.</p>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-[11px] font-semibold text-slate-600">
              <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-200" /> Positive share</span>
              <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-rose-500 shadow-sm shadow-rose-200" /> Negative share</span>
            </div>
          </div>
          <div className="relative mx-auto h-[480px] w-full max-w-[980px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={aspectChartData} outerRadius="70%" margin={{ top: 18, right: 34, bottom: 18, left: 34 }}>
                <defs>
                  <linearGradient id="positiveRadarFill" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.42} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0.12} />
                  </linearGradient>
                  <linearGradient id="negativeRadarFill" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.34} />
                    <stop offset="100%" stopColor="#fb7185" stopOpacity={0.10} />
                  </linearGradient>
                </defs>
                <PolarGrid gridType="polygon" stroke="#dbe5f0" strokeDasharray="3 5" />
                <PolarAngleAxis
                  dataKey="name"
                  tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }}
                  tickLine={false}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tickCount={5}
                  axisLine={false}
                  tick={{ fill: '#94a3b8', fontSize: 9 }}
                  tickFormatter={(value: number) => `${value}%`}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 16, border: '1px solid #dbeafe', boxShadow: '0 16px 36px rgba(15,23,42,.12)', padding: '11px 14px' }}
                  formatter={(value: any, name: any, item: any) => {
                    const isPositive = name === 'Positive share';
                    const rawCount = isPositive ? item.payload.positive : item.payload.negative;
                    return [`${rawCount.toLocaleString()} mentions · ${Number(value).toFixed(1)}%`, name];
                  }}
                  labelStyle={{ color: '#0f172a', fontWeight: 700, marginBottom: 5 }}
                />
                <Radar
                  name="Positive share"
                  dataKey="positiveShare"
                  stroke="#059669"
                  strokeWidth={2.5}
                  fill="url(#positiveRadarFill)"
                  fillOpacity={1}
                  dot={{ r: 3.5, fill: '#059669', stroke: '#ffffff', strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: '#059669', stroke: '#ffffff', strokeWidth: 2 }}
                  isAnimationActive
                  animationDuration={1500}
                  animationEasing="ease-out"
                />
                <Radar
                  name="Negative share"
                  dataKey="negativeShare"
                  stroke="#f43f5e"
                  strokeWidth={2.5}
                  fill="url(#negativeRadarFill)"
                  fillOpacity={1}
                  dot={{ r: 3.5, fill: '#f43f5e', stroke: '#ffffff', strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: '#f43f5e', stroke: '#ffffff', strokeWidth: 2 }}
                  isAnimationActive
                  animationBegin={180}
                  animationDuration={1650}
                  animationEasing="ease-out"
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="relative mt-1 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 border-t border-slate-100 pt-4 text-[10px] text-slate-500">
            <span>Each spoke represents one EV aspect</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:block" />
            <span>Hover over a point to see the original mention count</span>
          </div>
        </div>
      </section>

      {/* Review Explorer */}
      <div className="card mt-4 rounded-2xl border border-slate-200/80 p-6 shadow-sm transition-all duration-300 hover:shadow-lg sm:p-8">
        <div className="mb-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-600">Evidence discovery</p>
          <h3 className="mt-1 text-base font-bold text-gray-900">Review Explorer & Evidence Finder</h3>
          <p className="mt-1 text-xs text-slate-500">Search original customer feedback and inspect supporting evidence.</p>
        </div>
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search reviews by keyword (e.g. 'battery', 'slow', 'customer support')..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              className="input-field pl-9"
            />
          </div>
          <button onClick={handleSearch} disabled={searching} className="btn-primary">
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {searchResults.map(r => (
              <div key={r.id} className="border border-gray-100 rounded-lg p-3 bg-white">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-xs text-gray-400 font-mono">#{r.row_index}</span>
                  {r.rating !== null && (
                    <span className="text-xs text-amber-600 font-semibold">★ {r.rating}</span>
                  )}
                  {r.source && (
                    <span className="badge bg-gray-100 text-gray-500 text-[10px]">{r.source}</span>
                  )}
                  {r.is_duplicate && (
                    <span className="badge badge-negative text-[10px]">Duplicate</span>
                  )}
                </div>
                <p className="text-sm text-gray-800 leading-relaxed">
                  {r.cleaned_text || r.original_text}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* MODAL: ALL CRITICAL FLAGS REGISTER */}
      {/* ------------------------------------------------------------- */}
      {showCriticalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-rose-200">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-rose-50/60 rounded-t-2xl">
              <div className="flex items-center gap-2">
                <Flame className="text-rose-600" size={20} />
                <h3 className="font-bold text-gray-900">
                  Full Critical Safety & Hazard Flags Register ({(data.critical_flags || []).length})
                </h3>
              </div>
              <button
                onClick={() => setShowCriticalModal(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              <p className="text-xs text-gray-500 mb-2">
                All identified critical safety and operational hazards. Preserves individual review IDs and
                verbatim text evidence without masking.
              </p>

              {(data.critical_flags || []).length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-400">
                  No critical safety hazards recorded in this dataset.
                </div>
              ) : (
                (data.critical_flags || []).map((flag: CriticalFlagItem, idx: number) => (
                  <div key={idx} className="p-3.5 bg-rose-50/30 rounded-xl border border-rose-200">
                    <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="badge bg-rose-600 text-white font-bold text-[10px]">
                          {flag.severity}
                        </span>
                        <span className="font-bold text-sm text-gray-900">{flag.title}</span>
                      </div>
                      <span className="font-mono text-xs text-gray-600 font-bold">
                        Score: {flag.priority_score.toFixed(1)}
                      </span>
                    </div>

                    <p className="text-xs text-gray-700 italic bg-white p-2.5 rounded-lg border border-gray-100 mb-2">
                      "{flag.evidence_quote}"
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-gray-500 flex-wrap gap-2">
                      <span>
                        Review ID: <strong className="font-mono">{flag.review_id}</strong>
                      </span>
                      <span>
                        Harm: <strong className="text-rose-900">{flag.potential_harm}</strong>
                      </span>
                      <span>
                        Status: <strong className="text-amber-800">Unverified Complaint</strong>
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-gray-100 flex justify-end bg-gray-50 rounded-b-2xl">
              <button
                onClick={() => setShowCriticalModal(false)}
                className="btn-secondary text-xs px-4"
              >
                Close Register
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL: SIMULATE WEBHOOK REVIEW INGESTION */}
      {/* ------------------------------------------------------------- */}
      {showWebhookModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-xl w-full flex flex-col shadow-2xl border border-teal-200">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-teal-50/60 rounded-t-2xl">
              <div className="flex items-center gap-2">
                <Radio className="text-teal-600" size={20} />
                <h3 className="font-bold text-gray-900">
                  Simulate External Webhook Ingestion
                </h3>
              </div>
              <button
                onClick={() => setShowWebhookModal(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-4 space-y-3">
              <p className="text-xs text-gray-500">
                Test the dynamic review ingestion pipeline in real-time. Reviews are cleaned, classified, sentiment-scored,
                and evaluated for critical hazards immediately.
              </p>

              <div className="flex items-center gap-2 mb-2">
                <button
                  type="button"
                  onClick={() => handleSimulateWebhook('safety')}
                  className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-100 text-rose-800 border border-rose-200 hover:bg-rose-200"
                >
                  ⚡ Preset: Severe Arcing Hazard
                </button>
                <button
                  type="button"
                  onClick={() => handleSimulateWebhook('queue')}
                  className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-gray-100 text-gray-800 border border-gray-200 hover:bg-gray-200"
                >
                  ⏳ Preset: Queue Delay Complaint
                </button>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Source Platform:
                </label>
                <input
                  type="text"
                  value={webhookSource}
                  onChange={e => setWebhookSource(e.target.value)}
                  className="input-field text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Review Text:
                </label>
                <textarea
                  rows={3}
                  value={webhookText}
                  onChange={e => setWebhookText(e.target.value)}
                  className="input-field text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Rating: {webhookRating} / 5
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={webhookRating}
                  onChange={e => setWebhookRating(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>

            <div className="p-4 border-t border-gray-100 flex justify-end gap-2 bg-gray-50 rounded-b-2xl">
              <button
                onClick={() => setShowWebhookModal(false)}
                className="btn-secondary text-xs px-3"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSimulateWebhook()}
                disabled={submittingWebhook}
                className="btn-primary text-xs px-4 flex items-center gap-1.5"
              >
                {submittingWebhook ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    Ingesting...
                  </>
                ) : (
                  <>
                    <Zap size={14} />
                    Post Webhook Payload
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
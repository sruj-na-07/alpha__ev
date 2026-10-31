import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Zap,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
} from 'lucide-react';
import toast from 'react-hot-toast';
import Alpha from '../components/Alphi';
import {
  startSentimentAnalysis,
  getSentiments,
  getReviews,
  getDataset,
  exportAnalysisDataset,
  type SentimentResult,
  type Review,
} from '../api';

const SENTIMENTS = ['positive', 'negative', 'neutral'];
const EMOTIONS = ['happy', 'sad', 'frustrated', 'satisfaction', 'neutral'];

const PAGE_SIZE = 5;

// Same eligibility criteria used in Cleaning and Classification.
const isEligibleReview = (review: Review): boolean => {
  return (
    !review.is_duplicate &&
    !review.is_low_info &&
    Boolean((review.cleaned_text || review.original_text || '').trim())
  );
};

// Fetch all review pages and retain only eligible reviews.
const fetchAllReviews = async (datasetId: string): Promise<Review[]> => {
  const firstPage = await getReviews(datasetId, {
    page: 1,
    page_size: 100,
  });

  const totalPages = Math.ceil(firstPage.total / firstPage.page_size);

  if (totalPages <= 1) {
    return (firstPage.reviews || []).filter(isEligibleReview);
  }

  const remainingPages = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) =>
      getReviews(datasetId, {
        page: index + 2,
        page_size: 100,
      })
    )
  );

  return [firstPage, ...remainingPages]
    .flatMap(page => page.reviews || [])
    .filter(isEligibleReview);
};

// Keep only sentiment results belonging to eligible reviews.
const filterEligibleSentiments = (
  sentiments: SentimentResult[],
  reviews: Review[]
): SentimentResult[] => {
  const eligibleReviewIds = new Set(reviews.map(review => review.id));

  return sentiments.filter(sentiment =>
    eligibleReviewIds.has(sentiment.review_id)
  );
};

const sentimentColors: Record<string, string> = {
  positive: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  negative: 'text-red-700 bg-red-50 border-red-200',
  neutral: 'text-gray-700 bg-gray-50 border-gray-200',
};

const emotionColors: Record<string, string> = {
  happy: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  sad: 'text-blue-700 bg-blue-50 border-blue-200',
  frustrated: 'text-orange-700 bg-orange-50 border-orange-200',
  satisfaction: 'text-teal-700 bg-teal-50 border-teal-200',
  neutral: 'text-gray-700 bg-gray-50 border-gray-200',
};

const emotionEmojis: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  frustrated: '😤',
  satisfaction: '😌',
  neutral: '😐',
};

export default function SentimentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<
    'idle' | 'running' | 'done' | 'error'
  >('idle');

  const [sentiments, setSentiments] = useState<SentimentResult[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [currentPage, setCurrentPage] = useState(1);

  // Load existing sentiment results and eligible reviews.
  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    const loadData = async () => {
      const [datasetResult, sentimentResult, reviewResult] =
        await Promise.allSettled([
          getDataset(id),
          getSentiments(id, { limit: 20000 }),
          fetchAllReviews(id),
        ]);

      if (cancelled) return;

      if (reviewResult.status === 'fulfilled') {
        const eligibleReviews = reviewResult.value || [];

        setReviews(eligibleReviews);

        if (sentimentResult.status === 'fulfilled') {
          const eligibleSentiments = filterEligibleSentiments(
            sentimentResult.value || [],
            eligibleReviews
          );

          setSentiments(eligibleSentiments);

          if (eligibleSentiments.length > 0) {
            setStatus('done');
          }
        }
      } else {
        toast.error('Failed to load eligible reviews');
      }

      if (
        datasetResult.status === 'fulfilled' &&
        datasetResult.value.status === 'complete'
      ) {
        if (sentimentResult.status === 'fulfilled') {
          setStatus('done');
        }
      }
    };

    loadData().catch(() => {
      if (!cancelled) {
        toast.error('Failed to load sentiment data');
      }
    });

    return () => {
      cancelled = true;
    };
  }, [id]);

  // Run sentiment and emotion analysis.
  const handleAnalyze = async () => {
    if (!id) return;

    setStatus('running');
    setCurrentPage(1);

    try {
      const result = await startSentimentAnalysis(id, true);

      const [sentimentResults, reviewData] = await Promise.all([
        getSentiments(id, { limit: 20000 }),
        fetchAllReviews(id),
      ]);

      const eligibleReviews = reviewData || [];

      const eligibleSentiments = filterEligibleSentiments(
        sentimentResults || [],
        eligibleReviews
      );

      setReviews(eligibleReviews);
      setSentiments(eligibleSentiments);
      setStatus('done');

      toast.success(
        `Sentiment analysis complete! Analyzed ${eligibleSentiments.length} eligible reviews.`
      );
    } catch (err: any) {
      setStatus('error');

      toast.error(
        err.response?.data?.detail || 'Sentiment analysis failed'
      );
    }
  };

  // Download the processed dataset.
  const handleExport = async () => {
    if (!id) return;

    try {
      const blob = await exportAnalysisDataset(id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = `alphaev_sentiment_${id}.xlsx`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);

      toast.success('Processed sentiment dataset downloaded!');
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail ||
          'Failed to export sentiment dataset.'
      );
    }
  };

  // Distribution counts use only eligible sentiment results.
  const sentimentDist = SENTIMENTS.reduce((acc, sentiment) => {
    acc[sentiment] = sentiments.filter(
      item => item.overall_sentiment === sentiment
    ).length;

    return acc;
  }, {} as Record<string, number>);

  const emotionDist = EMOTIONS.reduce((acc, emotion) => {
    acc[emotion] = sentiments.filter(
      item => item.emotion === emotion
    ).length;

    return acc;
  }, {} as Record<string, number>);

  // Map eligible review IDs to their corresponding review text.
  const reviewMap = reviews.reduce((acc, review) => {
    acc[review.id] = review;
    return acc;
  }, {} as Record<string, Review>);

  // Pagination calculations.
  const totalReviews = sentiments.length;

  const totalPages = Math.max(
    1,
    Math.ceil(totalReviews / PAGE_SIZE)
  );

  const startIndex = (currentPage - 1) * PAGE_SIZE;

  const endIndex = Math.min(
    startIndex + PAGE_SIZE,
    totalReviews
  );

  const paginatedSentiments = sentiments.slice(
    startIndex,
    endIndex
  );

  const startReview = totalReviews === 0 ? 0 : startIndex + 1;

  // Keep the current page valid if the result count changes.
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const goToPage = (nextPage: number) => {
    setCurrentPage(Math.max(1, Math.min(nextPage, totalPages)));
  };

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Sentiment &amp; Emotion Analysis
          </h2>

          <p className="text-gray-500 mt-1">
            Discover customer emotions and overall sentiment tone
          </p>
        </div>

      
      </div>

      {/* Idle state */}
      {status === 'idle' && (
        <div className="card text-center py-10">
          <Alpha
            mood="idle"
            size="md"
            message="Ready to analyze sentiment and emotional tone across all your clean customer reviews!"
          />

          <button
            onClick={handleAnalyze}
            className="btn-primary mt-6 inline-flex items-center gap-2"
          >
            <Zap size={18} />
            Analyze Sentiment &amp; Emotion
          </button>
        </div>
      )}

      {/* Running state */}
      {status === 'running' && (
        <div className="card text-center py-10">
          <Alpha
            mood="thinking"
            size="md"
            message="Alpha is analyzing sentiment and customer feelings... 💭"
          />

          <div className="w-56 mx-auto mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-500 rounded-full animate-pulse"
              style={{ width: '60%' }}
            />
          </div>
        </div>
      )}

      {/* Error state */}
      {status === 'error' && (
        <div className="card text-center py-10">
          <Alpha
            mood="error"
            size="md"
            message="Sentiment analysis encountered an error. Please try again."
          />

          <button
            onClick={handleAnalyze}
            className="btn-primary mt-4"
          >
            Retry
          </button>
        </div>
      )}

      {/* Analysis results */}
      {status === 'done' && (
        <>
          {/* Export section */}
          <div className="card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="font-semibold text-gray-900">
                Download Processed Dataset
              </h3>

              <p className="text-sm text-gray-500 mt-1">
                Export reviews with aspect, sentiment and emotion labels.
              </p>
            </div>

            <button
              type="button"
              onClick={handleExport}
              className="btn-primary inline-flex items-center justify-center gap-2 whitespace-nowrap"
            >
              <Download size={16} />
              Download Excel
            </button>
          </div>

          {/* Sentiment and emotion distributions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Overall sentiment distribution */}
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">
                Overall Sentiment Distribution
              </h3>

              <div className="space-y-3">
                {SENTIMENTS.map(sentiment => {
                  const count = sentimentDist[sentiment] || 0;

                  const percentage =
                    sentiments.length > 0
                      ? (count / sentiments.length) * 100
                      : 0;

                  return (
                    <div
                      key={sentiment}
                      className="flex items-center gap-3"
                    >
                      <span className="w-24 text-sm font-semibold capitalize text-gray-700">
                        {sentiment}
                      </span>

                      <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            sentiment === 'positive'
                              ? 'bg-emerald-500'
                              : sentiment === 'negative'
                              ? 'bg-red-500'
                              : 'bg-gray-400'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>

                      <span className="text-sm text-gray-500 w-20 text-right">
                        {count} ({percentage.toFixed(0)}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Emotion distribution */}
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">
                Emotion Breakdown
              </h3>

              <div className="space-y-3">
                {EMOTIONS.map(emotion => {
                  const count = emotionDist[emotion] || 0;

                  const percentage =
                    sentiments.length > 0
                      ? (count / sentiments.length) * 100
                      : 0;

                  return (
                    <div
                      key={emotion}
                      className="flex items-center gap-3"
                    >
                      <span className="w-28 text-sm font-medium capitalize text-gray-700 flex items-center gap-1.5">
                        <span>{emotionEmojis[emotion]}</span>
                        {emotion}
                      </span>

                      <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal-500 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>

                      <span className="text-sm text-gray-500 w-20 text-right">
                        {count} ({percentage.toFixed(0)}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Individual review sentiment results */}
          <div className="card">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <h3 className="font-semibold text-gray-900">
                Review Sentiments &amp; Emotion Labels
              </h3>

              <span className="text-xs text-gray-500">
                {totalReviews} eligible reviews analyzed
              </span>
            </div>

            <div className="space-y-3">
              {paginatedSentiments.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-400">
                  No sentiment results found.
                </div>
              ) : (
                paginatedSentiments.map(sentiment => {
                  const review = reviewMap[sentiment.review_id];

                  const reviewText = review
                    ? review.cleaned_text || review.original_text
                    : `Review #${sentiment.review_id}`;

                  return (
                    <div
                      key={sentiment.id}
                      className="border border-gray-100 rounded-xl p-4 bg-white hover:border-gray-200 transition-colors"
                    >
                      {/* Review text */}
                      <p className="text-sm text-gray-800 mb-3 leading-relaxed whitespace-pre-wrap break-words">
                        {reviewText}
                      </p>

                      <div className="flex items-center gap-4 flex-wrap">
                        {/* Read-only sentiment label */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs text-gray-500 font-medium">
                            Sentiment:
                          </span>

                          <span
                            className={`text-xs font-semibold border rounded-lg px-2.5 py-1 capitalize ${
                              sentimentColors[
                                sentiment.overall_sentiment
                              ] || 'text-gray-700 bg-gray-50 border-gray-200'
                            }`}
                          >
                            {sentiment.overall_sentiment}
                          </span>

                          <span className="text-xs text-gray-400">
                            ({Math.round(
                              sentiment.sentiment_confidence * 100
                            )}%)
                          </span>
                        </div>

                        {/* Read-only emotion label */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs text-gray-500 font-medium">
                            Emotion:
                          </span>

                          <span
                            className={`text-xs font-semibold border rounded-lg px-2.5 py-1 capitalize ${
                              emotionColors[sentiment.emotion] ||
                              'text-gray-700 bg-gray-50 border-gray-200'
                            }`}
                          >
                            {emotionEmojis[sentiment.emotion] || '😐'}{' '}
                            {sentiment.emotion}
                          </span>

                          <span className="text-xs text-gray-400">
                            ({Math.round(
                              sentiment.emotion_confidence * 100
                            )}%)
                          </span>
                        </div>

                        {sentiment.is_human_corrected && (
                          <span className="badge bg-blue-100 text-blue-700">
                            Edited by User
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Pagination controls */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-5 pt-4 border-t border-gray-100">
              <div className="text-sm text-gray-500 text-center sm:text-left">
                Showing{' '}
                <span className="font-semibold text-gray-800">
                  {startReview}–{endIndex}
                </span>{' '}
                of{' '}
                <span className="font-semibold text-gray-800">
                  {totalReviews}
                </span>{' '}
                eligible reviews

                <span className="block text-xs mt-1">
                  Page {Math.min(currentPage, totalPages)} of{' '}
                  {totalPages} · 5 per page
                </span>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => goToPage(1)}
                  disabled={currentPage <= 1}
                  aria-label="First page"
                  title="First page"
                  className="btn-ghost text-sm px-2.5 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronsLeft size={16} />
                </button>

                <button
                  type="button"
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed inline-flex items-center gap-1"
                >
                  <ChevronLeft size={16} />
                  Previous
                </button>

                <span className="px-3 py-2 text-sm font-semibold rounded-lg bg-teal-50 text-teal-700">
                  {currentPage}
                </span>

                <button
                  type="button"
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed inline-flex items-center gap-1"
                >
                  Next
                  <ChevronRight size={16} />
                </button>

                <button
                  type="button"
                  onClick={() => goToPage(totalPages)}
                  disabled={currentPage >= totalPages}
                  aria-label="Last page"
                  title="Last page"
                  className="btn-ghost text-sm px-2.5 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronsRight size={16} />
                </button>
              </div>
            </div>
          </div>

          {/* Continue to dashboard */}
          <div className="flex justify-end">
            <button
              onClick={() => navigate(`/dataset/${id}/dashboard`)}
              className="btn-primary flex items-center gap-2"
            >
              View Analytics Dashboard
              <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
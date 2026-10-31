
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Brain,
  ArrowRight,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
} from 'lucide-react';
import toast from 'react-hot-toast';
import Alpha from '../components/Alphi';
import {
  startClassification,
  getPredictions,
  getReviews,
  getExplanation,
  getDataset,
  exportAnalysisDataset,
  ASPECT_DISPLAY_NAMES,
  type Prediction,
  type Review,
  type ExplainResponse,
  type AspectCode,
} from '../api';

const ASPECTS = Object.keys(ASPECT_DISPLAY_NAMES) as AspectCode[];

const PAGE_SIZE = 5;

// Fetch all reviews and retain only usable reviews.
const fetchAllReviews = async (datasetId: string): Promise<Review[]> => {
  const firstPage = await getReviews(datasetId, {
    page: 1,
    page_size: 100,
  });

  const totalPages = Math.ceil(
    firstPage.total / firstPage.page_size
  );

  const remainingPages =
    totalPages <= 1
      ? []
      : await Promise.all(
          Array.from({ length: totalPages - 1 }, (_, index) =>
            getReviews(datasetId, {
              page: index + 2,
              page_size: 100,
            })
          )
        );

  const allReviews = [
    firstPage,
    ...remainingPages,
  ].flatMap(page => page.reviews || []);

  return allReviews.filter(review =>
    !review.is_duplicate &&
    !review.is_low_info &&
    Boolean(
      (review.cleaned_text || review.original_text || '').trim()
    )
  );
};

export default function ClassificationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<
    'idle' | 'running' | 'done' | 'error'
  >('idle');

  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [explanation, setExplanation] =
    useState<ExplainResponse | null>(null);

  const [selectedReview, setSelectedReview] = useState<string | null>(null);
  const [explainingReviewId, setExplainingReviewId] =
    useState<string | null>(null);

  const [currentPage, setCurrentPage] = useState(1);

  // Load dataset, predictions, and eligible reviews.
  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    const loadData = async () => {
      try {
        const [
          datasetResult,
          predictionResult,
          reviewResult,
        ] = await Promise.allSettled([
          getDataset(id),
          getPredictions(id, { limit: 20000 }),
          fetchAllReviews(id),
        ]);

        if (cancelled) return;

        if (datasetResult.status === 'fulfilled') {
          if (
            ['classified', 'complete'].includes(
              datasetResult.value.status
            )
          ) {
            setStatus('done');
          }
        }

        if (reviewResult.status === 'fulfilled') {
          const eligibleReviews = reviewResult.value || [];

          setReviews(eligibleReviews);

          if (predictionResult.status === 'fulfilled') {
            const eligibleReviewIds = new Set(
              eligibleReviews.map(review => review.id)
            );

            const eligiblePredictions = (
              predictionResult.value || []
            ).filter(prediction =>
              eligibleReviewIds.has(prediction.review_id)
            );

            setPredictions(eligiblePredictions);

            if (eligiblePredictions.length > 0) {
              setStatus('done');
            }
          }
        }
      } catch {
        toast.error('Failed to load classification data.');
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, [id]);

  // Start classification.
  const handleClassify = async () => {
    if (!id) return;

    setStatus('running');
    setCurrentPage(1);
    setSelectedReview(null);
    setExplanation(null);

    try {
      const res = await startClassification(id, {
        threshold: 0.35,
        skip_duplicates: true,
      });

      const [preds, eligibleReviews] = await Promise.all([
        getPredictions(id, { limit: 20000 }),
        fetchAllReviews(id),
      ]);

      const eligibleReviewIds = new Set(
        eligibleReviews.map(review => review.id)
      );

      const eligiblePredictions = (preds || []).filter(
        prediction =>
          eligibleReviewIds.has(prediction.review_id)
      );

      setReviews(eligibleReviews);
      setPredictions(eligiblePredictions);
      setStatus('done');

      toast.success(
        `Classification complete! Classified ${res.reviews_classified} reviews (${eligiblePredictions.length} aspect instances displayed).`
      );
    } catch (err: any) {
      setStatus('error');

      toast.error(
        err.response?.data?.detail || 'Classification failed'
      );
    }
  };

  // Export the classified dataset.
  const handleExport = async () => {
    if (!id) return;

    try {
      const blob = await exportAnalysisDataset(id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = `alphaev_classification_${id}.xlsx`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.setTimeout(
        () => window.URL.revokeObjectURL(url),
        1000
      );

      toast.success('Classification dataset downloaded!');
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail ||
        'Failed to export classification dataset.'
      );
    }
  };

  // Show or hide SHAP explanations.
  const handleExplain = async (reviewId: string) => {
    if (selectedReview === reviewId) {
      setSelectedReview(null);
      setExplanation(null);
      return;
    }

    setSelectedReview(reviewId);
    setExplainingReviewId(reviewId);
    setExplanation(null);

    try {
      const result = await getExplanation(reviewId, 5);
      setExplanation(result);
    } catch {
      toast.error('Explanation unavailable for this review');
    } finally {
      setExplainingReviewId(null);
    }
  };

  // Group predictions by review ID.
  const predsByReview = predictions.reduce(
    (acc, prediction) => {
      if (!acc[prediction.review_id]) {
        acc[prediction.review_id] = [];
      }

      acc[prediction.review_id].push(prediction);

      return acc;
    },
    {} as Record<string, Prediction[]>
  );

  // All displayed reviews are eligible reviews.
  const classifiedReviews = reviews;

  const totalReviews = classifiedReviews.length;

  // Pagination calculations.
  const totalPages = Math.max(
    1,
    Math.ceil(totalReviews / PAGE_SIZE)
  );

  const startIndex = (currentPage - 1) * PAGE_SIZE;

  const endIndex = Math.min(
    startIndex + PAGE_SIZE,
    totalReviews
  );

  const paginatedReviews = classifiedReviews.slice(
    startIndex,
    endIndex
  );

  const startReview =
    totalReviews === 0 ? 0 : startIndex + 1;

  // Keep the page valid when the available reviews change.
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  // Calculate aspect-wise positive and negative counts.
  const aspectCounts = ASPECTS.reduce(
    (acc, aspect) => {
      acc[aspect] = {
        positive: 0,
        negative: 0,
      };

      predictions.forEach(prediction => {
        if (prediction.aspect === aspect) {
          if (prediction.polarity === 'pos') {
            acc[aspect].positive++;
          } else if (prediction.polarity === 'neg') {
            acc[aspect].negative++;
          }
        }
      });

      return acc;
    },
    {} as Record<string, {
      positive: number;
      negative: number;
    }>
  );

  return (
    <div className="space-y-6">

      {/* Page heading */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Aspect Classification
          </h2>

          <p className="text-gray-500 mt-1">
            Alpha detects what customers are talking about across 11 key EV aspects
          </p>
        </div>


      </div>

      {/* Model information */}
      <div className="flex items-start gap-3 p-3.5 bg-teal-50/70 border border-teal-100 rounded-xl text-sm text-teal-900">
        <Sparkles
          size={18}
          className="mt-0.5 shrink-0 text-teal-600"
        />

        <div>
          <p className="font-semibold text-teal-950">
            Multi-Label Aspect &amp; Polarity AI Model
          </p>

          <p className="text-xs text-teal-700 mt-0.5">
            Classifies each review into 11 domain aspects with
            positive or negative polarity, with SHAP
            word-attribution explainability.
          </p>
        </div>
      </div>

      {/* Idle state */}
      {status === 'idle' && (
        <div className="card text-center py-10">
          <Alpha
            mood="detective"
            size="md"
            message="Ready to classify your reviews into 11 EV charging aspects with positive/negative polarity!"
          />

          <button
            onClick={handleClassify}
            className="btn-primary mt-6 inline-flex items-center gap-2"
          >
            <Brain size={18} />
            Start Aspect Classification
          </button>
        </div>
      )}

      {/* Running state */}
      {status === 'running' && (
        <div className="card text-center py-10">
          <Alpha
            mood="detective"
            size="md"
            message="Alpha is analyzing aspects across each review... 🔍"
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
            message="Classification encountered an error. Please try again."
          />

          <button
            onClick={handleClassify}
            className="btn-primary mt-4"
          >
            Retry Classification
          </button>
        </div>
      )}

      {/* Classification results */}
      {status === 'done' && (
        <>
          {/* Export classified dataset */}
          <div className="card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="font-semibold text-gray-900">
                Download Classified Dataset
              </h3>

              <p className="text-sm text-gray-500 mt-1">
                Export every eligible cleaned review with binary aspect and polarity columns.
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

          {/* Aspect overview */}
          <div className="card">
            <div className="mb-4">
              <h3 className="font-semibold text-gray-900">
                Aspect Overview ({reviews.length} eligible reviews)
              </h3>

              <p className="text-xs text-gray-500 mt-1">
                {predictions.length} aspect instances detected across eligible reviews
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {ASPECTS.map(aspect => {
                const counts = aspectCounts[aspect] || {
                  positive: 0,
                  negative: 0,
                };

                return (
                  <div
                    key={aspect}
                    className="bg-gray-50 border border-gray-100 rounded-xl p-3 flex flex-col justify-between"
                  >
                    <p
                      className="text-xs font-semibold text-gray-700 mb-2"
                      title={ASPECT_DISPLAY_NAMES[aspect]}
                    >
                      {ASPECT_DISPLAY_NAMES[aspect]}
                    </p>

                    <div className="flex items-center gap-2">
                      <span className="badge badge-positive">
                        +{counts.positive}
                      </span>

                      <span className="badge badge-negative">
                        -{counts.negative}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Review classifications */}
          <div className="card">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <h3 className="font-semibold text-gray-900">
                Review Classifications &amp; Evidence
              </h3>

              <span className="text-xs text-gray-500">
                {totalReviews} eligible reviews processed
              </span>
            </div>

            <div className="space-y-3">
              {paginatedReviews.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-400">
                  No eligible reviews found in the cleaned dataset.
                </div>
              ) : (
                paginatedReviews.map(review => {
                  const preds =
                    predsByReview[review.id] ||
                    review.predictions ||
                    [];

                  const isSelected =
                    selectedReview === review.id;

                  return (
                    <div
                      key={review.id}
                      className="border border-gray-100 rounded-xl p-4 bg-white hover:border-gray-200 transition-colors"
                    >
                      {/* Review text */}
                      <p className="text-sm text-gray-800 leading-relaxed mb-3 whitespace-pre-wrap break-words">
                        {review.cleaned_text || review.original_text}
                      </p>

                      {/* Read-only aspect predictions */}
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        {preds.map(prediction => {
                          const isPositive =
                            prediction.polarity === 'pos';

                          return (
                            <div
                              key={prediction.id}
                              className={`flex flex-wrap items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${
                                isPositive
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                  : 'bg-red-50 text-red-800 border-red-200'
                              } ${
                                prediction.is_human_corrected
                                  ? 'ring-2 ring-blue-400'
                                  : ''
                              }`}
                            >
                              <span>
                                {
                                  (ASPECT_DISPLAY_NAMES as Record<
                                    string,
                                    string
                                  >)[prediction.aspect] ||
                                    prediction.aspect
                                }{' '}
                                {isPositive ? '(+)' : '(-)'}
                              </span>

                              <span className="text-[10px] opacity-75">
                                {Math.round(
                                  prediction.confidence * 100
                                )}
                                %
                              </span>
                            </div>
                          );
                        })}

                        {preds.length === 0 && (
                          <span className="text-xs text-gray-400 italic">
                            No aspect detected above the current threshold.
                          </span>
                        )}
                      </div>

                      {/* Explanation actions */}
                      <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-gray-50">
                        <button
                          onClick={() => handleExplain(review.id)}
                          className="text-xs text-teal-600 hover:text-teal-700 font-medium inline-flex items-center gap-1"
                        >
                          <Sparkles size={13} />

                          {isSelected
                            ? 'Hide Explanation'
                            : 'Explain Predictions (SHAP)'}
                        </button>

                        {explainingReviewId === review.id && (
                          <span className="text-xs text-gray-400">
                            Loading explanation...
                          </span>
                        )}
                      </div>

                      {/* SHAP explanation */}
                      {isSelected && explanation && (
                        <div className="mt-3 p-3.5 bg-gray-50/90 border border-gray-200 rounded-xl text-xs space-y-2">
                          {explanation.summary && (
                            <p className="text-gray-700 font-medium">
                              {explanation.summary}
                            </p>
                          )}

                          {explanation.aspect_explanations &&
                            Object.entries(
                              explanation.aspect_explanations
                            ).map(([aspect, words]) => (
                              <div
                                key={aspect}
                                className="pt-1"
                              >
                                <p className="font-semibold text-gray-700 mb-1">
                                  {
                                    (ASPECT_DISPLAY_NAMES as Record<
                                      string,
                                      string
                                    >)[aspect] || aspect
                                  }:
                                </p>

                                <div className="flex flex-wrap gap-1.5">
                                  {words && words.length > 0 ? (
                                    words.map((word, index) => (
                                      <span
                                        key={`${aspect}-${index}`}
                                        className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                                          word.score > 0
                                            ? 'bg-emerald-100 text-emerald-800'
                                            : 'bg-red-100 text-red-800'
                                        }`}
                                      >
                                        {word.word} (
                                        {word.score > 0 ? '+' : ''}
                                        {word.score.toFixed(2)})
                                      </span>
                                    ))
                                  ) : (
                                    <span className="text-gray-400 italic">
                                      No salient words found
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Pagination */}
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
                classified reviews

                <span className="block text-xs mt-1">
                  Page {Math.min(currentPage, totalPages)} of{' '}
                  {totalPages} · 5 per page
                </span>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setCurrentPage(1);
                    setSelectedReview(null);
                    setExplanation(null);
                  }}
                  disabled={currentPage <= 1}
                  className="btn-ghost text-sm px-2.5 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
                  aria-label="First page"
                  title="First page"
                >
                  <ChevronsLeft size={16} />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setCurrentPage(page =>
                      Math.max(1, page - 1)
                    );
                    setSelectedReview(null);
                    setExplanation(null);
                  }}
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
                  onClick={() => {
                    setCurrentPage(page =>
                      Math.min(totalPages, page + 1)
                    );
                    setSelectedReview(null);
                    setExplanation(null);
                  }}
                  disabled={currentPage >= totalPages}
                  className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed inline-flex items-center gap-1"
                >
                  Next
                  <ChevronRight size={16} />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setCurrentPage(totalPages);
                    setSelectedReview(null);
                    setExplanation(null);
                  }}
                  disabled={currentPage >= totalPages}
                  className="btn-ghost text-sm px-2.5 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
                  aria-label="Last page"
                  title="Last page"
                >
                  <ChevronsRight size={16} />
                </button>
              </div>
            </div>
          </div>

          {/* Continue to sentiment analysis */}
          <div className="flex justify-end">
            <button
              onClick={() =>
                navigate(`/dataset/${id}/sentiment`)
              }
              className="btn-primary flex items-center gap-2"
            >
              Continue to Sentiment Analysis
              <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}


import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  Check,
  Search,
  Download,
  Edit3,
  Save,
  Eye,
} from 'lucide-react';
import toast from 'react-hot-toast';
import Alpha from '../components/Alphi';
import {
  getDataset,
  startCleaning,
  getCleaningStatus,
  getCleaningReport,
  getReviews,
  updateReview,
  exportCleanedReviews,
  type Review,
  type CleaningReportResponse,
} from '../api';

const PAGE_SIZE = 10;

export default function CleaningPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);

  const [report, setReport] =
    useState<CleaningReportResponse | null>(null);

  const [reviews, setReviews] = useState<Review[]>([]);
  const [totalReviews, setTotalReviews] = useState(0);

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const [showComparison, setShowComparison] =
    useState<string | null>(null);

  const [isExporting, setIsExporting] = useState(false);

  // Pagination calculations.
  const totalPages = Math.max(
    1,
    Math.ceil(totalReviews / PAGE_SIZE)
  );

  const startReview =
    totalReviews === 0
      ? 0
      : (page - 1) * PAGE_SIZE + 1;

  const endReview = Math.min(
    page * PAGE_SIZE,
    totalReviews
  );

  // Fetch only usable reviews from the backend.
  const fetchReviews = useCallback(async () => {
    if (!id) return;

    try {
      const data = await getReviews(id, {
        page,
        page_size: PAGE_SIZE,
        usable_only: true,
        search: search.trim() || undefined,
      });

      setReviews(data.reviews || []);
      setTotalReviews(data.total || 0);
    } catch (error) {
      console.error('Failed to fetch usable reviews:', error);
      toast.error('Failed to load usable reviews');
    }
  }, [id, page, search]);

  // Restore dataset status when revisiting the page.
  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    const loadDataset = async () => {
      try {
        const dataset = await getDataset(id);

        if (cancelled) return;

        if (
          [
            'cleaned',
            'classifying',
            'classified',
            'complete',
          ].includes(dataset.status)
        ) {
          setStatus('done');
          setProgress(100);

          try {
            const cleaningReport = await getCleaningReport(id);

            if (!cancelled) {
              setReport(cleaningReport);
            }
          } catch (error) {
            console.error(
              'Failed to load cleaning report:',
              error
            );
          }
        }
      } catch (error) {
        console.error('Failed to load dataset:', error);
      }
    };

    loadDataset();

    return () => {
      cancelled = true;
    };
  }, [id]);

  // Reload reviews when pagination, search, or cleaning status changes.
  useEffect(() => {
    if (status === 'done') {
      fetchReviews();
    }
  }, [fetchReviews, status]);

  // Keep the current page within valid limits.
  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  // Start the cleaning pipeline.
  const handleStartCleaning = async () => {
    if (!id) return;

    setStatus('cleaning');
    setProgress(20);

    try {
      const cleaningReport = await startCleaning(id);

      setProgress(100);
      setStatus('done');
      setReport(cleaningReport);
      setPage(1);

      toast.success('Cleaning complete!');
    } catch (error: any) {
      console.error('Cleaning failed:', error);

      // Check whether cleaning completed despite a request error.
      try {
        const cleaningStatus = await getCleaningStatus(id);

        if (
          cleaningStatus.status === 'cleaned' ||
          cleaningStatus.status === 'complete' ||
          cleaningStatus.status === 'classified'
        ) {
          const cleaningReport = await getCleaningReport(id);

          setReport(cleaningReport);
          setStatus('done');
          setProgress(100);
          setPage(1);

          toast.success('Cleaning completed successfully!');
          return;
        }
      } catch (statusError) {
        console.error(
          'Could not recover cleaning status:',
          statusError
        );
      }

      setStatus('error');

      toast.error(
        error?.response?.data?.detail ||
          'Failed to clean dataset'
      );
    }
  };

  // Save a manually edited review.
  const handleSaveEdit = async (reviewId: string) => {
    try {
      await updateReview(reviewId, {
        cleaned_text: editText,
      });

      setEditingId(null);

      await fetchReviews();

      toast.success('Review updated');
    } catch (error) {
      console.error('Review update failed:', error);
      toast.error('Failed to update review');
    }
  };

  // Export the cleaning audit workbook.
  const handleExport = async () => {
    if (!id) {
      toast.error('Dataset ID is missing');
      return;
    }

    setIsExporting(true);

    try {
      const blob = await exportCleanedReviews(id);

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = `alphaev_cleaning_audit_${id}.xlsx`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);

      toast.success('Cleaning audit workbook downloaded');
    } catch (error: any) {
      console.error('Export failed:', error);

      toast.error(
        error?.response?.data?.detail ||
          'Excel export failed. Please run cleaning first and try again.'
      );
    } finally {
      setIsExporting(false);
    }
  };

  // Determine whether a review has any cleaning flags.
  // This is only used for visual highlighting, not filtering.
  const hasFlags = (review: Review) =>
    Boolean(
      (review.flags && review.flags.length > 0) ||
      review.is_duplicate ||
      review.is_low_info ||
      (review.language && review.language !== 'en')
    );

  return (
    <div className="space-y-6">

      {/* Page heading */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Data Cleaning
          </h2>

          <p className="text-gray-500 mt-1">
            Alpha sweeps your data clean
          </p>
        </div>


      </div>

      {/* Start cleaning */}
      {status === 'idle' && (
        <div className="card text-center py-10">
          <Alpha
            mood="cleaning"
            size="md"
            message="Ready to clean your dataset! This includes encoding fixes, HTML removal, duplicate detection, language identification, and low-information filtering."
          />

          <button
            onClick={handleStartCleaning}
            className="btn-primary mt-6 inline-flex items-center gap-2"
          >
            <Sparkles size={18} />
            Start Cleaning
          </button>
        </div>
      )}

      {/* Cleaning progress */}
      {status === 'cleaning' && (
        <div className="card text-center py-10">
          <Alpha
            mood="cleaning"
            size="md"
            message="Alpha is sweeping through your reviews... 🧹"
          />

          <div className="w-64 mx-auto mt-6">
            <div className="flex justify-between text-sm text-gray-500 mb-1">
              <span>Cleaning</span>
              <span>{Math.round(progress)}%</span>
            </div>

            <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-500 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="card text-center py-10">
          <Alpha
            mood="error"
            size="md"
            message="Oops! Something went wrong during cleaning."
          />

          <button
            onClick={handleStartCleaning}
            className="btn-primary mt-4"
          >
            Retry
          </button>
        </div>
      )}

      {/* Cleaning report */}
      {report && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Check size={18} className="text-teal-600" />
            Cleaning Report
          </h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: 'Total Reviews',
                value: report.total_reviews ?? totalReviews,
                color: 'text-gray-900',
              },
              {
                label: 'Usable Reviews',
                value: report.retained_count ?? 0,
                color: 'text-green-600',
              },
              {
                label: 'Exact Duplicates',
                value: report.exact_duplicates ?? 0,
                color: 'text-amber-600',
              },
              {
                label: 'Near-Duplicates',
                value: report.near_duplicates ?? 0,
                color: 'text-orange-600',
              },
              {
                label: 'Low Information',
                value: report.low_info_count ?? 0,
                color: 'text-red-600',
              },
              {
                label: 'Non-English Reviews',
                value: report.non_english_count ?? 0,
                color: 'text-blue-600',
              },
              {
                label: 'HTML Tags Removed',
                value: report.html_removed_count ?? 0,
                color: 'text-indigo-600',
              },
              {
                label: 'Encodings Fixed',
                value: report.encoding_fixed_count ?? 0,
                color: 'text-purple-600',
              },
            ].map(stat => (
              <div
                key={stat.label}
                className="bg-gray-50 rounded-xl p-3 border border-gray-100"
              >
                <p className="text-xs text-gray-500 font-medium">
                  {stat.label}
                </p>

                <p
                  className={`text-2xl font-bold ${stat.color} mt-1`}
                >
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Usable Reviews */}
      {(status === 'done' || reviews.length > 0) && (
        <div className="card">

          {/* Reviews heading and Export button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">

            <h3 className="font-semibold text-gray-900">
              Usable Reviews ({totalReviews})
            </h3>

            <button
              onClick={handleExport}
              disabled={isExporting || status !== 'done'}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold px-4 py-2 rounded-lg flex items-center justify-center gap-2 shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download size={15} />

              {isExporting
                ? 'Preparing Excel...'
                : 'Export Excel'}
            </button>
          </div>

          {/* Search */}
          <div className="relative w-full sm:max-w-sm mb-4">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />

            <input
              type="text"
              placeholder="Search usable reviews..."
              value={search}
              onChange={event => {
                setSearch(event.target.value);
                setPage(1);
              }}
              className="input-field pl-9 text-sm w-full"
            />
          </div>

          {/* Review cards */}
          <div className="space-y-2">

            {reviews.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                {search.trim()
                  ? 'No usable reviews found matching your search.'
                  : 'No usable reviews available.'}
              </div>
            ) : (
              reviews.map(review => {
                const flagged = hasFlags(review);

                return (
                  <div
                    key={review.id}
                    className={`border rounded-xl p-4 transition-colors ${
                      flagged
                        ? 'border-amber-200 bg-amber-50/40'
                        : 'border-gray-100 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">

                      <div className="flex-1 min-w-0">

                        {/* Review metadata */}
                        <div className="flex items-center gap-2 mb-1 flex-wrap">

                          <span className="text-xs text-gray-400 font-mono">
                            #{review.row_index}
                          </span>

                          {review.is_duplicate && (
                            <span className="badge badge-negative">
                              Duplicate
                            </span>
                          )}

                          {review.is_low_info && (
                            <span className="badge bg-amber-100 text-amber-700">
                              Low Info
                            </span>
                          )}

                          {review.language &&
                            review.language !== 'en' && (
                              <span className="badge bg-blue-100 text-blue-700">
                                {review.language}
                              </span>
                            )}

                          {review.rating != null && (
                            <span className="text-xs text-amber-600 font-medium">
                              ★ {review.rating}
                            </span>
                          )}

                          {review.flags?.map((flag, index) => {
                            const isExcluded =
                              flag.action === 'excluded';

                            return (
                              <span
                                key={`${review.id}-flag-${index}`}
                                className={`badge text-[10px] ${
                                  isExcluded
                                    ? 'bg-red-50 text-red-700 border border-red-200'
                                    : 'bg-amber-50 text-amber-800 border border-amber-200'
                                }`}
                                title={
                                  typeof flag.reason === 'string'
                                    ? flag.reason
                                    : flag.message
                                }
                              >
                                {flag.type || flag.message}
                              </span>
                            );
                          })}
                        </div>

                        {/* Review editing */}
                        {editingId === review.id ? (
                          <div className="space-y-2 mt-2">

                            <textarea
                              value={editText}
                              onChange={event =>
                                setEditText(event.target.value)
                              }
                              className="input-field text-sm min-h-[80px] w-full"
                            />

                            <div className="flex gap-2">
                              <button
                                onClick={() =>
                                  handleSaveEdit(review.id)
                                }
                                className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1"
                              >
                                <Save size={12} />
                                Save
                              </button>

                              <button
                                onClick={() =>
                                  setEditingId(null)
                                }
                                className="btn-ghost text-xs py-1.5 px-3"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-700 leading-relaxed break-words">
                            {review.cleaned_text ||
                              review.original_text}
                          </p>
                        )}
                      </div>

                      {/* Review actions */}
<div className="flex items-center gap-1 shrink-0">

  {review.cleaned_text &&
    review.original_text !== review.cleaned_text && (
      <button
        onClick={() =>
          setShowComparison(current =>
            current === review.id ? null : review.id
          )
        }
        className="btn-ghost p-1.5"
        title="Compare original and cleaned text"
        aria-label="Compare review text"
      >
        <Eye size={14} />
      </button>
    )}

</div>
                    </div>

                    {/* Original versus cleaned text */}
                    {showComparison === review.id && (
                      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">

                        <div className="bg-red-50/70 border border-red-100 rounded-lg p-3">
                          <p className="font-semibold text-red-700 mb-1">
                            Original Text
                          </p>

                          <p className="text-gray-700 whitespace-pre-wrap break-words">
                            {review.original_text}
                          </p>
                        </div>

                        <div className="bg-green-50/70 border border-green-100 rounded-lg p-3">
                          <p className="font-semibold text-green-700 mb-1">
                            Cleaned Text
                          </p>

                          <p className="text-gray-700 whitespace-pre-wrap break-words">
                            {review.cleaned_text}
                          </p>
                        </div>
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
                {startReview}–{endReview}
              </span>{' '}
              of{' '}
              <span className="font-semibold text-gray-800">
                {totalReviews}
              </span>{' '}
              usable reviews

              <span className="block text-xs mt-1">
                Page {Math.min(page, totalPages)} of {totalPages}
                {' · '}
                {PAGE_SIZE} per page
              </span>
            </div>

            <div className="flex items-center gap-2">

              <button
                type="button"
                onClick={() => setPage(1)}
                disabled={page <= 1}
                className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                First
              </button>

              <button
                type="button"
                onClick={() =>
                  setPage(current =>
                    Math.max(1, current - 1)
                  )
                }
                disabled={page <= 1}
                className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Previous
              </button>

              <span className="px-3 py-2 text-sm font-semibold rounded-lg bg-teal-50 text-teal-700">
                {page}
              </span>

              <button
                type="button"
                onClick={() =>
                  setPage(current =>
                    Math.min(totalPages, current + 1)
                  )
                }
                disabled={page >= totalPages}
                className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next
              </button>

              <button
                type="button"
                onClick={() => setPage(totalPages)}
                disabled={page >= totalPages}
                className="btn-ghost text-sm px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Last
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Continue to classification */}
      {status === 'done' && (
        <div className="flex justify-end">
          <button
            onClick={() =>
              navigate(`/dataset/${id}/classify`)
            }
            className="btn-primary flex items-center gap-2"
          >
            Continue to Classification
            <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

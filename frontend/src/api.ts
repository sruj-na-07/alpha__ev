import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
});

// --- Shared types ---

export type AspectCode =
  | 'pricing'
  | 'payment_issues'
  | 'charging_speed'
  | 'reliability'
  | 'waiting_time'
  | 'app_usability'
  | 'availability'
  | 'location_convenience'
  | 'improvement_suggestion'
  | 'overall_experience'
  | 'customer_support';

export type Polarity = 'pos' | 'neg';
export type OverallSentiment = 'positive' | 'negative' | 'neutral';
export type Emotion =
  | 'happy'
  | 'sad'
  | 'frustrated'
  | 'satisfaction'
  | 'neutral';

export type ReviewSeverity = 'Critical' | 'High' | 'Medium' | 'Low';

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = Record<string, JsonValue>;

// --- Dataset types ---

export interface Dataset {
  id: string;
  name: string;
  filename: string;
  original_filename: string;
  upload_time: string;
  status: string;
  row_count: number;
  version?: number;
  is_stale?: boolean;
  column_mapping: Record<string, string | null>;
  cleaning_stats: JsonObject;
}

export interface DatasetListResponse {
  total: number;
  datasets: Dataset[];
}

export interface UploadResponse {
  dataset_id: string;
  name: string;
  filename: string;
  status: string;
  row_count: number;
  columns: string[];
  suggested_mapping: Record<string, string | null>;
  sample_preview: Record<string, JsonValue>[];
}

export interface ColumnDetectionResponse {
  dataset_id: string;
  columns: string[];
  suggested_mapping: Record<string, string | null>;
  sample_preview: Record<string, JsonValue>[];
}

export type ColumnInfo = ColumnDetectionResponse;

export interface ColumnMappingRequest {
  text_column: string;
  rating_column?: string | null;
  date_column?: string | null;
  source_column?: string | null;
  reviewer_column?: string | null;
}

// --- Cleaning types ---

export interface CleaningReportResponse {
  dataset_id: string;
  total_reviews: number;
  cleaned_count: number;
  retained_count?: number;
  exact_duplicates: number;
  near_duplicates: number;
  low_info_count: number;
  non_english_count: number;
  html_removed_count: number;
  encoding_fixed_count: number;
  flags_breakdown: Record<string, number>;
}

export interface CleaningStatusResponse {
  dataset_id: string;
  status: string;
  progress: number;
  message: string;
}

// --- Review types ---

export interface ReviewFlag {
  type: string;
  message?: string;
  [key: string]: JsonValue | undefined;
}

export interface Prediction {
  id: number;
  review_id: string;
  aspect: AspectCode | string;
  polarity: Polarity;
  confidence: number;
  is_human_corrected: boolean;
  model_prediction?: string | null;
  model_confidence?: number | null;
}

export interface PredictionUpdateRequest {
  aspect: AspectCode;
  polarity: Polarity;
  confidence?: number;
}

export interface SentimentResult {
  id: number;
  review_id: string;
  overall_sentiment: OverallSentiment;
  sentiment_confidence: number;
  emotion: Emotion;
  emotion_confidence: number;
  is_human_corrected: boolean;
}

export interface SentimentUpdateRequest {
  overall_sentiment: OverallSentiment;
  emotion: Emotion;
  sentiment_confidence?: number;
  emotion_confidence?: number;
}

export interface Review {
  id: string;
  dataset_id: string;
  row_index: number;
  original_text: string;
  cleaned_text: string | null;
  rating: number | null;
  review_date: string | null;
  source: string | null;
  reviewer: string | null;
  flags: ReviewFlag[];
  is_duplicate: boolean;
  duplicate_of: string | null;
  language: string | null;
  is_low_info: boolean;
  predictions: Prediction[];
  sentiment: SentimentResult | null;
}

export interface ReviewListResponse {
  total: number;
  page: number;
  page_size: number;
  reviews: Review[];
}

export interface ReviewUpdateRequest {
  cleaned_text?: string | null;
  rating?: number | null;
  is_low_info?: boolean | null;
  is_duplicate?: boolean | null;
  flags?: ReviewFlag[] | null;
}

// --- Classification and explanation ---

export interface ClassificationResponse {
  dataset_id: string;
  status: string;
  reviews_classified: number;
  total_predictions_generated: number;
}

export interface WordImportance {
  word: string;
  score: number;
}

export interface ExplainResponse {
  review_id: string;
  text: string;
  aspect_explanations: Record<string, WordImportance[]>;
  summary: string;
}

export interface SentimentAnalysisResponse {
  dataset_id: string;
  total_analyzed: number;
  sentiment_counts: Record<OverallSentiment, number>;
  emotion_counts: Record<string, number>;
}

// --- Dashboard types ---

export interface QualityMetrics {
  total_rows: number;
  usable_rows: number;
  exact_duplicates: number;
  near_duplicates: number;
  low_info_reviews: number;
  non_english: number;
}

export interface AspectMetric {
  aspect: AspectCode;
  aspect_display: string;
  positive_count: number;
  negative_count: number;
  total_count: number;
  sentiment_ratio: number;
}

export interface SentimentDistribution {
  sentiment: OverallSentiment;
  count: number;
  percentage: number;
}

export interface EmotionDistribution {
  emotion: Emotion;
  count: number;
  percentage: number;
}

export interface PriorityIssue {
  aspect: AspectCode;
  aspect_display: string;
  severity: ReviewSeverity;
  complaint_count: number;
  frustration_count: number;
  average_rating: number | null;
  impact_score: number;
  key_drivers: string[];
  sample_evidence?: string | null;
}

export interface ActionableRecommendation {
  id: string;
  title: string;
  category: string;
  priority: string;
  description: string;
  target_aspect: string;
  expected_impact: string;
  suggested_action: string;
  supporting_review_count: number;
}

export interface SupportingReviewItem {
  review_id: string;
  quote: string;
  rating?: number | null;
  confidence?: number;
  status?: string;
}

export interface FeaturedProblem {
  hazard_key: string;
  title: string;
  category: string;
  severity: ReviewSeverity;
  priority_score: number;
  complaint_count: number;
  evidence_confidence: number;
  verification_status: string;
  urgency: string;
  potential_harm: string;
  recommended_action: string;
  supporting_review_ids: string[];
  supporting_reviews: SupportingReviewItem[];
  top_evidence_quote: string;
}

export interface CriticalFlagItem {
  review_id: string;
  hazard_key: string;
  title: string;
  severity: string;
  priority_score: number;
  evidence_confidence: number;
  verification_status: string;
  potential_harm: string;
  urgency: string;
  evidence_quote: string;
  rating?: number | null;
}

export interface DashboardData {
  dataset_id: string;
  dataset_name: string;
  total_reviews: number;
  average_rating: number | null;
  version?: number;
  is_stale?: boolean;
  quality_metrics: QualityMetrics;
  aspect_metrics: AspectMetric[];
  sentiment_distribution: SentimentDistribution[];
  emotion_distribution: EmotionDistribution[];
  top_strengths: string[];
  top_complaints: string[];
  priority_issues: PriorityIssue[];
  recommendations: ActionableRecommendation[];
  featured_problems?: FeaturedProblem[];
  critical_flags?: CriticalFlagItem[];
}

// --- Model evaluation ---

export interface AspectEvaluationMetric {
  label: string;
  aspect_display: string;
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

export interface ModelEvaluationResponse {
  overall_exact_match_ratio: number;
  hamming_loss: number;
  macro_precision: number;
  macro_recall: number;
  macro_f1: number;
  micro_f1: number;
  total_samples: number;
  aspect_metrics: AspectEvaluationMetric[];
  summary: string;
}

// --- Chatbot types ---

export interface ChatEvidenceItem {
  review_id: string;
  text: string;
  rating: number | null;
  aspects: string[];
  sentiment: string | null;
}

export interface ChatResponse {
  query: string;
  answer: string;
  intent: string;
  sql_or_search: string;
  total_matched: number;
  evidence: ChatEvidenceItem[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  sql_or_search?: string;
  total_matched?: number;
  evidence?: ChatEvidenceItem[];
}

// --- Canonical aspect display names ---

export const ASPECT_DISPLAY_NAMES: Record<AspectCode, string> = {
  pricing: 'Pricing',
  payment_issues: 'Payment Issues',
  charging_speed: 'Charging Speed',
  reliability: 'Reliability',
  waiting_time: 'Waiting Time',
  app_usability: 'App Usability',
  availability: 'Charger Availability',
  location_convenience: 'Location Convenience',
  improvement_suggestion: 'Improvement Suggestions',
  overall_experience: 'Overall Experience',
  customer_support: 'Customer Support',
};

// --- API functions ---

export const uploadFile = async (
  file: File,
  datasetName?: string,
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const params: Record<string, string> = {};
  if (datasetName) params.dataset_name = datasetName;

  const { data } = await api.post<UploadResponse>('/upload', formData, {
    params,
  });

  return data;
};

export const getDatasets = async (
  skip = 0,
  limit = 50,
): Promise<DatasetListResponse> => {
  const { data } = await api.get<DatasetListResponse>('/datasets', {
    params: { skip, limit },
  });

  return data;
};

export const getDataset = async (id: string): Promise<Dataset> => {
  const { data } = await api.get<Dataset>(
    `/datasets/${encodeURIComponent(id)}`,
  );
  return data;
};

export const getColumns = async (
  id: string,
): Promise<ColumnDetectionResponse> => {
  const { data } = await api.get<ColumnDetectionResponse>(
    `/datasets/${encodeURIComponent(id)}/columns`,
  );
  return data;
};

export const mapColumns = async (
  id: string,
  mapping: ColumnMappingRequest,
): Promise<Dataset> => {
  const { data } = await api.post<Dataset>(
    `/datasets/${encodeURIComponent(id)}/map-columns`,
    mapping,
  );
  return data;
};

export const startCleaning = async (
  id: string,
): Promise<CleaningReportResponse> => {
  const { data } = await api.post<CleaningReportResponse>(
    `/datasets/${encodeURIComponent(id)}/clean`,
  );
  return data;
};

export const getCleaningStatus = async (
  id: string,
): Promise<CleaningStatusResponse> => {
  const { data } = await api.get<CleaningStatusResponse>(
    `/datasets/${encodeURIComponent(id)}/cleaning-status`,
  );
  return data;
};

export const getCleaningReport = async (
  id: string,
): Promise<CleaningReportResponse> => {
  const { data } = await api.get<CleaningReportResponse>(
    `/datasets/${encodeURIComponent(id)}/cleaning-report`,
  );
  return data;
};

export interface ReviewQueryParams {
  page?: number;
  page_size?: number;
  limit?: number;
  is_duplicate?: boolean;
  is_low_info?: boolean;
  flags_only?: boolean;
   usable_only?: boolean;
  search?: string;
}

export const getReviews = async (
  id: string,
  params?: ReviewQueryParams,
): Promise<ReviewListResponse> => {
  const queryParams: Record<string, string | number | boolean> = {};

  if (params?.page !== undefined) queryParams.page = params.page;

  queryParams.page_size = params?.page_size ?? params?.limit ?? 20;

  if (params?.is_duplicate !== undefined) {
    queryParams.is_duplicate = params.is_duplicate;
  }

  if (params?.is_low_info !== undefined) {
    queryParams.is_low_info = params.is_low_info;
  }

  if (params?.flags_only !== undefined) {
    queryParams.flags_only = params.flags_only;
  }

  if (params?.usable_only !== undefined) {
  queryParams.usable_only = params.usable_only;
}

  if (params?.search) queryParams.search = params.search;

  const { data } = await api.get<ReviewListResponse>(
    `/datasets/${encodeURIComponent(id)}/reviews`,
    { params: queryParams },
  );

  return data;
};

export const updateReview = async (
  id: string,
  updates: ReviewUpdateRequest,
): Promise<Review> => {
  const { data } = await api.put<Review>(
    `/reviews/${encodeURIComponent(id)}`,
    updates,
  );

  return data;
};

export const startClassification = async (
  id: string,
  options?: { threshold?: number; skip_duplicates?: boolean },
): Promise<ClassificationResponse> => {
  const { data } = await api.post<ClassificationResponse>(
    `/datasets/${encodeURIComponent(id)}/classify`,
    null,
    {
      params: {
        threshold: options?.threshold ?? 0.35,
        skip_duplicates: options?.skip_duplicates ?? true,
      },
    },
  );

  return data;
};

export interface PredictionQueryParams {
  aspect?: AspectCode;
  polarity?: Polarity;
  is_human_corrected?: boolean;
  skip?: number;
  limit?: number;
}

export const getPredictions = async (
  id: string,
  params?: PredictionQueryParams,
): Promise<Prediction[]> => {
  const { data } = await api.get<Prediction[]>(
    `/datasets/${encodeURIComponent(id)}/predictions`,
    { params },
  );

  return data;
};

export const updatePrediction = async (
  id: number,
  updates: PredictionUpdateRequest,
): Promise<Prediction> => {
  const { data } = await api.put<Prediction>(
    `/predictions/${id}`,
    updates,
  );

  return data;
};

export const addPrediction = async (
  reviewId: string,
  prediction: PredictionUpdateRequest,
): Promise<Prediction> => {
  const { data } = await api.post<Prediction>(
    `/reviews/${encodeURIComponent(reviewId)}/predictions`,
    prediction,
  );

  return data;
};

export const getExplanation = async (
  reviewId: string,
  topK = 5,
): Promise<ExplainResponse> => {
  const { data } = await api.get<ExplainResponse>(
    `/reviews/${encodeURIComponent(reviewId)}/explain`,
    { params: { top_k: topK } },
  );

  return data;
};

export const startSentimentAnalysis = async (
  id: string,
  skipDuplicates = true,
): Promise<SentimentAnalysisResponse> => {
  const { data } = await api.post<SentimentAnalysisResponse>(
    `/datasets/${encodeURIComponent(id)}/analyze-sentiment`,
    null,
    { params: { skip_duplicates: skipDuplicates } },
  );

  return data;
};

export interface SentimentQueryParams {
  sentiment?: OverallSentiment;
  emotion?: Emotion;
  is_human_corrected?: boolean;
  skip?: number;
  limit?: number;
}

export const getSentiments = async (
  id: string,
  params?: SentimentQueryParams,
): Promise<SentimentResult[]> => {
  const { data } = await api.get<SentimentResult[]>(
    `/datasets/${encodeURIComponent(id)}/sentiments`,
    { params },
  );

  return data;
};

export const updateSentiment = async (
  id: number,
  updates: SentimentUpdateRequest,
): Promise<SentimentResult> => {
  const { data } = await api.put<SentimentResult>(
    `/sentiments/${id}`,
    updates,
  );

  return data;
};

export const getDashboard = async (
  id: string,
): Promise<DashboardData> => {
  const { data } = await api.get<DashboardData>(
    `/datasets/${encodeURIComponent(id)}/dashboard`,
  );

  return data;
};

export const exportAnalysisDataset = async (id: string): Promise<Blob> => {
  const { data } = await api.get<Blob>(
    `/datasets/${encodeURIComponent(id)}/analysis/export`,
    { responseType: 'blob' },
  );
  return data;
};

export const exportCleanedReviews = async (id: string): Promise<Blob> => {
  const { data } = await api.get<Blob>(
    `/datasets/${encodeURIComponent(id)}/clean/export`,
    {
      responseType: 'blob',
    },
  );

  return data;
};

export const exportResults = async (
  id: string,
  format: 'csv' | 'xlsx' = 'csv',
): Promise<Blob> => {
  const { data } = await api.get<Blob>(
    `/datasets/${encodeURIComponent(id)}/export`,
    {
      params: { format },
      responseType: 'blob',
    },
  );

  return data;
};

export const sendChatMessage = async (
  id: string,
  message: string,
): Promise<ChatResponse> => {
  const { data } = await api.post<ChatResponse>(
    `/datasets/${encodeURIComponent(id)}/chat`,
    { message },
  );

  return data;
};

export const getModelEvaluation = async (): Promise<ModelEvaluationResponse> => {
  const { data } = await api.get<ModelEvaluationResponse>('/model/evaluation');
  return data;
};

// --- Ingestion types & functions ---

export interface WebhookReviewInput {
  external_review_id: string;
  text: string;
  rating?: number | null;
  review_date?: string | null;
  source?: string;
  reviewer?: string | null;
}

export interface IngestionStatusResponse {
  connected: boolean;
  source_name: string;
  last_sync_time: string | null;
  total_received: number;
  total_processed: number;
  total_duplicates: number;
  total_failed: number;
  recent_syncs: Array<{
    id: number;
    source: string;
    status: string;
    received: number;
    inserted: number;
    duplicates: number;
    failed: number;
    timestamp: string | null;
  }>;
}

export interface IngestionResponse {
  status: string;
  total_received: number;
  total_inserted: number;
  total_duplicates: number;
  total_failed: number;
  dataset_id?: string | null;
  message: string;
}

export const getIngestionStatus = async (): Promise<IngestionStatusResponse> => {
  const { data } = await api.get<IngestionStatusResponse>('/ingestion/status');
  return data;
};

export const ingestReviews = async (
  reviews: WebhookReviewInput[],
  apiKey?: string,
  source = 'website_reviews',
  datasetId?: string,
): Promise<IngestionResponse> => {
  const headers: Record<string, string> = {};
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  const params: Record<string, string> = {};
  if (datasetId) {
    params.dataset_id = datasetId;
  }
  const { data } = await api.post<IngestionResponse>(
    '/ingestion/reviews',
    { source, reviews, api_key: apiKey },
    { headers, params },
  );
  return data;
};

export default api;
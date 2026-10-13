import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300000, // 5 min for large file processing
});

// --- Types ---
export interface Dataset {
  id: string;
  name: string;
  original_filename: string;
  upload_time: string;
  status: string;
  row_count: number;
  column_mapping: Record<string, string> | null;
  cleaning_stats: Record<string, any> | null;
}

export interface ColumnInfo {
  columns: string[];
  sample_rows: Record<string, any>[];
  suggested_mapping: Record<string, string>;
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
  flags: Array<{ type: string; message: string }>;
  is_duplicate: boolean;
  duplicate_of: string | null;
  language: string | null;
  is_low_info: boolean;
}

export interface Prediction {
  id: number;
  review_id: string;
  aspect: string;
  polarity: string;
  confidence: number;
  is_human_corrected: boolean;
  model_prediction: string;
  model_confidence: number;
}

export interface SentimentResult {
  id: number;
  review_id: string;
  overall_sentiment: string;
  sentiment_confidence: number;
  emotion: string;
  emotion_confidence: number;
  is_human_corrected: boolean;
}

export interface DashboardData {
  dataset: Dataset;
  total_reviews: number;
  cleaned_reviews: number;
  flagged_reviews: number;
  duplicate_reviews: number;
  low_info_reviews: number;
  sentiment_distribution: Record<string, number>;
  emotion_distribution: Record<string, number>;
  aspect_counts: Record<string, { positive: number; negative: number }>;
  rating_distribution: Record<string, number>;
  time_trends: Array<{ date: string; positive: number; negative: number; neutral: number }>;
  priority_issues: Array<{ aspect: string; count: number; severity: string; sample_reviews: string[] }>;
  recommendations: Array<{ title: string; description: string; evidence: string[]; priority: string }>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  evidence?: Array<{ review_id: string; text: string }>;
  stats?: Record<string, any>;
}

// --- API Functions ---
export const uploadFile = async (file: File): Promise<Dataset> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload', formData);
  return data;
};

export const getDatasets = async (): Promise<Dataset[]> => {
  const { data } = await api.get('/datasets');
  return data;
};

export const getDataset = async (id: string): Promise<Dataset> => {
  const { data } = await api.get(`/datasets/${id}`);
  return data;
};

export const getColumns = async (id: string): Promise<ColumnInfo> => {
  const { data } = await api.get(`/datasets/${id}/columns`);
  return data;
};

export const mapColumns = async (id: string, mapping: Record<string, string>): Promise<Dataset> => {
  const { data } = await api.post(`/datasets/${id}/map-columns`, mapping);
  return data;
};

export const getPreview = async (id: string, limit: number = 10): Promise<any[]> => {
  const { data } = await api.get(`/datasets/${id}/preview?limit=${limit}`);
  return data;
};

export const startCleaning = async (id: string): Promise<{ status: string }> => {
  const { data } = await api.post(`/datasets/${id}/clean`);
  return data;
};

export const getCleaningStatus = async (id: string): Promise<{ status: string; progress: number; stats: any }> => {
  const { data } = await api.get(`/datasets/${id}/cleaning-status`);
  return data;
};

export const getCleaningReport = async (id: string): Promise<any> => {
  const { data } = await api.get(`/datasets/${id}/cleaning-report`);
  return data;
};

export const getReviews = async (id: string, params?: { page?: number; limit?: number; flags_only?: boolean; search?: string }): Promise<{ reviews: Review[]; total: number; page: number; pages: number }> => {
  const { data } = await api.get(`/datasets/${id}/reviews`, { params });
  return data;
};

export const updateReview = async (id: string, updates: Partial<Review>): Promise<Review> => {
  const { data } = await api.put(`/reviews/${id}`, updates);
  return data;
};

export const startClassification = async (id: string): Promise<{ status: string }> => {
  const { data } = await api.post(`/datasets/${id}/classify`);
  return data;
};

export const getPredictions = async (id: string): Promise<Prediction[]> => {
  const { data } = await api.get(`/datasets/${id}/predictions`);
  return data;
};

export const updatePrediction = async (id: number, updates: Partial<Prediction>): Promise<Prediction> => {
  const { data } = await api.put(`/predictions/${id}`, updates);
  return data;
};

export const getExplanation = async (reviewId: string): Promise<any> => {
  const { data } = await api.get(`/reviews/${reviewId}/explain`);
  return data;
};

export const startSentimentAnalysis = async (id: string): Promise<{ status: string }> => {
  const { data } = await api.post(`/datasets/${id}/analyze-sentiment`);
  return data;
};

export const getSentiments = async (id: string): Promise<SentimentResult[]> => {
  const { data } = await api.get(`/datasets/${id}/sentiments`);
  return data;
};

export const updateSentiment = async (id: number, updates: Partial<SentimentResult>): Promise<SentimentResult> => {
  const { data } = await api.put(`/sentiments/${id}`, updates);
  return data;
};

export const getDashboard = async (id: string): Promise<DashboardData> => {
  const { data } = await api.get(`/datasets/${id}/dashboard`);
  return data;
};

export const exportResults = async (id: string, format: 'csv' | 'xlsx' = 'csv'): Promise<Blob> => {
  const { data } = await api.get(`/datasets/${id}/export`, {
    params: { format },
    responseType: 'blob',
  });
  return data;
};

export const sendChatMessage = async (id: string, message: string): Promise<ChatMessage> => {
  const { data } = await api.post(`/datasets/${id}/chat`, { message });
  return data;
};

export default api;

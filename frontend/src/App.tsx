import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import WelcomePage from './pages/WelcomePage';
import UploadPage from './pages/UploadPage';
import CleaningPage from './pages/CleaningPage';
import ClassificationPage from './pages/ClassificationPage';
import SentimentPage from './pages/SentimentPage';
import DashboardPage from './pages/DashboardPage';
import ChatbotPage from './pages/ChatbotPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route element={<Layout />}>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/dataset/:id/clean" element={<CleaningPage />} />
        <Route path="/dataset/:id/classify" element={<ClassificationPage />} />
        <Route path="/dataset/:id/sentiment" element={<SentimentPage />} />
        <Route path="/dataset/:id/dashboard" element={<DashboardPage />} />
        <Route path="/dataset/:id/chat" element={<ChatbotPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

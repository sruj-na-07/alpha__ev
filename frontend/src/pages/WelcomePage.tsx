import { useNavigate } from 'react-router-dom';
import { ArrowRight, Zap, Shield, BarChart3, Brain } from 'lucide-react';
import Alphi from '../components/Alphi';

export default function WelcomePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-navy-50 flex items-center justify-center p-6">
      <div className="max-w-4xl w-full text-center">
        {/* Hero */}
        <div className="mb-8">
          <Alphi mood="welcome" size="lg" />
        </div>

        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Alpha<span className="text-teal-600">EV</span>
        </h1>
        <p className="text-xl text-gray-500 mb-2 font-medium">
          Explainable AI-Powered EV Review Intelligence
        </p>
        <p className="text-gray-400 mb-10 max-w-xl mx-auto">
          Transform raw EV charging reviews into structured, evidence-based customer insights.
          Feed Alphi a dataset and watch the magic unfold! 🐱⚡
        </p>

        <button
          onClick={() => navigate('/upload')}
          className="btn-primary text-lg px-8 py-3.5 inline-flex items-center gap-2 group"
        >
          Feed Alphi a Dataset
          <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
        </button>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-16">
          {[
            { icon: Zap, title: 'Smart Cleaning', desc: 'Unicode, HTML, duplicates, language detection' },
            { icon: Brain, title: 'Aspect Classification', desc: '11 EV charging aspects with sentiment' },
            { icon: BarChart3, title: 'Live Dashboard', desc: 'Real-time stats from your actual data' },
            { icon: Shield, title: 'Explainable AI', desc: 'SHAP values and text evidence' },
          ].map((f, i) => (
            <div key={i} className="card text-left">
              <f.icon size={24} className="text-teal-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-1">{f.title}</h3>
              <p className="text-sm text-gray-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

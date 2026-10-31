import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Activity,
  BarChart3,
  BrainCircuit,
  Database,
  ShieldCheck,
  Sparkles,
  Zap,
  Gauge,
  MessageSquareText,
  Trash2,
} from 'lucide-react';
import { getDatasets, type Dataset } from '../api';

export default function WelcomePage() {
  const navigate = useNavigate();
  const [recentDatasets, setRecentDatasets] = useState<Dataset[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [hiddenDatasetIds, setHiddenDatasetIds] = useState<Array<Dataset['id']>>([]);

  useEffect(() => {
    getDatasets(0, 5)
      .then(res => {
        setRecentDatasets(res.datasets || []);
      })
      .catch(() => {})
      .finally(() => setLoadingDatasets(false));
  }, []);

  const getDestination = (ds: Dataset) => {
    switch (ds.status) {
      case 'uploaded':
        return `/dataset/${ds.id}/clean`;
      case 'cleaning':
      case 'cleaned':
        return `/dataset/${ds.id}/classify`;
      case 'classifying':
      case 'classified':
        return `/dataset/${ds.id}/sentiment`;
      case 'complete':
      default:
        return `/dataset/${ds.id}/dashboard`;
    }
  };

  const features = [
    {
      icon: Zap,
      title: 'Intelligent data cleaning',
      desc: 'Remove duplicates, noise and invalid reviews.',
      number: '01',
      tag: 'DATA QUALITY',
    },
    {
      icon: BrainCircuit,
      title: 'Aspect-based intelligence',
      desc: 'Classify feedback across 11 EV charging aspects.',
      number: '02',
      tag: '22 LABELS',
    },
    {
      icon: BarChart3,
      title: 'Review analytics',
      desc: 'See sentiment trends and recurring complaints.',
      number: '03',
      tag: 'INSIGHTS',
    },
    {
      icon: ShieldCheck,
      title: 'Explainable AI',
      desc: 'See why the model made each prediction.',
      number: '04',
      tag: 'TRANSPARENCY',
    },
  ];

  return (
    <main className="welcome-page">
      <div className="welcome-atmosphere welcome-atmosphere--sage" />
      <div className="welcome-atmosphere welcome-atmosphere--rose" />
      <div className="welcome-grain" />

      <div className="welcome-container">
        <header className="welcome-header">
          <a className="welcome-brand" href="/" aria-label="AlphaEV home">
            <span className="welcome-brand-mark"><Zap size={17} /></span>
            <span>alpha<span>ev</span></span>
          </a>
          <div className="welcome-header-label">
            <span className="welcome-status-dot" />
          <span>EXPLAINABLE INTELLEGENCE PLATFORM</span>
          </div>
          <div className="welcome-header-index">01 <i /> 06</div>
        </header>

        <section className="welcome-hero">
          <div className="welcome-hero-copy">
            <div className="welcome-eyebrow">
              <span className="welcome-eyebrow-line" />
              EXPLAINABLE AI FOR ELECTRIC MOBILITY
            </div>

            <h1 className="welcome-title">
              Every review<br />
              has a <em>signal.</em>
            </h1>

            <p className="welcome-subtitle">
              AlphaEV turns EV charging feedback into intelligence you can act on.
            </p>

            <p className="welcome-description">
              Understand what customers experience, identify where charging
              networks fall short, and uncover the issues that deserve attention —
              all through evidence-led review analysis.
            </p>

            <div className="welcome-actions">
              <button
                type="button"
                onClick={() => navigate('/upload')}
                className="welcome-primary-button"
              >
                Explore your dataset
                <span><ArrowRight size={17} /></span>
              </button>
              <div className="welcome-action-caption">
                <ShieldCheck size={14} />
                
              </div>
            </div>

            <div className="welcome-proof">
              <div className="welcome-proof-item">
                <strong>11</strong>
                <span>EV ASPECTS</span>
              </div>
              <div className="welcome-proof-divider" />
              <div className="welcome-proof-item">
                <strong>22</strong>
                <span>POLARITY LABELS</span>
              </div>
              <div className="welcome-proof-divider" />
              <div className="welcome-proof-item">
                <strong><Activity size={21} /></strong>
                <span>REVIEW SIGNALS</span>
              </div>
            </div>
          </div>

          <div className="welcome-visual" aria-label="EV review intelligence visual">
            <div className="welcome-visual-topline">
            </div>

            <div className="welcome-visual-canvas">
              <div className="welcome-visual-halo" />
              <svg className="welcome-flow-lines" viewBox="0 0 620 470" fill="none" aria-hidden="true">
                <path d="M-30 330C100 245 150 430 275 322S445 140 660 210" />
                <path d="M-20 355C105 275 170 445 295 342S455 170 650 240" />
                <path d="M-10 380C120 300 185 465 315 365S470 200 650 270" />
                <path d="M0 300C110 225 175 385 285 290S455 110 650 180" />
              </svg>

              <div className="welcome-visual-orbit welcome-visual-orbit--one" />
              <div className="welcome-visual-orbit welcome-visual-orbit--two" />

              <div className="welcome-car-art">
                <svg viewBox="0 0 620 300" role="img" aria-label="Minimal electric vehicle silhouette">
                  <defs>
                    <linearGradient id="carPaint" x1="90" y1="70" x2="520" y2="260" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#E7ECE5" />
                      <stop offset=".52" stopColor="#B9C7BC" />
                      <stop offset="1" stopColor="#879A8E" />
                    </linearGradient>
                    <linearGradient id="carGlass" x1="230" y1="70" x2="370" y2="170" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#DCE6E2" />
                      <stop offset="1" stopColor="#AABBB5" />
                    </linearGradient>
                    <filter id="carShadow" x="30" y="30" width="570" height="280" colorInterpolationFilters="sRGB">
                      <feGaussianBlur stdDeviation="12" />
                    </filter>
                  </defs>
                  <ellipse cx="316" cy="253" rx="230" ry="20" fill="#52675C" opacity=".16" filter="url(#carShadow)" />
                  <path d="M104 194L126 151C137 130 159 117 184 113L231 105L280 57C293 45 309 39 327 39H391C412 39 432 48 445 65L490 119L528 134C549 142 562 161 562 184V211C562 224 551 235 538 235H91C77 235 68 223 72 210L78 198C82 190 92 188 104 194Z" fill="url(#carPaint)" stroke="#71877A" strokeWidth="2.5" />
                  <path d="M214 111L286 60C297 52 310 47 325 47H389C405 47 419 54 430 67L470 116L214 111Z" fill="url(#carGlass)" stroke="#82978D" strokeWidth="2" />
                  <path d="M337 49L340 112" stroke="#91A49A" strokeWidth="2" />
                  <path d="M218 120L464 125" stroke="#F8F8F2" strokeOpacity=".55" strokeWidth="2" />
                  <path d="M96 190C174 176 445 176 544 190" stroke="#F8F8F2" strokeOpacity=".7" strokeWidth="2" />
                  <path d="M82 201C106 193 126 190 147 190" stroke="#F1E8DF" strokeWidth="7" strokeLinecap="round" />
                  <path d="M493 190C516 191 536 196 552 204" stroke="#D9B7AD" strokeWidth="7" strokeLinecap="round" />
                  <path d="M150 230C157 201 180 183 207 183C235 183 258 204 263 230" fill="#52645B" stroke="#E9EEE8" strokeWidth="7" />
                  <path d="M395 230C402 201 425 183 452 183C480 183 503 204 508 230" fill="#52645B" stroke="#E9EEE8" strokeWidth="7" />
                  <circle cx="207" cy="226" r="24" fill="#E7EBE5" />
                  <circle cx="207" cy="226" r="10" fill="#9AA99E" />
                  <circle cx="452" cy="226" r="24" fill="#E7EBE5" />
                  <circle cx="452" cy="226" r="10" fill="#9AA99E" />
                  <path d="M290 153H352" stroke="#F5F5EF" strokeOpacity=".7" strokeWidth="2" strokeLinecap="round" />
                  <path d="M310 142L300 155H310L304 169L324 149H313L319 142H310Z" fill="#758B7E" />
                </svg>
              </div>

              <div className="welcome-insight-card welcome-insight-card--top">
                <span className="welcome-insight-icon"><MessageSquareText size={15} /></span>
                <div>
                  <small>REVIEW SIGNAL</small>
                  <strong>Charging reliability</strong>
                </div>
                <span className="welcome-insight-indicator" />
              </div>

              <div className="welcome-insight-card welcome-insight-card--bottom">
                <div className="welcome-insight-chart">
                  <span /><span /><span /><span /><span /><span /><span />
                </div>
                <div>
                  <small>ASPECT INTELLIGENCE</small>
                  <strong>Patterns, not anecdotes.</strong>
                </div>
              </div>

              <div className="welcome-visual-coordinate">12°58' N &nbsp; 77°35' E</div>
              <div className="welcome-visual-index">ALPHAEV / 001</div>
            </div>

            <div className="welcome-visual-foot">
              <span>LISTEN</span><i /><span>CLASSIFY</span><i /><span>EXPLAIN</span><i /><span>ACT</span>
            </div>
          </div>
        </section>

        {!loadingDatasets && recentDatasets.some(ds => !hiddenDatasetIds.includes(ds.id)) && (
          <section className="welcome-datasets">
            <div className="welcome-section-heading">
              <div>
                <span className="welcome-section-eyebrow">CONTINUE YOUR WORK</span>
                <h2>Recent datasets</h2>
              </div>
              <span className="welcome-dataset-count">
                {recentDatasets.filter(ds => !hiddenDatasetIds.includes(ds.id)).length} {recentDatasets.filter(ds => !hiddenDatasetIds.includes(ds.id)).length === 1 ? 'DATASET' : 'DATASETS'}
              </span>
            </div>
            <div className="welcome-dataset-list">
              {recentDatasets.filter(ds => !hiddenDatasetIds.includes(ds.id)).map(ds => (
                <button
                  type="button"
                  key={ds.id}
                  onClick={() => navigate(getDestination(ds))}
                  className="welcome-dataset-row"
                >
                  <span className="welcome-dataset-icon"><Database size={17} /></span>
                  <span className="welcome-dataset-info">
                    <span className="welcome-dataset-name">{ds.name || ds.original_filename}</span>
                    <span className="welcome-dataset-meta">
                      {ds.row_count} reviews <span className="welcome-meta-dot">·</span>
                      <span className="capitalize">{ds.status}</span>
                    </span>
                  </span>
                  <span className="welcome-dataset-actions">
                    <span className="welcome-dataset-open">Open <ArrowRight size={14} /></span>
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label={`Hide ${ds.name || ds.original_filename} from recent datasets`}
                      className="welcome-dataset-hide"
                      onClick={event => {
                        event.stopPropagation();
                        setHiddenDatasetIds(current => [...current, ds.id]);
                      }}
                      onKeyDown={event => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          event.stopPropagation();
                          setHiddenDatasetIds(current => [...current, ds.id]);
                        }
                      }}
                    >
                      <Trash2 size={14} />
                      <span>Hide</span>
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        <section className="welcome-features">
          <div className="welcome-section-heading welcome-features-heading">
            <div>
              <span className="welcome-section-eyebrow">WHAT ALPHAEV DOES</span>
              <h2>PRIORITISES THE ISSUES | PROVIDES INSIGHTS</h2>
            </div>
          </div>
          <div className="welcome-feature-grid">
            {features.map(feature => (
              <article className="welcome-feature-card" key={feature.number}>
                <div className="welcome-feature-top">
                  <span className="welcome-feature-icon"><feature.icon size={19} /></span>
                  <span className="welcome-feature-number">{feature.number}</span>
                </div>
                <span className="welcome-feature-tag">{feature.tag}</span>
                <h3>{feature.title}</h3>
                <p>{feature.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <footer className="welcome-footer">
         
          <span className="welcome-footer-rule" />
          
        </footer>
      </div>
    </main>
  );
}

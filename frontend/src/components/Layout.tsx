
import { useState, useEffect } from 'react';
import { Outlet, NavLink, useParams } from 'react-router-dom';
import {
  BarChart3,
  Upload,
  Sparkles,
  Brain,
  MessageSquare,
  Home,
  Zap,
  Database,
} from 'lucide-react';
import { getDataset } from '../api';

const navItems = [
  { to: '/upload', icon: Upload, label: 'Upload' },
];

const datasetNavItems = [
  { suffix: '/clean', icon: Sparkles, label: 'Clean' },
  { suffix: '/classify', icon: Brain, label: 'Classify' },
  { suffix: '/sentiment', icon: Zap, label: 'Sentiment' },
  { suffix: '/dashboard', icon: BarChart3, label: 'Dashboard' },
  { suffix: '/chat', icon: MessageSquare, label: 'Chat' },
];

export default function Layout() {
  const { id } = useParams();
  const [datasetName, setDatasetName] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      getDataset(id)
        .then(ds => setDatasetName(ds.name || ds.original_filename))
        .catch(() => setDatasetName(null));
    } else {
      setDatasetName(null);
    }
  }, [id]);

  return (
    <div className="min-h-screen flex app-shell">
      <aside className="w-64 bg-white border-r border-gray-100 flex flex-col shadow-sm shrink-0 app-sidebar">

        <div className="p-5 border-b border-gray-100">
          <NavLink to="/" className="flex items-center gap-3 group">

            <div className="app-brand-mark">
              <Zap size={25} strokeWidth={2.4} />
            </div>

            <div>
              <h1 className="text-lg font-bold text-navy-950 group-hover:text-teal-600 transition-colors">
                AlphaEV
              </h1>
              <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">
                Review Intelligence
              </p>
            </div>

          </NavLink>
        </div>

        <nav className="flex-1 p-3 space-y-1">

          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-teal-50 text-teal-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <Home size={18} />
            Home
          </NavLink>

          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-teal-50 text-teal-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}

          {id && (
            <>
              <div className="pt-4 pb-2 px-3">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                  Active Dataset
                </p>

                {datasetName && (
                  <p
                    className="text-xs font-bold text-teal-800 truncate mt-0.5 flex items-center gap-1"
                    title={datasetName}
                  >
                    <Database size={11} className="shrink-0 text-teal-600" />
                    <span className="truncate">{datasetName}</span>
                  </p>
                )}
              </div>

              {datasetNavItems.map(item => (
                <NavLink
                  key={item.suffix}
                  to={`/dataset/${id}${item.suffix}`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-teal-50 text-teal-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`
                  }
                >
                  <item.icon size={18} />
                  {item.label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        <div className="p-4 border-t border-gray-100">
          <p className="text-xs text-gray-400 text-center">
            AlphaEV v1.0 · Built for EV insights
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-gray-50/50 app-main">
        <div className="max-w-7xl mx-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

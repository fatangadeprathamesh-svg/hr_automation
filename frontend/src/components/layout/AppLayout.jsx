import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import Footer from './Footer';
import { AlertCircle, X } from 'lucide-react';

export default function AppLayout({ title = 'Month-End HR Self-Audit Assistant', onPersonaChange = null }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [roleNotice, setRoleNotice] = useState(location.state?.roleNotice || null);

  useEffect(() => {
    if (location.state?.roleNotice) {
      setRoleNotice(location.state.roleNotice);
      // Clear React Router's state immediately so it does not persist across navigations
      navigate(location.pathname, { replace: true, state: {} });
      const timer = setTimeout(() => {
        setRoleNotice(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [location.pathname, location.state]);

  return (
    <div className="min-h-screen app-gradient-bg flex flex-col justify-between">
      {/* Desktop Left Rail Sidebar (fixed floating pill) */}
      <Sidebar />

      {/* Main Content Area: symmetrically padded on left and right for perfect viewport centering */}
      <div className="flex-1 min-w-0 flex flex-col justify-between py-6 px-4 sm:px-6 md:pl-28 md:pr-28 lg:pl-32 lg:pr-32 pb-24 md:pb-8 w-full">
        <div className="max-w-7xl w-full mx-auto">
          <TopBar title={title} onPersonaChange={onPersonaChange} />

          {/* Role access restriction banner */}
          {roleNotice && (
            <div className="mb-6 rounded-2xl border border-amber-500/30 bg-amber-500/10 dark:bg-amber-500/15 p-4 text-xs font-semibold text-amber-700 dark:text-amber-300 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
                <span>{roleNotice}</span>
              </div>
              <button
                type="button"
                onClick={() => setRoleNotice(null)}
                className="text-amber-600 dark:text-amber-400 hover:opacity-75 transition-opacity"
                aria-label="Dismiss notice"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <main>
            <Outlet />
          </main>
        </div>
        <div className="max-w-7xl w-full mx-auto mt-auto">
          <Footer />
        </div>
      </div>
    </div>
  );
}

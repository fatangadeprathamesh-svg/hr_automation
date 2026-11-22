import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { UserCheck, Users, Shield, ScrollText, LogOut, FileSearch, UploadCloud, Briefcase } from 'lucide-react';
import { logout } from '../../api';

export default function Sidebar() {
  const navigate = useNavigate();

  const navItems = [
    { to: '/employee', label: 'Employee', icon: UserCheck },
    { to: '/manager', label: 'Manager', icon: Users },
    { to: '/hr', label: 'HR Admin', icon: Shield },
    { to: '/duties', label: 'Duties', icon: Briefcase },
    { to: '/data-import', label: 'Import', icon: UploadCloud },
    { to: '/audit-log', label: 'Audit log', icon: ScrollText },
  ];

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <>
      {/* Desktop Left Icon-Rail Sidebar */}
      <aside
        className="hidden md:flex flex-col items-center justify-between w-20 py-6 glass-panel fixed left-4 top-4 bottom-4 rounded-3xl z-40"
        aria-label="Main navigation"
      >
        <div className="flex flex-col items-center gap-8 w-full">
          {/* Logo Brand Icon */}
          <div className="w-12 h-12 rounded-2xl bg-[var(--accent)] flex items-center justify-center text-[var(--accent-ink)] shadow-md shadow-[var(--accent-glow)]">
            <FileSearch className="w-6 h-6" />
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-col items-center gap-4 w-full px-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `group relative flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition-all duration-200 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none ${
                      isActive
                        ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-md shadow-[var(--accent-glow)]'
                        : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-white/60 dark:hover:bg-slate-800/60'
                    }`
                  }
                  title={item.label}
                  aria-label={item.label}
                >
                  <Icon className="w-6 h-6" />
                  <span className="text-[10px] font-medium mt-1 leading-none">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom Sign-out action */}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center justify-center w-14 h-14 rounded-2xl text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:outline-none"
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut className="w-5 h-5" />
          <span className="text-[10px] font-medium mt-1">Sign out</span>
        </button>
      </aside>

      {/* Mobile Bottom Tab Bar */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 glass-panel border-t border-slate-200 dark:border-slate-800 px-4 py-2 flex items-center justify-around z-50"
        aria-label="Mobile navigation"
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center py-1 px-2 rounded-xl text-xs font-medium transition-colors ${
                  isActive
                    ? 'text-[var(--accent-text)] font-semibold'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5 mb-0.5" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center justify-center py-1 px-2 rounded-xl text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-rose-600"
          aria-label="Sign out"
        >
          <LogOut className="w-5 h-5 mb-0.5" />
          <span>Exit</span>
        </button>
      </nav>
    </>
  );
}

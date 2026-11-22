import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import Footer from './Footer';

export default function AppLayout({ title = 'Month-End HR Self-Audit Assistant', onPersonaChange = null }) {
  return (
    <div className="min-h-screen app-gradient-bg flex">
      {/* Desktop Left Rail Sidebar */}
      <Sidebar />

      {/* Main Content Area - padded to avoid desktop rail and mobile bottom bar */}
      <div className="flex-1 md:pl-28 px-4 sm:px-6 lg:px-8 py-6 pb-24 md:pb-8 max-w-7xl mx-auto w-full flex flex-col justify-between">
        <div>
          <TopBar title={title} onPersonaChange={onPersonaChange} />
          <main>
            <Outlet />
          </main>
        </div>
        <Footer />
      </div>
    </div>
  );
}

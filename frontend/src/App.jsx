import React, { useState } from 'react';
import Navbar from './components/Navbar';
import EmployeePortal from './components/EmployeePortal';
import ManagerPortal from './components/ManagerPortal';
import HRPortal from './components/HRPortal';
import { PERSONAS, setPersona } from './api';

export default function App() {
  const [currentPersona, setCurrentPersona] = useState(PERSONAS.EMP001);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  function handleSelectPersona(p) {
    setPersona(p);
    setCurrentPersona(p);
    setRefreshTrigger((prev) => prev + 1);
  }

  function handleStateChange() {
    setRefreshTrigger((prev) => prev + 1);
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        currentPersona={currentPersona}
        onSelectPersona={handleSelectPersona}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentPersona.role === 'employee' && (
          <EmployeePortal
            key={`emp-${currentPersona.id}-${refreshTrigger}`}
            persona={currentPersona}
            onStateChange={handleStateChange}
          />
        )}

        {currentPersona.role === 'manager' && (
          <ManagerPortal
            key={`mgr-${currentPersona.id}-${refreshTrigger}`}
            persona={currentPersona}
            onStateChange={handleStateChange}
          />
        )}

        {currentPersona.role === 'hr_admin' && (
          <HRPortal
            key={`hr-${currentPersona.id}-${refreshTrigger}`}
            persona={currentPersona}
          />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        Month-End HR Self-Audit Assistant &copy; 2026. Deterministic rules &bull; Version-bound approvals &bull; Immutable audit ledger.
      </footer>
    </div>
  );
}

import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Shell } from './components/Shell';

const AckPage = lazy(() => import('./pages/AckPage').then((module) => ({ default: module.AckPage })));
const CompliancePage = lazy(() => import('./pages/CompliancePage').then((module) => ({ default: module.CompliancePage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const HeatCheckPage = lazy(() => import('./pages/HeatCheckPage').then((module) => ({ default: module.HeatCheckPage })));
const LedgerPage = lazy(() => import('./pages/LedgerPage').then((module) => ({ default: module.LedgerPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage })));
const ReplayPage = lazy(() => import('./pages/ReplayPage').then((module) => ({ default: module.ReplayPage })));
const RestPage = lazy(() => import('./pages/RestPage').then((module) => ({ default: module.RestPage })));
const RulebooksPage = lazy(() => import('./pages/RulebooksPage').then((module) => ({ default: module.RulebooksPage })));
const SetupPage = lazy(() => import('./pages/SetupPage').then((module) => ({ default: module.SetupPage })));
const VerifyPage = lazy(() => import('./pages/VerifyPage').then((module) => ({ default: module.VerifyPage })));

function PageLoading() {
  return <div className="page-wrap"><div className="loading-state">Loading ShiftShield page…</div></div>;
}

export function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route path="/rest/:siteCode" element={<RestPage />} />
        <Route path="/ack/:token" element={<AckPage />} />
        <Route path="/verify/:certificateId" element={<VerifyPage />} />
        <Route element={<Shell />}>
          <Route index element={<HeatCheckPage />} />
          <Route path="setup" element={<SetupPage />} />
          <Route path="setup/:siteId" element={<SetupPage />} />
          <Route path="dashboard/:siteId" element={<DashboardPage />} />
          <Route path="compliance/:siteId" element={<CompliancePage />} />
          <Route path="ledger/:siteId" element={<LedgerPage />} />
          <Route path="replay" element={<ReplayPage />} />
          <Route path="demo" element={<Navigate to="/replay?auto=1" replace />} />
          <Route path="rulebooks" element={<RulebooksPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

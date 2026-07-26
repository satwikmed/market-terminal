import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { BriefPage } from './pages/BriefPage';
import { CompanyPage } from './pages/CompanyPage';
import { ComparePage } from './pages/ComparePage';
import { HomePage } from './pages/HomePage';
import { LandingPage } from './pages/LandingPage';
import { MacroPage } from './pages/MacroPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { RiskPage } from './pages/RiskPage';
import { ScreenerPage } from './pages/ScreenerPage';
import { StatusPage } from './pages/StatusPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route index element={<LandingPage />} />
        <Route element={<Layout />}>
          <Route path="map" element={<HomePage />} />
          <Route path="company/:ticker" element={<CompanyPage />} />
          <Route path="screener" element={<ScreenerPage />} />
          <Route path="risk" element={<RiskPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="macro" element={<MacroPage />} />
          <Route path="brief" element={<BriefPage />} />
          <Route path="data" element={<StatusPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

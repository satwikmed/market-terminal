import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { BriefPage } from './pages/BriefPage';
import { CompanyPage } from './pages/CompanyPage';
import { HomePage } from './pages/HomePage';
import { MacroPage } from './pages/MacroPage';
import { StatusPage } from './pages/StatusPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="company/:ticker" element={<CompanyPage />} />
          <Route path="macro" element={<MacroPage />} />
          <Route path="brief" element={<BriefPage />} />
          <Route path="data" element={<StatusPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

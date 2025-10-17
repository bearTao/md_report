import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import TemplateList from './pages/templates/TemplateList';
import TemplateEdit from './pages/templates/TemplateEdit';
import TemplateEditSimple from './pages/templates/TemplateEditSimple';
import GenerateReport from './pages/generate/GenerateReport';
import ReportProgress from './pages/generate/ReportProgress';
import ReportPreview from './pages/reports/ReportPreview';
import AISettings from './pages/settings/AISettings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/templates" replace />} />
              <Route path="templates" element={<TemplateList />} />
              <Route path="templates/:templateId/edit-simple" element={<TemplateEditSimple />} />
              <Route path="templates/:templateId/edit" element={<TemplateEdit />} />
              <Route path="generate" element={<GenerateReport />} />
              <Route path="generate/:taskId" element={<ReportProgress />} />
              <Route path="reports/:reportId" element={<ReportPreview />} />
              <Route path="settings/ai" element={<AISettings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;

import { createBrowserRouter, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Home from './pages/Home';
import ChatPage from './pages/ChatPage';
import StockPage from './pages/StockPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'stocks',
        element: <StockPage />,
      },
      {
        path: 'stocks/:code',
        element: <StockPage />,
      },
      {
        path: 'analysis',
        element: <div>分析报告页面</div>,
      },
      {
        path: 'chat',
        element: <ChatPage />,
      },
      {
        path: 'settings',
        element: <div>设置页面</div>,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

export default router;

import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { RequireRole } from '@/components/RequireRole'
import LoginPage from '@/pages/LoginPage'
import FirmsPage from '@/pages/platform/FirmsPage'
import CompaniesPage from '@/pages/firm/CompaniesPage'
import PaymentHeadsPage from '@/pages/firm/PaymentHeadsPage'
import TeamPage from '@/pages/firm/TeamPage'
import UploadPage from '@/pages/company/UploadPage'
import ManualTransactionPage from '@/pages/company/ManualTransactionPage'
import TransactionHistoryPage from '@/pages/company/TransactionHistoryPage'
import CompanyReportsPage from '@/pages/company/ReportsPage'
import QueuePage from '@/pages/accountant/QueuePage'
import TransactionDetailPage from '@/pages/accountant/TransactionDetailPage'
import ReportsUploadPage from '@/pages/accountant/ReportsUploadPage'
import DashboardPage from '@/pages/DashboardPage'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <Navigate to="/login" replace /> },
  {
    element: (
      <RequireRole roles={['platform_admin']}>
        <AppLayout />
      </RequireRole>
    ),
    children: [
      { path: '/platform/firms', element: <FirmsPage /> },
    ],
  },
  {
    element: (
      <RequireRole roles={['firm_admin']}>
        <AppLayout />
      </RequireRole>
    ),
    children: [
      { path: '/firm/companies', element: <CompaniesPage /> },
      { path: '/firm/companies/:companyId/payment-heads', element: <PaymentHeadsPage /> },
      { path: '/firm/team', element: <TeamPage /> },
    ],
  },
  {
    element: (
      <RequireRole roles={['company_user']}>
        <AppLayout />
      </RequireRole>
    ),
    children: [
      { path: '/company/upload', element: <UploadPage /> },
      { path: '/company/manual', element: <ManualTransactionPage /> },
      { path: '/company/transactions', element: <TransactionHistoryPage /> },
      { path: '/company/reports', element: <CompanyReportsPage /> },
    ],
  },
  {
    element: (
      <RequireRole roles={['accountant']}>
        <AppLayout />
      </RequireRole>
    ),
    children: [
      { path: '/accountant/queue', element: <QueuePage /> },
      { path: '/accountant/transactions/:id', element: <TransactionDetailPage /> },
      { path: '/accountant/reports', element: <ReportsUploadPage /> },
    ],
  },
  {
    element: (
      <RequireRole roles={['platform_admin', 'firm_admin', 'accountant', 'company_user']}>
        <AppLayout />
      </RequireRole>
    ),
    children: [
      { path: '/dashboard', element: <DashboardPage /> },
    ],
  },
])

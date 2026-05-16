import { Download } from 'lucide-react'
import { useReports } from '@/hooks/useReports'
import { useAuthStore } from '@/store/authStore'

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function ReportsPage() {
  const user = useAuthStore(s => s.user)
  const companyId = user?.company_id ?? undefined

  const { data: reports, isLoading, isError } = useReports(companyId)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-500 mt-1">MIS reports prepared by your accountant.</p>
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Loading…</p>}

      {isError && <p className="text-red-500 text-sm">Failed to load reports. Please refresh.</p>}

      {!isLoading && !isError && reports?.length === 0 && (
        <div className="flex items-center justify-center py-16 text-center">
          <p className="text-gray-500">No reports available yet.</p>
        </div>
      )}

      {!isLoading && !isError && reports && reports.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Title</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Filename</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Uploaded</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Download</th>
              </tr>
            </thead>
            <tbody>
              {reports.map(report => (
                <tr key={report.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{report.title}</td>
                  <td className="px-4 py-3 text-gray-600">{report.original_name}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(report.created_at)}</td>
                  <td className="px-4 py-3">
                    <a
                      href={`/api/reports/${report.id}/file`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <Download className="h-4 w-4" />
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

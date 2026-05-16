import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useCompanies } from '@/hooks/useOnboarding'
import { useReports } from '@/hooks/useReports'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'

async function downloadReport(reportId: string, filename: string) {
  const res = await api.get(`/reports/${reportId}/file`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function ReportsUploadPage() {
  const qc = useQueryClient()
  const { data: companies = [] } = useCompanies()
  const { data: reports = [], isLoading: reportsLoading } = useReports()

  const [companyId, setCompanyId] = useState('')
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!file || !companyId || !title.trim()) {
      toast.error('Please fill in all fields and select a file')
      return
    }
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', title.trim())
    fd.append('company_id', companyId)
    setUploading(true)
    try {
      await api.post('/reports', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success('Report uploaded')
      setTitle('')
      setFile(null)
      setCompanyId('')
      if (fileRef.current) fileRef.current.value = ''
      qc.invalidateQueries({ queryKey: ['reports'] })
    } catch (err: unknown) {
      toast.error((err as any).response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Upload Reports</h1>

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div>
          <Label>Company</Label>
          <Select value={companyId} onChange={e => setCompanyId(e.target.value)}>
            <option value="">— select company —</option>
            {companies.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Report Title</Label>
          <Input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. April 2024 MIS"
          />
        </div>
        <div>
          <Label>File</Label>
          <input
            ref={fileRef}
            type="file"
            className="block mt-1 text-sm"
            onChange={e => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <Button onClick={handleUpload} disabled={uploading}>
          {uploading ? 'Uploading…' : 'Upload Report'}
        </Button>
      </div>

      <h2 className="text-lg font-semibold mt-8 mb-4">Recent Reports</h2>
      {reportsLoading && <p className="text-gray-500">Loading...</p>}
      {!reportsLoading && reports.length === 0 && (
        <p className="text-gray-500">No reports uploaded yet.</p>
      )}
      {reports.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 divide-y">
          {reports.map(r => (
            <div key={r.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="font-medium">{r.title}</p>
                <p className="text-sm text-gray-500">{r.original_name} · {r.created_at.slice(0, 10)}</p>
              </div>
              <button
                onClick={() => downloadReport(r.id, r.original_name)}
                className="text-sm text-blue-600 hover:underline"
              >
                Download
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

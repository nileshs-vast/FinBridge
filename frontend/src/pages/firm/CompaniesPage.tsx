import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useCompanies, useCreateCompany } from '@/hooks/useOnboarding'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'

export default function CompaniesPage() {
  const navigate = useNavigate()
  const { data: companies = [], isLoading } = useCompanies()
  const createCompany = useCreateCompany()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [businessType, setBusinessType] = useState<'manufacturing' | 'it' | 'services'>('it')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')

  const handleCreate = () => {
    if (!name.trim() || !adminEmail.trim() || !adminPassword.trim()) {
      toast.error('All fields are required')
      return
    }
    createCompany.mutate(
      { name: name.trim(), business_type: businessType, admin_email: adminEmail.trim(), admin_password: adminPassword },
      {
        onSuccess: () => {
          toast.success('Company created — payment head template applied automatically')
          setOpen(false)
          setName(''); setAdminEmail(''); setAdminPassword('')
        },
        onError: (err: unknown) => {
          toast.error((err as any).response?.data?.detail || 'Failed to create company')
        },
      }
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Companies</h1>
        <Button onClick={() => setOpen(true)}>+ Create Company</Button>
      </div>

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {!isLoading && companies.length === 0 && (
        <p className="text-gray-500">No companies yet.</p>
      )}

      {companies.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Business Type</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {companies.map(c => (
                <tr key={c.id}>
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 capitalize text-gray-600">{c.business_type}</td>
                  <td className="px-4 py-3 text-gray-500">{c.created_at.slice(0, 10)}</td>
                  <td className="px-4 py-3">
                    <button
                      className="text-blue-600 hover:underline text-sm"
                      onClick={() => navigate(`/firm/companies/${c.id}/payment-heads`)}
                    >
                      Payment Heads
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Create Company</h2>
            <div>
              <Label>Company Name</Label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="Acme Ltd" />
            </div>
            <div>
              <Label>Business Type</Label>
              <Select value={businessType} onChange={e => setBusinessType(e.target.value as typeof businessType)}>
                <option value="it">IT</option>
                <option value="manufacturing">Manufacturing</option>
                <option value="services">Services</option>
              </Select>
            </div>
            <div>
              <Label>Admin Email</Label>
              <Input type="email" value={adminEmail} onChange={e => setAdminEmail(e.target.value)} />
            </div>
            <div>
              <Label>Admin Password</Label>
              <Input type="password" value={adminPassword} onChange={e => setAdminPassword(e.target.value)} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setOpen(false)} disabled={createCompany.isPending}>Cancel</Button>
              <Button onClick={handleCreate} disabled={createCompany.isPending}>
                {createCompany.isPending ? 'Creating…' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { toast } from 'sonner'
import { useFirms, useCreateFirm } from '@/hooks/useOnboarding'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function FirmsPage() {
  const { data: firms = [], isLoading } = useFirms()
  const createFirm = useCreateFirm()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')

  const handleCreate = () => {
    if (!name.trim() || !adminEmail.trim() || !adminPassword.trim()) {
      toast.error('All fields are required')
      return
    }
    createFirm.mutate(
      { name: name.trim(), admin_email: adminEmail.trim(), admin_password: adminPassword },
      {
        onSuccess: () => {
          toast.success('Firm created')
          setOpen(false)
          setName(''); setAdminEmail(''); setAdminPassword('')
        },
        onError: (err: unknown) => {
          toast.error((err as any).response?.data?.detail || 'Failed to create firm')
        },
      }
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Firms</h1>
        <Button onClick={() => setOpen(true)}>+ Create Firm</Button>
      </div>

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {!isLoading && firms.length === 0 && (
        <p className="text-gray-500">No firms yet.</p>
      )}

      {firms.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {firms.map(f => (
                <tr key={f.id}>
                  <td className="px-4 py-3 font-medium">{f.name}</td>
                  <td className="px-4 py-3 text-gray-500">{f.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Create Firm</h2>
            <div>
              <Label>Firm Name</Label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="Acme Accounting" />
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
              <Button variant="outline" onClick={() => setOpen(false)} disabled={createFirm.isPending}>Cancel</Button>
              <Button onClick={handleCreate} disabled={createFirm.isPending}>
                {createFirm.isPending ? 'Creating…' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

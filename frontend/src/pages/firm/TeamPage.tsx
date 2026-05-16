import { useState } from 'react'
import { toast } from 'sonner'
import { useUsers, useCreateUser } from '@/hooks/useOnboarding'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function TeamPage() {
  const { data: users = [], isLoading } = useUsers('accountant')
  const createUser = useCreateUser()

  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleAdd = () => {
    if (!email.trim() || !password.trim()) { toast.error('Email and password required'); return }
    createUser.mutate(
      { role: 'accountant', email: email.trim(), password },
      {
        onSuccess: () => {
          toast.success('Accountant added')
          setOpen(false)
          setEmail(''); setPassword('')
        },
        onError: (err: unknown) => {
          toast.error((err as any).response?.data?.detail || 'Failed to create user')
        },
      }
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Team</h1>
        <Button onClick={() => setOpen(true)}>+ Add Accountant</Button>
      </div>

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {!isLoading && users.length === 0 && (
        <p className="text-gray-500">No accountants yet.</p>
      )}

      {users.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Role</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.map(u => (
                <tr key={u.id}>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3 capitalize text-gray-600">{u.role}</td>
                  <td className="px-4 py-3 text-gray-500">{u.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Add Accountant</h2>
            <div>
              <Label>Email</Label>
              <Input type="email" value={email} onChange={e => setEmail(e.target.value)} />
            </div>
            <div>
              <Label>Password</Label>
              <Input type="password" value={password} onChange={e => setPassword(e.target.value)} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setOpen(false)} disabled={createUser.isPending}>Cancel</Button>
              <Button onClick={handleAdd} disabled={createUser.isPending}>
                {createUser.isPending ? 'Adding…' : 'Add'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

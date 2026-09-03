import { useCallback, useEffect, useState, type FormEvent } from 'react'
import * as orgApi from '../api/organizations'
import { ApiError, firstApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { useOrganizations } from '../organizations/useOrganizations'
import type { AssignableRole, OrganizationMember } from '../types/organization'
import { CreateOrganizationForm } from './CreateOrganizationForm'

function RenameForm({ id, name }: { id: number; name: string }) {
  const { renameOrganization } = useOrganizations()
  const [value, setValue] = useState(name)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSaving(true)
    try {
      await renameOrganization(id, value.trim())
    } catch (err) {
      setError(
        (err instanceof ApiError && firstApiError(err.data)) ||
          'Could not rename the organization.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="stacked-form" onSubmit={handleSubmit} noValidate>
      <label>
        Organization name
        <input
          name="organization-name"
          required
          minLength={2}
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </label>
      {error && (
        <p role="alert" className="auth-error">
          {error}
        </p>
      )}
      <button type="submit" className="btn btn--primary" disabled={saving || value.trim() === name}>
        {saving ? 'Saving…' : 'Save name'}
      </button>
    </form>
  )
}

function Members({ organizationId, canManage }: { organizationId: number; canManage: boolean }) {
  const { authorizedRequest } = useAuth()
  const [members, setMembers] = useState<OrganizationMember[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyUser, setBusyUser] = useState<number | null>(null)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<AssignableRole>('member')
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    try {
      const list = await orgApi.listMembers(authorizedRequest, organizationId)
      setMembers(list)
      setFailed(false)
    } catch {
      setFailed(true)
    }
  }, [authorizedRequest, organizationId])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const list = await orgApi.listMembers(authorizedRequest, organizationId)
        if (!cancelled) {
          setMembers(list)
          setFailed(false)
        }
      } catch {
        if (!cancelled) setFailed(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [authorizedRequest, organizationId])

  async function run<T>(userId: number, action: () => Promise<T>) {
    setError(null)
    setBusyUser(userId)
    try {
      await action()
      await load()
    } catch (err) {
      setError(
        (err instanceof ApiError && firstApiError(err.data)) || 'That action was not allowed.',
      )
    } finally {
      setBusyUser(null)
    }
  }

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setAdding(true)
    try {
      await orgApi.addMember(authorizedRequest, organizationId, email.trim(), role)
      setEmail('')
      setRole('member')
      await load()
    } catch (err) {
      setError((err instanceof ApiError && firstApiError(err.data)) || 'Could not add that member.')
    } finally {
      setAdding(false)
    }
  }

  if (failed) {
    return (
      <p role="alert" className="auth-error">
        Could not load members.{' '}
        <button type="button" className="link-button" onClick={() => void load()}>
          Retry
        </button>
      </p>
    )
  }
  if (members === null) {
    return <p className="section__status">Loading members…</p>
  }

  return (
    <div>
      {error && (
        <p role="alert" className="auth-error">
          {error}
        </p>
      )}
      <ul className="member-list">
        {members.map(({ user, role: memberRole }) => {
          const isOwner = memberRole === 'owner'
          return (
            <li key={user.id} className="member-list__row">
              <div>
                <strong>{user.email}</strong>
                <div className="member-list__meta">{memberRole}</div>
              </div>
              {canManage && !isOwner && (
                <div className="member-list__actions">
                  <label className="visually-hidden" htmlFor={`role-${user.id}`}>
                    Role for {user.email}
                  </label>
                  <select
                    id={`role-${user.id}`}
                    value={memberRole}
                    disabled={busyUser === user.id}
                    onChange={(event) =>
                      void run(user.id, () =>
                        orgApi.changeMemberRole(
                          authorizedRequest,
                          organizationId,
                          user.id,
                          event.target.value as AssignableRole,
                        ),
                      )
                    }
                  >
                    <option value="admin">admin</option>
                    <option value="member">member</option>
                  </select>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={busyUser === user.id}
                    onClick={() => {
                      if (window.confirm(`Remove ${user.email} from this organization?`)) {
                        void run(user.id, () =>
                          orgApi.removeMember(authorizedRequest, organizationId, user.id),
                        )
                      }
                    }}
                  >
                    Remove
                  </button>
                </div>
              )}
            </li>
          )
        })}
      </ul>

      {canManage && (
        <form className="inline-form" onSubmit={handleAdd} noValidate>
          <label>
            Add member by email
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Role
            <select
              value={role}
              onChange={(event) => setRole(event.target.value as AssignableRole)}
            >
              <option value="member">member</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <button type="submit" className="btn btn--primary" disabled={adding}>
            {adding ? 'Adding…' : 'Add member'}
          </button>
        </form>
      )}
    </div>
  )
}

function DangerZone({ id, name }: { id: number; name: string }) {
  const { deleteOrganization } = useOrganizations()
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (
      !window.confirm(
        `Delete "${name}"? This permanently removes its customers, orders and invoices.`,
      )
    ) {
      return
    }
    setError(null)
    setDeleting(true)
    try {
      await deleteOrganization(id)
    } catch (err) {
      setError(
        (err instanceof ApiError && firstApiError(err.data)) ||
          'Could not delete the organization.',
      )
      setDeleting(false)
    }
  }

  return (
    <section className="card card--danger" aria-label="Danger zone">
      <h3>Danger zone</h3>
      <p className="section__status">
        Deleting an organization cannot be undone. Only the owner can do this.
      </p>
      {error && (
        <p role="alert" className="auth-error">
          {error}
        </p>
      )}
      <button
        type="button"
        className="btn btn--danger"
        disabled={deleting}
        onClick={() => void handleDelete()}
      >
        {deleting ? 'Deleting…' : 'Delete organization'}
      </button>
    </section>
  )
}

export function OrganizationSettings() {
  const { currentOrganization, organizations } = useOrganizations()
  if (!currentOrganization) return null

  const role = currentOrganization.role
  const canManage = role === 'owner' || role === 'admin'
  const isOwner = role === 'owner'

  return (
    <div className="settings">
      <section className="card" aria-label="Organization details">
        <h3>Organization</h3>
        {canManage ? (
          <RenameForm id={currentOrganization.id} name={currentOrganization.name} />
        ) : (
          <p className="section__status">Only owners and admins can change the name.</p>
        )}
      </section>

      <section className="card" aria-label="Members">
        <h3>Members</h3>
        <Members organizationId={currentOrganization.id} canManage={canManage} />
      </section>

      <section className="card" aria-label="Your organizations">
        <h3>Your organizations</h3>
        <ul className="plain-list">
          {organizations.map((org) => (
            <li key={org.id}>
              <span>{org.name}</span>
              <span className="role-pill">{org.role}</span>
            </li>
          ))}
        </ul>
        <CreateOrganizationForm />
      </section>

      {isOwner && <DangerZone id={currentOrganization.id} name={currentOrganization.name} />}
    </div>
  )
}

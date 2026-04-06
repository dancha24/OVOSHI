import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { patchProfile, getOkLedger, postOkLedger } from '../api/client'
import { useAuth, canAccessLeaderCabinet, canManageClanPoints, canManageSettings } from '../hooks/useAuth'
import LedgerTable from '../components/LedgerTable'

export default function Profile() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState({ nickname: '', uid: '', birth_date: '' })
  const [saving, setSaving] = useState(false)
  const [ledger, setLedger] = useState([])
  const [ledgerLoading, setLedgerLoading] = useState(true)
  const [ledgerErr, setLedgerErr] = useState('')
  const [okAmount, setOkAmount] = useState('')
  const [okComment, setOkComment] = useState('')
  const [okBusy, setOkBusy] = useState(false)
  const [okFormErr, setOkFormErr] = useState('')

  useEffect(() => {
    if (user?.profile) {
      const bd = user.profile.birth_date
      setForm({
        nickname: user.profile.nickname || '',
        uid: user.profile.uid || '',
        birth_date: typeof bd === 'string' ? bd.slice(0, 10) : '',
      })
    }
  }, [user])

  useEffect(() => {
    if (!user?.id) return
    setLedgerLoading(true)
    setLedgerErr('')
    getOkLedger(user.id)
      .then(setLedger)
      .catch((e) => setLedgerErr(e.response?.data?.detail || e.message || 'Ошибка'))
      .finally(() => setLedgerLoading(false))
  }, [user?.id])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!user) return
    const uidAllowed =
      user.can_change_own_uid === true ||
      (user.can_change_own_uid === undefined &&
        (user.role === 'leader' || user.is_superuser || user.is_staff))
    setSaving(true)
    try {
      const payload = {
        nickname: form.nickname.trim().slice(0, 50),
        birth_date: form.birth_date || null,
      }
      if (uidAllowed) {
        payload.uid = form.uid.trim()
      }
      const updated = await patchProfile(payload)
      setUser(updated)
    } finally {
      setSaving(false)
    }
  }

  const submitOwnOk = async (e) => {
    e.preventDefault()
    if (!user?.id || !canManageClanPoints(user)) return
    const amount = parseInt(String(okAmount).trim(), 10)
    if (Number.isNaN(amount) || amount === 0) {
      setOkFormErr('Укажите ненулевую целую сумму.')
      return
    }
    const comment = okComment.trim()
    if (!comment) {
      setOkFormErr('Укажите комментарий.')
      return
    }
    setOkBusy(true)
    setOkFormErr('')
    try {
      const res = await postOkLedger(user.id, { amount, comment })
      if (res.participant) {
        setUser((u) => (u ? { ...u, clan_points: res.participant.clan_points } : u))
      }
      const rows = await getOkLedger(user.id)
      setLedger(rows)
      setOkAmount('')
      setOkComment('')
    } catch (err) {
      const d = err.response?.data
      setOkFormErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : err.message || 'Ошибка')
    } finally {
      setOkBusy(false)
    }
  }

  if (!user) return null

  const canEditUid =
    user.can_change_own_uid === true ||
    (user.can_change_own_uid === undefined &&
      (user.role === 'leader' || user.is_superuser || user.is_staff))

  return (
    <div className="mx-auto" style={{ maxWidth: 720 }}>
      <h2 className="h4 mb-4">Мой профиль</h2>

      <div className="card vk-card border-0 shadow-none mb-4">
        <div className="card-body">
          <dl className="row mb-0 small">
            <dt className="col-sm-4">ID участника</dt>
            <dd className="col-sm-8">{user.id}</dd>
            <dt className="col-sm-4">Роль</dt>
            <dd className="col-sm-8">{user.role_display}</dd>
            <dt className="col-sm-4">ОК</dt>
            <dd className="col-sm-8">{user.clan_points ?? '—'}</dd>
            <dt className="col-sm-4">Дата рождения</dt>
            <dd className="col-sm-8">
              {user.profile?.birth_date
                ? new Date(user.profile.birth_date).toLocaleDateString('ru-RU')
                : '—'}
            </dd>
            <dt className="col-sm-4">Возраст</dt>
            <dd className="col-sm-8">
              {user.profile?.age_years != null ? `${user.profile.age_years} лет` : '—'}
            </dd>
          </dl>
        </div>
      </div>

      {canAccessLeaderCabinet(user) && (
        <div className="card vk-card border-0 shadow-none mb-4">
          <div className="card-header vk-card-header fw-semibold">Кабинет лидера</div>
          <div className="card-body">
            <ul className="list-unstyled mb-0">
              {canManageSettings(user) && (
                <li className="mb-2">
                  <Link to="/leader/settings">Настройки сайта</Link>
                </li>
              )}
              <li className="mb-2">
                <Link to="/leader/applications">Заявки в клан</Link>
              </li>
              <li>
                <Link to="/leader/participants">Участники</Link>
              </li>
              <li>
                <Link to="/leader/lots">Лоты магазина</Link>
              </li>
            </ul>
          </div>
        </div>
      )}

      <div className="card vk-card border-0 shadow-none mb-4">
        <div className="card-header vk-card-header fw-semibold">История ОК</div>
        <div className="card-body">
          {ledgerLoading ? (
            <div className="d-flex align-items-center gap-2 text-muted small">
              <span className="spinner-border spinner-border-sm" role="status" />
              Загрузка…
            </div>
          ) : null}
          {ledgerErr ? <div className="alert alert-danger py-2 small mb-3">{ledgerErr}</div> : null}
          {!ledgerLoading && !ledgerErr ? <LedgerTable rows={ledger} /> : null}
          {canManageClanPoints(user) && (
            <form onSubmit={submitOwnOk} className="mt-3 pt-3 border-top">
              <p className="small fw-semibold text-secondary mb-3">Начислить / списать себе ОК</p>
              <div className="row g-2">
                <div className="col-md-4">
                  <label className="form-label small mb-1">Сумма ОК</label>
                  <input
                    type="number"
                    className="form-control form-control-sm"
                    value={okAmount}
                    onChange={(e) => setOkAmount(e.target.value)}
                    placeholder="±число"
                  />
                </div>
                <div className="col-md-8">
                  <label className="form-label small mb-1">Комментарий</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={okComment}
                    onChange={(e) => setOkComment(e.target.value)}
                  />
                </div>
              </div>
              {okFormErr ? <div className="text-danger small mt-2">{okFormErr}</div> : null}
              <button type="submit" className="btn btn-primary btn-sm mt-3" disabled={okBusy}>
                {okBusy ? 'Запись…' : 'Записать в журнал'}
              </button>
            </form>
          )}
        </div>
      </div>

      <div className="card vk-card border-0 shadow-none">
        <div className="card-header vk-card-header fw-semibold">Никнейм, UID, дата рождения</div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Никнейм (до 50 символов)</label>
              <input
                type="text"
                className="form-control"
                maxLength={50}
                value={form.nickname}
                onChange={(e) => setForm((f) => ({ ...f, nickname: e.target.value }))}
              />
            </div>
            <div className="mb-3">
              <label className="form-label">UID</label>
              <input
                type="text"
                className="form-control"
                value={form.uid}
                onChange={(e) => setForm((f) => ({ ...f, uid: e.target.value }))}
                readOnly={!canEditUid}
                title={!canEditUid ? 'Меняет лидер в разделе «Участники»' : undefined}
              />
              {!canEditUid ? (
                <p className="form-text small text-muted mb-0">
                  Игровой UID для вашей роли меняет лидер в кабинете «Участники».
                </p>
              ) : null}
            </div>
            <div className="mb-3">
              <label className="form-label">Дата рождения</label>
              <input
                type="date"
                className="form-control"
                value={form.birth_date}
                onChange={(e) => setForm((f) => ({ ...f, birth_date: e.target.value }))}
              />
              <p className="form-text small text-muted mb-0">Возраст на сайте считается автоматически.</p>
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Сохранение…' : 'Сохранить'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

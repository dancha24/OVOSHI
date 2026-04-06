import { useState, useEffect } from 'react'
import { getApplications, patchApplication } from '../api/client'

const STATUS_LABELS = {
  pending: 'На рассмотрении',
  approved: 'Принята',
  rejected: 'Отклонена',
}

/** Текст по умолчанию для новой заявки — нельзя оставить при принятии/отклонении без замены. */
const PENDING_COMMENT_BOILERPLATE = 'На рассмотрении'

function commentValidForDecision(text) {
  const t = (text ?? '').trim()
  return t.length > 0 && t !== PENDING_COMMENT_BOILERPLATE
}

export default function AdminApplications() {
  const [filterStatus, setFilterStatus] = useState('pending')
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [commentById, setCommentById] = useState({})
  const [busyId, setBusyId] = useState(null)

  const load = () => {
    setLoading(true)
    setError('')
    const params = filterStatus === 'all' ? {} : { status: filterStatus }
    getApplications(params)
      .then((rows) => {
        setList(rows)
        const next = {}
        rows.forEach((r) => {
          const c = (r.status_comment || '').trim()
          next[r.id] =
            r.status === 'pending' && c === PENDING_COMMENT_BOILERPLATE
              ? ''
              : (r.status_comment || '')
        })
        setCommentById((prev) => ({ ...prev, ...next }))
      })
      .catch((e) => setError(e.response?.data?.detail || e.message || 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }

  useEffect(() => load(), [filterStatus])

  const decide = async (id, status) => {
    const typed = (commentById[id] ?? '').trim()
    if (!commentValidForDecision(commentById[id] ?? '')) {
      setError('Укажите комментарий к решению (нельзя оставить пустым или текст «На рассмотрении»).')
      return
    }
    setBusyId(id)
    setError('')
    try {
      await patchApplication(id, { status, status_comment: typed })
      await load()
    } catch (e) {
      const d = e.response?.data
      setError(
        (typeof d === 'object' && d?.detail) ||
          d?.status?.[0] ||
          d?.non_field_errors?.[0] ||
          e.message ||
          'Ошибка',
      )
    } finally {
      setBusyId(null)
    }
  }

  if (loading && list.length === 0) {
    return (
      <div className="d-flex align-items-center gap-2 text-muted">
        <span className="spinner-border spinner-border-sm" role="status" />
        Загрузка…
      </div>
    )
  }

  return (
    <div className="container-fluid px-0">
      <h2 className="h4 mb-3">Заявки в клан</h2>
      <p className="text-secondary small mb-3" style={{ maxWidth: 640 }}>
        Принятие или отклонение шлёт заявителю сообщение в ВК. Комментарий к решению обязателен (нельзя оставить пустым или «На рассмотрении»). Принятие выставляет роль «Игрок», если был «Гость». Дата и время решения сохраняются в таблице.
      </p>
      <div className="btn-group flex-wrap mb-3" role="group" aria-label="Фильтр заявок">
        {[
          { key: 'pending', label: 'На рассмотрении' },
          { key: 'approved', label: 'Принятые' },
          { key: 'rejected', label: 'Отклонённые' },
          { key: 'all', label: 'Все' },
        ].map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`btn btn-sm btn-outline-primary ${filterStatus === key ? 'active' : ''}`}
            onClick={() => setFilterStatus(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {error ? <div className="alert alert-danger py-2 small mb-3">{String(error)}</div> : null}
      <div className="table-responsive card border-0 shadow-sm">
        <table className="table table-striped table-hover align-middle mb-0 small">
          <thead className="table-light">
            <tr>
              <th className="text-nowrap">Создана</th>
              <th className="text-nowrap">Решение</th>
              <th>ID</th>
              <th>Ник / UID</th>
              <th>Дата рождения</th>
              <th>Город</th>
              <th>ВК</th>
              <th>ОК</th>
              <th>Статус</th>
              <th style={{ minWidth: 160 }}>Комментарий</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.map((row) => (
              <tr key={row.id}>
                <td className="text-nowrap">
                  {row.created_at ? new Date(row.created_at).toLocaleString('ru-RU') : '—'}
                </td>
                <td className="text-nowrap">
                  {row.resolved_at
                    ? new Date(row.resolved_at).toLocaleString('ru-RU')
                    : '—'}
                </td>
                <td>{row.user ?? '—'}</td>
                <td>
                  {row.nickname || '—'}
                  <br />
                  <span className="text-muted">{row.uid || '—'}</span>
                </td>
                <td className="text-nowrap">
                  {row.birth_date
                    ? `${new Date(row.birth_date).toLocaleDateString('ru-RU')}${
                        row.age_years != null ? ` (${row.age_years} л.)` : ''
                      }`
                    : '—'}
                </td>
                <td>{row.city || '—'}</td>
                <td>
                  {row.vk_user_id ? (
                    <a href={`https://vk.com/id${row.vk_user_id}`} target="_blank" rel="noreferrer">
                      {row.vk_user_id}
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
                <td>{row.clan_points_snapshot}</td>
                <td>{STATUS_LABELS[row.status] || row.status}</td>
                <td>
                  {row.status === 'pending' ? (
                    <textarea
                      rows={2}
                      className="form-control form-control-sm"
                      value={commentById[row.id] ?? ''}
                      onChange={(e) =>
                        setCommentById((m) => ({ ...m, [row.id]: e.target.value }))
                      }
                      placeholder="Обязательный комментарий к решению"
                    />
                  ) : (
                    row.status_comment || '—'
                  )}
                </td>
                <td className="text-nowrap">
                  {row.status === 'pending' && (
                    <>
                      <button
                        type="button"
                        className="btn btn-success btn-sm me-1"
                        disabled={
                          busyId === row.id
                          || !commentValidForDecision(commentById[row.id] ?? '')
                        }
                        onClick={() => decide(row.id, 'approved')}
                      >
                        Принять
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        disabled={
                          busyId === row.id
                          || !commentValidForDecision(commentById[row.id] ?? '')
                        }
                        onClick={() => decide(row.id, 'rejected')}
                      >
                        Отклонить
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!loading && list.length === 0 && <p className="text-muted small mt-3 mb-0">Заявок нет.</p>}
    </div>
  )
}

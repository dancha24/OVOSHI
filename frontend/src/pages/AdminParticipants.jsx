import { useState, useEffect, useMemo } from 'react'
import {
  getParticipants,
  patchParticipant,
  getOkLedger,
  postOkLedger,
  postParticipantKick,
  postParticipantBan,
  postParticipantUnban,
} from '../api/client'
import { useAuth, canManageClanPoints } from '../hooks/useAuth'
import LedgerTable from '../components/LedgerTable'
import { IconBrickBan, IconInfo, IconKick } from '../components/ModerationIcons'

const ROLE_LABELS = {
  guest: 'Гость',
  player: 'Игрок',
  elite: 'Элита',
  deputy: 'Заместитель',
  leader: 'Лидер',
  associate: 'Соучастник',
  banned: 'Забанен',
}

/** Роли в форме «Изменить» — без соучастника/бана (они через отдельные действия). */
const EDIT_ROLE_LABELS = {
  guest: 'Гость',
  player: 'Игрок',
  elite: 'Элита',
  deputy: 'Заместитель',
  leader: 'Лидер',
}

function roleLabelsForFilter(viewerRole) {
  const entries = Object.entries(ROLE_LABELS)
  if (viewerRole === 'deputy') {
    return entries.filter(([k]) => k !== 'guest' && k !== 'associate')
  }
  return entries
}

function vkIdFromBotEmail(email) {
  if (!email || typeof email !== 'string') return null
  const m = /^vk(\d+)@/i.exec(email.trim())
  if (!m) return null
  const n = parseInt(m[1], 10)
  return Number.isFinite(n) && n > 0 ? n : null
}

function vkProfileHref(vkUserId) {
  if (vkUserId == null || vkUserId === '') return null
  const n = Number(vkUserId)
  if (!Number.isFinite(n) || n < 1) return null
  return `https://vk.com/id${n}`
}

function vkLinkForRow(vkUserId, email) {
  const id = vkUserId != null && vkUserId !== '' ? vkUserId : vkIdFromBotEmail(email)
  return vkProfileHref(id)
}

/** API отдаёт YYYY-MM-DD или null */
function formatBirthDateRu(iso) {
  if (!iso || typeof iso !== 'string') return '—'
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim())
  if (!m) return '—'
  return `${m[3]}.${m[2]}.${m[1]}`
}

function formatAgeYears(n) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  const k = Number(n)
  return `${k} ${pluralRuYears(k)}`
}

function pluralRuYears(n) {
  const a = Math.abs(n) % 100
  const b = a % 10
  if (a > 10 && a < 20) return 'лет'
  if (b === 1) return 'год'
  if (b >= 2 && b <= 4) return 'года'
  return 'лет'
}

/** ISO datetime от API → локальная строка */
function formatDateTimeRu(iso) {
  if (!iso || typeof iso !== 'string') return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Индикатор в колонке статуса: красный — бан; жёлтый — кик/соучастник; зелёный — ок. */
function ModerationDot({ row }) {
  const banned = row.role === 'banned' || Boolean(row.banned_at)
  const kicked = Boolean(row.kicked_at) || row.role === 'associate'
  let colorClass = 'bg-success'
  let label = 'Всё в порядке'
  if (banned) {
    colorClass = 'bg-danger'
    label = 'Забанен'
  } else if (kicked) {
    colorClass = 'bg-warning'
    label = 'Исключён из клана (соучастник)'
  }
  return (
    <span
      className={`d-inline-block rounded-circle ${colorClass}`}
      style={{ width: '0.65rem', height: '0.65rem', verticalAlign: 'middle' }}
      title={label}
      role="img"
      aria-label={label}
    />
  )
}

function canShowKickBan(me, row) {
  if (!me || row.id === me.id) {
    return { kick: false, ban: false, unban: false }
  }
  if (row.role === 'leader') {
    return { kick: false, ban: false, unban: false }
  }
  if (row.role === 'banned') {
    return { kick: false, ban: false, unban: true }
  }
  if (row.role === 'deputy' && me.role !== 'leader' && !me.is_superuser) {
    return { kick: false, ban: false, unban: false }
  }
  return { kick: true, ban: true, unban: false }
}

function roleOptionsForEdit(currentRole) {
  if (currentRole === 'associate') {
    return { ...EDIT_ROLE_LABELS, associate: ROLE_LABELS.associate }
  }
  return EDIT_ROLE_LABELS
}

/** YYYY-MM-DD → полных лет (как на бэке), для предпросмотра в форме */
function ageYearsFromIsoDate(iso) {
  if (!iso || typeof iso !== 'string') return null
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim())
  if (!m) return null
  const y = Number(m[1])
  const mo = Number(m[2])
  const da = Number(m[3])
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(da)) return null
  const today = new Date()
  const ty = today.getFullYear()
  const tm = today.getMonth() + 1
  const td = today.getDate()
  let n = ty - y
  if (tm < mo || (tm === mo && td < da)) n -= 1
  return n
}

/** Имя из ВК: если есть ссылка на профиль — кликабельно с ↗. */
function VkNameCell({ vkUserId, displayName }) {
  const href = vkLinkForRow(vkUserId, null)
  const label = displayName && String(displayName).trim() ? displayName.trim() : '—'
  if (!href) {
    return <span>{label}</span>
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-decoration-none"
      title={href}
    >
      {label}
      {' '}
      <span aria-hidden="true">↗</span>
    </a>
  )
}

export default function AdminParticipants() {
  const { user: me } = useAuth()
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [okForId, setOkForId] = useState(null)
  const [okLedger, setOkLedger] = useState([])
  const [okLoading, setOkLoading] = useState(false)
  const [okErr, setOkErr] = useState('')
  const [okAmount, setOkAmount] = useState('')
  const [okComment, setOkComment] = useState('')
  const [okBusy, setOkBusy] = useState(false)

  const [kickForId, setKickForId] = useState(null)
  const [kickReason, setKickReason] = useState('')
  const [kickBusy, setKickBusy] = useState(false)
  const [kickErr, setKickErr] = useState('')

  const [banForId, setBanForId] = useState(null)
  const [banReason, setBanReason] = useState('')
  const [banBusy, setBanBusy] = useState(false)
  const [banErr, setBanErr] = useState('')

  const [unbanForId, setUnbanForId] = useState(null)
  const [unbanBusy, setUnbanBusy] = useState(false)

  /** Строка таблицы для модалки «Подробнее» (кик/бан и снятие бана). */
  const [infoRow, setInfoRow] = useState(null)
  const [infoUnbanBusy, setInfoUnbanBusy] = useState(false)

  const [filterText, setFilterText] = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [filterUidConfirmed, setFilterUidConfirmed] = useState('')

  const filteredList = useMemo(() => {
    let rows = list
    const q = filterText.trim().toLowerCase()
    if (q) {
      rows = rows.filter((row) => {
        const idStr = String(row.id)
        const nick = (row.nickname || '').toLowerCase()
        const uid = (row.uid || '').toLowerCase()
        const vkName = (row.vk_display_name || '').toLowerCase()
        return (
          idStr.includes(q)
          || nick.includes(q)
          || uid.includes(q)
          || vkName.includes(q)
        )
      })
    }
    if (filterRole) {
      rows = rows.filter((r) => r.role === filterRole)
    }
    if (filterUidConfirmed === 'yes') {
      rows = rows.filter((r) => r.uid_confirmed)
    }
    if (filterUidConfirmed === 'no') {
      rows = rows.filter((r) => !r.uid_confirmed)
    }
    return rows
  }, [list, filterText, filterRole, filterUidConfirmed])

  const filtersActive = Boolean(filterText.trim() || filterRole || filterUidConfirmed)

  const clearFilters = () => {
    setFilterText('')
    setFilterRole('')
    setFilterUidConfirmed('')
  }

  const load = () => {
    setLoading(true)
    getParticipants()
      .then(setList)
      .finally(() => setLoading(false))
  }

  useEffect(() => load(), [])

  useEffect(() => {
    if (okForId == null) {
      setOkLedger([])
      return
    }
    setOkLoading(true)
    setOkErr('')
    getOkLedger(okForId)
      .then(setOkLedger)
      .catch((e) => setOkErr(e.response?.data?.detail || e.message || 'Ошибка'))
      .finally(() => setOkLoading(false))
  }, [okForId])

  const startEdit = (row) => {
    setEditingId(row.id)
    const bd = row.birth_date
    setEditForm({
      nickname: row.nickname || '',
      uid: row.uid || '',
      birth_date: typeof bd === 'string' ? bd.slice(0, 10) : '',
      // karma: row.karma,
      role: row.role,
      uid_confirmed: row.uid_confirmed,
    })
  }

  const saveEdit = async () => {
    if (editingId == null) return
    const payload = {
      nickname: editForm.nickname.trim().slice(0, 50),
      uid: editForm.uid.trim(),
      birth_date: editForm.birth_date ? editForm.birth_date : null,
      uid_confirmed: editForm.uid_confirmed,
    }
    if (editForm.role !== 'banned') {
      payload.role = editForm.role
    }
    await patchParticipant(editingId, payload)
    setEditingId(null)
    load()
  }

  const cancelEdit = () => setEditingId(null)

  const openOk = (id) => {
    setOkForId(id)
    setOkAmount('')
    setOkComment('')
    setOkErr('')
  }

  const closeOk = () => {
    setOkForId(null)
  }

  useEffect(() => {
    if (okForId == null) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setOkForId(null)
    }
    window.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [okForId])

  const closeKick = () => {
    setKickForId(null)
    setKickReason('')
    setKickErr('')
  }

  const closeBan = () => {
    setBanForId(null)
    setBanReason('')
    setBanErr('')
  }

  const closeUnban = () => {
    setUnbanForId(null)
  }

  useEffect(() => {
    const open = kickForId != null || banForId != null || unbanForId != null || infoRow != null
    if (!open) return undefined
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [kickForId, banForId, unbanForId, infoRow])

  useEffect(() => {
    if (infoRow == null) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setInfoRow(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [infoRow])

  const submitKick = async (e) => {
    e.preventDefault()
    if (kickForId == null) return
    const r = kickReason.trim()
    if (r.length < 3) {
      setKickErr('Укажите причину (не короче 3 символов).')
      return
    }
    setKickBusy(true)
    setKickErr('')
    try {
      await postParticipantKick(kickForId, { reason: r })
      closeKick()
      load()
    } catch (err) {
      const d = err.response?.data
      setKickErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : err.message || 'Ошибка')
    } finally {
      setKickBusy(false)
    }
  }

  const submitBan = async (e) => {
    e.preventDefault()
    if (banForId == null) return
    const r = banReason.trim()
    if (r.length < 3) {
      setBanErr('Укажите причину (не короче 3 символов).')
      return
    }
    setBanBusy(true)
    setBanErr('')
    try {
      await postParticipantBan(banForId, { reason: r })
      closeBan()
      load()
    } catch (err) {
      const d = err.response?.data
      setBanErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : err.message || 'Ошибка')
    } finally {
      setBanBusy(false)
    }
  }

  const submitUnban = async () => {
    if (unbanForId == null) return
    setUnbanBusy(true)
    try {
      await postParticipantUnban(unbanForId)
      closeUnban()
      load()
    } finally {
      setUnbanBusy(false)
    }
  }

  const closeInfo = () => {
    setInfoRow(null)
    setInfoUnbanBusy(false)
  }

  const submitUnbanFromInfo = async () => {
    if (infoRow == null) return
    setInfoUnbanBusy(true)
    try {
      await postParticipantUnban(infoRow.id)
      closeInfo()
      load()
    } finally {
      setInfoUnbanBusy(false)
    }
  }

  const submitOk = async (e) => {
    e.preventDefault()
    if (okForId == null || !canManageClanPoints(me)) return
    const amount = parseInt(String(okAmount).trim(), 10)
    if (Number.isNaN(amount) || amount === 0) {
      setOkErr('Укажите ненулевую целую сумму (для списания — отрицательное число).')
      return
    }
    const comment = okComment.trim()
    if (!comment) {
      setOkErr('Укажите комментарий.')
      return
    }
    setOkBusy(true)
    setOkErr('')
    try {
      await postOkLedger(okForId, { amount, comment })
      setOkAmount('')
      setOkComment('')
      const rows = await getOkLedger(okForId)
      setOkLedger(rows)
      load()
    } catch (err) {
      const d = err.response?.data
      setOkErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : err.message || 'Ошибка')
    } finally {
      setOkBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="d-flex align-items-center gap-2 text-muted">
        <span className="spinner-border spinner-border-sm" role="status" />
        Загрузка…
      </div>
    )
  }

  return (
    <div className="container-fluid px-0">
      <h2 className="h4 mb-3">Участники</h2>
      <p className="text-secondary small mb-3" style={{ maxWidth: 720 }}>
        Очки клана (ОК) меняются только через журнал: кнопка «Журнал ОК» у участника — там история, начисление и списание
        (нужны права лидера или заместителя). В колонке «ВК» — имя из ВК (если входили через VK ID); иначе никнейм. По клику на имя с ↗ — открывается профиль ВК, если известен id.
        {' '}
        <strong className="text-body">Статус</strong> (кружок): зелёный — без исключения и бана; жёлтый — исключён из клана (соучастник); красный — забанен.
        {' '}
        Действия: кроссовок (исключить) и кирпичная стена (забанить), контуры как в Lucide; «i» — подробности об исключении и бане и снятие бана.
        {me?.role === 'deputy' ? (
          <> Заместителю в этом списке не показываются гости и соучастники — только игроки и выше.</>
        ) : null}
      </p>

      <div className="card vk-card border-0 shadow-none mb-3">
        <div className="card-body py-3">
          <div className="row g-2 align-items-end">
            <div className="col-12 col-md-4 col-lg-4">
              <label className="form-label small mb-1" htmlFor="participants-filter-text">
                Поиск
              </label>
              <input
                id="participants-filter-text"
                type="search"
                className="form-control form-control-sm"
                placeholder="ID, никнейм, UID или имя в ВК…"
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                autoComplete="off"
              />
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1" htmlFor="participants-filter-role">
                Роль
              </label>
              <select
                id="participants-filter-role"
                className="form-select form-select-sm"
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
              >
                <option value="">Все</option>
                {roleLabelsForFilter(me?.role).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1" htmlFor="participants-filter-uid">
                UID подтверждён
              </label>
              <select
                id="participants-filter-uid"
                className="form-select form-select-sm"
                value={filterUidConfirmed}
                onChange={(e) => setFilterUidConfirmed(e.target.value)}
              >
                <option value="">Все</option>
                <option value="yes">Да</option>
                <option value="no">Нет</option>
              </select>
            </div>
            <div className="col-12 col-md-2 col-lg-auto d-flex gap-2 flex-wrap align-items-center">
              {filtersActive ? (
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={clearFilters}>
                  Сбросить
                </button>
              ) : null}
            </div>
          </div>
          {filtersActive || filteredList.length !== list.length ? (
            <p className="text-secondary small mb-0 mt-2">
              Показано: <strong className="text-body">{filteredList.length}</strong>
              {list.length !== filteredList.length ? (
                <>
                  {' '}
                  из <strong className="text-body">{list.length}</strong>
                </>
              ) : null}
            </p>
          ) : null}
        </div>
      </div>

      <div className="table-responsive card vk-card border-0 shadow-none mb-4">
        <table className="table table-striped table-hover align-middle mb-0 small">
          <thead className="table-light">
            <tr>
              <th>ID</th>
              <th>ВК</th>
              <th>Никнейм</th>
              <th>Дата рождения</th>
              <th>Возраст</th>
              <th>UID</th>
              <th>ОК</th>
              {/* <th>Карма</th> */}
              <th>Роль</th>
              <th className="text-center text-nowrap">Статус</th>
              <th>UID ок</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filteredList.length === 0 ? (
              <tr>
                <td colSpan={11} className="text-center text-secondary py-4">
                  {list.length === 0 ? 'Участников пока нет.' : 'Никто не подходит под фильтры.'}
                </td>
              </tr>
            ) : null}
            {filteredList.map((row) => (
              <tr key={row.id}>
                {editingId === row.id ? (
                  <>
                    <td className="text-nowrap">{row.id}</td>
                    <td className="text-break">
                      <VkNameCell vkUserId={row.vk_user_id} displayName={row.vk_display_name} />
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        maxLength={50}
                        value={editForm.nickname}
                        onChange={(e) => setEditForm((f) => ({ ...f, nickname: e.target.value }))}
                      />
                    </td>
                    <td>
                      <input
                        type="date"
                        className="form-control form-control-sm"
                        style={{ maxWidth: '11rem' }}
                        value={editForm.birth_date || ''}
                        onChange={(e) => setEditForm((f) => ({ ...f, birth_date: e.target.value }))}
                      />
                    </td>
                    <td className="text-nowrap text-secondary small">
                      {formatAgeYears(ageYearsFromIsoDate(editForm.birth_date))}
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={editForm.uid}
                        onChange={(e) => setEditForm((f) => ({ ...f, uid: e.target.value }))}
                      />
                    </td>
                    <td>{row.clan_points}</td>
                    {/* Карма временно скрыта
                    <td>
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        style={{ width: 72 }}
                        value={editForm.karma}
                        onChange={(e) => setEditForm((f) => ({ ...f, karma: +e.target.value }))}
                      />
                    </td>
                    */}
                    <td>
                      {editForm.role === 'banned' ? (
                        <span className="small text-danger">{ROLE_LABELS.banned}</span>
                      ) : (
                        <select
                          className="form-select form-select-sm"
                          value={editForm.role}
                          onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value }))}
                        >
                          {Object.entries(roleOptionsForEdit(editForm.role)).map(([k, v]) => (
                            <option key={k} value={k}>{v}</option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="text-center">
                      <ModerationDot row={row} />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={editForm.uid_confirmed}
                        onChange={(e) => setEditForm((f) => ({ ...f, uid_confirmed: e.target.checked }))}
                        disabled={editForm.role === 'banned'}
                      />
                    </td>
                    <td className="text-nowrap">
                      <button type="button" className="btn btn-primary btn-sm me-1" onClick={saveEdit}>Сохранить</button>
                      <button type="button" className="btn btn-outline-secondary btn-sm" onClick={cancelEdit}>Отмена</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="text-nowrap">{row.id}</td>
                    <td className="text-break">
                      <VkNameCell vkUserId={row.vk_user_id} displayName={row.vk_display_name} />
                    </td>
                    <td>{row.nickname || '—'}</td>
                    <td className="text-nowrap">{formatBirthDateRu(row.birth_date)}</td>
                    <td className="text-nowrap">{formatAgeYears(row.age_years)}</td>
                    <td>{row.uid || '—'}</td>
                    <td>{row.clan_points}</td>
                    {/* <td>{row.karma}</td> */}
                    <td>{ROLE_LABELS[row.role] || row.role}</td>
                    <td className="text-center">
                      <ModerationDot row={row} />
                    </td>
                    <td>{row.uid_confirmed ? 'Да' : 'Нет'}</td>
                    <td className="text-nowrap">
                      <div className="d-flex flex-wrap gap-1 align-items-center justify-content-end">
                        <button
                          type="button"
                          className="btn btn-outline-info btn-sm p-1 px-2"
                          title="Подробнее: исключение, бан"
                          aria-label="Подробнее о модерации"
                          onClick={() => setInfoRow(row)}
                        >
                          <IconInfo size={18} />
                        </button>
                        <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => startEdit(row)}>
                          Изменить
                        </button>
                        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => openOk(row.id)}>
                          Журнал ОК
                        </button>
                        {(() => {
                          const flags = canShowKickBan(me, row)
                          return (
                            <>
                              {flags.kick ? (
                                <button
                                  type="button"
                                  className="btn btn-outline-warning btn-sm p-1 px-2"
                                  title="Исключить из клана"
                                  aria-label="Исключить из клана"
                                  onClick={() => {
                                    setKickForId(row.id)
                                    setKickReason('')
                                    setKickErr('')
                                  }}
                                >
                                  <IconKick size={18} />
                                </button>
                              ) : null}
                              {flags.ban ? (
                                <button
                                  type="button"
                                  className="btn btn-outline-danger btn-sm p-1 px-2"
                                  title="Забанить"
                                  aria-label="Забанить"
                                  onClick={() => {
                                    setBanForId(row.id)
                                    setBanReason('')
                                    setBanErr('')
                                  }}
                                >
                                  <IconBrickBan size={18} />
                                </button>
                              ) : null}
                              {flags.unban ? (
                                <button
                                  type="button"
                                  className="btn btn-outline-success btn-sm"
                                  onClick={() => setUnbanForId(row.id)}
                                >
                                  Снять бан
                                </button>
                              ) : null}
                            </>
                          )
                        })()}
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {okForId != null ? (
        <>
          <div
            className="modal fade show d-block"
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-ok-ledger-title"
            onClick={closeOk}
          >
            <div
              className="modal-dialog modal-lg modal-dialog-scrollable modal-dialog-centered"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-content bg-body border-secondary">
                <div className="modal-header border-secondary">
                  <h5 className="modal-title mb-0" id="admin-ok-ledger-title">
                    Журнал ОК — участник ID {okForId}
                  </h5>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={closeOk}>
                    Закрыть
                  </button>
                </div>
                <div className="modal-body">
                  {okLoading ? (
                    <div className="d-flex align-items-center gap-2 text-muted small">
                      <span className="spinner-border spinner-border-sm" role="status" />
                      Загрузка журнала…
                    </div>
                  ) : (
                    <LedgerTable rows={okLedger} />
                  )}
                  {okErr ? <div className="alert alert-danger py-2 small mt-3 mb-0">{String(okErr)}</div> : null}
                  {canManageClanPoints(me) && (
                    <form onSubmit={submitOk} className="row g-2 align-items-end mt-3 pt-3 border-top border-secondary">
                      <div className="col-auto">
                        <label className="form-label small mb-1">Сумма ОК</label>
                        <input
                          type="number"
                          className="form-control form-control-sm"
                          style={{ width: 120 }}
                          value={okAmount}
                          onChange={(e) => setOkAmount(e.target.value)}
                          placeholder="+10 / -5"
                        />
                      </div>
                      <div className="col">
                        <label className="form-label small mb-1">Комментарий</label>
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          value={okComment}
                          onChange={(e) => setOkComment(e.target.value)}
                        />
                      </div>
                      <div className="col-auto">
                        <button type="submit" className="btn btn-primary btn-sm" disabled={okBusy}>
                          {okBusy ? '…' : 'Записать'}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" role="presentation" onClick={closeOk} />
        </>
      ) : null}

      {kickForId != null ? (
        <>
          <div
            className="modal fade show d-block"
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-kick-title"
            onClick={closeKick}
          >
            <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
              <div className="modal-content bg-body border-secondary">
                <div className="modal-header border-secondary">
                  <h5 className="modal-title mb-0" id="admin-kick-title">
                    Исключить из клана (ID {kickForId})
                  </h5>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={closeKick}>
                    Отмена
                  </button>
                </div>
                <form className="modal-body" onSubmit={submitKick}>
                  <p className="small text-secondary mb-2">
                    Пользователь станет соучастником (турниры и т.п.), очки клана сохраняются.
                  </p>
                  <label className="form-label small" htmlFor="kick-reason">Причина (обязательно)</label>
                  <textarea
                    id="kick-reason"
                    className="form-control form-control-sm"
                    rows={3}
                    value={kickReason}
                    onChange={(e) => setKickReason(e.target.value)}
                    placeholder="Кратко: конкурс на выбывание, …"
                    required
                  />
                  {kickErr ? <div className="alert alert-danger py-2 small mt-2 mb-0">{String(kickErr)}</div> : null}
                  <div className="d-flex gap-2 justify-content-end mt-3">
                    <button type="button" className="btn btn-outline-secondary btn-sm" onClick={closeKick}>
                      Отмена
                    </button>
                    <button type="submit" className="btn btn-warning btn-sm" disabled={kickBusy}>
                      {kickBusy ? '…' : 'Исключить'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" role="presentation" onClick={closeKick} />
        </>
      ) : null}

      {banForId != null ? (
        <>
          <div
            className="modal fade show d-block"
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-ban-title"
            onClick={closeBan}
          >
            <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
              <div className="modal-content bg-body border-secondary">
                <div className="modal-header border-secondary">
                  <h5 className="modal-title mb-0" id="admin-ban-title">
                    Забанить (ID {banForId})
                  </h5>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={closeBan}>
                    Отмена
                  </button>
                </div>
                <form className="modal-body" onSubmit={submitBan}>
                  <p className="small text-secondary mb-2">
                    Очки клана обнулятся, запись появится в журнале ОК. Доступ к сайту и боту будет заблокирован.
                  </p>
                  <label className="form-label small" htmlFor="ban-reason">Причина (обязательно)</label>
                  <textarea
                    id="ban-reason"
                    className="form-control form-control-sm"
                    rows={3}
                    value={banReason}
                    onChange={(e) => setBanReason(e.target.value)}
                    required
                  />
                  {banErr ? <div className="alert alert-danger py-2 small mt-2 mb-0">{String(banErr)}</div> : null}
                  <div className="d-flex gap-2 justify-content-end mt-3">
                    <button type="button" className="btn btn-outline-secondary btn-sm" onClick={closeBan}>
                      Отмена
                    </button>
                    <button type="submit" className="btn btn-danger btn-sm" disabled={banBusy}>
                      {banBusy ? '…' : 'Забанить'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" role="presentation" onClick={closeBan} />
        </>
      ) : null}

      {unbanForId != null ? (
        <>
          <div
            className="modal fade show d-block"
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-unban-title"
            onClick={closeUnban}
          >
            <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
              <div className="modal-content bg-body border-secondary">
                <div className="modal-header border-secondary">
                  <h5 className="modal-title mb-0" id="admin-unban-title">
                    Снять бан (ID {unbanForId})
                  </h5>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={closeUnban}>
                    Отмена
                  </button>
                </div>
                <div className="modal-body">
                  <p className="small text-secondary mb-3">
                    Роль станет «Гость», очки клана не восстанавливаются. Пользователь снова сможет пользоваться ботом и подать заявку.
                  </p>
                  <div className="d-flex gap-2 justify-content-end">
                    <button type="button" className="btn btn-outline-secondary btn-sm" onClick={closeUnban}>
                      Отмена
                    </button>
                    <button type="button" className="btn btn-success btn-sm" disabled={unbanBusy} onClick={() => void submitUnban()}>
                      {unbanBusy ? '…' : 'Снять бан'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" role="presentation" onClick={closeUnban} />
        </>
      ) : null}

      {infoRow != null ? (
        <>
          <div
            className="modal fade show d-block"
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-participant-info-title"
            onClick={closeInfo}
          >
            <div
              className="modal-dialog modal-dialog-scrollable modal-dialog-centered"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-content bg-body border-secondary">
                <div className="modal-header border-secondary">
                  <h5 className="modal-title mb-0" id="admin-participant-info-title">
                    Участник #{infoRow.id}
                    {infoRow.nickname ? ` — ${infoRow.nickname}` : ''}
                  </h5>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={closeInfo}>
                    Закрыть
                  </button>
                </div>
                <div className="modal-body small">
                  <p className="text-secondary mb-3">
                    Роль: <strong className="text-body">{ROLE_LABELS[infoRow.role] || infoRow.role}</strong>
                    . ОК: <strong className="text-body">{infoRow.clan_points ?? '—'}</strong>
                  </p>

                  {(infoRow.kicked_at || infoRow.role === 'associate') && (
                    <div className="mb-3 pb-3 border-bottom border-secondary">
                      <h6 className="h6 text-body mb-2">Исключение из клана</h6>
                      {infoRow.kicked_at ? (
                        <dl className="row mb-0 small">
                          <dt className="col-sm-4 text-secondary">Когда</dt>
                          <dd className="col-sm-8">{formatDateTimeRu(infoRow.kicked_at)}</dd>
                          <dt className="col-sm-4 text-secondary">Кто</dt>
                          <dd className="col-sm-8">{infoRow.kicked_by_label || '—'}</dd>
                          <dt className="col-sm-4 text-secondary">Причина</dt>
                          <dd className="col-sm-8 text-break">{infoRow.kick_reason?.trim() || '—'}</dd>
                        </dl>
                      ) : (
                        <p className="text-secondary mb-0">Роль «Соучастник»; отдельная запись об исключении не сохранена.</p>
                      )}
                    </div>
                  )}

                  {(infoRow.banned_at || infoRow.role === 'banned') && (
                    <div className="mb-3">
                      <h6 className="h6 text-body mb-2">Бан</h6>
                      {infoRow.banned_at ? (
                        <dl className="row mb-0 small">
                          <dt className="col-sm-4 text-secondary">Когда</dt>
                          <dd className="col-sm-8">{formatDateTimeRu(infoRow.banned_at)}</dd>
                          <dt className="col-sm-4 text-secondary">Кто</dt>
                          <dd className="col-sm-8">{infoRow.banned_by_label || '—'}</dd>
                          <dt className="col-sm-4 text-secondary">Причина</dt>
                          <dd className="col-sm-8 text-break">{infoRow.ban_reason?.trim() || '—'}</dd>
                        </dl>
                      ) : (
                        <p className="text-secondary mb-0">Роль «Забанен»; дата бана не указана.</p>
                      )}
                    </div>
                  )}

                  {!(
                    infoRow.kicked_at
                    || infoRow.role === 'associate'
                    || infoRow.banned_at
                    || infoRow.role === 'banned'
                  ) ? (
                    <p className="text-secondary mb-0">
                      Нет записей об исключении из клана или бане (статус в таблице — зелёный индикатор).
                    </p>
                  ) : null}

                  {canShowKickBan(me, infoRow).unban ? (
                    <div className="pt-3 mt-2 border-top border-secondary">
                      <p className="text-secondary small mb-2">
                        Снять бан: роль станет «Гость», очки клана не восстанавливаются.
                      </p>
                      <button
                        type="button"
                        className="btn btn-success btn-sm"
                        disabled={infoUnbanBusy}
                        onClick={() => void submitUnbanFromInfo()}
                      >
                        {infoUnbanBusy ? '…' : 'Снять бан'}
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" role="presentation" onClick={closeInfo} />
        </>
      ) : null}
    </div>
  )
}

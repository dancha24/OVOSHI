import { useState, useEffect } from 'react'
import {
  getShopLotsAll,
  createShopLot,
  patchShopLot,
  deleteShopLot,
} from '../api/client'

function emptyNewForm() {
  return {
    title: '',
    price_points: '',
    sort_order: '0',
    is_active: true,
  }
}

function lotFormData(fields, imageFile) {
  const fd = new FormData()
  fd.append('title', (fields.title || '').trim())
  fd.append('price_points', String(Math.max(0, parseInt(String(fields.price_points), 10) || 0)))
  fd.append('sort_order', String(Math.max(0, parseInt(String(fields.sort_order), 10) || 0)))
  fd.append('is_active', fields.is_active ? 'true' : 'false')
  if (imageFile) fd.append('image', imageFile)
  return fd
}

export default function AdminShopLots() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [newForm, setNewForm] = useState(emptyNewForm)
  const [newImage, setNewImage] = useState(null)
  const [newBusy, setNewBusy] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [editImage, setEditImage] = useState(null)
  const [rowBusy, setRowBusy] = useState(null)

  const load = () => {
    setLoading(true)
    setErr('')
    getShopLotsAll()
      .then(setList)
      .catch((e) => {
        setErr(e.response?.data?.detail || e.message || 'Не удалось загрузить лоты')
        setList([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const submitNew = async (e) => {
    e.preventDefault()
    const title = newForm.title.trim()
    if (!title) {
      setErr('Укажите название лота.')
      return
    }
    const price = parseInt(String(newForm.price_points), 10)
    if (Number.isNaN(price) || price < 1) {
      setErr('Цена должна быть целым числом не меньше 1 ОК.')
      return
    }
    setNewBusy(true)
    setErr('')
    try {
      const payload = lotFormData(newForm, newImage)
      await createShopLot(payload)
      setNewForm(emptyNewForm())
      setNewImage(null)
      load()
    } catch (e2) {
      const d = e2.response?.data
      setErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : e2.message || 'Ошибка')
    } finally {
      setNewBusy(false)
    }
  }

  const startEdit = (row) => {
    setEditingId(row.id)
    setEditImage(null)
    setEditForm({
      title: row.title || '',
      price_points: String(row.price_points ?? ''),
      sort_order: String(row.sort_order ?? 0),
      is_active: Boolean(row.is_active),
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditImage(null)
  }

  const saveEdit = async (id) => {
    const title = editForm.title.trim()
    if (!title) {
      setErr('Укажите название лота.')
      return
    }
    const price = parseInt(String(editForm.price_points), 10)
    if (Number.isNaN(price) || price < 1) {
      setErr('Цена должна быть целым числом не меньше 1 ОК.')
      return
    }
    setRowBusy(id)
    setErr('')
    try {
      if (editImage) {
        await patchShopLot(id, lotFormData(editForm, editImage))
      } else {
        await patchShopLot(id, {
          title,
          price_points: price,
          sort_order: parseInt(String(editForm.sort_order), 10) || 0,
          is_active: editForm.is_active,
        })
      }
      setEditingId(null)
      setEditImage(null)
      load()
    } catch (e2) {
      const d = e2.response?.data
      setErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : e2.message || 'Ошибка')
    } finally {
      setRowBusy(null)
    }
  }

  const removeLot = async (id) => {
    if (!window.confirm('Удалить этот лот? Покупки в ВК по старой кнопке перестанут находить лот.')) return
    setRowBusy(id)
    setErr('')
    try {
      await deleteShopLot(id)
      if (editingId === id) cancelEdit()
      load()
    } catch (e2) {
      const d = e2.response?.data
      setErr(typeof d === 'object' ? (d.detail || JSON.stringify(d)) : e2.message || 'Ошибка')
    } finally {
      setRowBusy(null)
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
      <h2 className="h4 mb-3">Лоты магазина</h2>
      <p className="text-secondary small mb-3" style={{ maxWidth: 720 }}>
        Каталог за очки клана (ОК): отображается в боте ВК и на сайте для игроков. Неактивные лоты в каталог не попадают.
      </p>

      {err ? <div className="alert alert-danger py-2 small mb-3">{err}</div> : null}

      <div className="card border-0 shadow-sm mb-4">
        <div className="card-header vk-card-header fw-semibold">Новый лот</div>
        <div className="card-body">
          <form onSubmit={submitNew} className="row g-2 align-items-end">
            <div className="col-12 col-md-4">
              <label className="form-label small mb-1">Название</label>
              <input
                className="form-control form-control-sm"
                value={newForm.title}
                onChange={(e) => setNewForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Например, 60 UC"
              />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label small mb-1">Цена, ОК</label>
              <input
                type="number"
                min={1}
                className="form-control form-control-sm"
                value={newForm.price_points}
                onChange={(e) => setNewForm((f) => ({ ...f, price_points: e.target.value }))}
              />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label small mb-1">Порядок</label>
              <input
                type="number"
                min={0}
                className="form-control form-control-sm"
                value={newForm.sort_order}
                onChange={(e) => setNewForm((f) => ({ ...f, sort_order: e.target.value }))}
              />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label small mb-1">Картинка</label>
              <input
                type="file"
                accept="image/*"
                className="form-control form-control-sm"
                onChange={(e) => setNewImage(e.target.files?.[0] || null)}
              />
            </div>
            <div className="col-6 col-md-2 d-flex align-items-center gap-2">
              <div className="form-check mb-0">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="new-lot-active"
                  checked={newForm.is_active}
                  onChange={(e) => setNewForm((f) => ({ ...f, is_active: e.target.checked }))}
                />
                <label className="form-check-label small" htmlFor="new-lot-active">Активен</label>
              </div>
            </div>
            <div className="col-12 col-md-auto">
              <button type="submit" className="btn btn-primary btn-sm" disabled={newBusy}>
                {newBusy ? '…' : 'Добавить'}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="table-responsive card border-0 shadow-sm">
        <table className="table table-striped table-hover align-middle mb-0 small">
          <thead className="table-light">
            <tr>
              <th style={{ width: 72 }}>Фото</th>
              <th>Название</th>
              <th className="text-nowrap">Цена, ОК</th>
              <th className="text-nowrap">Порядок</th>
              <th>Активен</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-muted text-center py-4">
                  Лотов пока нет — добавьте первый выше.
                </td>
              </tr>
            ) : (
              list.map((row) => (
                <tr key={row.id}>
                  {editingId === row.id ? (
                    <>
                      <td>
                        <div className="d-flex flex-column gap-1 align-items-start">
                          {row.image_url ? (
                            <img src={row.image_url} alt="" className="rounded" style={{ maxWidth: 64, maxHeight: 64, objectFit: 'cover' }} />
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                          <input
                            type="file"
                            accept="image/*"
                            className="form-control form-control-sm"
                            style={{ maxWidth: 200 }}
                            onChange={(e) => setEditImage(e.target.files?.[0] || null)}
                          />
                        </div>
                      </td>
                      <td>
                        <input
                          className="form-control form-control-sm"
                          value={editForm.title}
                          onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={1}
                          className="form-control form-control-sm"
                          style={{ width: 88 }}
                          value={editForm.price_points}
                          onChange={(e) => setEditForm((f) => ({ ...f, price_points: e.target.value }))}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          className="form-control form-control-sm"
                          style={{ width: 72 }}
                          value={editForm.sort_order}
                          onChange={(e) => setEditForm((f) => ({ ...f, sort_order: e.target.value }))}
                        />
                      </td>
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={editForm.is_active}
                          onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
                        />
                      </td>
                      <td className="text-nowrap">
                        <button
                          type="button"
                          className="btn btn-primary btn-sm me-1"
                          disabled={rowBusy === row.id}
                          onClick={() => saveEdit(row.id)}
                        >
                          Сохранить
                        </button>
                        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={cancelEdit}>
                          Отмена
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>
                        {row.image_url ? (
                          <img src={row.image_url} alt="" className="rounded" style={{ width: 56, height: 56, objectFit: 'cover' }} />
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td className="fw-medium">{row.title}</td>
                      <td>{row.price_points}</td>
                      <td>{row.sort_order}</td>
                      <td>{row.is_active ? 'Да' : 'Нет'}</td>
                      <td className="text-nowrap">
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm me-1"
                          disabled={rowBusy === row.id}
                          onClick={() => startEdit(row)}
                        >
                          Изменить
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-danger btn-sm"
                          disabled={rowBusy === row.id}
                          onClick={() => removeLot(row.id)}
                        >
                          Удалить
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

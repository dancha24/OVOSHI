import { useState, useEffect } from 'react'
import { getSettings, patchSettings } from '../api/client'

export default function AdminSettings() {
  const [vk_public_url, setVk_public_url] = useState('')
  const [recruiter_url, setRecruiter_url] = useState('')
  const [saving, setSaving] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    getSettings().then((data) => {
      setVk_public_url(data.vk_public_url || '')
      setRecruiter_url(data.recruiter_url || '')
      setLoaded(true)
    }).catch(() => setLoaded(true))
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await patchSettings({ vk_public_url, recruiter_url })
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) {
    return (
      <div className="d-flex align-items-center gap-2 text-muted">
        <span className="spinner-border spinner-border-sm" role="status" />
        Загрузка…
      </div>
    )
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 560 }}>
      <h2 className="h4 mb-4">Настройки сайта</h2>
      <div className="card shadow-sm border-0">
        <div className="card-body p-4">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Ссылка на паблик клана ВКонтакте</label>
              <input
                type="url"
                className="form-control"
                value={vk_public_url}
                onChange={(e) => setVk_public_url(e.target.value)}
                placeholder="https://vk.com/..."
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Ссылка на наборщика</label>
              <p className="form-text small text-secondary mb-2">
                Показывается в боте ВК в разделе «Вступить» (шаг «напиши наборщику»). Если пусто — берётся из VK_BOT_RECRUITER_URL на сервере.
              </p>
              <input
                type="url"
                className="form-control"
                value={recruiter_url}
                onChange={(e) => setRecruiter_url(e.target.value)}
                placeholder="https://vk.com/id… или https://vk.me/…"
              />
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

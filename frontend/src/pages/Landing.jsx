import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSettings } from '../api/client'

export default function Landing() {
  const navigate = useNavigate()
  const [settings, setSettings] = useState({ vk_public_url: '' })

  useEffect(() => {
    getSettings().then(setSettings).catch(() => {})
  }, [])

  return (
    <div className="mx-auto" style={{ maxWidth: 720 }}>
      <div className="card vk-card border-0 shadow-none">
        <div className="card-body p-4 p-md-5">
          <h1 className="h2 mb-3">OVOSHI</h1>
          <p className="lead text-secondary">
            Мы ценим киберспортивный рост участников и поощряем их.
          </p>
          <ul className="mb-4 ps-3">
            <li>Ежедневные розыгрыши</li>
            <li>Турниры</li>
            <li>Клановые эвенты</li>
            <li>Стримы</li>
            <li>Социальная активность</li>
          </ul>
          <p className="mb-3">Ждём тебя в своих рядах.</p>
          {settings.vk_public_url && (
            <p className="mb-3">
              <a href={settings.vk_public_url} target="_blank" rel="noopener noreferrer">Паблик клана ВКонтакте</a>
            </p>
          )}
          <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
            <button
              type="button"
              className="ovoshi-btn-login"
              onClick={() => navigate('/login')}
            >
              <span className="ovoshi-btn-login__label">Войти на сайт</span>
            </button>
            <span className="text-muted small">только для участников клана (не гостей); гости — через бота ВК</span>
          </div>
          <p className="text-muted small mb-0">
            {settings.vk_public_url ? (
              <>
                Новый участник?{' '}
                <a href={settings.vk_public_url} target="_blank" rel="noopener noreferrer">
                  Зарегистрируйтесь через сообщество ВКонтакте
                </a>
                {' '}
                (напишите боту в группе).
              </>
            ) : (
              <>Новый участник — только через сообщество ВКонтакте (бот в группе клана); ссылку на группу задаёт лидер в настройках сайта.</>
            )}
          </p>
        </div>
      </div>
    </div>
  )
}

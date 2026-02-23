import { useEffect, useState } from 'react'

const appTitle = import.meta.env.VITE_APP_TITLE || 'AI-Based Timetable Automation'
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const cards = [
  {
    title: 'Frontend',
    value: 'React + Vite',
    desc: 'Coordinator dashboard foundation with module navigation.',
  },
  {
    title: 'Backend',
    value: 'FastAPI',
    desc: 'Tenant-aware API endpoints for users, scopes, and generation.',
  },
  {
    title: 'Database',
    value: 'PostgreSQL Schema',
    desc: 'Tenant, RBAC, scope, and timetable entities included.',
  },
]

export default function App() {
  const [health, setHealth] = useState('Checking...')
  const [dbHealth, setDbHealth] = useState('Checking...')

  useEffect(() => {
    const checkServices = async () => {
      try {
        const healthResponse = await fetch(`${apiBaseUrl}/health`)
        const healthData = await healthResponse.json()
        setHealth(healthData.status === 'ok' ? 'Online' : 'Unavailable')
      } catch {
        setHealth('Unavailable')
      }

      try {
        const dbResponse = await fetch(`${apiBaseUrl}/db-health`)
        const dbData = await dbResponse.json()
        setDbHealth(dbData.database === 'connected' ? `Connected (${dbData.method})` : 'Unavailable')
      } catch {
        setDbHealth('Unavailable')
      }
    }

    checkServices()
  }, [])

  return (
    <main style={{ fontFamily: 'Arial, sans-serif', padding: '2rem', maxWidth: 900, margin: '0 auto' }}>
      <h1>{appTitle}</h1>
      <p>Multi-tenant baseline implementation scaffold.</p>
      <p>
        API Base URL: <code>{apiBaseUrl}</code>
      </p>

      <section style={{ marginBottom: '1.5rem', border: '1px solid #ddd', borderRadius: 10, padding: '1rem' }}>
        <h2 style={{ marginTop: 0 }}>System Review</h2>
        <p>
          <strong>Backend:</strong> {health}
        </p>
        <p>
          <strong>Database:</strong> {dbHealth}
        </p>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: '1rem' }}>
        {cards.map((card) => (
          <article key={card.title} style={{ border: '1px solid #ddd', borderRadius: 10, padding: '1rem' }}>
            <h3>{card.title}</h3>
            <strong>{card.value}</strong>
            <p>{card.desc}</p>
          </article>
        ))}
      </section>
    </main>
  )
}

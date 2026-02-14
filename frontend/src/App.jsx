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
  {
    title: 'Testing',
    value: 'Pytest',
    desc: 'API health, user lifecycle, and timetable generation tests.',
  },
]

export default function App() {
  return (
    <main style={{ fontFamily: 'Arial, sans-serif', padding: '2rem', maxWidth: 900, margin: '0 auto' }}>
      <h1>{appTitle}</h1>
      <p>Multi-tenant baseline implementation scaffold.</p>
      <p>
        API Base URL: <code>{apiBaseUrl}</code>
      </p>
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

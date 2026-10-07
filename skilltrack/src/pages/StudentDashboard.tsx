import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, errorMessage } from '../api'
import Card from '../components/Card'
import { Icon, StudentIllustration } from '../components/AuthLayout'
import { semesters } from '../data/studentData'
import { useFetch } from '../useFetch'
import type { FetchState } from '../useFetch'

type LevelStatus = 'cleared' | 'active' | 'locked' | 'removed'

interface Dashboard {
  user: { name: string; department: string | null; semester: number | null }
  domains: { id: number; name: string }[]
  points_to_unlock: number
  max_attempts: number | null
  enrollment: { domain_id: number; domain: string; status: string; is_common: boolean; points: number; current_level: number } | null
  levels: { id: number; number: number; name: string; status: LevelStatus; attempts_used: number; score: number | null; first_attempt: boolean }[]
  slots: { id: number; starts_at: string; venue: string; seats_left: number }[]
  booked_slot_id: number | null
  skill_gap: { level_name: string; weak: { topic: string; score: number }[] } | null
  certificates: { code: string; title: string; issued_at: string; first_attempt: boolean }[]
}

interface AiRec { domain: string; match: number; reason: string }
interface AiPrep {
  level: string
  focus_topics: { topic: string; why: string }[]
  study_plan: string[]
  requirements: string[]
}
interface AiAdvice { topic: string; tips: string[] }

const PATHS = {
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z',
  star: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z',
  flag: 'M5 21V4m0 0h11l-2 4 2 4H5',
  book: 'M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2V5zM4 19a2 2 0 002 2h13',
  calendar: 'M7 3v4M17 3v4M4 9h16M5 5h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z',
  chart: 'M4 20V10M10 20V4M16 20v-8M22 20H2',
  ribbon: 'M12 14a6 6 0 100-12 6 6 0 000 12zM8.5 13L7 22l5-3 5 3-1.5-9',
  cap: 'M12 3L2 8l10 5 10-5-10-5zM6 10.5V15c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5',
  check: 'M5 13l4 4L19 7',
  lock: 'M16 11V7a4 4 0 00-8 0v4M6 11h12a1 1 0 011 1v8a1 1 0 01-1 1H6a1 1 0 01-1-1v-8a1 1 0 011-1z',
  chat: 'M4 5h16v11H9l-5 4V5z',
}

const ico = (name: keyof typeof PATHS, className = 'h-4 w-4') => (
  <Icon className={className}><path strokeLinecap="round" strokeLinejoin="round" d={PATHS[name]} /></Icon>
)

const primaryBtn =
  'group inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:-translate-y-0.5 hover:bg-indigo-500 hover:shadow-indigo-500/40 active:translate-y-0 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none'

function AiStatus({ state }: { state: FetchState<unknown> }) {
  if (state.loading) {
    return (
      <p className="flex items-center gap-2 rounded-xl bg-indigo-50 px-3 py-2 text-sm text-indigo-600">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
        Asking Gemini…
      </p>
    )
  }
  if (state.error) {
    return (
      <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
        {state.error} <button onClick={state.retry} className="ml-1 font-semibold text-indigo-600 underline">Try again</button>
      </p>
    )
  }
  return null
}

function StatTile({ label, value, icon }: { label: string; value: ReactNode; icon: ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white/15 px-4 py-3 backdrop-blur transition hover:bg-white/25">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/25">{icon}</span>
      <div>
        <div className="text-xl font-bold leading-none">{value}</div>
        <div className="mt-1 text-xs text-white/80">{label}</div>
      </div>
    </div>
  )
}

const STATUS_STYLE: Record<LevelStatus, string> = {
  cleared: 'bg-emerald-100 text-emerald-700',
  active: 'bg-indigo-100 text-indigo-700',
  locked: 'bg-slate-100 text-slate-500',
  removed: 'bg-red-100 text-red-700',
}

const STATUS_DOT: Record<LevelStatus, string> = {
  cleared: 'bg-emerald-500 text-white',
  active: 'bg-gray-900 text-white ring-4 ring-gray-100',
  locked: 'bg-slate-100 text-slate-400',
  removed: 'bg-red-100 text-red-500',
}

const STATUS_LABEL: Record<LevelStatus, string> = {
  cleared: 'Cleared', active: 'In progress', locked: 'Locked', removed: 'Removed',
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

export default function StudentDashboard() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [loadError, setLoadError] = useState('')
  const [actionError, setActionError] = useState('')
  const [pickDomain, setPickDomain] = useState<number | ''>('')

  const hasActiveLevel = !!data?.levels.some((l) => l.status === 'active')
  const recs = useFetch<{ recommendations: AiRec[] }>(data && (data.user.semester ?? 1) >= 3 ? '/ai/recommendations' : null)
  // Load the AI cards one after another, so the free Gemini tier's requests-per-minute limit is not hit
  const prep = useFetch<AiPrep>(hasActiveLevel && !recs.loading ? '/ai/prep' : null)
  const advice = useFetch<{ advice: AiAdvice[] }>(data?.skill_gap && !recs.loading && !prep.loading ? '/ai/gap-advice' : null)

  const load = useCallback(async () => {
    try {
      const res = await api.get<Dashboard>('/me/dashboard')
      setData(res.data)
      setLoadError('')
    } catch (err) {
      setLoadError(errorMessage(err, 'Could not load your dashboard'))
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function act(request: () => Promise<unknown>) {
    setActionError('')
    try {
      await request()
      await load()
    } catch (err) {
      setActionError(errorMessage(err))
    }
  }

  async function downloadCertificate(code: string) {
    setActionError('')
    try {
      const res = await api.get<Blob>(`/me/certificates/${code}/pdf`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `${code}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setActionError(errorMessage(err, 'Could not download the certificate'))
    }
  }

  if (loadError) return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{loadError}</p>
  if (!data) {
    return (
      <div className="flex items-center gap-3 text-sm text-slate-500">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
        Loading your dashboard…
      </div>
    )
  }

  const { user, enrollment, levels, slots } = data
  const semester = user.semester ?? 1
  const activeLevel = levels.find((l) => l.status === 'active')
  const canPickDomain = semester >= 3 && (!enrollment || enrollment.status === 'removed' || enrollment.points >= data.points_to_unlock)
  const enrolledIds = new Set(enrollment ? [enrollment.domain_id] : [])
  const pointsPct = enrollment ? Math.min(100, Math.round((enrollment.points / data.points_to_unlock) * 100)) : 0
  const badges = levels.filter((l) => l.first_attempt).length
  const clearedCount = levels.filter((l) => l.status === 'cleared').length
  const semPct = semesters.length > 1 ? ((semester - 1) / (semesters.length - 1)) * 100 : 0
  const edge = `${50 / semesters.length}%`

  return (
    <div className="space-y-6">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl bg-slate-950 p-6 text-white shadow-2xl sm:p-10 xl:min-h-72">
        <div className="pointer-events-none absolute -right-20 -top-20 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-1/4 h-96 w-96 rounded-full bg-purple-600/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-1/4 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="relative z-10 max-w-xl xl:max-w-[55%]">
          <p className="text-sm font-medium text-white/80">Welcome back 👋</p>
          <h1 className="mt-1 text-3xl font-bold sm:text-4xl">{user.name}</h1>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
            {user.department && <span className="rounded-full bg-white/20 px-3 py-1">{user.department}</span>}
            <span className="rounded-full bg-white/20 px-3 py-1">Semester {semester}</span>
            {enrollment && <span className="rounded-full bg-amber-300/90 px-3 py-1 text-amber-950">{enrollment.domain}</span>}
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-2 2xl:grid-cols-4">
            <StatTile label="Points" value={enrollment?.points ?? 0} icon={ico('star', 'h-5 w-5')} />
            <StatTile label="Levels cleared" value={`${clearedCount}/${levels.length}`} icon={ico('flag', 'h-5 w-5')} />
            <StatTile label="First-try badges" value={badges} icon={ico('sparkle', 'h-5 w-5')} />
            <StatTile label="Certificates" value={data.certificates.length} icon={ico('ribbon', 'h-5 w-5')} />
          </div>
        </div>
        <div className="pointer-events-none absolute -bottom-2 right-6 hidden w-72 xl:block">
          <StudentIllustration />
        </div>
      </section>

      {actionError && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</p>
      )}

      {/* Semester stepper */}
      <Card title="Semester progress" icon={ico('cap')}>
        <div className="relative">
          <div className="absolute top-5 h-1.5 rounded-full bg-slate-100/80 shadow-inner" style={{ left: edge, right: edge }}>
            <div className="h-full rounded-full bg-linear-to-r from-indigo-500 to-purple-500 shadow-md transition-all duration-700" style={{ width: `${semPct}%` }} />
          </div>
          <ol className="relative grid" style={{ gridTemplateColumns: `repeat(${semesters.length}, minmax(0, 1fr))` }}>
            {semesters.map((s) => {
              const state = s.sem < semester ? 'done' : s.sem === semester ? 'current' : 'upcoming'
              const dot = {
                done: 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30',
                current: 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/40 ring-4 ring-indigo-500/20',
                upcoming: 'border-2 border-slate-200 bg-white text-slate-400',
              }[state]
              return (
                <li key={s.sem} className="flex flex-col items-center text-center">
                  <span className={`relative flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${dot}`}>
                    {state === 'done' ? ico('check', 'h-5 w-5') : s.sem}
                    {state === 'current' && <span className="absolute inset-0 animate-ping rounded-full bg-indigo-400/40" />}
                  </span>
                  <span className={`mt-2 text-sm font-semibold ${state === 'upcoming' ? 'text-slate-400' : 'text-slate-800'}`}>Sem {s.sem}</span>
                  <span className="text-xs text-slate-500">{s.label}</span>
                </li>
              )
            })}
          </ol>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="AI recommended domains (top 3)" icon={ico('sparkle')}>
          <AiStatus state={recs} />
          <ul className="space-y-4">
            {(recs.data?.recommendations ?? []).map((r) => (
              <li key={r.domain} className="rounded-xl bg-slate-50 p-3">
                <div className="flex justify-between text-sm font-semibold">
                  <span>{r.domain}</span><span className="text-indigo-600">{r.match}% match</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-100/80 shadow-inner">
                  <div className="h-2 rounded-full bg-linear-to-r from-indigo-500 to-purple-500 transition-all duration-700" style={{ width: `${r.match}%` }} />
                </div>
                <p className="mt-2 text-xs text-slate-500">{r.reason}</p>
              </li>
            ))}
          </ul>

          {semester < 3 ? (
            <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">Semesters 1–2 use common assessments. Domain selection opens in Semester 3.</p>
          ) : canPickDomain ? (
            <div className="mt-4 flex gap-2">
              <select
                value={pickDomain}
                onChange={(e) => setPickDomain(e.target.value ? Number(e.target.value) : '')}
                className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
              >
                <option value="">Choose a domain…</option>
                {data.domains.filter((d) => !enrolledIds.has(d.id)).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
              <button
                disabled={pickDomain === ''}
                onClick={() => act(() => api.post('/enrollments', { domain_id: pickDomain }))}
                className={primaryBtn}
              >
                Enroll
              </button>
            </div>
          ) : (
            <p className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">Earn {data.points_to_unlock} points to unlock another domain.</p>
          )}
        </Card>

        <Card title="Points & badges" icon={ico('star')}>
          {enrollment ? (
            <>
              {enrollment.is_common ? (
                <>
                  <div className="text-4xl font-bold text-slate-900">{enrollment.points} <span className="text-base font-normal text-slate-500">pts</span></div>
                  <p className="mt-2 text-sm text-slate-500">Domain selection opens in Semester 3, based on how you do in these common tests.</p>
                </>
              ) : (
                <>
                  <div className="text-4xl font-bold text-slate-900">
                    {enrollment.points} <span className="text-base font-normal text-slate-500">/ {data.points_to_unlock} pts</span>
                  </div>
                  <div className="mt-3 h-3 rounded-full bg-slate-100/80 shadow-inner">
                    <div className="h-3 rounded-full bg-linear-to-r from-indigo-500 to-purple-500 transition-all duration-700" style={{ width: `${pointsPct}%` }} />
                  </div>
                  <p className="mt-2 text-sm text-slate-500">
                    {enrollment.points >= data.points_to_unlock
                      ? 'You can unlock another domain.'
                      : `Earn ${data.points_to_unlock - enrollment.points} more points to unlock another domain.`}
                  </p>
                </>
              )}
              <p className="mt-4 inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-800">
                🏅 First-attempt badges: {badges}
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-500">Enroll in a domain to start earning points and badges.</p>
          )}
        </Card>
      </div>

      {enrollment && (
        <Card title={`${enrollment.domain} · Levels`} icon={ico('flag')}>
          <ul className="space-y-2">
            {levels.map((l) => (
              <li key={l.id} className={`flex flex-wrap items-center gap-3 rounded-xl border p-3 transition hover:shadow-md ${l.status === 'active' ? 'border-indigo-200 bg-indigo-50/50' : 'border-slate-100'}`}>
                <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${STATUS_DOT[l.status]}`}>
                  {l.status === 'cleared' ? ico('check', 'h-5 w-5') : l.status === 'locked' ? ico('lock') : l.number}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold">{l.name} {l.first_attempt && <span title="Cleared on first attempt">🏅</span>}</div>
                  <div className="text-xs text-slate-500">
                    Attempts: {l.attempts_used}{data.max_attempts !== null && `/${data.max_attempts}`}{l.score !== null && ` · Last score ${l.score}%`}
                  </div>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLE[l.status]}`}>{STATUS_LABEL[l.status]}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-400">
            {data.max_attempts !== null
              ? `Failing all ${data.max_attempts} attempts removes you from the domain.`
              : 'Your test opens for the semester you are in. You can retake it until you clear it.'}
          </p>
        </Card>
      )}

      {activeLevel && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title={`Prepare for ${activeLevel.name}`} icon={ico('book')}>
            <AiStatus state={prep} />
            {prep.data && (
              <div className="space-y-4">
                <div>
                  <p className="mb-1.5 text-sm font-semibold">What to learn</p>
                  <ul className="space-y-1.5 text-sm text-slate-600">
                    {prep.data.focus_topics.map((t) => (
                      <li key={t.topic} className="rounded-lg bg-slate-50 px-3 py-2"><span className="font-semibold text-slate-800">{t.topic}</span> — {t.why}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="mb-1.5 text-sm font-semibold">Study plan</p>
                  <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600 marker:font-semibold marker:text-indigo-500">
                    {prep.data.study_plan.map((s) => <li key={s}>{s}</li>)}
                  </ol>
                </div>
                <div>
                  <p className="mb-1.5 text-sm font-semibold">Requirements</p>
                  <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 marker:text-indigo-500">
                    {prep.data.requirements.map((t) => <li key={t}>{t}</li>)}
                  </ul>
                </div>
              </div>
            )}
            <button className={`${primaryBtn} mt-4`}>Take a mock test (from home)</button>
          </Card>

          <Card title="Book your test slot" icon={ico('calendar')}>
            {slots.length === 0 && <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">No upcoming slots for this level yet. Ask your admin or track owner to schedule one.</p>}
            <ul className="space-y-3">
              {slots.map((s) => {
                const booked = s.id === data.booked_slot_id
                return (
                  <li key={s.id} className={`flex items-center justify-between gap-3 rounded-xl border p-3 text-sm transition hover:shadow-md ${booked ? 'border-emerald-300 bg-emerald-50' : 'border-slate-100'}`}>
                    <div className="flex items-center gap-3">
                      <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${booked ? 'bg-emerald-500 text-white' : 'bg-indigo-50 text-indigo-600'}`}>{ico('calendar', 'h-5 w-5')}</span>
                      <div>
                        <div className="font-semibold">{fmtDate(s.starts_at)} · {fmtTime(s.starts_at)}</div>
                        <div className="text-xs text-slate-500">{s.venue} · {s.seats_left} seats left</div>
                      </div>
                    </div>
                    {booked ? (
                      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Booked ✓</span>
                    ) : (
                      <button
                        disabled={s.seats_left === 0}
                        onClick={() => act(() => api.post(`/slots/${s.id}/book`))}
                        className={primaryBtn}
                      >
                        {data.booked_slot_id ? 'Switch' : 'Book'}
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={data.skill_gap ? `Skill-gap analysis · ${data.skill_gap.level_name}` : 'Skill-gap analysis'} icon={ico('chart')}>
          {data.skill_gap ? (
            <>
              <ul className="space-y-3">
                {data.skill_gap.weak.map((w) => (
                  <li key={w.topic} className="text-sm">
                    <div className="flex justify-between font-medium"><span>{w.topic}</span><span className="text-red-600">{w.score}%</span></div>
                    <div className="mt-1.5 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-red-500" style={{ width: `${w.score}%` }} /></div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-slate-500">Topics to improve before your next attempt.</p>
              <div className="mt-4 border-t border-slate-100 pt-4">
                <p className="flex items-center gap-2 text-sm font-semibold">{ico('sparkle', 'h-4 w-4 text-indigo-500')} How to improve</p>
                <div className="mt-2"><AiStatus state={advice} /></div>
                <ul className="mt-2 space-y-3 text-sm text-slate-600">
                  {advice.data?.advice.map((a) => (
                    <li key={a.topic} className="rounded-xl bg-slate-50 p-3">
                      <span className="font-semibold text-slate-800">{a.topic}</span>
                      <ul className="mt-1 list-disc pl-5 marker:text-indigo-500">{a.tips.map((t) => <li key={t}>{t}</li>)}</ul>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">Your skill-gap analysis appears after your first test.</p>
          )}
        </Card>

        <Card title="Certificates" icon={ico('ribbon')}>
          {data.certificates.length === 0 && <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500">Clear a test to earn your first certificate.</p>}
          <ul className="space-y-3">
            {data.certificates.map((c) => (
              <li key={c.code} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 p-3 text-sm transition hover:shadow-md">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600">{ico('ribbon', 'h-5 w-5')}</span>
                  <div>
                    <div className="font-semibold">{c.title} {c.first_attempt && '🏅'}</div>
                    <div className="text-xs text-slate-500">Issued {fmtDate(c.issued_at)} · {c.code}</div>
                  </div>
                </div>
                <button onClick={() => downloadCertificate(c.code)} className="shrink-0 rounded-lg border border-indigo-200 px-3 py-1.5 text-xs font-semibold text-indigo-600 transition hover:bg-indigo-50">Download PDF</button>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000'
const S_KEY = 'pg_overview_schedule_v1'

async function api(path: string, init?: RequestInit) {
  const r = await fetch(API_BASE + path, init)
  const t = await r.text()
  let data: any
  try { data = JSON.parse(t) } catch { data = t }
  if (!r.ok) throw { status: r.status, data }
  return data
}

function useOverviewSchedule() {
  const [state, setState] = useState<{ids: string[], idx: number}>({ids: [], idx: 0})
  useEffect(() => {
    (async () => {
      let s: any = null
      try { s = JSON.parse(localStorage.getItem(S_KEY) || 'null') } catch {}
      if (s && Array.isArray(s.ids) && typeof s.idx === 'number') { setState(s); return }
      const ids: string[] = await api('/v1/events/ids')
      const ids60 = ids.slice(0, 60)
      for (let i = ids60.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random()*(i+1));
        ;[ids60[i], ids60[j]] = [ids60[j], ids60[i]]
      }
      const ns = { ids: ids60, idx: 0 }
      localStorage.setItem(S_KEY, JSON.stringify(ns))
      setState(ns)
    })()
  }, [])
  const next = useCallback(() => {
    setState(s => {
      const idx = Math.min(s.idx + 1, s.ids.length)
      const ns = { ...s, idx }
      localStorage.setItem(S_KEY, JSON.stringify(ns))
      return ns
    })
  }, [])
  const reset = useCallback(() => {
    localStorage.removeItem(S_KEY); window.location.reload()
  }, [])
  const period = useMemo(() => ({ year: Math.floor(state.idx/12)+1, month: (state.idx%12)+1 }), [state.idx])
  return { state, period, next, reset }
}

function yen(n: any){ if(n==null||isNaN(n)) return ''; try { return Number(n).toLocaleString('ja-JP')} catch { return String(n)} }

export default function Home(){
  const [text, setText] = useState('')
  const [res, setRes] = useState<any|null>(null)
  const [loading, setLoading] = useState(false)
  const { state, period, next, reset } = useOverviewSchedule()
  const [actual, setActual] = useState<any|null>(null)

  const predict = useCallback(async () => {
    setLoading(true); setRes(null); setActual(null)
    try {
      const r = await api('/v1/budget/predict', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_text: text })
      })
      setRes(r)
    } catch(e){ setRes({ error: e }) }
    finally { setLoading(false) }
  }, [text])

  const showActual = useCallback(async () => {
    try {
      const id = state.ids[Math.min(state.idx, state.ids.length-1)]
      const m = await api(`/v1/events/meta?budget_id=${encodeURIComponent(id)}`)
      setActual({ name: m['事業名'] ?? m['jigyo_mei'] ?? '', init: m['当初予算'] ?? m['tosho_yosan'] })
    } catch(e){ setActual({ error: true }) }
  }, [state])

  return (
    <div style={{fontFamily: 'ui-sans-serif, system-ui', padding: 20}}>
      <h1>Policy Game Frontend</h1>

      <section style={{marginTop: 8, padding: 12, border: '1px solid #ddd', borderRadius: 8}}>
        <h2>目的と課題</h2>
        <div>{period.year}年 {period.month}月</div>
        <div style={{marginTop: 8}}>
          <button onClick={next}>更新</button>
          <button onClick={reset} style={{marginLeft: 8}}>最初から</button>
        </div>
      </section>

      <section style={{marginTop: 12, padding: 12, border: '1px solid #ddd', borderRadius: 8}}>
        <h2>予算推定</h2>
        <input value={text} onChange={e=>setText(e.target.value)} placeholder='テキストを入力' style={{width:'100%', padding:8}} />
        <div style={{marginTop:8}}>
          <button onClick={predict} disabled={loading || !text.trim()}>テキストで予測</button>
          {res && !res.error && (
            <>
              <div style={{marginTop:8, color:'#64748b'}}>✅ 推定当初予算</div>
              <div style={{fontWeight:700, fontSize:22}}>{yen(res.estimate_initial)} 円</div>
              <div style={{marginTop:8}}>
                <button onClick={showActual}>今月の事業の当初予算を確認</button>
              </div>
              {actual && !actual.error && (
                <div style={{marginTop:6, color:'#64748b'}}>事業名: {actual.name} / 当初予算: {yen(actual.init)} 円</div>
              )}
            </>
          )}
          {res && res.error && <pre style={{color:'crimson'}}>{JSON.stringify(res.error, null, 2)}</pre>}
        </div>
      </section>

      {res && res.topk && Array.isArray(res.topk) && (
        <section style={{marginTop: 12}}>
          <h3 style={{color:'#64748b'}}>類似事業</h3>
          <div style={{display:'grid', gridTemplateColumns:'1fr', gap:12}}>
            {res.topk.map((r:any)=>{
              const sim = Number(r.similarity ?? 0)
              const sim01 = Math.max(0, Math.min(1, (sim + 1) / 2))
              const simPct = (sim01*100).toFixed(0)
              return (
                <div key={r.rank} style={{border:'1px solid #ddd', borderRadius:12, padding:12, background:'#0b1020', color:'#e5e7eb'}}>
                  <div style={{display:'flex', alignItems:'center', gap:8}}>
                    <span style={{padding:'2px 8px', border:'1px solid #334155', borderRadius:999}}>#${r.rank}</span>
                    <span style={{fontWeight:700}}>{r.name ?? ''}</span>
                  </div>
                  <div style={{marginTop:6, width:'100%', height:8, background:'#0b1020', border:'1px solid #334155', borderRadius:999}}>
                    <div style={{height:'100%', width:`${simPct}%`, background:'linear-gradient(135deg, #60a5fa, #a78bfa)', borderRadius:999}} />
                  </div>
                  <div style={{display:'flex', justifyContent:'space-between', marginTop:6, color:'#94a3b8'}}>
                    <span>sim {sim.toFixed(3)} ({simPct}%)</span>
                    <span>当初 {yen(r.initial_budget)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}


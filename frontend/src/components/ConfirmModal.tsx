import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'

interface Props {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  titleKey?: string
  messageKey?: string
  confirmKey?: string
  cancelKey?: string
  variant?: 'danger' | 'primary'
}

export default function ConfirmModal({ open, onClose, onConfirm, titleKey = 'app.controls.resetConfirmTitle', messageKey = 'app.controls.resetConfirmMessage', confirmKey = 'app.controls.resetConfirmOk', cancelKey = 'app.controls.resetCancel', variant = 'danger' }: Props) {
  const { t, lang } = useI18n()
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768)
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="clan-details-backdrop" onClick={onClose} style={{ zIndex: 110, padding: isMobile ? 'env(safe-area-inset-top) 12px env(safe-area-inset-bottom)' : undefined, overflow: 'auto' }}>
      <div className="clan-details-panel" onClick={e => e.stopPropagation()} style={{
        width: isMobile ? '92vw' : '420px',
        maxWidth: '92vw',
        height: 'auto',
        maxHeight: isMobile ? '90dvh' : '80vh',
        display: 'flex',
        flexDirection: 'column',
        padding: 0,
        background: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: 12,
        overflow: 'hidden',
        boxShadow: '0 20px 48px rgba(0,0,0,0.8)',
      }}>
        <header style={{ padding: isMobile ? '14px 16px 10px' : '16px 18px', borderBottom: '1px solid #21262d', background: '#161b22', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 20 }}>⚠️</span>
          <h2 style={{ fontSize: isMobile ? 15 : 16, margin: 0, color: '#e6edf3', fontWeight: 700 }}>{t(titleKey)}</h2>
          <button className="god-close" onClick={onClose} style={{ marginLeft: 'auto', fontSize: 20, cursor: 'pointer', color: '#8b949e', background: 'transparent', border: 'none' }} aria-label="close">×</button>
        </header>
        <div style={{ padding: isMobile ? '16px' : '18px', color: '#c9d1d9', fontSize: 13, lineHeight: 1.5 }}>
          <p style={{ margin: 0 }}>{t(messageKey)}</p>
          <p style={{ margin: '10px 0 0', fontSize: 12, color: '#8b949e' }}>{lang === 'vi' ? 'Gợi ý: dùng Save trước khi reset nếu muốn giữ thế giới.' : lang === 'fr' ? 'Astuce : Sauvegardez avant de réinitialiser pour garder le monde.' : 'Tip: Save before reset to keep the world.'}</p>
        </div>
        <footer style={{ padding: isMobile ? '10px 16px max(12px, env(safe-area-inset-bottom))' : '12px 18px', borderTop: '1px solid #21262d', background: '#161b22', display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ padding: isMobile ? '10px 16px' : '6px 14px', background: '#21262d', border: '1px solid #30363d', borderRadius: 6, color: '#c9d1d9', cursor: 'pointer', minHeight: isMobile ? 44 : undefined, touchAction: 'manipulation' }}>{t(cancelKey)}</button>
          <button onClick={() => { onClose(); onConfirm() }} style={{ padding: isMobile ? '10px 16px' : '6px 14px', background: variant === 'danger' ? '#da3633' : '#238636', border: `1px solid ${variant === 'danger' ? '#f85149' : '#2ea043'}`, borderRadius: 6, color: '#fff', cursor: 'pointer', fontWeight: 700, minHeight: isMobile ? 44 : undefined, touchAction: 'manipulation' }}>{t(confirmKey)}</button>
        </footer>
      </div>
    </div>
  )
}

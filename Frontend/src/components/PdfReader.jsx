import { useEffect, useRef } from 'react'

export default function PdfReader({ title, viewUrl, downloadUrl, onClose }) {
  const closeRef = useRef(null)

  useEffect(() => {
    const previous = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()

    function onKey(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      if (previous instanceof HTMLElement) previous.focus()
    }
  }, [onClose])

  return (
    <div className="reader" role="dialog" aria-modal="true" aria-label={title}>
      <div className="reader-bar">
        <p>{title}</p>
        <div className="reader-actions">
          <a href={downloadUrl}>Download the PDF</a>
          <button ref={closeRef} type="button" onClick={onClose}>Close</button>
        </div>
      </div>
      <iframe className="reader-frame" title={title} src={viewUrl} />
    </div>
  )
}

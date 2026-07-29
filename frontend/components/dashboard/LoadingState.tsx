export default function LoadingState() {
  return (
    <div className="empty-state" aria-live="polite">
      <div className="loader" />
      <h3>Consultando Gmail</h3>
      <p>Estamos recuperando los mensajes más recientes.</p>
    </div>
  );
}

export default function Header({ saldo, onReiniciar }) {
  return (
    <header>
      <h1>Casino - Modelación y Simulación</h1>
      <div className="saldo-box">
        <span className="saldo-label">Saldo</span>
        <span className="saldo-valor">{Math.round(saldo * 100) / 100}</span>
        <button onClick={onReiniciar}>Reiniciar saldo</button>
      </div>
    </header>
  );
}

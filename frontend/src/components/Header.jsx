export default function Header({ saldo, onReiniciar }) {
  return (
    <header>
      <h1>🎰 Casino - Modelación y Simulación</h1>
      <div className="saldo-box">
        Saldo: <span>{Math.round(saldo * 100) / 100}</span> 💰
        <button onClick={onReiniciar}>Reiniciar saldo</button>
      </div>
    </header>
  );
}

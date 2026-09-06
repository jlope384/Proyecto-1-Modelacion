// Avanza una rotación (en grados) siempre hacia adelante hasta llegar
// exactamente al ángulo `base` (mod 360), dando un par de vueltas extra
// para que la animación de aterrizaje se sienta como un giro real.
export function nextRot(prev, base) {
  const diff = (((base - prev) % 360) + 360) % 360;
  return prev + 360 * 2 + diff;
}

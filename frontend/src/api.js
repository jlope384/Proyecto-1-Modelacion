// Llamadas a la API Flask (backend/app.py). Vite hace proxy de /api a 127.0.0.1:5000.
export async function api(ruta, opciones) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch {
    throw new Error("No hay conexión con la API. ¿Está corriendo `python app.py` en backend/?");
  }
  let cuerpo = {};
  try {
    cuerpo = await respuesta.json();
  } catch {
    throw new Error(`La API respondió ${respuesta.status} sin JSON. ¿Está corriendo el backend?`);
  }
  if (!respuesta.ok) throw new Error(cuerpo.error || `Error ${respuesta.status}`);
  return cuerpo;
}

export function post(ruta, cuerpo) {
  return api(ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo || {}),
  });
}

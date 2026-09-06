import { useCallback, useEffect, useRef, useState } from "react";

// Muestra un resultado como toast efímero: se limpia solo a los `duracion` ms.
// Si se llama a `mostrar` de nuevo antes de que expire, reinicia el temporizador.
export function useToast(duracion = 2000) {
  const [resultado, setResultado] = useState(null);
  const timeoutRef = useRef(null);

  const mostrar = useCallback(
    (texto, tipo) => {
      clearTimeout(timeoutRef.current);
      setResultado({ texto, tipo, id: Date.now() });
      timeoutRef.current = setTimeout(() => setResultado(null), duracion);
    },
    [duracion]
  );

  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  return [resultado, mostrar];
}

# Dashboard de inversiones (SBS + benchmarks)

Dashboard personal en un único `index.html` autocontenido: cartera MyInvestor + cripto, acciones de Trading 212 y comparativa contra benchmarks.

## Modelo de privacidad (importante)

- **El código no lleva cifras.** `DEFAULT_RECORDS` se neutralizó: antes tenía saldos reales incrustados y por eso no se podía publicar la página.
- **Los datos viajan cifrados.** Desde 2026-10-26 viven en la rama `datos` de este repositorio, fichero `cartera.enc.json`, que solo guarda un envoltorio:

  ```json
  { "v": 2, "kdf": "PBKDF2-SHA256", "iter": 250000, "salt": "...", "iv": "...", "ct": "..." }
  ```

  Algoritmo: AES-256-GCM, clave derivada del PIN con PBKDF2-SHA256 (250.000 iteraciones). La clave vive **solo en memoria**; el PIN nunca se envía ni se guarda en disco (como mucho en `sessionStorage` si marcas "recordar mientras el navegador esté abierto").
- Sin el PIN correcto no se puede leer nada, aunque el fichero sea público.
- **Escribir exige un token de GitHub** (fine-grained, solo `dashboard-inversiones`, permiso *Contents: Read and write*). Se pega una vez en "Nube GitHub" y viaja **dentro** del payload cifrado (`cloud.token`), así que los demás dispositivos lo obtienen al poner el PIN. Nadie sin PIN puede escribir.
- **El PIN es irrecuperable.** Si se pierde, los datos cifrados no se pueden descifrar. Guarda una copia en claro fuera de git.

Antes los datos estaban en npoint (`https://api.npoint.io/00c7f3df788f252ae701`): algunas redes de empresa lo bloquean y aceptaba escrituras de cualquiera. Ahora solo se lee para migrar: si la rama `datos` está vacía, la web prueba npoint y luego la copia local del navegador.

## Sincronización entre dispositivos

- Cada cambio se guarda al momento en el navegador y, agrupado, en la nube (sin pulsar nada).
- La web comprueba la nube cada minuto y al volver a la pestaña (no mientras hay una ventana de edición abierta).
- Fusión a 3 bandas (último estado sincronizado, local y remoto) por `id` de registro y de activo: los cambios de dos dispositivos se juntan. Si los dos tocan lo mismo, gana el que guarda; si uno borra y otro edita, se conserva. Los registros antiguos reciben un id determinista (`rAAAAMMDD_n`) para que coincidan entre dispositivos.
- Escritura con el `sha` del fichero (control de concurrencia de GitHub): si otro dispositivo guardó en medio, se vuelve a leer, se fusiona y se reintenta.
- Sin conexión, los cambios quedan marcados (`inv_cloud_dirty_v1`) y se suben solos al volver la red.

## Uso

1. Abrir la URL publicada (GitHub Pages).
2. Introducir el PIN: el navegador descarga el envoltorio, deriva la clave y descifra.
3. Editar saldos: se guardan cifrados de vuelta en la nube.

Abrir el fichero en local con `file://` **no** sincroniza: el navegador bloquea el `fetch` desde `file://`.

## Cuentas, registros parciales y objetivos (2026-10)

- Cada activo pertenece a una **cuenta** (`pillar`): `myinvestor` o `crypto`. Trading 212 es una cuenta suelta, no un activo, y su peso objetivo vive en `appSettings.stockTarget`.
- Un registro puede **actualizar solo una cuenta**. Los activos que no se informan se **arrastran** desde el último valor conocido en `calculateProcessedData()`.
- Aportaciones desglosadas en `record.flows = { myinvestor, crypto, t212 }`. `record.aport` sigue guardándose como suma (`myinvestor + crypto`) para no alterar los benchmarks ni los KPI existentes.
- Registros antiguos sin `flows`: toda la aportación se atribuye a fondos, y desde el segundo registro se reparte de forma proporcional al peso previo de fondos/cripto.
- Objetivos con auto-ajuste: al cambiar un `%` el resto se reparte proporcionalmente hasta sumar 100. `locked` fija una fila. `order` guarda el orden de arrastre.
- Ajustes locales en `localStorage['inversiones_settings_v1']` y dentro del payload cifrado (`settings`). Compatible hacia atrás: un payload sin `settings` usa los valores por defecto.

## Aportaciones y correcciones de cálculo (2026-10-26)

- **Botón Aportación**: registro rápido (`kind: 'aport'`) que suma cada importe al último saldo conocido del fondo. "Repartir" usa la misma lógica que la calculadora de rebalanceo, y la calculadora tiene un botón para registrar su propuesta.
- **Aportación sin saldos nuevos**: si una cuenta recibe dinero y ninguno de sus saldos cambia, `calculateAllProcessed()` suma la aportación al último saldo (en proporción) en vez de contarla como pérdida. El formulario de saldos avisa y permite elegir el fondo.
- **Precios de benchmark**: un registro sin precio se interpola por fecha entre el anterior y el siguiente (`navSeries`). El formulario ya no copia el precio anterior.
- **Capital inicial**: si el primer registro no lleva aportación, su saldo cuenta como capital invertido (antes salía como ganancia).
- **Volatilidad**: se escala por los días de cada intervalo con retornos logarítmicos. La fórmula anterior la infravaloraba unas 5 veces con registros mensuales (y el Sharpe salía inflado). Los registros con saldos estimados no entran en volatilidad, caída máxima ni beta.
- **Historial**: editar o borrar con un filtro de fechas activo apuntaba a otro registro (índice de la lista filtrada). Ahora se usa `_idx`.
- **Gráficos**: el eje X es temporal (respeta los días reales), hay un tooltip por fecha con lo aportado, la zona de ganancia/pérdida frente a lo aportado, la visibilidad de las series se recuerda y el gráfico de rentabilidad tiene un modo TWR (por defecto) y otro "sobre lo aportado".
- **Estadísticas anuales**: TWR por año (igual que en Riesgo), ganancia en euros y diferencia frente al MSCI.

## Pestaña Riesgo & Comparativa

Métricas calculadas con los registros y el calendario real: TWR (índice encadenado ajustado por flujos), retorno total, TIR/XIRR (bisección), volatilidad anualizada, Sharpe (tasa libre de riesgo 2 %), máximo drawdown y beta frente al MSCI World. Columnas: cartera total, MyInvestor, Cripto, Trading 212, MSCI World y S&P 500. El retorno anual y el Sharpe solo se muestran con al menos 6 meses de histórico.

## Migración desde el formato antiguo (en claro)

Si el JSON remoto todavía no tiene `v: 2`, la página detecta el formato antiguo, pide un PIN (dos veces, mínimo 6 caracteres) y guarda una versión cifrada. Hasta que se hace esa migración, los datos siguen en claro en la nube.

## Copias de seguridad (Nivel 1)

El dashboard no depende de que la nube siga intacta:

- Cada vez que se descarga o se guarda el envoltorio cifrado, se guarda también en el navegador (`inv_cloud_last` y hasta 20 versiones en `inv_cloud_history_v1`).
- Botón **⬇ Copia**: descarga el JSON cifrado a disco (`cartera-cifrada-AAAA-MM-DD.json`).
- Botón **⬆ Restaurar**: abre una copia cifrada con el PIN actual y la convierte en los datos actuales (se sube a la nube).
- Si la nube no responde o la han vaciado, la web ofrece abrir la **última copia local** pidiendo el PIN.

(El antiguo "Nivel 2", que nadie sin PIN pudiera escribir, queda resuelto con el token cifrado de GitHub.)


## Histórico & Crisis (2026-10-26)

Pestaña que aplica tu reparto de hoy (objetivos o saldos actuales, con rebalanceo mensual) a periodos pasados: COVID, subida de tipos de 2022, invasión de Ucrania, SVB, aranceles de 2025, deuda europea 2011, crisis de 2008 y cualquier año natural o rango.

- Datos: `historicos.json`, cierre mensual real de cada ISIN publicado por Financial Times. Se regenera con `python scripts/actualizar_historicos.py`.
- Lo que cotiza en USD (el ETC de oro) se pasa a EUR con el tipo oficial diario del BCE.
- Nada se rellena: un fondo sin precio en el periodo queda fuera y la pestaña dice cuál y cuánto pesaba. La cripto y las acciones sueltas de T212 no tienen serie y se excluyen.
- Única sustitución (desactivable): iShares Developed World (existe desde 08/2025) → Vanguard Global Stock Index EUR, que sigue el mismo índice MSCI World.

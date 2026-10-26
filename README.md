# Dashboard de inversiones (SBS + benchmarks)

Dashboard personal en un único `index.html` autocontenido: cartera MyInvestor + cripto, acciones de Trading 212 y comparativa contra benchmarks.

## Modelo de privacidad (importante)

- **El código no lleva cifras.** `DEFAULT_RECORDS` se neutralizó: antes tenía saldos reales incrustados y por eso no se podía publicar la página.
- **Los datos viajan cifrados.** El JSON remoto (`https://api.npoint.io/00c7f3df788f252ae701`) guarda solo un envoltorio:

  ```json
  { "v": 2, "kdf": "PBKDF2-SHA256", "iter": 250000, "salt": "...", "iv": "...", "ct": "..." }
  ```

  Algoritmo: AES-256-GCM, clave derivada del PIN con PBKDF2-SHA256 (250.000 iteraciones). La clave vive **solo en memoria**; el PIN nunca se envía ni se guarda en disco (como mucho en `sessionStorage` si marcas "recordar mientras el navegador esté abierto").
- Sin el PIN correcto no se puede leer nada, aunque alguien abra la URL o descargue el JSON.
- **El PIN es irrecuperable.** Si se pierde, los datos cifrados no se pueden descifrar. Guarda una copia en claro fuera de git.

⚠️ El endpoint de npoint es público y **acepta escrituras sin autenticación**: quien tenga la URL e inserte un JSON válido puede reemplazar el contenido (cifrado, así que no leería nada, pero sí podría borrarte los datos). Por eso conviene tener la copia de seguridad local.

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

El dashboard no depende de que el npoint siga intacto:

- Cada vez que se descarga o se guarda el envoltorio cifrado, se guarda también en el navegador (`inv_cloud_last` y hasta 20 versiones en `inv_cloud_history_v1`).
- Botón **⬇ Copia**: descarga el JSON cifrado a disco (`cartera-cifrada-AAAA-MM-DD.json`).
- Botón **⬆ Restaurar**: sube una copia cifrada al npoint y la deja lista para abrir con el PIN.
- Si la nube no responde o la han vaciado, la web ofrece abrir la **última copia local** pidiendo el PIN.

Pendiente (Nivel 2): endpoint propio en la VM que acepte escrituras firmadas con una clave derivada del PIN, para que nadie sin PIN pueda escribir en la nube.


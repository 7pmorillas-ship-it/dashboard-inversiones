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

## Migración desde el formato antiguo (en claro)

Si el JSON remoto todavía no tiene `v: 2`, la página detecta el formato antiguo, pide un PIN (dos veces, mínimo 6 caracteres) y guarda una versión cifrada. Hasta que se hace esa migración, los datos siguen en claro en la nube.

## Copias de seguridad (Nivel 1)

El dashboard no depende de que el npoint siga intacto:

- Cada vez que se descarga o se guarda el envoltorio cifrado, se guarda también en el navegador (`inv_cloud_last` y hasta 20 versiones en `inv_cloud_history_v1`).
- Botón **⬇ Copia**: descarga el JSON cifrado a disco (`cartera-cifrada-AAAA-MM-DD.json`).
- Botón **⬆ Restaurar**: sube una copia cifrada al npoint y la deja lista para abrir con el PIN.
- Si la nube no responde o la han vaciado, la web ofrece abrir la **última copia local** pidiendo el PIN.

Pendiente (Nivel 2): endpoint propio en la VM que acepte escrituras firmadas con una clave derivada del PIN, para que nadie sin PIN pueda escribir en la nube.


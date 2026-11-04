# Automatización Pandora

Este proyecto automatiza la extracción de información desde SAP, el análisis de
precios y márgenes, y la liberación o el bloqueo de documentos VA14L. Los
documentos que necesitan una decisión manual se revisan en una página HTML; las
decisiones se guardan y se procesan después con Python.

## 1. Requisitos y configuración inicial

### Carpeta de archivos Pandora

`PANDORA_DATA_DIR` debe apuntar a la carpeta que contiene los archivos de
intercambio de Pandora, por ejemplo `detalle_bloqueado.xlsx` y `precios.XLSX`.
El programa usa esa carpeta directamente; no agrega subdirectorios.

Para definirla permanentemente para tu usuario de Windows, abre PowerShell y
ejecuta una vez:

```powershell
[Environment]::SetEnvironmentVariable(
    "PANDORA_DATA_DIR",
    "C:\Users\MaxService\Pandora\Archivos_sap",
    "User"
)
```

Reemplaza la ruta por la carpeta real de este equipo. `configuracion.py` lee el
valor persistente del usuario, así que Python puede usarlo aunque la terminal o
el editor no lo hayan heredado al iniciarse.

Los nombres de archivos están centralizados en `configuracion.py`. Entre los
principales están:

| Archivo | Uso |
| --- | --- |
| `detalle_bloqueado.xlsx` | Detalle de documentos y líneas obtenido desde SAP |
| `precios.XLSX` | Precios usados para evaluar las líneas |
| `pandora_final.xlsx` | Resultado completo del análisis, con todas las líneas |
| `pandora_revision.html` | Página para revisar documentos pendientes |
| `liberar.xlsx` | Lista de documentos que procesará la liberación VA14L |
| `escalado.xlsx` | Lista de documentos que procesará el bloqueo VA14L |

### SAP y credenciales

SAP GUI debe estar instalado y permitir scripting. La ubicación se puede
configurar con `SAPLOGON_PATH`; si no se define, se usa la ruta SAP GUI habitual.
El inicio de sesión obtiene estas variables del entorno:
`SAP_USER`, `SAP_PASSWORD`, `SAP_CLIENT` y `SAP_LANGUAGE`.

## 2. Qué hace `main.py`

Ejecuta el flujo automático completo:

1. Abre o reutiliza la sesión SAP y maximiza la ventana al inicio.
2. Ejecuta las extracciones VBAK, VBAP y ZCLSD0022.
3. Cruza el detalle de ventas con los precios y calcula descuentos y márgenes.
4. Aplica las reglas de Pandora por línea y determina una categoría por
   documento de ventas.
5. Genera `pandora_final.xlsx`, `pandora_revision.html` y las listas de
   liberación y bloqueo.
6. Ejecuta VA14L de inmediato para los documentos clasificados automáticamente
   como liberados o rechazados.

Los documentos con `Documento Por Revisar` no se incluyen en esas listas
automáticas. Quedan disponibles para revisión posterior y no hacen que `main.py`
espere al usuario.

## 3. Revisar documentos en el HTML

Al generar Pandora, se abre `pandora_revision.html` en el navegador. La página
muestra únicamente los documentos que requieren revisión manual. Cada documento
aparece una vez y contiene todas sus líneas en una tabla; la decisión se toma a
nivel de documento y aplica a todas sus líneas.

La página permite:

- buscar por número de documento o por texto de sus líneas;
- seleccionar `Liberado` o `Bloqueado` para cada documento;
- guardar las decisiones seleccionadas como `decisiones_pandora.json`.

Se pueden guardar decisiones parciales. Los documentos sin decisión no se
procesan. Al guardar una selección parcial, la página avisa cuántos documentos
quedarán pendientes.

La página es solo una interfaz de revisión: no inicia SAP ni modifica las listas
Excel. El JSON descargado es el archivo que Python usa después.

## 4. Guardar el JSON en una ubicación fija

Por defecto, Python busca el JSON más reciente cuyo nombre empiece con
`decisiones_pandora` dentro de `PANDORA_DATA_DIR`. Esto incluye nombres que el
navegador crea para descargas repetidas, como `decisiones_pandora (1).json`.

Para no tener que buscar ni seleccionar el archivo en cada ejecución, configura
una sola vez el navegador para guardar las descargas en la carpeta de datos de
Pandora y desactiva la opción de preguntar dónde guardar cada archivo. La ruta
predeterminada es la misma carpeta configurada en `PANDORA_DATA_DIR`.

Si prefieres guardar el JSON en otra carpeta, define la variable de usuario
`PANDORA_DECISIONES_JSON` con una ruta de archivo dentro de esa carpeta. Por
ejemplo:

```powershell
[Environment]::SetEnvironmentVariable(
    "PANDORA_DECISIONES_JSON",
    "C:\Users\MaxService\Downloads\decisiones_pandora.json",
    "User"
)
```

Configura también el navegador para descargar en la carpeta indicada (`Downloads`
en este ejemplo). El programa busca allí el JSON más reciente con el nombre
`decisiones_pandora*.json`. La variable se lee desde la configuración persistente
del usuario de Windows.

## 5. Aplicar y ejecutar las decisiones manuales

Cuando quieras procesar las decisiones guardadas:

1. Ejecuta desde la carpeta del proyecto:

   ```powershell
   python .\aplicar_decisiones_pandora.py
   ```

2. Python encuentra automáticamente el JSON más reciente en la ubicación
   configurada; no aparece un selector de archivos.
3. El script comprueba que el JSON corresponda a la misma generación de
   `pandora_final.xlsx` y que sus documentos sigan pendientes.
4. Reemplaza `liberar.xlsx` y `escalado.xlsx` únicamente con los documentos que
   seleccionaste manualmente. Mantiene la estructura simple de una columna que
   consume VA14L. Las listas automáticas procesadas previamente por `main.py` no
   se vuelven a incluir.
5. Cuando estés listo para ejecutar en SAP, cierra los archivos Excel abiertos y
   ejecuta:

   ```powershell
   python .\ejecuta_liberaciones.py
   ```

Ese lanzador procesa las listas manuales: primero libera los documentos de
`liberar.xlsx` y luego bloquea los de `escalado.xlsx`.

## 6. Consideraciones sobre las revisiones

- Si guardas solo una parte de las decisiones, el resto queda sin procesar y no
  aparece en las listas manuales.
- Si generas Pandora otra vez, se crea una nueva página y un nuevo identificador
  de generación. Un JSON anterior no se puede aplicar a ese nuevo resultado;
  abre la página nueva y guarda las decisiones de nuevo.
- El JSON se guarda como archivo local y puede conservarse para procesarlo más
  tarde. Evita reemplazarlo manualmente con un JSON de otra generación.
- Los archivos `liberar.xlsx` y `escalado.xlsx` se reemplazan al aplicar las
  decisiones manuales; contienen el lote manual vigente, no un historial.

## 7. Ejecutar los procesos por separado

Para correr solo las liberaciones y bloqueos de una lista ya preparada:

```powershell
python .\ejecuta_liberaciones.py
```

Para ejecutar el flujo completo desde las extracciones hasta las decisiones
automáticas de VA14L:

```powershell
python .\main.py
```

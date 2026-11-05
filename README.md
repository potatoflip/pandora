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
| `clientes.xlsx` | Solicitantes y nombre de cliente obtenido desde KNA1 |
| `cliente_vendedor.xlsx` | Relación KNVP entre solicitantes y vendedores ZV |
| `vendedores.xlsx` | Maestro con código y nombre de vendedor |
| `listado_factura.xlsx` | Facturas históricas filtradas desde VBRK |
| `detalle_factura.xlsx` | Detalle histórico de precios y costes desde VBRP |
| `precios.XLSX` | Lista de precios normal |
| `precios_distribuidor.xlsx` | Lista de precios del canal distribuidor |
| `pandora_final.xlsx` | Resultado completo del análisis, con todas las líneas |
| `pandora_revision.html` | Página para revisar documentos pendientes |
| `pandora_historial.sqlite3` | Historial persistente de operaciones y errores |
| `pandora_historial.html` | Resumen y consulta de los dos registros |
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
2. Ejecuta VBAK, incluyendo la oficina de ventas, y consulta KNVP para vincular
   los solicitantes con los vendedores ZV. KNA1 aporta los nombres de cliente.
3. Extrae el detalle VBAP, las facturas VBRK/VBRP y ambas listas de precios.
4. Cruza ventas, oficinas, solicitantes, vendedores e historial de precios.
5. Calcula descuentos y márgenes, y aplica las reglas por línea y documento.
6. Genera `pandora_final.xlsx`, `pandora_revision.html`, el historial HTML y las listas de
   liberación y bloqueo.
7. Ejecuta VA14L de inmediato para los documentos clasificados automáticamente
   como liberados o rechazados.

El rango de fechas de VBRK se configura en `configuracion.py`, con las variables
`VBRK_FECHA_DESDE` y `VBRK_FECHA_HASTA` en formato `dd.mm.yyyy`. La fecha final
vacía significa que la consulta termina en la fecha actual.

La fecha de creación de pedidos consultada por VBAP (`ERDAT`) se cambia en
`configuracion.py`, con `VBAP_FECHA_DESDE`. El filtro usa la condición “mayor
que” desde esa fecha, sin límite final. Por defecto conserva el 1 de octubre del
año vigente; puedes cambiar esa única fecha para acotar las líneas descargadas.

En el análisis, el canal 10 usa `precios_distribuidor.xlsx`; si el material no
tiene precio en esa lista, se conserva el precio normal. `pandora_final.xlsx`
incluye el canal, el nombre del solicitante, ambas referencias de precio y la
lista aplicada. También agrega la última factura disponible por solicitante y
material como referencia histórica, ordenada por `Fecha de precio` de VBRP.
Los valores unitarios históricos se calculan así:

- `Subtotal 1 × 100 / Cantidad facturada` para el precio neto.
- `Valor neto × 100 / Cantidad facturada` para el precio de lista.
- `Costes internos × 100 / Cantidad facturada` para el coste unitario.

Para completar el historial, la variante de salida VBRK debe exportar el
solicitante (`KUNAG`, que puede aparecer como `Solicitante`) junto a `Factura`.
La fecha histórica se toma de `Fecha de precio` en VBRP; VBRK no necesita
exportar `FKDAT`.

En cada ejecución, Pandora une VBRK con VBRP por número de factura para conocer
el solicitante asociado a cada posición facturada. Después cruza esas posiciones
con los pedidos actuales por `Solicitante` y `Material`, y conserva la factura
más reciente según `Fecha de precio`. Las columnas históricas se agregan al final
de `pandora_final.xlsx`; no reemplazan los precios ni los demás datos del pedido
actual. En la página de revisión, un ticket junto a `Precio neto` indica que ese
valor coincide con `Precio lista histórico`. Es una referencia visual para la
revisión, no una decisión automática.

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

Para revisar el diseño sin ejecutar SAP ni generar los Excel de trabajo, ejecuta
`python .\test\generar_vista_previa.py` desde la raíz del proyecto. El script
actualiza `test\vista_previa.html` con datos ficticios que muestran una revisión
normal en amarillo, una crítica en rojo y una línea aprobada sin resaltar. Abre
ese HTML en el navegador para comprobar cambios de la interfaz; vuelve a
ejecutar el comando después de modificar la plantilla, los estilos o el
comportamiento. Ambos archivos de demostración se mantienen en `test/`,
separados de los procesos de producción.

Se pueden guardar decisiones parciales. Los documentos sin decisión no se
procesan. Al guardar una selección parcial, la página avisa cuántos documentos
quedarán pendientes.

La página es solo una interfaz de revisión: no inicia SAP ni modifica las listas
Excel. El JSON descargado es el archivo que Python usa después.

El nombre del cliente, el canal, la oficina de ventas, el nombre de la oficina,
el código y nombre del vendedor, y el estado del cruce se muestran en el
encabezado de cada documento. No aparecen como columnas repetidas en la tabla de
líneas.

La página sigue el sistema visual Max Service: paleta de marca, tipografía,
estructura de navegación y selector con los temas Original, Oscuro, Lino, Greda,
Cordillera y Telar. Los logos claro y oscuro, junto con el icono, se conservan en
`assets/` y se incorporan dentro del HTML generado, por lo que la página no
necesita cargar imágenes desde una ruta externa. El encabezado identifica al
módulo con el nombre `Not_Kimi`.

Las fuentes de la interfaz están separadas para facilitar cambios de diseño:

- `proceso_excel/revision_pandora/templates/revision_pandora.html`
- `proceso_excel/revision_pandora/static/revision_pandora.css`
- `proceso_excel/revision_pandora/static/revision_pandora.js`

`proceso_excel/revision_html.py` incorpora los datos, estilos, comportamiento y
logos en `pandora_revision.html`, así que el archivo final se puede abrir de
forma local sin depender de esa estructura de carpetas en tiempo de uso.

## Historial persistente y registros

La página de revisión incluye un enlace **Historial**. Abre `pandora_historial.html`,
que presenta el resumen más reciente por oficina de ventas y dos registros:

- **Operaciones:** clasificación automática, decisiones manuales y resultado
  real de VA14L, con documento, solicitante, vendedor, oficina, decisión y origen.
- **Errores del sistema:** excepciones del programa y diagnósticos SAP, incluidos
  etapa, código y mensaje SAP cuando están disponibles.

La información se conserva en `pandora_historial.sqlite3` dentro de
`PANDORA_DATA_DIR`; el HTML se regenera a partir de esa base de datos. El resumen
por oficina cuenta los documentos liberados automáticamente, bloqueados y
enviados a revisión en la última generación. Las liberaciones y bloqueos
procesados desde `ejecuta_liberaciones.py` quedan marcados como manuales y se
acumulan en el historial.

El cruce usa la primera columna `Cliente` de KNVP como solicitante y la segunda
columna `Cliente` como código del vendedor (función `ZV`), y busca su nombre en
`vendedores.xlsx` (`Cliente` / `Nombre 1`). Si falta el maestro o hay más de un
vendedor posible, Pandora continúa con el análisis, registra el problema y deja
el vendedor sin asignar en el historial. La oficina se obtiene de la columna
`Oficina de ventas` de VBAK y se etiqueta con el catálogo entregado.

Las nuevas ejecuciones ya no generan un CSV por proceso ni diagnósticos SAP en
archivos separados. Los CSV y textos de ejecuciones anteriores se conservan;
no se eliminan ni se importan automáticamente.

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
   Al registrar estas decisiones, esos documentos dejan de contarse como `Por
   revisión` en el resumen de `pandora_historial.html`, aunque todavía no hayas
   ejecutado VA14L. Los documentos que no seleccionaste permanecen pendientes.
5. Cuando estés listo para ejecutar en SAP, cierra los archivos Excel abiertos y
   ejecuta:

   ```powershell
   python .\ejecuta_liberaciones.py
   ```

Ese lanzador procesa las listas manuales: primero libera los documentos de
`liberar.xlsx` y luego bloquea los de `escalado.xlsx`.

Aplicar las decisiones no vuelve a consultar ni modifica los precios históricos:
estos ya quedaron vinculados en `pandora_final.xlsx` durante la generación de
Pandora y sirven como referencia para la revisión. Este histórico de precios es
distinto del historial operativo de liberaciones.

El historial operativo no depende de volver a ejecutar `main.py`: al ejecutar
`ejecuta_liberaciones.py`, VA14L registra cada documento procesado, si fue una
liberación o un bloqueo manual, y el resultado devuelto por SAP en
`pandora_historial.sqlite3`. El HTML del historial se regenera al terminar cada
lista. `aplicar_decisiones_pandora.py` registra antes la decisión que elegiste;
`ejecuta_liberaciones.py` registra después el resultado real de ejecutarla. Así,
puedes revisar el HTML y ejecutar tus decisiones más tarde sin generar Pandora
otra vez.

El histórico de precios que se compara en la página de revisión sí se calcula
durante `main.py` con las extracciones VBRK/VBRP de esa generación. La siguiente
ejecución de `main.py` vuelve a consultarlas y actualiza esa referencia; no es el
registro de liberaciones ni se modifica al liberar un pedido.

Durante VA14L, SAP puede abrir `SAPLM61Q` con el título **Tratamiento
componentes: Entrada colectiva**. El proceso cancela esa pantalla con F12 cada
vez que aparece, espera a volver a los campos de bloqueo y guarda los valores
registrados sin modificar los componentes.

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

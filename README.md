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
| pandora_historial.xlsx | Libro exportable con las tablas del historial en hojas separadas |
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

La consola muestra dos cronómetros independientes: **Parte 1** mide desde el
inicio de la extracción y preparación hasta justo antes de VA14L; **Parte 2**
mide las liberaciones y bloqueos automáticos hasta que finalizan. Si ejecutas
`ejecuta_liberaciones.py` después de revisar y aplicar decisiones, la consola
muestra además el tiempo total de esa etapa manual de VA14L.

El lanzador muestra un porcentaje de avance por hitos terminados: la extracción
y preparación ocupa el 60%; las liberaciones y bloqueos automáticos ocupan el
20% cada uno, y avanzan con cada documento procesado. En la ejecución manual,
liberaciones y bloqueos ocupan la mitad del avance cada uno. Aplicar las
decisiones también informa el avance de sus etapas. Si el proceso falla, la
barra permanece en el último hito alcanzado.

Al conectar con SAP, el programa recorre todas las conexiones y pestañas abiertas
y reutiliza una sesión autenticada. Si SAP muestra el aviso de sesiones
duplicadas, selecciona continuar sin cerrar las demás sesiones. Antes de
ejecutar VBAK, espera que SE16N muestre los campos de selección; si no aparecen,
registra un error explicativo en vez de continuar con una pantalla incompleta.

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
- copiar el número desde el encabezado de cada documento con el botón de copia;
- seleccionar `Liberado` o `Bloqueado` para cada documento;
- guardar las decisiones seleccionadas como `decisiones_pandora.json`.

El filtro inicial queda en **Pendientes**. Puedes cambiarlo a **Todos** para
consultar también los documentos con decisiones guardadas. El menú lateral
aparece contraído al abrir la página y se puede desplegar desde su botón.

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

La tabla permite ordenar por encabezado y fijar columnas hasta la que elijas.
Al seleccionar una línea queda resaltada para facilitar su lectura; al hacer
clic fuera de la tabla se quita el resaltado. Los miles se muestran con punto
y los decimales con coma según el formato chileno; el número del documento se
conserva sin separadores. Las líneas que requieren revisión se marcan en
amarillo y las de margen o descuento más crítico en rojo; las líneas aprobadas
no reciben color de alerta.

Cuando hay precios históricos, el encabezado del documento muestra un indicador
verde y cada línea con factura histórica lleva una marca junto al número de
venta. Si el precio neto coincide con el precio de lista histórico, aparece
además una marca en esa celda. La tabla ajusta sus columnas según el contenido y
permite desplazarse horizontalmente sin separar un número de documento.

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

El historial tiene botones separados para el resumen por oficina, los
vendedores, las liberaciones repetidas, las operaciones y los errores. Cada
tabla se puede filtrar desde su buscador, ordenar pulsando sus encabezados y
fijar columnas con el icono de chincheta. La pestaña Liberaciones repetidas
incluye gráficos por sucursal, vendedor y cliente, los conteos generales y el
detalle por documento. El botón Exportar a Excel descarga un libro con una
hoja por cada tabla y por los datos de los gráficos.

El selector de apariencia incluye el tema **Pandora**, con una paleta oscura y
gradientes dorados, morados y azul arcano. La selección se comparte entre la
revisión y el historial.

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

En el resumen del historial también aparecen las notas de venta liberadas
exitosamente más de una vez. La tabla agrupa por oficina, solicitante y
documento e indica cuántas liberaciones exitosas se registraron; el gráfico
cuenta los documentos repetidos por oficina. Se incluyen solo liberaciones
exitosas; los bloqueos, errores y documentos no encontrados no se cuentan.

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

## 8. Usar el lanzador de escritorio

El lanzador ofrece botones para ejecutar `main.py`, aplicar las decisiones del
HTML y ejecutar las liberaciones/bloqueos manuales. La salida de cada proceso y
sus errores aparecen en una consola dentro de la ventana. Usa negro, morado y
dorado; incluye una barra de avance por etapas y documentos, y muestra a la
izquierda los tiempos de preparación, VA14L automático y VA14L manual cuando
cada etapa termina. La carpeta de datos se
lee de `PANDORA_DATA_DIR`; no es necesario volver a ingresarla al abrir el
lanzador.

Para construir `dist\PandoraEjecutor.exe` y crear el acceso directo `Pandora`
en el escritorio, ejecuta una vez desde PowerShell en la raíz del proyecto:

```powershell
.\crear_lanzador_escritorio.ps1
```

La primera construcción crea un entorno local `.venv-lanzador` e instala
PyInstaller. Requiere conexión a Internet durante esa instalación. El acceso
directo apunta al ejecutable dentro de `dist/`, por lo que conserva el código y
los archivos de Pandora en la carpeta del proyecto. `main.py` y la ejecución
manual de VA14L muestran una confirmación antes de iniciar acciones en SAP.

## 9. Arquitectura actual y responsabilidades

La aplicación está dividida por responsabilidad para que pueda integrarse más
adelante en Kimi sin mezclar las reglas comerciales con la automatización SAP o
con la interfaz:

| Componente | Responsabilidad actual |
| --- | --- |
| configuracion.py | Rutas de datos, nombres de archivos y fechas de extracción |
| main.py | Coordina extracción, análisis y VA14L automático |
| proceso_sap/ | Automatiza SAP GUI para extraer información y procesar VA14L |
| proceso_excel/pandora_excel.py | Coordina preparación, cruces, reglas, cálculos y generación de resultados |
| proceso_excel/reglas_pandora.py y calculos_pandora.py | Decisiones y cálculos comerciales |
| proceso_excel/revision_html.py | Genera el HTML autónomo con datos, estilos, JavaScript y logos integrados |
| proceso_excel/historial.py | Guarda eventos en SQLite y regenera el HTML del historial |
| aplicar_decisiones_pandora.py | Valida el JSON y reemplaza las listas manuales de VA14L |
| lanzador_pandora.py | Ventana Windows para lanzar procesos, ver la consola, el avance y los tiempos |
| test/ | Generador de vista previa con datos ficticios; no ejecuta procesos SAP |

El flujo actual usa SAP GUI para descargar los listados, Excel como formato de
intercambio y entrada al análisis, SQLite para el historial operativo y páginas
HTML locales para revisión. La página de revisión no ejecuta Python: descargar
las decisiones y aplicarlas son pasos separados.

El historial de precios y el historial operativo son datos distintos. El
primero compara el pedido actual con facturas VBRK/VBRP obtenidas en cada
generación de Pandora. El segundo registra clasificaciones, decisiones y
resultados VA14L a lo largo del tiempo.

## 10. Preparación para integrar Pandora en Kimi

La integración en Kimi y el reemplazo de las lecturas de SAP por una base de
datos son planes futuros. No se han cambiado todavía las consultas SAP, las
reglas de negocio ni el método de acceso a datos.

### Límites que conviene conservar

- **Acceso a datos:** hoy vive principalmente en proceso_sap/ y usa SAP GUI.
  En el futuro podrá sustituirse por un adaptador de base de datos.
- **Reglas Pandora:** los cruces, precios, cálculos y decisiones deben seguir
  separados de la tecnología usada para leer los datos.
- **Revisión:** la página actual es un HTML local autónomo. Al llevarla a Kimi,
  se adaptará para cargar y guardar información a través de los servicios del
  sitio, manteniendo el trabajo de decisión a nivel de documento.
- **Ejecución:** guardar una decisión no inicia VA14L. La ejecución permanece
  bajo una acción explícita del usuario y en el backend.
- **Historial:** las clasificaciones, resultados y errores deben conservar
  una fuente persistente consultable desde el módulo integrado.

La dirección prevista para la fuente de datos es:

    Actual: SAP GUI → Excel de intercambio → análisis Pandora → HTML y VA14L
    Futura: base de datos → adaptador de lectura → análisis Pandora → Kimi y VA14L

El adaptador futuro debe entregar al análisis los mismos conceptos normalizados
que Pandora ya utiliza: pedidos y posiciones, solicitantes/clientes, vendedores,
facturas y posiciones facturadas, listas de precios, oficina y canal de
distribución. La estructura física de las tablas y sus nombres aún no están
definidos; no se deben inventar consultas ni asumir un motor de base de datos.

### Información que falta definir antes de implementar el acceso a datos

Con el equipo responsable de la base habrá que acordar:

1. Motor, servidor, base, esquema y vistas que se pueden consultar.
2. Permisos de solo lectura, autenticación y almacenamiento seguro de
   credenciales. Los secretos no deben quedar en el repositorio ni en el HTML.
3. Correspondencia entre cada exportación actual y las tablas/vistas nuevas.
4. Tipos, unidades, claves de unión, valores nulos y significado de las fechas.
5. Filtros de sociedad/organización, canal, estados y rangos de fechas.
6. Frecuencia de actualización, tamaño esperado, límites y comportamiento ante
   desconexiones o datos incompletos.
7. Qué servicio del backend Kimi será responsable de generar la revisión,
   almacenar las decisiones y solicitar la ejecución.

### Secuencia recomendada para la transición

1. Revisar la estructura de Kimi: tecnología, rutas, autenticación, componentes
   visuales y forma de desplegar módulos internos.
2. Documentar las columnas normalizadas que consume Pandora y crear una
   implementación de lectura de prueba sin cambiar las reglas comerciales.
3. Para un mismo rango, comparar datos SAP y base de datos: documentos,
   posiciones, solicitantes, fechas, materiales, precios y resultados calculados.
4. Resolver discrepancias y validar con usuarios antes de cambiar la fuente
   predeterminada.
5. Integrar la revisión como una página del backend de Kimi. El navegador no
   debe conectarse directamente a SAP o a la base ni ejecutar archivos Python.
6. Mantener VA14L como proceso SAP independiente mientras siga siendo la forma
   autorizada de liberar o bloquear documentos.

La primera fusión debe preservar el funcionamiento actual y dejar explícito
qué partes todavía requieren SAP GUI. La migración a base de datos será un
cambio posterior, con acceso de lectura y validación de resultados antes de
retirar las exportaciones actuales.

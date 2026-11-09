# Especificación funcional: reglas de negocio de Pandora en Kimi

**Estado:** propuesta funcional para implementación futura  
**Fecha:** 9 de noviembre de 2026  
**Alcance:** permitir consultar, crear, editar, probar, activar y revertir reglas comerciales de Pandora desde un apartado propio del sitio Kimi.

> Este documento especifica el comportamiento deseado. No implementa la pantalla ni cambia las reglas actuales de Pandora.

## 1. Objetivo

Hoy Pandora calcula descuentos y márgenes, clasifica líneas y determina una decisión por documento desde código Python. El objetivo es administrar esas reglas desde una página HTML integrada en Kimi, sin tener que modificar código para ajustar umbrales, agregar una regla o cambiar su prioridad.

La página será una interfaz de administración. Kimi guardará las reglas en el backend y el backend será quien las valide y ejecute. El navegador no ejecutará Python, no accederá a SAP ni aplicará liberaciones VA14L.

## 2. Ubicación en Kimi

Agregar un apartado independiente en la navegación del sitio:

**Kimi > Pandora > Reglas de negocio**

Debe ser una sección distinta de:

- **Revisión Pandora**, donde se toman decisiones manuales por documento.
- **Historial Pandora**, donde se consultan resultados y operaciones.
- **Operaciones**, desde donde se ejecutan procesos autorizados.

La administración de reglas no debe mezclarse con la decisión manual de liberar o bloquear un pedido.

## 3. Funcionamiento actual que hay que conservar

Las siguientes reglas están implementadas en `proceso_excel/reglas_pandora.py`. Los cálculos previos están en `proceso_excel/calculos_pandora.py` y la ejecución está coordinada en `proceso_excel/pandora_excel.py`.

### 3.1 Indicadores calculados antes de evaluar reglas

- **Margen de línea %** = (Valor neto - Costes internos) / Valor neto.
- **Descuento %** = 1 - (Precio neto / Precio Venta).
- **Margen de documento %** = (venta total del documento - coste total del documento) / venta total del documento.
- La evaluación usa proporciones decimales: por ejemplo, 0,16 equivale a 16%. El Excel presenta los porcentajes convertidos a porcentaje.

### 3.2 Reglas por línea actuales

| Orden | Condición | Resultado actual |
| --- | --- | --- |
| 1 | Precio de lista ausente o igual a cero | `ERROR`: precio lista no encontrado o igual a 0. |
| 2 | Descuento no calculable | `ERROR`: no se pudo calcular el descuento. |
| 3 | Descuento mayor que 25% | `Rechazada`; requiere autorización de gerencia. |
| 4 | Descuento menor o igual a 16% | `Aprobada`; descuento dentro del estándar. |
| 5 | Descuento mayor que 16% y menor o igual a 25% | `Revision`; requiere autorización. |
| 6 | Caso no contemplado | `ERROR`. |

En el tramo de revisión, Pandora agrega al motivo si el margen de línea es al menos 25% y el margen del documento al menos 30%. Esos dos umbrales cambian el texto del motivo, pero el resultado de la línea sigue siendo `Revision`.

**Inconsistencia que debe resolverse con el área comercial:** el comentario del código dice “descuento hasta el 15%”, pero la constante y el comportamiento ejecutable usan 16%. Hasta que se confirme la decisión de negocio, la especificación considera 16% como el valor real vigente. La migración no debe cambiar silenciosamente este umbral.

### 3.3 Regla de documento actual

Pandora consolida las decisiones de todas las líneas de un documento en este orden:

1. Si alguna línea tiene `ERROR`, el documento queda como **Documento con Error**.
2. Si no hay error, pero alguna línea está `Rechazada`, queda como **Documento Rechazado**.
3. Si todas las líneas están `Aprobada`, queda como **Documento Liberado**.
4. Se permite **Documento Liberado** por excepción si existe exactamente una línea `Revision`, todas las demás están `Aprobada`, y la línea en revisión tiene descuento menor o igual a 20% y margen de línea mayor o igual a 15%.
5. En cualquier otro caso, queda como **Documento Por Revisar**.

La decisión manual, cuando corresponda, se realiza una sola vez por documento y se aplica a todas sus líneas.

### 3.4 Resultado de las decisiones automáticas

Actualmente los documentos liberados automáticamente se preparan para la lista de liberar y los rechazados para la lista de escalado/bloqueo. Los documentos por revisar no deben detener `main.py`: quedan para revisión posterior. Cambiar una regla no debe ejecutar una liberación o bloqueo SAP en el acto.

## 4. Tipos de regla que administrará la página

La primera versión debe permitir editar reglas de estos tipos:

1. **Validación de datos:** precio o indicador ausente, valor no calculable u otra condición que deba producir error.
2. **Clasificación por línea:** condiciones sobre descuento y márgenes que producen aprobada, revisión o rechazada.
3. **Consolidación por documento:** reglas que toman decisiones de las líneas y calculan la clasificación global del documento.
4. **Selección de precio:** cuando corresponda, reglas de qué lista de precios usar, prioridad y respaldo. La regla actual es que canal 10 prefiere precio distribuidor y usa precio normal si no existe ese precio para el material.

Cada regla tendrá un ámbito explícito: `dato`, `linea`, `documento` o `precio`. La aplicación mostrará un formulario apropiado para cada tipo.

## 5. Interfaz propuesta

### 5.1 Listado de reglas

Mostrar las reglas de la versión activa en una tabla con:

- Nombre y descripción.
- Tipo/ámbito.
- Prioridad de evaluación.
- Estado: borrador, activa, deshabilitada o archivada.
- Último cambio: usuario, fecha y versión.
- Resultado configurado.
- Acciones permitidas: ver, duplicar, editar borrador y simular.

La tabla debe permitir buscar, filtrar por tipo/estado y ordenar por prioridad. El listado en sí no debe permitir activar o desactivar una regla con un clic accidental.

### 5.2 Crear o editar regla

El formulario permitirá:

- Nombre, descripción y ámbito.
- Condiciones usando una lista cerrada de campos disponibles, operadores y valores.
- Unir condiciones con `TODAS` o `CUALQUIERA`.
- Resultado y mensaje que verá el usuario en Pandora.
- Prioridad y estado habilitado/deshabilitado.
- Vigencia desde/hasta, si el negocio necesita programar cambios.

El usuario no escribirá código Python, JavaScript, SQL ni expresiones libres. Las reglas se construirán con controles y operadores permitidos por el backend.

### 5.3 Campos disponibles en la primera versión

- Descuento %.
- Margen línea %.
- Margen documento %.
- Precio de lista (`Precio Venta`).
- Precio neto.
- Valor neto y costes internos.
- Canal de distribución.
- Número de líneas del documento.
- Cantidad de líneas aprobadas, en revisión, rechazadas o con error.
- Disponibilidad de un precio normal o distribuidor.

La lista definitiva debe validarse con el área comercial y el responsable del backend. No se deben exponer columnas personales o de SAP que no sean necesarias para evaluar las reglas.

### 5.4 Simulación antes de activar

Desde el borrador, el usuario podrá seleccionar una ejecución anterior o una muestra autorizada y simular la nueva configuración. La simulación debe mostrar:

- Cantidad de documentos y líneas evaluadas.
- Clasificación anterior y nueva, con conteos y variaciones.
- Reglas que dispararon en cada clasificación.
- Ejemplos de documentos/líneas afectados con identificadores y motivos.
- Errores de configuración o datos faltantes.
- Cambios en las listas que se generarían: liberar, escalar/bloquear y por revisar.

La simulación será de solo lectura: no escribirá SAP, no cambiará la versión activa, no reemplazará archivos de ejecución ni iniciará VA14L.

## 6. Ciclo de vida, versiones y auditoría

Cada cambio seguirá este flujo:

1. El usuario crea o modifica un **borrador**.
2. El backend valida la configuración.
3. El usuario solicita una simulación y revisa el impacto.
4. Un usuario autorizado activa la versión con una confirmación explícita.
5. Kimi conserva la versión anterior y el detalle del cambio.

Para cada versión se registrará:

- Identificador de versión y estado.
- Reglas completas de esa versión.
- Usuario creador y usuario activador.
- Fecha/hora y comentario del cambio.
- Configuración anterior y diferencias respecto de la nueva.
- Resultados/resumen de simulación y conjunto de datos de prueba usado.

Debe existir una opción **Restaurar versión**, que cree una nueva versión a partir de una anterior. No se borran ni editan versiones ya activadas.

Una ejecución Pandora guardará el identificador de la versión de reglas usada. Una revisión ya generada conservará esa versión, aunque luego se publique una nueva. Así se evita que una revisión pendiente cambie de significado mientras la persona la está aprobando.

## 7. Validaciones obligatorias

El backend rechazará el borrador si:

- Hay umbrales fuera del rango permitido o porcentajes en formato inválido.
- Las condiciones están incompletas, usan un campo no permitido o combinan tipos incompatibles.
- Hay prioridades ambiguas o reglas que no dejan una salida definida.
- Se solapan reglas de forma que el resultado dependa de un orden no declarado.
- La regla puede convertir un error de datos en una aprobación sin una excepción autorizada.
- No existe un resultado de respaldo para una línea/documento que no coincida con ninguna regla.

Los rangos máximos permitidos para cada porcentaje, y quién puede activar una regla, deben ser acordados por el área comercial y el administrador de Kimi antes de programar la publicación.

## 8. Persistencia y servicios del backend

El HTML se comunica con servicios autenticados de Kimi. La regla activa se almacena en la base de datos/configuración del backend, no en `localStorage`, en un Excel local ni dentro del HTML.

Servicios sugeridos (nombres de referencia, no contrato definitivo):

- `GET /api/pandora/rules` - consulta versión activa y reglas.
- `GET /api/pandora/rules/versions` - lista de versiones e historial de cambios.
- `POST /api/pandora/rules/drafts` - crea un borrador.
- `PUT /api/pandora/rules/drafts/{id}` - modifica un borrador.
- `POST /api/pandora/rules/drafts/{id}/validate` - valida estructura y conflictos.
- `POST /api/pandora/rules/drafts/{id}/simulate` - evalúa una muestra sin efectos laterales.
- `POST /api/pandora/rules/drafts/{id}/publish` - activa una versión confirmada.
- `POST /api/pandora/rules/versions/{id}/restore` - restaura una versión creando una nueva.

Los servicios finales deben seguir las convenciones del backend existente de Kimi. El frontend nunca debe conectarse directamente a la base de datos ni a SAP.

## 9. Integración con el procesamiento actual de Pandora

La evaluación debe tener una sola fuente de verdad. Python/Pandora y el módulo Kimi no deben mantener copias independientes de las reglas que puedan divergir.

Ruta recomendada:

1. Definir un esquema común de reglas versionadas y validarlo en el backend.
2. Extraer la evaluación actual de `reglas_pandora.py` detrás de una interfaz que pueda recibir una versión explícita de reglas.
3. Mantener una versión de reglas inicial que reproduzca exactamente los resultados actuales, excepto el umbral 15%/16% que debe confirmarse.
4. Hacer que el flujo Python use la misma versión activa del backend o una exportación versionada y firmada/aprobada que el equipo defina. No dejar una copia antigua incrustada en el EXE.
5. Registrar el `ruleset_version` en Pandora final, en la generación de revisión y en el historial.
6. Comparar resultados anteriores y nuevos antes de retirar las constantes Python.

Si el EXE se ejecuta sin conexión al backend, debe usar la última configuración descargada que haya sido validada, mostrar qué versión aplica y no inventar una configuración si el archivo falta o está corrupto. La política de funcionamiento sin conexión debe acordarse con Kimi.

## 10. Seguridad y autorización

- Respetar inicio de sesión y permisos existentes de Kimi.
- Definir permisos separados para consultar, editar borradores, simular, activar reglas y restaurar versión.
- Proteger cambios críticos con confirmación adicional o aprobación de segundo usuario si la política de la empresa lo requiere.
- Validar todos los datos en el servidor, además del navegador.
- Proteger los servicios contra solicitudes sin autenticación, CSRF y reenvíos duplicados.
- Registrar auditoría inmutable y limitar acceso a la configuración.
- No incluir credenciales ni conexiones SAP en el HTML.

## 11. Compatibilidad y límites

- La primera versión gestiona **reglas de negocio Pandora**. No administra parámetros técnicos SAP, credenciales, rutas del equipo ni la extracción de tablas.
- No se modifica manualmente una decisión concreta en esta página; esa acción continúa en **Revisión Pandora**.
- Publicar reglas solo afecta las ejecuciones posteriores. No reescribe automáticamente un Excel, una revisión HTML ni el historial ya generado.
- Una ejecución o liberación VA14L requiere una acción explícita dentro del flujo operativo autorizado. Guardar o activar reglas nunca inicia VA14L por sí solo.
- El módulo debe poder mantenerse aunque la fuente de Pandora migre desde exportaciones SAP/Excel a una base de datos. Las reglas usan nombres de negocio normalizados, no nombres de columnas del Excel.

## 12. Criterios de aceptación

La función se considerará lista cuando:

1. El usuario encuentre **Reglas de negocio** dentro de Pandora en Kimi.
2. Pueda ver las reglas activas, crear y editar borradores, reordenar prioridad y deshabilitar una regla sin alterar la versión activa.
3. El sistema valide reglas incompletas, inválidas o ambiguas en el servidor y explique cómo corregirlas.
4. Pueda simular el borrador y comparar conteos/ejemplos contra una versión anterior, sin escribir datos operativos ni ejecutar SAP.
5. Solo un usuario autorizado pueda publicar; cada publicación queda versionada y auditada.
6. Una versión previa se pueda restaurar sin borrar la nueva ni perder el historial.
7. Cada ejecución y revisión indique qué versión de reglas usó y mantenga esa versión fija para la revisión ya creada.
8. La versión inicial reproduzca los resultados actuales en datos de referencia, una vez confirmada la diferencia entre 15% y 16%.
9. Las hojas Excel, la revisión HTML, el historial, la ejecución Python y el módulo Kimi obtengan las decisiones de la misma fuente de reglas.
10. Activar reglas no libere ni bloquee pedidos automáticamente ni cambie VA14L.

## 13. Decisiones pendientes del negocio y del equipo Kimi

- ¿El umbral estándar es 15% o 16%?
- ¿Quién puede editar y quién puede activar una versión? ¿Se requiere doble aprobación?
- ¿Qué límites absolutos se aceptan para descuento y margen?
- ¿Se podrán programar reglas por fecha, organización, canal, material, cliente u oficina?
- ¿Qué conjuntos de ejecuciones se permitirán usar para simular y quién puede ver los documentos de ejemplo?
- ¿El EXE necesita aplicar reglas actualizadas cuando no tenga conexión con Kimi?
- ¿Dónde quedará la fuente persistente de reglas dentro del backend/base de datos de Kimi?
- ¿El motor de reglas se ejecutará en Python en el backend o se migrará a otro servicio? Debe mantenerse una implementación común para todas las salidas.

## 14. Código de referencia revisado

- `proceso_excel/reglas_pandora.py`: umbrales, evaluación por línea y consolidación por documento.
- `proceso_excel/calculos_pandora.py`: cálculo de descuento y márgenes.
- `proceso_excel/pandora_excel.py`: orden de preparación, aplicación de reglas y generación de resultados.
- `proceso_excel/formato_pandora.py`: Excel de resultado y listas que alimentan las acciones posteriores.
- `README.md`, sección 10: límites y dirección futura de integración con Kimi.

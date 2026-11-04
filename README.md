# Automatización Pandora

## Configuración de rutas

Los nombres de archivo están centralizados en `configuracion.py`, en la sección
`ARCHIVOS`. Define `PANDORA_DATA_DIR` en cada computador con la ruta completa
de la carpeta donde están tus archivos. El programa usa esa carpeta tal cual;
no añade ningún subdirectorio. Por ejemplo, en PowerShell:

```powershell
$env:PANDORA_DATA_DIR = "C:\Users\carli\OneDrive\Documentos\Archivos_pandora"
python main.py
```

Ese comando configura la variable solo para la ventana actual. Para guardarla
de forma permanente para tu usuario de Windows, ejecuta una vez:

```powershell
[Environment]::SetEnvironmentVariable("PANDORA_DATA_DIR", "C:\Users\carli\OneDrive\Documentos\Archivos_pandora", "User")
```

En la computadora del trabajo, configura la misma variable con la ruta completa
de la carpeta de datos de ese equipo. Así no tendrás que modificar el código
al cambiar de computadora.

Si SAP GUI está instalado en otra ubicación, también se puede definir
`SAPLOGON_PATH`. Las credenciales SAP ya se leen desde variables de entorno:
`SAP_USER`, `SAP_PASSWORD`, `SAP_CLIENT` y `SAP_LANGUAGE`.


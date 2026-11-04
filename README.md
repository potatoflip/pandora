# Automatización Pandora

## Configuración de rutas

Las rutas y los nombres de archivo están centralizados en `configuracion.py`,
en las secciones `ARCHIVOS` y `RUTAS`. Por defecto, se usa la carpeta
`Archivos_sap` dentro del proyecto. Para usar una carpeta distinta en otro computador, define
la variable de entorno `PANDORA_DATA_DIR` con la ruta deseada. Por ejemplo, en
PowerShell:

```powershell
$env:PANDORA_DATA_DIR = "D:\Pandora\Archivos_sap"
python main.py
```

Si SAP GUI está instalado en otra ubicación, también se puede definir
`SAPLOGON_PATH`. Las credenciales SAP ya se leen desde variables de entorno:
`SAP_USER`, `SAP_PASSWORD`, `SAP_CLIENT` y `SAP_LANGUAGE`.


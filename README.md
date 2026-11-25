# SecureDev Tickets - aplicación base

Código fuente para el encargo de la Evaluación Parcial 3 de OCY1102. Las tareas y entregables están definidos en la pauta entregada por el docente.

## Levantar con Docker

Se requiere Docker Desktop con motor Linux y Docker Compose. En PowerShell:

```powershell
docker compose up -d --build
```

Abrir http://localhost:8000. Usuarios de prueba: `ana / ana123` y `bruno / bruno123`.

La aplicación expone métricas en http://localhost:8000/metrics: solicitudes HTTP, duración e intentos de acceso fallidos. SQLite sigue guardando los datos de tickets. La integración de estas métricas con la monitorización y la documentación de incidentes forman parte del encargo.

Para detener la aplicación:

```powershell
docker compose down
```

Los datos quedan en un volumen Docker; `docker compose down -v` reinicia los datos de prueba. El código, la configuración y las credenciales son solo para un entorno de laboratorio local.

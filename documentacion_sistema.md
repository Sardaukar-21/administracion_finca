# Documentación Técnica de Arquitectura y Lógica del Sistema - AdmiFinca

Este informe técnico documenta en detalle la estructura de la aplicación **AdmiFinca**, detallando la arquitectura del sistema, la comunicación entre el frontend y el backend, la integración del motor de Inteligencia Artificial, las validaciones de seguridad e inputs implementadas, y la generación dinámica de reportes.

---

## 1. Arquitectura General y Flujo de Datos

La aplicación está construida sobre una arquitectura desacoplada y limpia utilizando **Reflex** (framework de Python para desarrollo web reactivo).

```
                      +------------------------------------+
                      |       FRONTEND (Capa Vista)        |
                      |   - UI Declarativa (Reflex)        |
                      |   - Componentes Reactivos          |
                      +-----------------+------------------+
                                        |  Enlace de Estado
                                        v
                      +------------------------------------+
                      |     CONTROLADOR DE ESTADO (State)  |
                      |   - Variables reactivas (rx.Var)   |
                      |   - Gestores de eventos asíncronos |
                      +-----------------+------------------+
                                        |  Hilos de Trabajo (rx.run_in_thread)
                                        v
                      +------------------------------------+
                      |      BACKEND (Lógica y Datos)      |
                      |   - backend_*.py (Consultas SQL)   |
                      |   - ia_provider.py / backend_ia.py |
                      |   - backend_reporte_pdf.py (FPDF2)  |
                      +-----------------+------------------+
                                        |  PyMySQL / Connection Pools
                                        v
                      +------------------------------------+
                      |         BASE DE DATOS (MySQL)      |
                      +------------------------------------+
```

### Separación de Responsabilidades:
1. **Frontend (Capa de Presentación)**: Localizado en la carpeta `Administracion_Finca/views/`. Define la estructura visual declarativa en Python utilizando componentes de Reflex (como `rx.table.root`, `rx.card`, `rx.button`, etc.).
2. **Controladores de Estado (States)**: Definidos en las clases que heredan de `rx.State` (como `IAState` en `views/ia.py` o `AlimentacionState` en `views/alimentacion.py`). Mantienen el estado dinámico y exponen variables reactivas (`@rx.var`) al frontend.
3. **Backend (Lógica de Negocio y Consultas)**: Módulos como `backend_animales.py`, `backend_alimentacion.py`, y `backend_ia.py` que se encargan de estructurar y ejecutar queries hacia la base de datos.
4. **Capa de Datos**: Centralizada en `database.py`, la cual expone `obtener_conexion()` para establecer conexiones directas con la base de datos MySQL de forma eficiente.

---

## 2. Relación Frontend-Backend y Conexión de Vistas

Toda la interactividad en AdmiFinca se realiza a través del enlace de datos de Reflex. Para evitar congelar la interfaz de usuario en consultas de bases de datos pesadas o peticiones HTTP a la IA, el frontend delega estas tareas mediante **hilos de ejecución de fondo** (`rx.run_in_thread`).

### Principales Módulos y sus Flujos:

#### A. Registro y Control de Animales (`animales.py` <-> `backend_animales.py`)
- **Frontend**: El usuario llena el formulario de registro (código de identificación, especie, sexo, fecha de nacimiento, peso inicial y consumo diario).
- **Controlador**: El `AnimalesState` recopila los datos y ejecuta asíncronamente `backend_animales.registrar_animal_completo`.
- **Backend**:
  1. Calcula automáticamente la **Categoría INSAI** oficial para Venezuela según la edad y especie (por ejemplo: Bovinos < 12 meses es "Becerra"/"Becerro", > 24 meses es "Vaca"/"Toro"; Ovinos/Caprinos < 6 meses es "Cordero/Cabrito", etc.).
  2. Inserta en la base de datos el animal y sus registros biométricos de entrada dentro de una **transacción SQL segura** (si un paso falla, se hace rollback automático).

#### B. Alimentación y Semáforo Zootécnico (`alimentacion.py` <-> `backend_alimentacion.py`)
- **Frontend**: Muestra la tabla de Dietas y Consumos Individuales.
- **Relación de Ideales**: El sistema calcula en tiempo real los rangos ideales de peso y consumo basándose en la especie y la edad del animal:
  - **Bovino joven** (< 6 meses): Peso ideal 60-120 kg | Consumo ideal 1.5-3.0 kg/día.
  - **Ovino adulto** (> 12 meses): Peso ideal 50-80 kg | Consumo ideal 1.5-2.5 kg/día.
- **Semáforo Visual**: El frontend evalúa dinámicamente si el peso y consumo real coinciden con los rangos ideales, mostrando badges de alerta visual:
  - <span style="color:#22c55e">**Óptimo / Normal**</span>: El animal está dentro de los rangos zootécnicos recomendados.
  - <span style="color:#eab308">**Deficiente / Bajo**</span>: El animal está bajo de peso o consume menos alimento de lo que requiere (riesgo de desnutrición).
  - <span style="color:#ef4444">**Exceso / Alto**</span>: Consumo de alimento o peso excesivo (sobrecosto innecesario o sobrepeso).

#### C. Control Sanitario (`vacunacion.py` <-> `backend_ia.py`)
- **Frontend**: Permite registrar vacunas aplicadas y ver alertas de vacunas faltantes por animal.
- **Backend**:
  - `auditar_vacunas_faltantes_finca()`: Compara dinámicamente la especie de cada animal activo con el catálogo oficial de vacunas exigidas. 
  - Cruza el historial y detecta si al animal le falta alguna vacuna obligatoria (por ejemplo: Fiebre Aftosa obligatoria nacional para Bovinos, o Brucelosis para hembras).

---

## 3. Implementación de la Inteligencia Artificial (IA)

AdmiFinca cuenta con un módulo de inteligencia artificial altamente robusto parametrizado en `ia_provider.py` y `backend_ia.py`.

### Arquitectura de Proveedores de IA (`ia_provider.py`)
El sistema está diseñado para operar bajo dos modalidades configurables en el archivo `.env` (`IA_PROVIDER`):
1. **LM Studio (Local/Offline)**: Apunta a un servidor local de modelos de lenguaje (como Llama 3 o Qwen) en el puerto `1234`. Esto permite ejecutar predicciones sin internet y sin costos adicionales.
2. **Google Gemini (Nube/Online)**: Utiliza la API oficial de Google Gemini (`gemini-2.5-flash` o `gemini-pro`) para diagnósticos avanzados y de alta calidad mediante llamadas en la nube.

### A. Auditoría Clínica Veterinaria Individual
Cuando el usuario presiona el botón **"Auditar con IA"** en la tabla de predicciones:
1. **Recopilación de Contexto (`obtener_contexto_clinico`)**: El backend extrae de la base de datos la ficha técnica del animal: especie, sexo, edad exacta, categoría INSAI, último peso registrado, consumo, historial completo de vacunas aplicadas con vigencia, y si se encuentra en **período de retiro de medicamentos** (cuarentena de fármacos).
2. **Reglas del Prompt Clínico**: Se envía un prompt de sistema estricto indicando que actúe como un médico veterinario del estado Falcón, Venezuela.
   - **Regla de Oro Inquebrantable**: Si el animal se encuentra en período de retiro activo (por ejemplo, vacunado recientemente con un lote biológico que requiere 30 días de resguardo), el estado de salud se **fuerza obligatoriamente a "ALERTA" o "CRÍTICO"** para evitar la venta o faena ilegal del ejemplar, garantizando la inocuidad alimentaria.
3. **Respuesta Estructurada JSON**: La IA responde estrictamente en formato JSON:
   ```json
   {
       "estado_salud": "optimo/alerta/critico",
       "diagnostico": "Análisis resumido en máximo 20 palabras.",
       "requerimiento": "Acción inmediata recomendada en máximo 15 palabras."
   }
   ```
   El frontend lee este JSON y renderiza dinámicamente la ventana modal de diagnóstico con su correspondiente color del semáforo.

### B. Auditoría Gerencial Colectiva (Macro)
Cuando el usuario genera el **Reporte Gerencial con IA**:
1. El backend consolida los costos diarios y mensuales de la finca (multiplicando el consumo total del rebaño activo por el costo de alimento configurado).
2. Audita e identifica todos los animales bovinos activos que **no tienen la vacuna obligatoria de Fiebre Aftosa**.
3. Extrae todas las vacunas con dosis vencidas y cuántos días de retraso llevan.
4. Lista los animales con anomalías de peso o ingesta.
5. **Prompt de Estrategia Financiera**: Envía toda esta matriz a la IA con un prompt detallado para generar un informe organizado que separa los riesgos sanitarios (riesgo epidemiológico en Falcón por Fiebre Aftosa) de la estrategia de optimización alimenticia (racionamiento de animales sobrealimentados para ahorrar dinero).

---

## 4. Validaciones de Inputs y Seguridad en el Frontend

Para asegurar la robustez del sistema y la integridad de la base de datos contra fallos del usuario o scripts maliciosos, se han implementado medidas de validación en múltiples capas:

### A. Prevención de Inyección SQL
- **Consultas Parametrizadas**: Ninguna variable es concatenada directamente dentro de las cadenas de consultas SQL. En todos los archivos `backend_*.py`, las consultas utilizan placeholders (`%s`) y pasan los valores como tuplas a la librería PyMySQL:
  ```python
  # Implementación Correcta y Segura en backend_animales.py
  cursor.execute("SELECT id_especie FROM especies WHERE nombre = %s;", (nombre_especie,))
  ```
  Esto previene que caracteres maliciosos como `' OR '1'='1` alteren la lógica de la base de datos.

### B. Sanitización contra Scripting Malicioso (XSS y HTML Injection)
- **Compilación e Inmutabilidad de Reflex**: Al utilizar Reflex, los inputs de texto del frontend (`rx.input`) se enlazan de forma bidireccional a variables del estado (`rx.Var`). Reflex compila y renderiza estos componentes sanitizándolos automáticamente en el cliente de React antes de dibujarlos en la pantalla.
- **Validaciones de Tipos de Datos en el State**: Al recibir datos numéricos (como precios o consumos de alimentos en `views/alimentacion.py`), el State valida explícitamente la entrada convirtiéndola en un tipo flotante (`float`) dentro de bloques `try-except`. Si un atacante ingresa una cadena de comandos en lugar de un precio, el sistema captura el error y aplica un valor por defecto seguro (por ejemplo, `0.50`), bloqueando la ejecución de código dañino.

### C. Buscador Reactivo y Seguro en Frontend
- Para evitar que un usuario realice peticiones maliciosas masivas o "denial-of-service" (DoS) a la base de datos mediante la barra de búsqueda, la búsqueda en las tablas de AdmiFinca (IA, Alimentación, Vacunas) se realiza a través de **propiedades reactivas filtradas del lado del cliente** (`@rx.var`):
  ```python
  @rx.var
  def datos_biometricos_ia_filtrados(self) -> list[list]:
      if self.busqueda.strip() == "":
          return self.datos_biometricos_ia
      termino = self.busqueda.strip().lower()
      return [
          row for row in self.datos_biometricos_ia
          if (termino in str(row[0]).lower()) or (termino in str(row[1]).lower())
      ]
  ```
  Esto asegura que la base de datos solo sea consultada una vez al cargar la vista, y el filtrado posterior ocurra instantáneamente en memoria, protegiendo el backend.

---

## 5. Reporte Gerencial PDF Automatizado (`backend_reporte_pdf.py`)

Para permitir la toma de decisiones gerenciales fuera de la plataforma, se desarrolló un generador de reportes en PDF exportable de nivel corporativo utilizando la librería **FPDF2**.

### Características Técnicas del Reporte PDF:
1. **Envuelto de Texto Automático (Wrapping)**: Se migró la estructura al gestor nativo de tablas de FPDF2 (`with pdf.table(...)`). Esto soluciona los problemas de desbordamiento de columnas cuando un animal posee múltiples vacunas faltantes, permitiendo que la celda expanda su altura automáticamente hacia abajo.
2. **Estética y Diseño Visual Coherente**:
   - Encabezado púrpura oscuro que coincide con la marca de AdmiFinca.
   - Alternancia de colores en filas de tabla (cebra-row con color lila claro y blanco) para una lectura fluida.
   - Indicadores de KPI en bloques destacados con formato de moneda y unidades.
3. **Ortografía en Español**: Todo el texto estático y dinámico del PDF soporta la codificación estándar para el idioma español (acentos, diéresis, eñes) nativamente sobre la tipografía Helvetica estándar.
4. **Secciones Estructuradas del Reporte**:
   - **Sección 1**: Resumen Financiero de Alimentación (gasto proyectado diario, mensual y anualizado).
   - **Sección 2**: Censo y Estado Biométrico con semáforo de pesos e ideales.
   - **Sección 3**: Auditoría Sanitaria de Vacunas Faltantes obligatorias por animal.
   - **Sección 4**: Reporte de Retrasos en dosis vencidas expresado en días transcurridos.
   - **Sección 5**: Historial de Inmunización del Rebaño.
   - **Sección 6**: Diagnóstico explícito de anomalías alimenticias (Subalimentación y Sobrealimentación).
   - **Sección 7**: Desglose porcentual del costo diario por especie.
   - **Nota Legal**: Disclaimer zootécnico y de responsabilidad.

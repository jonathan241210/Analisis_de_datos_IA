# 🧪 DataLab Copiloto IA

Aplicación web interactiva en **Streamlit** para análisis exploratorio, limpieza,
transformación de datos y Machine Learning sobre archivos CSV/Excel, con un
**Copiloto de IA conversacional** (NVIDIA NIM API / DeepSeek) integrado.

## 1. Estructura del proyecto

```
ds_copilot/
├── app.py                          # Punto de entrada Streamlit (navegación entre módulos)
├── config.py                       # Claves de API, catálogo de modelos, constantes
├── requirements.txt
├── .env.example
├── modules/
│   ├── data_ingestion.py           # Módulo 1: carga CSV/Excel/TSV
│   ├── eda.py                      # Módulo 2: análisis exploratorio
│   ├── data_wrangling.py           # Módulo 3: limpieza y transformación
│   ├── machine_learning.py         # Módulo 4: ML supervisado/no supervisado
│   └── ai_copilot/
│       ├── client.py               # Llamadas HTTP a NVIDIA NIM / DeepSeek
│       ├── context_builder.py      # Payload de metadata + contexto adaptativo
│       ├── prompts.py              # System prompt del copiloto
│       ├── executor.py             # Ejecución controlada del código generado
│       └── ui_chat.py              # Interfaz de chat (selector, botones copiar/ejecutar)
└── utils/
    ├── session_state.py            # Estado global de sesión (df, historial, chat)
    └── helpers.py                  # Funciones auxiliares
```

## 2. Instalación

```bash
# 1. Crear y activar un entorno virtual
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar las claves de API
cp .env.example .env
# Edita .env y coloca tus claves de NVIDIA_API_KEY y/o DEEPSEEK_API_KEY

# 4. Ejecutar la aplicación
streamlit run app.py
```

La app quedará disponible en `http://localhost:8501`.

## 3. Módulos

1. **Ingesta de Datos** — carga drag-and-drop de CSV/TSV/Excel con detección
   automática de separador y codificación, y vista previa inmediata.
2. **EDA** — métricas generales, estadística descriptiva, diagnóstico de calidad
   (nulos, duplicados, varianza cero) e histogramas/boxplots/heatmap de correlación.
3. **Data Wrangling** — imputación/eliminación de nulos y duplicados, casteo de
   tipos, escalado (StandardScaler/MinMaxScaler), codificación (One-Hot/Label),
   renombrado/filtrado de columnas y exportación a CSV. Incluye botón de "deshacer".
4. **Machine Learning** — supervisado (regresión lineal/logística, Random Forest,
   Decision Tree, XGBoost) con métricas (MSE, R², Accuracy, F1, matriz de
   confusión); no supervisado (K-Means con método del codo, DBSCAN, PCA 2D/3D).
5. **Copiloto de IA** — selector de modelo (NVIDIA Nemotron / DeepSeek-R1), chat
   con bloques de código Python ejecutables directamente sobre el `df` activo,
   con botones **📋 Copiar** y **▶️ Ejecutar**.

## 4. Manejo seguro de ejecución de código IA

El código Python generado por la IA **nunca se ejecuta a ciegas**:

- `modules/ai_copilot/executor.py` valida cada bloque con el módulo `ast` antes
  de ejecutarlo: rechaza imports fuera de una lista blanca (pandas, numpy,
  matplotlib, seaborn, plotly, sklearn), accesos a atributos dunder, y llamadas
  a funciones/módulos peligrosos (`eval`, `exec`, `open`, `os`, `subprocess`, etc.).
- El código corre en un `exec()` con un `globals()`/`builtins` restringido —no
  el entorno real del proceso— y siempre sobre una **copia** de `df`.
- El resultado solo reemplaza el DataFrame de la sesión si la ejecución termina
  sin errores.
- Para un aislamiento a nivel de sistema operativo (recomendado en producción
  con usuarios no confiables), se sugiere además ejecutar el proceso de
  Streamlit dentro de un contenedor Docker con permisos mínimos y sin acceso
  de red saliente salvo a los endpoints de IA necesarios.

## 5. Notas sobre el Copiloto de IA

- **Regla de oro:** nunca se envía el dataset completo a la IA, solo metadata
  (`shape`, `dtypes`, columnas, `head(3)`, `sample(3)`, `describe()`, nulos,
  top valores categóricos) — ver `context_builder.py`.
- **Contexto adaptativo:** según palabras clave en la pregunta del usuario
  (limpieza, correlación, outliers, ML, gráficos) se añaden bloques extra de
  contexto solo cuando son relevantes, para optimizar tokens.
- El modelo **nunca** opera directamente sobre los datos: solo genera código
  Python, que el backend ejecuta sobre el `df` real tras la validación de
  seguridad.

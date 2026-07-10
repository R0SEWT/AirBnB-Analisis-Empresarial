# Prompt para generar la PPTX CRISP-DM de Airbnb

Actua como consultor senior de estrategia analitica, ciencia de datos y diseno ejecutivo. Necesito una presentacion PowerPoint editable en espanol, basada solamente en la informacion del proyecto actual de Airbnb disponible en el repositorio.

Tema de la presentacion:

Modelado CRISP-DM para un sistema predictivo de calidad y riesgo de listings de Airbnb.

Objetivo SMART:

Desarrollar e implementar, en un plazo de 12 meses hasta diciembre de 2026, un sistema predictivo de calidad y riesgo de listings basado en machine learning, que identifique con precision minima de 85% los listings con alta probabilidad de generar disputas graves antes de su primera reserva, y que reduzca en al menos 20% la tasa de disputas graves en EE.UU., Brasil, Mexico, Espana y Japon frente a la linea base 2S-2025.

Pregunta de negocio:

Como reducir la tasa de disputas graves en los 5 paises en un 20%?

Fuentes internas a usar:

- `README.md`
- `docs/architecture.md`
- `docs/data-medallion.md`
- `docs/dashboard-model.md`
- `docs/trust-risk-analytics.md`
- `docs/crisp-dm-modelado-airbnb.md`
- `data/gold/listings.parquet`
- `data/gold/reviews.parquet`
- `data/gold/analytics/listing_trust_risk.parquet`
- `data/gold/analytics/market_trust_risk_summary.parquet`
- `data/gold/analytics/risk_segment_summary.parquet`

Restricciones:

- No inventar metricas de precision ni reduccion real de disputas.
- Indicar que la precision de 85% y la reduccion de 20% estan pendientes de validacion porque faltan tablas reales de reservas, disputas y soporte.
- Usar el `risk_score` actual como baseline explicable, no como modelo supervisado validado.
- Explicar que la primera review observada es un proxy operativo hasta incorporar outcomes reales.
- No usar logos oficiales si no hay asset verificado; usar solo el nombre Airbnb como texto.

Estructura sugerida de 10 diapositivas:

1. Portada: tesis del proyecto, objetivo SMART y pregunta de negocio.
2. Enfoque de negocio: convertir la pregunta en un sistema preventivo de decision.
3. CRISP-DM: mapa de las seis fases aplicado al caso Airbnb.
4. Comprension de datos: arquitectura medallion y activos gold/analytics disponibles.
5. Baseline actual: score interpretable de trust/risk, componentes y segmentos.
6. Evidencia por mercado: ranking de riesgo en EE.UU., Brasil, Mexico, Espana y Japon.
7. Preparacion para ML: features pre-reserva y etiqueta futura `severe_dispute_flag`.
8. Modelado y evaluacion: escalera de modelos, metricas y criterio de aprobacion.
9. Despliegue y roadmap: flujo operativo y plan de 12 meses hacia diciembre 2026.
10. Decision final: respuesta a la pregunta de negocio, brechas y siguientes acciones.

Estilo visual:

- Presentacion ejecutiva, limpia, academica y orientada a decisiones.
- Fondo claro calido, texto oscuro, acento coral asociado a Airbnb y acentos secundarios teal/gold.
- Usar diagramas, barras, tablas compactas y timelines; evitar diapositivas llenas de parrafos.
- Cada slide debe tener un titulo con conclusion, no solo un tema.
- Incluir pies discretos con fuente interna del repositorio.

Resultado esperado:

- Archivo `.pptx` editable.
- Narrativa clara de CRISP-DM.
- Evidencia cuantitativa actual: 136,615 listings, 5,361,259 reviews, 12,441 listings High, 9.11% High/Critical, mercados disponibles y brechas de datos.
- Cierre honesto: el proyecto esta listo para baseline proxy y dashboard; para validar el objetivo SMART se requieren reservas, disputas y soporte.

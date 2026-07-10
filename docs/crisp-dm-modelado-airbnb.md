# Modelado CRISP-DM - Airbnb Trust & Safety

## 1. Comprension del negocio

### Objetivo SMART seleccionado

Desarrollar e implementar, en un plazo de 12 meses hasta diciembre de 2026, un sistema predictivo de calidad y riesgo de listings basado en machine learning, que identifique con precision minima de 85% los listings con alta probabilidad de generar disputas graves antes de su primera reserva, y que reduzca en al menos 20% la tasa de disputas graves en EE.UU., Brasil, Mexico, Espana y Japon frente a la linea base 2S-2025.

### Pregunta de negocio

Como reducir la tasa de disputas graves en los 5 paises en un 20%?

### Enfoque analitico

El caso se formula como un problema de clasificacion binaria y priorizacion de riesgo a nivel de `listing_id`. El sistema debe estimar la probabilidad de que un listing genere una disputa grave y convertir esa probabilidad en acciones operativas antes de su primera reserva: revision manual, verificacion adicional del host, mejora de contenido del anuncio, monitoreo preventivo o hold temporal para casos de riesgo alto.

La informacion disponible en el proyecto ya contiene una base de analitica de confianza y riesgo. Actualmente existe un `risk_score` interpretable de 0 a 100, un `trust_score`, segmentos `Low`, `Moderate`, `High` y `Critical`, causas proxy y acciones recomendadas. Ese score debe tratarse como baseline explicable, no como evidencia de precision de machine learning, porque el repositorio documenta que aun faltan etiquetas reales de disputas graves.

### Criterios de exito

| Tipo | Criterio |
|---|---|
| Negocio | Reducir en al menos 20% la tasa de disputas graves frente a la linea base 2S-2025 en EE.UU., Brasil, Mexico, Espana y Japon. |
| Modelo | Alcanzar precision minima de 85% para detectar listings con alta probabilidad de disputa grave. |
| Operacion | Priorizar listings `High` y `Critical` para acciones preventivas de Trust & Safety, soporte, compliance y mejora de experiencia. |
| Medicion | Incorporar tablas de reservas, disputas y soporte para medir precision, falsos positivos, tasa real de disputas, escalamiento humano y tiempo de resolucion. |

### Usuarios de negocio

- Lider de Ciencia de Datos: monitorea desempeno, precision, falsos positivos, deriva y calibracion.
- Equipo de Trust & Safety: prioriza revision manual, verificacion adicional y prevencion de fraude.
- Operaciones por mercado: identifica paises, ciudades y segmentos con mayor concentracion de riesgo.
- Producto: evalua cambios en flujo, soporte, pricing o contenido del listing.
- Legal y Compliance: observa mercados donde restricciones locales pueden afectar la operacion.

## 2. Comprension de los datos

### Fuentes actuales del proyecto

El repositorio usa arquitectura medallion:

```text
raw -> bronze -> silver -> gold
```

Las fuentes raw esperadas son:

```text
data/raw/listings*.csv.gz
data/raw/reviews*.csv.gz
```

Las salidas gold principales son:

```text
data/gold/listings.parquet
data/gold/reviews.parquet
```

Tambien existe un mart analitico de riesgo:

```text
data/gold/analytics/listing_trust_risk.parquet
data/gold/analytics/market_trust_risk_summary.parquet
data/gold/analytics/risk_segment_summary.parquet
data/gold/analytics/trust_risk_summary.json
```

### Cobertura actual observada

Segun los marts generados en el proyecto:

| Recurso | Filas | Uso |
|---|---:|---|
| `data/gold/listings.parquet` | 136,615 | Entidad principal a nivel de listing. |
| `data/gold/reviews.parquet` | 5,361,259 | Evidencia historica de reviews por listing. |
| `data/gold/analytics/listing_trust_risk.parquet` | 136,615 | Score y segmentacion de riesgo por listing. |
| `data/gold/analytics/market_trust_risk_summary.parquet` | 7 | Resumen por mercado disponible. |

Los 5 paises objetivo estan representados por 7 mercados disponibles:

| Pais | Mercados actuales |
|---|---|
| United States | Asheville, New Orleans |
| Brazil | Rio de Janeiro |
| Mexico | Mexico City |
| Spain | Barcelona, Girona / Costa Brava |
| Japan | Tokyo |

### Variables disponibles

`listings` contiene identificadores, host, ubicacion, tipo de propiedad, capacidad, precio, disponibilidad y ratings declarados. Entre las variables utiles para modelado estan:

- `listing_id`, `host_id`, `host_since`
- `host_is_superhost`, `host_identity_verified`
- `host_response_rate`, `host_acceptance_rate`
- `neighbourhood_cleansed`, `latitude`, `longitude`
- `property_type`, `room_type`, `accommodates`
- `bathrooms`, `bedrooms`, `beds`
- `price`, `price_per_accommodates`
- `minimum_nights`, `maximum_nights`, `availability_365`
- `number_of_reviews`, `review_scores_rating`, `reviews_per_month`
- `description`, `name`, `_source_file`

`reviews` contiene:

- `listing_id`, `review_id`, `review_date`
- `review_year`, `review_month`
- `reviewer_id`, `comments`
- `comment_length`, `has_comment`

El mart `listing_trust_risk` agrega:

- `risk_score`, `trust_score`, `risk_segment`
- `primary_risk_driver`, `dispute_cause_proxy`
- `listing_lifecycle_stage`, `recommended_action`
- componentes: `quality_risk`, `host_trust_risk`, `review_confidence_risk`, `listing_completeness_risk`, `price_market_risk`

### Estado actual del riesgo proxy

| Segmento | Listings | Risk score promedio | Trust score promedio | Rating promedio | Reviews observadas promedio |
|---|---:|---:|---:|---:|---:|
| Low | 99,573 | 8.49 | 91.51 | 4.81 | 53.28 |
| Moderate | 24,601 | 38.68 | 61.32 | 4.20 | 2.25 |
| High | 12,441 | 54.40 | 45.60 | 2.59 | 0.07 |

No hay listings `Critical` en el mart actual. Los listings `High` representan 12,441 de 136,615 listings, aproximadamente 9.11%.

### Resumen por mercado

| Pais | Mercado | Listings | Risk score promedio | Listings High/Critical | Tasa High/Critical |
|---|---|---:|---:|---:|---:|
| Spain | Barcelona | 18,177 | 26.48 | 3,374 | 18.56% |
| Spain | Girona / Costa Brava | 17,069 | 20.99 | 1,688 | 9.89% |
| Brazil | Rio de Janeiro | 43,068 | 19.96 | 5,340 | 12.40% |
| United States | New Orleans | 453 | 16.13 | 34 | 7.51% |
| Mexico | Mexico City | 27,051 | 13.98 | 1,550 | 5.73% |
| Japan | Tokyo | 27,945 | 12.92 | 370 | 1.32% |
| United States | Asheville | 2,852 | 9.76 | 85 | 2.98% |

### Brechas de datos

El proyecto documenta que, con los recursos actuales, la primera review observada se usa como proxy operativo de actividad posterior a reserva. Para entrenar y evaluar el sistema predictivo final se deben incorporar:

- reservas, para conocer fecha de primera reserva y evitar leakage;
- disputas, para construir la etiqueta real de disputa grave;
- soporte, para medir tiempo de resolucion y escalamiento humano;
- logs de decisiones de IA/operacion, para medir falsos positivos y acciones aplicadas;
- linea base 2S-2025 de disputas graves por pais/mercado.

Sin estas fuentes no se debe afirmar precision de 85% ni reduccion real de 20%; solo se puede documentar el baseline proxy y el diseno CRISP-DM del modelo.

## 3. Preparacion de los datos

### Pipeline actual

El flujo de preparacion existente es:

```text
data/raw -> data/bronze -> data/silver -> data/gold -> data/gold/analytics
```

La capa `silver` tipifica, limpia y deduplica entidades:

- convierte `listing_id`, `host_id`, precios, porcentajes y fechas;
- normaliza booleanos de host;
- elimina duplicados por `listing_id` y `review_id`;
- calcula `comment_length`, `has_comment` y `price_per_accommodates`.

La capa `gold` publica:

- `listings.parquet`, una fila por `listing_id`;
- `reviews.parquet`, una fila por `review_id`.

El mart de analitica de riesgo agrega reviews por listing y calcula senales como:

- `observed_reviews`
- `first_observed_review_date`
- `last_observed_review_date`
- `avg_comment_length`
- `non_empty_review_count`
- `review_recency_days`

### Variables candidatas para modelado

| Grupo | Variables |
|---|---|
| Calidad del listing | `review_scores_rating`, longitud de `description`, completitud de precio, banos, dormitorios, coordenadas. |
| Confianza del host | `host_identity_verified`, `host_is_superhost`, `host_response_rate`, `host_acceptance_rate`, antiguedad del host. |
| Evidencia de reviews | `observed_reviews`, `avg_comment_length`, `review_recency_days`, `number_of_reviews`, `reviews_per_month`. |
| Mercado y ubicacion | `country`, `market_label`, `neighbourhood_cleansed`, `latitude`, `longitude`. |
| Oferta y reglas | `room_type`, `property_type`, `accommodates`, `minimum_nights`, `maximum_nights`, `availability_365`. |
| Precio | `price`, `price_per_accommodates`, bandera de precio atipico por mercado y tipo de habitacion. |

### Definicion de etiqueta futura

La etiqueta recomendada para el modelo supervisado es:

```text
severe_dispute_flag = 1 si el listing genera una disputa grave en la primera reserva o dentro de una ventana operativa definida despues de la primera reserva; 0 en caso contrario.
```

La ventana debe fijarse con negocio y operaciones. Para mantener coherencia con el objetivo, las features usadas al momento de scoring deben existir antes de la primera reserva. Las variables calculadas despues de la reserva solo pueden usarse para evaluacion, no para prediccion preventiva.

## 4. Modelado

### Formulacion

El modelo final se plantea como:

```text
P(disputa_grave = 1 | senales_pre_reserva_del_listing)
```

La salida debe ser:

- probabilidad de disputa grave;
- segmento de riesgo operativo;
- explicacion principal del riesgo;
- accion recomendada.

### Baseline actual

El baseline disponible es `interpretable_rule_based_score_v1`, implementado en `src/analytics/trust_risk.py`. Calcula:

```text
risk_score = quality_risk
           + host_trust_risk
           + review_confidence_risk
           + listing_completeness_risk
           + price_market_risk
```

Y:

```text
trust_score = 100 - risk_score
```

Los segmentos son:

| Segmento | Rango |
|---|---|
| Low | 0-24 |
| Moderate | 25-49 |
| High | 50-74 |
| Critical | 75-100 |

Este baseline sirve para priorizacion inicial, auditoria de reglas y comparacion futura contra modelos supervisados.

### Escalera de modelos

La arquitectura del proyecto recomienda comenzar por baselines fuertes antes de modelos complejos:

1. Regresion logistica.
2. Random forest.
3. Gradient boosting.
4. Modelo tabular con embeddings de texto.
5. Ensamble.

Para este caso, la primera version supervisada deberia iniciar con regresion logistica y gradient boosting, porque permiten comparar interpretabilidad, precision y ranking de riesgo sin introducir complejidad innecesaria.

### Estrategia de entrenamiento

Cuando existan reservas y disputas:

- construir snapshots historicos de listings antes de la primera reserva;
- unir la etiqueta `severe_dispute_flag`;
- separar train/valid/test por tiempo para evitar leakage;
- calibrar probabilidades por pais o mercado si hay diferencias fuertes;
- elegir umbral de accion que alcance precision minima de 85%;
- medir recall para asegurar que no se detecten muy pocos casos;
- validar equidad por pais, mercado, tipo de habitacion y tipo de host.

## 5. Evaluacion

### Metricas tecnicas

El proyecto define metricas para clasificacion y ranking de riesgo. Para este objetivo se priorizan:

- `precision`, porque la meta minima es 85%;
- `recall`, para estimar cuantas disputas graves son detectadas;
- `F1`, como balance entre precision y recall;
- `ROC-AUC` y `PR-AUC`, especialmente si la disputa grave es poco frecuente;
- `precision@k` y `recall@k`, para listas operativas de revision;
- `false_positive_rate`, para no afectar injustamente a hosts;
- calibracion, para que una probabilidad estimada sea interpretable;
- segment fairness, para controlar sesgos por mercado;
- model drift, para detectar degradacion temporal.

### Metricas de negocio

La reduccion de disputas graves debe calcularse frente a la linea base 2S-2025:

```text
reduccion_disputas = (tasa_base_2S_2025 - tasa_post_modelo) / tasa_base_2S_2025
```

El objetivo se cumple si:

```text
reduccion_disputas >= 20%
```

La tasa debe medirse por pais y en conjunto para EE.UU., Brasil, Mexico, Espana y Japon.

### Criterios de aprobacion

El modelo solo debe pasar a despliegue amplio si cumple:

- precision mayor o igual a 85% en test temporal;
- reduccion observada o experimental de al menos 20% en disputas graves;
- falsos positivos dentro de tolerancia operativa;
- monitoreo por mercado sin deterioros graves;
- trazabilidad de accion recomendada por listing.

## 6. Despliegue

### Flujo operativo propuesto

1. Ejecutar pipeline medallion:

```bash
python -m src.pipeline.run_medallion
```

2. Construir marts de riesgo:

```bash
python -m src.pipeline.build_trust_risk_analytics
```

3. Generar dashboard:

```bash
python -m src.dashboard.trust_risk_dashboard
```

4. Priorizar listings:

- `Critical`: hold preventivo o revision inmediata.
- `High`: revision manual y accion correctiva.
- `Moderate`: monitoreo y mejora de informacion.
- `Low`: operacion normal.

### Salidas para negocio

| Salida | Uso |
|---|---|
| `listing_trust_risk.parquet` | Priorizacion granular por listing. |
| `market_trust_risk_summary.parquet` | Gestion por pais y mercado. |
| `risk_segment_summary.parquet` | Seguimiento ejecutivo por segmento. |
| `trust_risk_dashboard.html` | Visualizacion local para Trust & Safety y operaciones. |

### Monitoreo

El monitoreo debe incluir:

- precision y recall por mes;
- tasa de disputas graves por pais;
- volumen de listings `High` y `Critical`;
- falsos positivos confirmados;
- deriva de variables como precio, disponibilidad, rating y reviews;
- comparacion contra linea base 2S-2025;
- efectividad de acciones recomendadas.

## 7. Plan de 12 meses hacia diciembre 2026

| Periodo | Entregable |
|---|---|
| Meses 1-2 | Integrar contratos de datos para reservas, disputas y soporte; fijar definicion de disputa grave y linea base 2S-2025. |
| Meses 3-4 | Construir snapshots pre-reserva, features historicas y etiqueta `severe_dispute_flag`. |
| Meses 5-6 | Entrenar baseline supervisado y gradient boosting; comparar contra `risk_score` actual. |
| Meses 7-8 | Calibrar umbrales por pais/mercado y validar precision minima de 85%. |
| Meses 9-10 | Piloto operativo en los 5 paises con revision manual y acciones preventivas. |
| Meses 11-12 | Medir reduccion vs 2S-2025, ajustar monitoreo y preparar despliegue productivo. |

## 8. Decision final del CRISP-DM

El proyecto debe avanzar desde el score proxy explicable actual hacia un modelo predictivo supervisado, siempre que se integren las fuentes faltantes de reservas, disputas y soporte. Con la informacion disponible hoy, la propuesta mas consistente es usar el `risk_score` actual como baseline de priorizacion, documentar la brecha de etiquetas y preparar el pipeline para entrenar un clasificador de disputa grave a nivel de listing cuando existan datos reales de outcomes.

La respuesta a la pregunta de negocio es: reducir la tasa de disputas graves en 20% requiere identificar preventivamente los listings de mayor riesgo, aplicar acciones diferenciadas antes de su primera reserva y medir el impacto contra la linea base 2S-2025 en cada pais objetivo.

# Modelo analitico de confianza y riesgo

Esta rama agrega un modelo analitico explicable para producir informacion dashboard-ready sobre confianza y riesgo en listings de Airbnb.

## Objetivo del dashboard

Monitorear la calidad y el riesgo de listings antes y despues de su primera reserva, identificar mercados y tipos de propiedades con mayor probabilidad de disputas graves, y apoyar decisiones de Trust & Safety, soporte, compliance y mejora de experiencia.

Con los recursos actuales, el dashboard usa la primera review observada como proxy operativo de actividad posterior a reserva. Para calcular precision, falsos positivos, tasa real de disputas graves, escalamiento humano y tiempo de resolucion se deben incorporar tablas de reservas, disputas y soporte.

## Usuarios del dashboard

- Lider de Ciencia de Datos: monitorea desempeno del modelo, precision, falsos positivos y deriva cuando existan etiquetas reales.
- Equipo de Trust & Safety: prioriza revision manual, verificacion adicional y prevencion de fraude.
- Equipo de Operaciones por mercado: identifica paises o ciudades con mayor concentracion de riesgo.
- Equipo de Producto: evalua si cambios de flujo, soporte o pricing reducen fricciones.
- Equipo Legal/Compliance: observa mercados donde restricciones locales pueden afectar operacion.

## Indicadores clave

| Indicador | Estado actual | Uso de negocio |
|---|---|---|
| Listings de alto riesgo | Calculado desde `risk_segment` High/Critical | Reducir exposicion a disputas antes de la primera reserva. |
| Precision del modelo | Pendiente de etiquetas de disputa grave | Meta minima: 85%. |
| Tasa de disputas graves | Pendiente de reservas y disputas | Meta: reduccion minima de 20% frente a linea base 2S-2025. |
| Tiempo de resolucion | Pendiente de sistema de soporte | Evaluar eficacia de soporte IA + humano. |
| Escalamiento humano | Pendiente de logs de IA/soporte | Controlar que la automatizacion no elimine juicio contextual. |
| Falsos positivos | Pendiente de outcomes posteriores | Evitar impacto injusto sobre hosts. |

## Entradas

```text
data/gold/listings.parquet
data/gold/reviews.parquet
```

## Salidas

```text
data/gold/analytics/listing_trust_risk.parquet
data/gold/analytics/market_trust_risk_summary.parquet
data/gold/analytics/risk_segment_summary.parquet
data/gold/analytics/trust_risk_summary.json
```

Tambien se generan CSV para consumo practico en BI:

```text
data/gold/analytics/listing_trust_risk.csv
data/gold/analytics/market_trust_risk_summary.csv
data/gold/analytics/risk_segment_summary.csv
```

## Componentes del score

El `risk_score` se calcula de 0 a 100 mediante cinco componentes:

| Componente | Senales |
|---|---|
| `quality_risk` | rating bajo o ausente |
| `host_trust_risk` | identidad no verificada, no superhost, baja respuesta o aceptacion |
| `review_confidence_risk` | pocas reviews, reviews antiguas o comentarios muy cortos |
| `listing_completeness_risk` | descripcion corta, precio ausente, atributos incompletos |
| `price_market_risk` | precio atipico o alta disponibilidad con baja evidencia de demanda |

Tambien se calcula:

```text
trust_score = 100 - risk_score
```

## Segmentos

| Segmento | Rango |
|---|---|
| Low | 0-24 |
| Moderate | 25-49 |
| High | 50-74 |
| Critical | 75-100 |

## Ejecucion

```bash
python -m src.pipeline.build_trust_risk_analytics
python -m src.dashboard.trust_risk_dashboard
```

Dashboard generado:

```text
dashboards/trust_risk_dashboard.html
```

## Visualizaciones implementadas

| Visualizacion | Contenido | Decision que habilita |
|---|---|---|
| Mapa geografico | Estados Unidos, Brasil, Mexico, Espana y Japon segun archivos gold disponibles | Priorizar acciones locales. |
| Tarjetas KPI | Listings evaluados, alto riesgo, porcentaje alto riesgo, risk score y trust score | Monitoreo ejecutivo. |
| Tabla de KPIs operativos | Precision, disputas graves, resolucion, escalamiento y falsos positivos como metricas pendientes de fuente | Alinear brechas de datos. |
| Embudo de riesgo | Listings evaluados -> alto riesgo -> revision manual -> hold preventivo | Medir eficiencia del flujo operativo. |
| Matriz causa-impacto | Causas proxy: limpieza/fotos, seguridad/comunicacion, evidencia insuficiente, contenido, precio/cancelacion | Atacar causas raiz. |
| Serie temporal proxy | High-risk listings por mes de ultima review observada | Medir evolucion hasta incorporar disputas reales. |
| Ranking de segmentos | Mercado, tipo de habitacion y etapa del listing | Definir politicas diferenciadas. |

## Uso en Power BI, Tableau o Looker

Importar las tablas de `data/gold/analytics/` como marts de consumo:

- `listing_trust_risk`: granularidad por `listing_id`.
- `market_trust_risk_summary`: resumen por mercado.
- `risk_segment_summary`: resumen por segmento.

Metricas sugeridas:

- promedio de `risk_score`
- promedio de `trust_score`
- cantidad de listings High/Critical
- tasa de alto riesgo
- distribucion por `primary_risk_driver`
- acciones recomendadas por prioridad

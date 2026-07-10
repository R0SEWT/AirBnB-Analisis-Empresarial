# TB4 - Resultados para pegar: RFM Airbnb Trust & Safety

## 1. Rango temporal y datos procesados

- Rango temporal de reviews: 2010-06-07 a 2026-02-14.
- Fecha de corte RFM: 2026-02-15 = max(review_date) + 1 dia.
- Meses disponibles: 189.
- Reviews procesadas: 5,361,259.
- Listings procesados en los 5 paises objetivo: 136,615.
- Listings con al menos una review: 111,624.
- Se filtro a los 5 paises objetivo: 136,615 -> 136,615 listings.

## 2. Definicion RFM usada

- Recency: dias desde la ultima review observada hasta la fecha de corte. Menor recency implica actividad mas reciente.
- Frequency: cantidad de reviews observadas por listing. Se usa como proxy operativo de actividad posterior a reserva.
- Monetary proxy: `price * observed_reviews`. Es un proxy monetario, no ingreso real ni revenue de Airbnb.
- Annual value proxy: `price * reviews_per_month * 12` cuando `reviews_per_month` esta disponible.
- Los scores R, F y M van de 1 a 5. En R, menor recency recibe mayor score. En F y M, mayor valor recibe mayor score.

## 3. Tabla de segmentos RFM

| rfm_segment | cantidad_listings | porcentaje | recency_promedio | frequency_promedio | monetary_proxy_promedio | risk_score_promedio | high_critical_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Valor medio operativo | 43514 | 31.85 | 329.89 | 25.29 | 122,316.11 | 11.80 | 0.13 |
| Dormidos | 40201 | 29.43 | 3,651.29 | 0.87 | 1,889.62 | 40.18 | 30.79 |
| Champions / Alto valor activo | 24656 | 18.05 | 153.14 | 101.05 | 595,080.11 | 3.66 | 0.00 |
| Frecuentes de bajo valor | 12579 | 9.21 | 116.84 | 113.84 | 0.00 | 9.20 | 0.00 |
| Potenciales en crecimiento | 11869 | 8.69 | 153.50 | 8.15 | 63,693.39 | 8.75 | 0.03 |
| Alto valor en riesgo | 3752 | 2.75 | 526.66 | 54.71 | 298,921.02 | 8.97 | 0.00 |
| Nuevos o poca evidencia | 44 | 0.03 | 137.50 | 1.00 | 701.84 | 24.54 | 2.27 |

## 4. Tabla de mercados

| country | market_label | listings | segmento_dominante | rfm_promedio | risk_score_promedio | high_critical_pct |
| --- | --- | --- | --- | --- | --- | --- |
| Japan | Tokyo | 27945 | Valor medio operativo | 10.44 | 12.92 | 1.32 |
| United States | Asheville | 2852 | Valor medio operativo | 10.20 | 9.76 | 2.98 |
| Mexico | Mexico City | 27051 | Champions / Alto valor activo | 9.92 | 13.98 | 5.73 |
| United States | New Orleans | 453 | Frecuentes de bajo valor | 8.31 | 16.13 | 7.51 |
| Brazil | Rio de Janeiro | 43068 | Dormidos | 8.22 | 19.96 | 12.40 |
| Spain | Girona / Costa Brava | 17069 | Valor medio operativo | 6.93 | 20.99 | 9.89 |
| Spain | Barcelona | 18177 | Dormidos | 6.86 | 26.48 | 18.56 |

## 5. Tabla de prioridad de accion

| priority_segment | cantidad | porcentaje | accion_recomendada |
| --- | --- | --- | --- |
| Monitoreo bajo | 88373 | 64.69 | Seguimiento ligero; priorizar solo si cambia actividad o riesgo. |
| Proteger y retener | 35801 | 26.21 | Mantener visibilidad, monitorear calidad y proteger oferta de alto valor. |
| Bajo valor pero riesgoso | 12392 | 9.07 | Depurar, corregir datos minimos o mantener monitoreo preventivo. |
| Corregir antes de escalar | 49 | 0.04 | Aplicar mejoras de calidad/verificacion antes de campanas o mayor exposicion. |
| Prioridad critica | 0 | 0.00 | Revision Trust & Safety inmediata; corregir confianza antes de impulsar demanda. |

## 6. Interpretacion ejecutiva

- Se identificaron 35,801 listings con nivel RFM alto. Estos listings combinan actividad reciente, frecuencia y valor monetario proxy.
- Se identificaron 12,441 listings en segmentos Trust & Safety High/Critical.
- El cruce RFM x riesgo produce 0 listings de `Prioridad critica`: alto valor/actividad proxy y riesgo alto.
- Los listings de `Proteger y retener` son relevantes para crecimiento, pero deben mantenerse monitoreados para evitar deterioro de calidad.
- Los listings de `Corregir antes de escalar` no deberian recibir mayor exposicion comercial hasta resolver senales de confianza o calidad.

## 7. Limitaciones

- El repositorio no contiene reservas, pagos, comisiones ni disputas reales.
- Las reviews se usan como proxy de actividad posterior a reserva.
- `monetary_proxy` no debe llamarse ingreso real; solo aproxima valor potencial observable.
- `risk_score` y `risk_segment` son proxies analiticos del proyecto, no evidencia de disputas internas reales de Airbnb.
- Los precios provienen de mercados con monedas distintas; el proxy monetario no esta normalizado por tipo de cambio.
- No se afirma reduccion de disputas porque no existe una tabla de disputas reales.

## 8. Recomendaciones de negocio

- Priorizar `Prioridad critica` para revision Trust & Safety antes de acciones de crecimiento.
- Usar `Proteger y retener` para mantener oferta de alto valor proxy con riesgo bajo o moderado.
- Usar `Corregir antes de escalar` para activar acciones de mejora de calidad, verificacion o contenido.
- Usar la tabla de mercado para asignar capacidad operativa por pais y mercado.
- Integrar el RFM como complemento del modelo de riesgo de TB3 en el dashboard de confianza/riesgo.

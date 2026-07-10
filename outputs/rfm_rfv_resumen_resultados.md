# Resumen RFM/RFV - Airbnb

## Alcance

- Unidad de analisis: `listing_id`.
- Fuente principal: `data/gold/analytics/listing_trust_risk.parquet`.
- Fecha de corte analitica: 2026-02-14.
- RFM usa recencia, frecuencia y un proxy monetario `precio x reviews`.
- RFV usa recencia, frecuencia y un proxy de valor/confianza basado en `trust_score` y rating.
- No existen reservas ni gasto real en el repositorio; por tanto, RFM/RFV se presentan como proxies academicos y operativos.

## Hallazgos principales

- Total de listings segmentados: 136,615.
- Segmento RFM mas numeroso: Activos de alto potencial (36,551 listings; 26.75%).
- Segmento RFV mas numeroso: Valiosos a potenciar (39,070 listings; 28.60%).
- Accion operativa mas frecuente: Depurar, corregir o monitorear (61,353 listings; 44.91%).
- Mercado con mayor RFV promedio: Asheville (United States) con RFV promedio 10.85.
- Mercado con mas listings de alto potencial comercial y riesgo de confianza: Tokyo (Japan) con 3,441 listings.

## Uso recomendado

- `Mantener y proteger`: listings con buena traccion y buen valor/confianza; monitoreo y retencion.
- `Alto potencial comercial con riesgo de confianza`: prioridad para Trust & Safety y mejora de calidad antes de impulsar demanda.
- `Reactivar demanda de listings confiables`: candidatos para campanas, visibilidad, soporte a hosts o revision de precio.
- `Depurar, corregir o monitorear`: baja traccion y bajo valor/confianza; evaluar completitud, disponibilidad y calidad minima.

## Limitaciones

- Reviews se usan como proxy de reservas/actividad.
- Precio por noche se usa como proxy monetario; no representa ingreso real ni comisiones.
- `trust_score` y `risk_segment` son proxies del proyecto, no disputas internas reales.

# TB3 - Resumen ejecutivo de resultados Airbnb

## 1. Caso de uso seleccionado

Se desarrollo un caso de analitica empresarial para Airbnb orientado al **Dashboard de Confianza y Riesgo de Listings**. El objetivo es priorizar listings con menor confianza operacional y anticipar la actividad mensual del marketplace para apoyar Trust & Safety, Operaciones, Producto y Compliance.

## 2. Regresion logistica

- **Objetivo:** clasificar listings con mayor riesgo o menor confianza operacional mediante `high_risk_listing`.
- **Variable objetivo:** proxy academica basada en `risk_segment` High/Critical del mart `listing_trust_risk` cuando esta disponible. No representa disputas reales internas.
- **Principales variables utilizadas:** precio, disponibilidad, rating, numero de reviews, reviews por mes, senales del host, capacidad, reglas de estancia, ubicacion, tipo de propiedad, tipo de habitacion y longitudes de texto del listing.
- **Mejor modelo:** logistic_base.
- **Metricas obtenidas:** accuracy=0.9734, precision=0.8614, recall=0.8441, F1=0.8526, ROC-AUC=0.9903.
- **Interpretacion de negocio:** el modelo permite priorizar revision operativa de listings con senales de baja confianza, especialmente cuando se combina con explicabilidad por coeficientes y segmentacion por mercado.
- **Limitaciones:** las metricas se calculan contra una etiqueta proxy. Para afirmar precision real o reduccion de disputas se requieren reservas, disputas, soporte y snapshots previos a la primera reserva.

## 3. Series de tiempo

- **Metrica pronosticada:** Cantidad mensual de reviews como proxy de demanda/actividad (`monthly_reviews`).
- **Periodo analizado:** 2010-06-01 a 2026-02-01.
- **Modelos comparados:** XGBoost, LightGBM, CatBoost.
- **Mejor modelo:** XGBoost por menor RMSE.
- **Metricas obtenidas:** MAE=38941.17, RMSE=44779.14, SMAPE=60.03%, R2=-0.3820.
- **Interpretacion de negocio:** el forecast ayuda a anticipar meses con mayor actividad observable, ajustar capacidad de soporte, preparar campanas de calidad y priorizar mercados antes de picos de demanda.
- **Limitaciones:** reviews no equivalen a reservas. Los ultimos meses pueden estar incompletos por fecha de corte de los datos y la serie agrega mercados heterogeneos.

## 4. Implementacion propuesta

- Integrar la probabilidad de `high_risk_listing` al dashboard como score predictivo complementario al `risk_score` explicable.
- Usar el forecast mensual para planificar capacidad operativa, soporte y campanas de mejora de calidad.
- Trust & Safety podria priorizar revision manual de listings de alto riesgo en meses o mercados con alta actividad prevista.
- Operaciones podria monitorear desviaciones entre actividad real y pronosticada para ajustar recursos.
- Producto y Compliance podrian usar las explicaciones del modelo para mejorar flujos de verificacion, contenido del anuncio y cumplimiento local.

## 5. Conclusion final alineada a CRISP-DM

La TB3 implementa dos casos practicos y ejecutables bajo CRISP-DM. La regresion logistica aborda la priorizacion de riesgo a nivel de listing y la serie de tiempo estima actividad mensual del marketplace. Ambos casos son utiles para decision empresarial, pero sus resultados deben presentarse como evidencia academica sobre datos publicos y no como medicion real de disputas internas de Airbnb.

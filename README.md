# airbnb-analytics

Proyecto académico para el curso **1ACC0243 - Análisis Empresarial y Data Science**.

Caso de estudio: **Airbnb**.

El proyecto conecta análisis estratégico, arquitectura de datos, iniciativas analíticas, visualización de datos e informes académicos.

## Tesis del proyecto

Airbnb debe evolucionar de un marketplace centrado en crecimiento y conversión hacia una plataforma analítica gobernada por confianza, donde Ciencia de Datos apoye calidad, control de riesgo, alineación con hosts, preparación regulatoria y mejores decisiones de negocio.

## Estructura esperada

```text
.
├── app/
├── configs/
├── data/
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── dashboards/
├── docs/
├── notebooks/
├── reports/
├── src/
├── tests/
├── README.md
└── CLAUDE.md
```

## Arquitectura de datos

El proyecto usa una arquitectura medallion:

```text
raw → bronze → silver → gold
```

La documentación estable está en:

```text
docs/architecture.md
```

## Gestión de tareas

Este repo usa Beads para seguimiento de trabajo:

```bash
bd prime
bd ready
bd show <id>
bd update <id> --claim
bd close <id>
```

No usar archivos `TODO.md` como fuente de verdad.

## Flujo de ramas

```text
feature/* → dev → main
```

- `main`: entregable estable.
- `dev`: rama de integración.
- `feature/*`: trabajo temporal y acotado.

## Reportes

Los informes académicos van en:

```text
reports/
```

Antes de cerrar una tarea de informe, compilar LaTeX y verificar que no falten imágenes.

Ejemplo:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error reports/tb2/main.tex
```

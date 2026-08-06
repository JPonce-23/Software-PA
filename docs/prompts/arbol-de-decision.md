# ÁRBOL DE DECISIÓN FINAL

```text
PROMPT 1
│
├── Propuesta viable
│   └── PROMPT 2
│
├── Bloqueo funcional
│   └── PROMPT 1B
│       └── decisiones del usuario
│           └── PROMPT 1B.2
│               └── PROMPT 2
│
├── Contradicción
│   └── PROMPT 1C
│       ├── resuelta → PROMPT 1
│       ├── funcional → PROMPT 1B
│       └── entorno → PROMPT 1D
│
└── Falta de entorno
    └── PROMPT 1D
        └── PROMPT 1

PROMPT 2
│
├── Implementación completa
│   └── PROMPT 3
│
├── Implementación parcial
│   └── PROMPT 2D
│       └── PROMPT 3
│
├── Propuesta no viable
│   └── PROMPT 2B
│       └── PROMPT 2
│
├── Bloqueo funcional
│   └── PROMPT 1B
│       └── PROMPT 1B.2
│           └── PROMPT 2
│
└── Falta de entorno
    └── PROMPT 2C
        └── PROMPT 2

PROMPT 3
│
├── Completa y validada
│   └── PROMPT 3F
│
├── Aprobada con riesgos menores
│   └── PROMPT 3F
│
├── Rechazada
│   └── PROMPT 3C
│       └── PROMPT 3
│
├── Incompleta
│   └── PROMPT 2D
│       └── PROMPT 3
│
├── Correcciones pendientes
│   └── PROMPT 3C
│       └── PROMPT 3
│
├── Falta de entorno
│   └── PROMPT 2C
│       └── PROMPT 3
│
└── Decisión funcional
    └── PROMPT 1B
        └── PROMPT 1B.2
            └── PROMPT 2
                └── PROMPT 3
```

# Plataforma de pagos instantáneos

## Visión general

El servicio de ingesta expone una API REST que recibe las órdenes de pago y
las publica en un topic de Kafka particionado por ordenante.

El motor de liquidación consume del topic, valida el saldo contra el core
bancario mediante una llamada síncrona y persiste el movimiento en PostgreSQL.

Un job de conciliación nocturno compara los movimientos persistidos con el
extracto del core y emite un informe de discrepancias.

## Decisiones

- Se eligió Kafka sobre una cola tradicional para poder reprocesar desde un
  offset en caso de incidente.
- La validación contra el core es síncrona por requisito regulatorio.

## Riesgos

- El core bancario es un punto único de fallo: si no responde, la liquidación
  se detiene por completo.
- La conciliación nocturna deja una ventana de hasta 24 horas para detectar
  discrepancias.

# Leather-Flex 3D · software (versión 0.1)

Convierte las fotos que toma el escáner en:

1. **Mapa de la piel** a escala real (une todas las fotos).
2. **Defectos** marcados: rayas, picaduras, manchas, arrugas y agujeros, con tipo, posición y tamaño en mm.
3. **Acomodo de moldes** (capelladas, billeteras, etc.) que esquiva los defectos.
4. **Plantilla de corte DXF** en milímetros + reporte JSON + imágenes.

## Instalación (una vez)

Necesitan Python 3.10 o más nuevo.

```
pip install -r requirements.txt
```

## Uso con la interfaz (recomendado)

```
streamlit run app.py
```

Se abre en el navegador. Para ver cómo funciona sin cuero ni celular, presionen **"Probar con un escaneo simulado"**.

## Paso a paso con el escáner real

**1. Calibración (una vez por escáner y celular)**
- Descarguen el tablero desde la app (o `tablero_calibracion_10mm.png`) e imprímanlo **al 100 %**, sin "ajustar a la página". Midan con regla que cada cuadro mida 10 mm.
- Pongan el tablero bajo el escáner y tomen una foto. Luego tomen una foto de una hoja blanca mate.
- Súbanlas en "1 · Calibración". La app muestra la escala (mm por píxel) y el giro de la cámara.

**2. Fotos de la piel**
- En el iPhone: Ajustes › Cámara › Formatos › **Más compatible** (así guarda JPG, no HEIC).
- Fijen el enfoque y la exposición (mantener el dedo sobre la pantalla hasta que diga *Bloqueo AE/AF*).
- Tomen las fotos posición por posición con la regla y la traba. Dos formas de indicar la posición:
  - **Renombrar** cada foto como su posición: `A1.jpg`, `A2.jpg`, `B1.jpg`… (columna = letra, fila = número), o
  - **Dejar los nombres del iPhone** y tomar siempre en el mismo orden: columna A de la fila 1 a la última, luego la columna B, etc. Indiquen en la app cuántas fotos hay por columna.
- El paso entre posiciones es 100 mm por defecto (el de la regla). Si cambian la regla, cámbienlo en Parámetros.

**3. Moldes**
- Un archivo DXF por molde, en **milímetros**, con el contorno cerrado (polilínea, o líneas y arcos que se unan).
- En `moldes_ejemplo/` hay ejemplos. Para cada molde se puede pedir una cantidad o dejar 0 para que llene la piel.
- Si el cuero tiene dirección (hilo), activen "Respetar el hilo del cuero" (solo giros de 0° y 180°).

**4. Resultado**
Descarguen `plantilla_corte.dxf` (capas PIEL, DEFECTOS, PIEZAS, TEXTOS), `reporte.json` y el mapa.

## Uso por consola

```
python -m leatherflex tablero tablero.png
python -m leatherflex calibrar tablero.jpg blanco.jpg calib.json
python -m leatherflex procesar fotos/ calib.json resultados/ --molde moldes_ejemplo/billetera.dxf:10 --molde capellada.dxf
python -m leatherflex simular prueba/          # escaneo sintético para probar
```

## Cómo funciona por dentro

| Etapa | Archivo | Qué hace |
|---|---|---|
| Calibración | `calibracion.py` | Escala y giro con el tablero de ajedrez; corrección de luz con la hoja blanca |
| Captura | `captura.py` | Lee las fotos, les asigna su posición y las lleva a 0,4 mm/px |
| Unión | `montaje.py` | Parte de la posición de la traba y la corrige midiendo el grano del cuero en cada traslape (correlación de fase + mínimos cuadrados) |
| Defectos | `defectos.py` | Separa la piel de la mesa; compara cada punto con el "cuero normal" de su alrededor a dos escalas (25 mm y 120 mm) |
| Acomodo | `acomodo.py` | Coloca moldes en una rejilla de 2 mm con margen de 5 mm a defectos y bordes; prueba dos estrategias y se queda con la mejor |
| Salidas | `exportar.py` | Imagen, DXF y JSON |

## Pruebas

```
python -m pytest -q tests
```

Las pruebas generan un escaneo sintético donde se conoce la verdad y comprueban la calibración, la unión de fotos, los defectos y que ninguna pieza toque un defecto. Resultados en 4 escaneos simulados (giros de −2° a +3°, traba con hasta ±2,5 mm de error, fotos con y sin nombre):

- Calibración: escala exacta (0,1000 mm/px) y giro recuperado.
- Unión de fotos: error máximo de 0,53 mm.
- Defectos: 6 de 6 encontrados en todos los casos, 0 falsas alarmas.
- Piezas: ninguna a menos de 6,6 mm de un defecto real.
- Tiempo: unos 2 segundos por piel simulada de 24 fotos.

## Lo que todavía no está probado (próximos pasos)

- **Fotos reales.** La simulación no tiene distorsión del lente, cuero ondulado, brillos ni sombras. La primera prueba real debe ser con una hoja cuadriculada de medidas conocidas, para medir el error de unión verdadero.
- **Ajuste de la sensibilidad** con cueros reales (liso, graso, con mucho grano). El parámetro *umbral_sigma* controla cuánto detecta.
- **Clasificación de defectos.** Hoy se clasifica por forma y color; con fotos reales etiquetadas se puede entrenar un modelo.
- **Acomodo.** Es un acomodo voraz sobre rejilla: rápido y correcto, pero no el óptimo. Se puede mejorar con más giros y búsqueda local.

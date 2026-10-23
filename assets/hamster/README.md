# Hámster · atlas de sprites

`atlas.png` es el atlas RGBA que usa la aplicación. Está organizado en 4 columnas
por 3 filas: reposo, habla, caricias, sueño; cuatro pasos; y cuatro poses de salto.
El cargador recorta transparencia y escala cada grupo una sola vez para evitar
cambios de tamaño entre fotogramas.

`atlas-generated.png` conserva la salida original del generador. El script
`scripts/prepare_pet_atlas.py hamster` elimina componentes aislados del borde y
reconstruye el atlas empaquetado (requiere Pillow solo para preparar el recurso;
la aplicación no importa Pillow).

Estilo: hámster sirio de aspecto natural, pelaje canela y crema, fondo transparente.
El personaje es curioso y amable; sus respuestas y frases pasivas se mantienen
separadas de las personalidades del gato y el golden.

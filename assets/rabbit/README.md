# Conejo · atlas de sprites

`atlas.png` es el atlas RGBA utilizado por la aplicación. `atlas-generated.png`
conserva la primera salida; `atlas-generated-v2.png` contiene la caminata y los
saltos revisados, y `seated-generated.png` contiene las cuatro poses superiores
con margen inferior suficiente para que no se corten las patas. Las columnas de
la primera fila son reposo, habla, caricias y sueño; la segunda tiene cuatro
pasos y la tercera cuatro fases de caída y salto.

El conejo de pelaje crema con manchas canela se generó en estilo de recorte
naturalista para combinar con las mascotas existentes. Para reconstruir el atlas:
`python scripts/prepare_pet_atlas.py rabbit --source-name atlas-generated-v2.png --seated-name seated-generated.png`.
Pillow solo se necesita para esa preparación; la aplicación usa Qt para cargar y
escalar el atlas.

Su personalidad es alegre, amable y curiosa. Tiene respuestas de prueba y frases
pasivas propias, y comparte el movimiento, las caricias, el micrófono y el menú.
Los efectos de pasos y cierre se conservan; los sonidos vocales siguen siendo
exclusivos del gato.

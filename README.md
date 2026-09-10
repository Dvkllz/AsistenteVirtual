# Asistente Virtual · v1.0

Mascota de escritorio en Python y PyQt6, inicialmente para Windows.
Se ubica abajo a la derecha, respeta el espacio de la barra de tareas y permanece
encima de otras ventanas. Arrastra el personaje para moverlo; la posición se
recuerda para el siguiente inicio. El menú de clic derecho permite volver a la
esquina, cambiar de modo y cerrar la mascota.

## Movimiento y tamaño

El gato es un 20 % más pequeño: pasa de 140 a 112 píxeles lógicos de alto.
Se ajusta a un máximo de 117 × 112 manteniendo la proporción. La ventana mide
268 × 332; el texto conserva su tamaño legible, no se reduce un 20 %.

- Arrastra y suelta el personaje: cae con gravedad y rebota suavemente.
- Suéltalo mientras lo mueves para lanzarlo; mantenerlo quieto antes de soltarlo
  elimina el impulso horizontal. Los rebotes pierden fuerza hasta quedar en reposo.
- Clic derecho → **Dar un salto** para hacerlo saltar.
- Clic derecho → **Pasear** para caminar por la parte inferior y girar en los
  bordes. Desmarca la opción para detenerlo. Escribir o arrastrarlo cancela el paseo.
- Clic derecho → **Física activada** permite desactivar/reactivar el movimiento.
  Esta preferencia se recuerda; el modo OpenAI sigue requiriendo activación explícita.
- Al escribir o abrir el menú, la mascota se queda quieta. Al salir del campo de
  texto puede volver a caer. Puedes desactivar la física para dejarla fija.

Los límites son los del área útil del monitor (sin invadir la barra de tareas).
Se mueve el conjunto de personaje y diálogo: no detecta superficies de otras
ventanas. Al soltarla queda dentro del monitor elegido al arrastrar. Si cambia la
pantalla o una posición guardada queda fuera, vuelve a una ubicación visible.
La física usa un temporizador solo durante el movimiento; en reposo se detiene.
Todo funciona en modo local sin solicitudes a OpenAI.

## Travesuras automáticas

Se activan por defecto y puedes pausarlas con clic derecho →
**Travesuras automáticas**. La preferencia se recuerda.

- Paseos de 5–10 segundos, con oportunidades de inicio cada 20–45 segundos.
  Alterna direcciones y rebota en los límites del monitor, sin robar el foco.
- Frases graciosas cada 45–90 segundos, elegidas de una lista local sin repetir
  la anterior. No consumen tokens, tampoco en modo OpenAI. Respetan al menos
  20 segundos de lectura de la última respuesta y no borran preguntas pendientes.
- Tras 10 segundos con el cursor quieto, intenta darle un zarpazo: se acerca con
  un pequeño salto, muestra la pata levantada y un destello de arañazo.
  Solo una vez por periodo de quietud; mover el ratón reinicia los 10 segundos
  y cancela el intento si ya había empezado. La posición se consulta cada 250 ms.
- El cursor debe estar fuera de la interfaz de la mascota y en su mismo monitor.
  El gato respeta el área útil, por lo que en los extremos solo puede acercarse.
  El zarpazo ahora empuja el cursor real una sola vez: 24 píxeles hacia el lado
  del golpe y 8 hacia arriba, sin salir del área útil. No hace clics ni lo bloquea.
  Cancela si mueves el cursor o mantienes pulsado un botón, también fuera de la app.
  Clic derecho → **Empujar cursor al dar zarpazo** permite desactivar solo ese
  empujón y conservar el efecto visual; la preferencia se recuerda.
  Su propio empujón no inicia otra persecución.

Se pausan al escribir, seleccionar una respuesta, abrir el menú, arrastrar el
gato o esperar una respuesta. Desactivar la física también desactiva los paseos
y zarpazos, pero permite las bromas. No se instalan capturadores del teclado ni
del ratón, no se guardan posiciones del cursor y no se envían a ningún servicio.

## Inicio rápido (sin gastar tokens)

Requiere Python 3.11 o posterior. Desde PowerShell en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Después de instalar, también puedes abrir **Iniciar mascota.bat** con doble clic.
No abre una consola persistente. Escribe una pregunta y pulsa Enter.
El modo predeterminado devuelve una respuesta fija de demostración, sin red,
sin clave y sin consumo de tokens. No es una respuesta de IA.

## Activar OpenAI de forma explícita

La aplicación busca `OPENAI_API_KEY` primero en las variables de entorno de
Windows y después en `.env.local`. Este archivo está ignorado por Git. No pegues
la clave en el código, en el chat ni en un archivo que Git pueda rastrear.

Si la clave está copiada en el portapapeles de Windows, puedes guardarla sin
mostrarla en la consola con:

```powershell
.\.venv\Scripts\python.exe scripts/save_clipboard_key.py
```

```powershell
.\.venv\Scripts\python.exe main.py --live
```

También puedes cambiar entre ambos modos desde el menú de clic derecho. El
indicador inferior mostrará **OPENAI · consume tokens**. La aplicación solo
envía una solicitud al pulsar Enter con texto. El modelo predeterminado es
`gpt-4.1-mini`; se puede cambiar con `OPENAI_MODEL`. El acceso al modelo y la
facturación dependen de tu cuenta de la API.

- Máximo 800 caracteres por pregunta y 120 tokens de salida por solicitud.
- Respuestas breves en español con sarcasmo amistoso.
- Sin historial: cada pregunta es independiente.
- Sin reintentos automáticos ni llamadas al iniciar.
- Solicitudes con `store=False`; la aplicación no guarda conversaciones.
- Tiempo de espera HTTP de 20 segundos y errores legibles sin mostrar secretos.

Las solicitudes corren en `QThread`. Se deshabilita la entrada mientras llega
la respuesta para evitar envíos duplicados; la mascota sigue siendo arrastrable.
Si cierras durante una solicitud, la ventana desaparece de inmediato y el proceso
termina cuando acaba la solicitud o su espera. Cerrar no garantiza cancelar una
solicitud ya recibida por OpenAI ni su posible coste.

## Gato siamés y estructura

La mascota es un siamés realista de complexión intermedia. Sus cuatro poses están
en `assets/siamese/`: `idle.png` (quieto), `talking.png` (mostrando una respuesta),
`falling.png` (sujetado o en el aire) y `walking.png` (paseando).
Son PNG con transparencia real, sin el fondo cuadriculado de los bocetos.
Se escalan una sola vez al iniciar y se reflejan al cambiar de dirección.
El estado de hablar dura unos segundos; no hay audio ni llamadas adicionales.

Caminar usa cuatro fotogramas en bucle (120 ms cada uno). Saltar muestra cuatro
poses según el impulso, ascenso, punto alto y descenso, también al perseguir el
cursor. Se reutilizan los temporizadores de movimiento: no sigue animando en
reposo ni carga imágenes en cada paso. El gato conserva su tamaño reducido.
Consulta [los fotogramas y prompts](assets/siamese/animation/ANIMATION.md).

Consulta [el diseño y sus prompts](assets/siamese/DESIGN.md) para ver su procedencia.
`assets/placeholder.png` se conserva únicamente como respaldo si faltan imágenes.

- `main.py`: inicio y selección explícita del modo API.
- `desktop_pet/window.py`: ventana, arrastre, menú y trabajo en segundo plano.
- `desktop_pet/physics.py`: gravedad, colisiones, fricción e impulso al soltar.
- `desktop_pet/sprites.py`: imágenes por estado, prioridad y orientación.
- `desktop_pet/autonomy.py`: paseos ocasionales, bromas locales y juego con el cursor.
- `desktop_pet/service.py`: conexión independiente de la interfaz y personalidad.
- `tests/`: comprobaciones locales de interfaz e integración simulada.

La lógica está separada de la interfaz para facilitar una futura adaptación a
otros sistemas. Esta entrega se verifica en Windows; no incluye instalador `.exe`,
voz, memoria ni inicio automático.

## Verificación sin API

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:QT_QPA_PLATFORM
```

Las pruebas sustituyen el cliente o el servicio: no hacen solicitudes reales.

Integración basada en la [documentación oficial de generación de texto](https://developers.openai.com/api/docs/guides/text)
y el [modelo GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

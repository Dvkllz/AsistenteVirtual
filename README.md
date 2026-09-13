# Asistente Virtual · v1.0

Mascota de escritorio en Python y PyQt6, inicialmente para Windows.
Se ubica abajo a la derecha, respeta el espacio de la barra de tareas y permanece
encima de otras ventanas. Haz clic y arrastra para moverlo; la posición se
recuerda para el siguiente inicio. El menú de clic derecho permite volver a la
esquina, cambiar de modo y cerrar la mascota.

## Movimiento y tamaño

El gato es un 20 % más pequeño: pasa de 140 a 112 píxeles lógicos de alto.
Las poses sentadas caben en 117 × 112; el paseo usa 152 × 112 para que el cuerpo
no se encoja al ajustar una pose horizontal con cola larga. Los cuatro pasos
comparten escala y línea del suelo, sin recortar patas ni cola. La ventana mide
268 × 332; el texto conserva su tamaño legible, no se reduce un 20 %.

- Haz clic y arrastra el personaje: al soltar cae y rebota suavemente.
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

## Caricias y ronroneo

Pasa el ratón de un lado a otro **sobre su cabeza, sin pulsar botones**.
Tras un movimiento de ida y vuelta, se queda quieto, cierra los ojos en una
pose relajada y emite un ronroneo suave. Pasar una sola vez, moverlo sobre el
cuerpo o dejarlo quieto no activa las caricias.
**Clic izquierdo y arrastrar** sigue sirviendo para agarrarlo y lanzarlo,
sin Mayús ni otras teclas. Agarrarlo interrumpe las caricias inmediatamente.

El gesto admite pequeñas curvas y funciona aunque el campo de preguntas conserve
el foco, sin borrarlo ni interrumpir la escritura.
El ronroneo se detiene al pulsar un botón, salir de la cabeza o pasar 650 ms sin mover
el ratón. También al cambiar de aplicación, abrir el menú o cerrar la mascota.
Mientras lo acaricias, se pausan la física y las travesuras, sin robar el foco.
Puedes silenciarlo con clic derecho → **Ronroneo al acariciar**; se recuerda
la preferencia y la pose sigue funcionando sin sonido. Ahora usa un ronroneo
real grabado, en bucle local y sin red. No consume tokens. Si no hay dispositivo de audio,
la interacción visual sigue disponible.

## Sonidos y diálogo temporal

Los efectos se incluyen en `assets/audio/`; no dependen de la
carpeta Escritorio para funcionar. Se reproducen localmente con Qt, sin API:

- `meow1.mp3`, `meow2.mp3`, `meow3.mp3`: los tres maullidos proporcionados. Suena
  solo uno al empezar cada diálogo, elegido al azar sin repetir el anterior.
  No hay bucle de voz ni sonido de final de diálogo. Los antiguos `speech.mp3`
  y `end.mp3` se retiraron del proyecto; sus originales externos no se modifican.
- `caminar1.mp3`: bucle mientras camina, incluido el paseo llevando el cursor.
  Se detiene al parar, saltar, agarrarlo, acariciarlo o abrir el menú.
- `explota.mp3`: una vez al cerrar. La ventana desaparece enseguida y el proceso
  deja terminar el sonido sin bloquear la interfaz. Si falla el audio, se cierra
  igualmente; hay un límite de seguridad de 10 segundos para la reproducción.

El globo aparece solo durante el diálogo (6–30 segundos según la longitud),
también para errores o avisos, y después queda invisible. Su espacio se reserva
para que el gato no salte de posición. El campo de preguntas y el indicador de
modo siguen disponibles. No hay globo ni sonido de bienvenida al iniciar.
La lectura se calcula como 3 segundos para advertir el mensaje más 0,4 segundos
por palabra: una respuesta de 45 palabras permanece 21 segundos.
Mientras espera la API, solo cambia el indicador inferior; el maullido suena
al llegar la respuesta, no también durante la espera.

Clic derecho → **Sonidos del gato** permite silenciar los maullidos y efectos;
se recuerda la preferencia. El ronroneo tiene su propio interruptor.
Interrumpir un diálogo con otro o cerrar detiene el maullido anterior.

## Siestas

Tras 30 segundos sin actividad de ratón ni teclado en la sesión de Windows,
el gato se acurruca en su sprite de dormir, muestra «Zzz» y duerme 5 segundos. Después despierta.
Puede volver a dormir tras otros 30 segundos; no entra en un ciclo inmediato.
Si vuelves a usar el ratón o teclado, lo agarras o abres su menú, despierta antes.
El ronroneo solo suena durante las caricias, no durante la siesta.

No interrumpe una respuesta pendiente, un diálogo, caricias, un arrastre ni un
salto. Detiene el paseo mientras duerme y conserva las preguntas escritas.
Usa `sleeping.png`, distinto de las caricias. Se consulta el tiempo desde la última entrada
cada medio segundo; no se capturan imágenes ni se registra lo que escribes.
En plataformas sin este detector de Windows, las siestas no se activan.

Los maullidos y `ronroneo.mp3` son los archivos proporcionados por el usuario.
Detalles y correspondencia de archivos en [audios locales](assets/audio/README.md).

## Travesuras automáticas

Se activan por defecto y puedes pausarlas con clic derecho →
**Travesuras automáticas**. La preferencia se recuerda.

- Paseos de 5–10 segundos, con oportunidades de inicio cada 20–45 segundos.
  Alterna direcciones y rebota en los límites del monitor, sin robar el foco.
- Frases graciosas cada 45–90 segundos, elegidas de una lista local sin repetir
  la anterior. No consumen tokens, tampoco en modo OpenAI. Respetan al menos
  20 segundos desde la última respuesta y todo su tiempo visible; no borran preguntas pendientes.
  Hay 28 frases, incluyendo bromas de escapar de la pantalla y conquistar el sofá.
- Tras 10 segundos con el cursor quieto, intenta darle un zarpazo: se acerca con
  un pequeño salto, muestra la pata levantada y un destello de arañazo.
  Solo una vez por periodo de quietud; mover el ratón reinicia los 10 segundos
  y cancela el intento si ya había empezado. La posición se consulta cada 250 ms.
- El cursor debe estar fuera de la interfaz de la mascota y en su mismo monitor.
  El gato respeta el área útil, por lo que en los extremos solo puede acercarse.
  Por defecto lo atrapa y lo lleva junto a la boca durante un paseo de hasta
  tres segundos y 120 píxeles. No hace clics ni bloquea el ratón.
  Se suelta antes del siguiente movimiento si mueves el ratón, pulsas un botón
  o presionas Escape. También al abrir el menú, cerrar la mascota o desactivar
  la física. Al soltarlo no devuelve el cursor a su posición anterior.
  Clic derecho → **Llevarse el cursor (3 segundos)** permite desactivar la captura.
  Si está desactivada, el zarpazo puede empujar el cursor una sola vez:
  24 píxeles hacia el lado del golpe y 8 hacia arriba, sin salir del área útil.
  Cancela si mueves el cursor o mantienes pulsado un botón, también fuera de la app.
  Clic derecho → **Empujar cursor al dar zarpazo** permite desactivar solo ese
  empujón y conservar el efecto visual; la preferencia se recuerda.
  Sus propios movimientos no inician otra persecución. Desactiva ambas opciones
  del cursor para conservar solamente la interacción visual.

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

## Hablarle por micrófono

1. Activa **Usar OpenAI** desde el menú de clic derecho.
2. Pulsa **🎙**: el indicador rojo y «GRABANDO» confirman la captura.
3. Habla y pulsa **■** para transcribir. Se detiene sola a los 15 segundos.
4. Revisa el dictado en el campo de texto y pulsa **Enter** para pedir la respuesta.

El botón avisa de que transcribir consume créditos. Cada dictado enviado hace
una transcripción con `gpt-4o-mini-transcribe`; Enter hace una consulta de texto
separada. No hay reintentos automáticos. El modo de prueba no abre el micrófono
ni llama a la API. No se sobrescriben borradores existentes.

**Escape**, cambiar de aplicación, abrir el menú, agarrar el gato o cerrar
cancelan una grabación todavía activa sin enviarla. Una solicitud ya enviada
puede finalizar y tener coste aunque cierres la mascota.
El audio se conserva solo en memoria y se descarta después; no hay escucha
permanente ni archivos de grabaciones. Las grabaciones vacías, muy cortas o
prácticamente silenciosas se rechazan localmente (no es un detector perfecto de voz).
El audio enviado se procesa en OpenAI según las condiciones de tu cuenta.

Durante la grabación y transcripción se pausan las travesuras y las siestas.
Si no funciona, revisa el micrófono predeterminado y los permisos para aplicaciones
de escritorio en la privacidad de Windows. Puedes seguir usando el teclado.
Las respuestas del gato siguen siendo texto y un maullido, no voz sintetizada.
Integración basada en la [documentación oficial de transcripción](https://developers.openai.com/api/docs/guides/speech-to-text)
y [GPT-4o mini Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe).

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
envía una solicitud de texto al pulsar Enter (el dictado usa otra de transcripción). El modelo predeterminado es
`gpt-4.1-mini`; se puede cambiar con `OPENAI_MODEL`. El acceso al modelo y la
facturación dependen de tu cuenta de la API.

- Máximo 800 caracteres por pregunta y 120 tokens de salida por solicitud.
- Respuestas breves en español, casi siempre sarcásticas; empatía sin sarcasmo ante temas sensibles.
- Sin historial: cada pregunta es independiente.
- Sin reintentos automáticos ni llamadas al iniciar.
- Solicitudes con `store=False`; la aplicación no guarda conversaciones.
- Tiempo de espera HTTP de 20 segundos y errores legibles sin mostrar secretos.

Las solicitudes corren en `QThread`. Se deshabilita la entrada mientras llega
la respuesta para evitar envíos duplicados; la mascota sigue siendo arrastrable.
Si cierras durante una solicitud, la ventana desaparece de inmediato y el proceso
termina cuando acaban tanto la solicitud (o su espera) como el sonido de cierre.
Cerrar no garantiza cancelar una
solicitud ya recibida por OpenAI ni su posible coste.

## Gato siamés y estructura

La mascota es un siamés realista de complexión intermedia. Sus seis estados están
en `assets/siamese/`: `idle.png` (quieto), `talking.png` (mostrando una respuesta),
`falling.png` (sujetado o en el aire), `walking.png` (paseando) y
`petting.png` (acariciado), además de `sleeping.png` (dormido).
Son PNG con transparencia real, sin el fondo cuadriculado de los bocetos.
Se escalan una sola vez al iniciar y se reflejan al cambiar de dirección.
El estado de hablar dura unos segundos y comienza con uno de los tres maullidos;
no sintetiza la respuesta como voz ni hace llamadas adicionales.

Caminar usa cuatro fotogramas en bucle (120 ms cada uno), con perfil, tamaño y
encuadre común para evitar cambios de escala entre pasos. Saltar muestra cuatro
poses según el impulso, ascenso, punto alto y descenso, también al perseguir el
cursor. Se reutilizan los temporizadores de movimiento: no sigue animando en
reposo ni carga imágenes en cada paso. El gato conserva su tamaño reducido.
Consulta [los fotogramas y prompts](assets/siamese/animation/ANIMATION.md).
La revisión de caminar y las caricias se documentan en
[poses, sonido y prompts](assets/siamese/PETTING.md). El salto no se modificó.

Consulta [el diseño y sus prompts](assets/siamese/DESIGN.md) para ver su procedencia.
La pose nueva y su prompt están en [dormir](assets/siamese/SLEEPING.md).
`assets/placeholder.png` se conserva únicamente como respaldo si faltan imágenes.

- `main.py`: inicio y selección explícita del modo API.
- `desktop_pet/window.py`: ventana, arrastre, menú y trabajo en segundo plano.
- `desktop_pet/physics.py`: gravedad, colisiones, fricción e impulso al soltar.
- `desktop_pet/sprites.py`: imágenes por estado, prioridad y orientación.
- `desktop_pet/autonomy.py`: paseos ocasionales, bromas locales y juego con el cursor.
- `desktop_pet/purring.py`: reproducción local del ronroneo, sin bloquear la interfaz.
- `desktop_pet/sounds.py`: efectos MP3, bucles y finalización del sonido al cerrar.
- `desktop_pet/napping.py`: detección de inactividad y siestas de cinco segundos.
- `desktop_pet/voice.py`: grabación voluntaria en memoria y transcripción limitada.
- `desktop_pet/service.py`: conexión independiente de la interfaz y personalidad.
- `tests/`: comprobaciones locales de interfaz e integración simulada.

La lógica está separada de la interfaz para facilitar una futura adaptación a
otros sistemas. Esta entrega se verifica en Windows; no incluye instalador `.exe`,
voz sintetizada, memoria ni inicio automático; sí admite dictado voluntario.

## Verificación sin API

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:QT_QPA_PLATFORM
```

Las pruebas sustituyen el cliente o el servicio: no hacen solicitudes reales.

Integración basada en la [documentación oficial de generación de texto](https://developers.openai.com/api/docs/guides/text)
y el [modelo GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

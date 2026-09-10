# Asistente Virtual · v1.0

Mascota de escritorio en Python y PyQt6, inicialmente para Windows.
Se ubica abajo a la derecha, respeta el espacio de la barra de tareas y permanece
encima de otras ventanas. Arrastra el personaje para moverlo; la posición se
recuerda para el siguiente inicio. El menú de clic derecho permite volver a la
esquina, cambiar de modo y cerrar la mascota.

## Movimiento y tamaño

La ventana ahora mide 268 × 360 píxeles lógicos (antes 320 × 440); el personaje
se ajusta a 146 × 140 manteniendo la proporción. El texto mantiene su tamaño legible.

- Arrastra y suelta el personaje: cae con gravedad y rebota suavemente.
- Suéltalo mientras lo mueves para lanzarlo; mantenerlo quieto antes de soltarlo
  elimina el impulso horizontal. Los rebotes pierden fuerza hasta quedar en reposo.
- Clic derecho → **Dar un salto** para hacerlo saltar.
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

## Imagen y estructura

Reemplaza `assets/placeholder.png` por otro PNG con transparencia y reinicia.
La imagen se ajusta manteniendo su proporción. El placeholder se generó localmente
con formas simples; se puede regenerar con:

```powershell
.\.venv\Scripts\python.exe scripts/create_placeholder.py
```

- `main.py`: inicio y selección explícita del modo API.
- `desktop_pet/window.py`: ventana, arrastre, menú y trabajo en segundo plano.
- `desktop_pet/physics.py`: gravedad, colisiones, fricción e impulso al soltar.
- `desktop_pet/service.py`: conexión independiente de la interfaz y personalidad.
- `tests/`: comprobaciones locales de interfaz e integración simulada.

La lógica está separada de la interfaz para facilitar una futura adaptación a
otros sistemas. Esta entrega se verifica en Windows; no incluye instalador `.exe`,
animación, voz, memoria ni inicio automático.

## Verificación sin API

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:QT_QPA_PLATFORM
```

Las pruebas sustituyen el cliente o el servicio: no hacen solicitudes reales.

Integración basada en la [documentación oficial de generación de texto](https://developers.openai.com/api/docs/guides/text)
y el [modelo GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

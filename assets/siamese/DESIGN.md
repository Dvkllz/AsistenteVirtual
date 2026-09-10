# Gato siamés aprobado

Diseño realista de complexión intermedia, ligeramente rellenito. Generado con la
herramienta integrada de imágenes; sin usar la clave API del proyecto. Eliminación
del fondo cuadriculado mediante procesamiento local, autorizada por el usuario.

## Archivos de producción

- `idle.png`: sentado y en reposo.
- `talking.png`: maullando mientras se muestra una respuesta (sin voz).
- `falling.png`: en el aire o sujetado con el ratón.
- `walking.png`: paseando por el borde inferior; se refleja al cambiar de dirección.

Los cuatro PNG son RGBA de 512 × 512, con transparencia real. Se cargan y escalan
una sola vez, a un máximo de 146 × 140 píxeles lógicos. Las poses son imágenes
estáticas por estado, no ciclos de animación cuadro a cuadro.

Prioridad: arrastre/caída, respuesta, paseo, reposo. Hablar dura entre 1,8 y 6,5
segundos según el texto. Pasear se activa mediante clic derecho → Pasear;
se cancela al escribir, arrastrar, saltar, desactivar la física o volver a la esquina.

La referencia elegida se conserva en `concepts/siamese-balanced.png`; su fondo
original no es transparente y no se carga en la aplicación. Las versiones
rechazadas se enviaron a la papelera y no se usan.

## Preparación local

`scripts/prepare_cat_sprite.py` elimina el fondo neutro conservando el color del
pelaje. Usa Pillow y NumPy, solo para preparar recursos: no son dependencias de
la mascota. El recorte se revisó sobre fondo claro y oscuro con
`scripts/preview_cat_sprites.py`. No es un eliminador de fondos genérico.

## Prompt de la referencia aprobada

Use case: precise-object-edit.
Edit target: the provided photorealistic sitting Siamese cat. The previous edit made the cat too fat. Reduce its belly, chest, flank and cheek volume by about HALF OF THE ADDED PLUMPNESS: aim for a normal well-fed real adult Siamese, only slightly rounded, not skinny and not fat.
Keep the same exact realistic photographic style, same face, natural blue eyes, cream short fur with seal-brown mask ears paws tail, same sitting position, view angle and lighting. Its chest should be slimmer, waist gently defined, torso moderately narrow with just a small soft belly. Do not shorten legs or enlarge head. No cartoon or human characteristics.
Full cat in frame with safe margins. Isolated cutout with genuine transparent alpha background. No patterns behind it, no scenery, no props or text.

## Prompt: talking

Use case: precise-object-edit. Asset type: single desktop pet sprite.
Reference: the approved INTERMEDIATE-WEIGHT realistic Siamese cat shown last. Keep this exact real feline identity and realistic photographic style: only mildly rounded torso, not fat or barrel-shaped, natural adult head and almond blue eyes, seal-brown face mask ears paws and tail, short cream fur. Keep the exact intermediate body condition of the reference, do not increase or reduce its weight. No human expressions or cartoon features.
Full single cat visible with safe margins, square canvas. Same neutral soft lighting. Transparent background with actual alpha; if not possible use plain pure white, absolutely NO checkerboard pattern. No ground shadow, props or text.
Change ONLY pose:
Sitting naturally in the same three-quarter view facing right, both front paws on the ground, mouth slightly open in a natural meow. Same torso outline as the approved reference. No human smile or raised paw.

## Prompt: falling

Use case: precise-object-edit. Asset type: single desktop pet sprite.
Reference: the approved INTERMEDIATE-WEIGHT realistic Siamese cat shown last. Keep this exact real feline identity and realistic photographic style: only mildly rounded torso, not fat or barrel-shaped, natural adult head and almond blue eyes, seal-brown face mask ears paws and tail, short cream fur. Keep the exact intermediate body condition of the reference, do not increase or reduce its weight. No human expressions or cartoon features.
Full single cat visible with safe margins, square canvas. Same neutral soft lighting. Transparent background with actual alpha; if not possible use plain pure white, absolutely NO checkerboard pattern. No ground shadow, props or text.
Change ONLY pose:
Midair descending from a little jump, body horizontal, all four legs stretched down preparing to land, head upright facing right, tail gently back for balance. Real cat landing posture. Belly just slightly soft, not large, no cartoon fear or injury.

## Prompt: walking

Use case: precise-object-edit. Asset type: single desktop pet sprite.
Reference: the approved INTERMEDIATE-WEIGHT realistic Siamese cat shown last. Keep this exact real feline identity and realistic photographic style: only mildly rounded torso, not fat or barrel-shaped, natural adult head and almond blue eyes, seal-brown face mask ears paws and tail, short cream fur. Keep the exact intermediate body condition of the reference, do not increase or reduce its weight. No human expressions or cartoon features.
Full single cat visible with safe margins, square canvas. Same neutral soft lighting. Transparent background with actual alpha; if not possible use plain pure white, absolutely NO checkerboard pattern. No ground shadow, props or text.
Change ONLY pose:
Walking naturally to the RIGHT on all fours, side view with head slightly toward viewer, one front paw lifted and diagonally opposite hind leg stepping. Tail gently curved upward, small soft belly, no exaggerated bulge. Real quadrupedal feline anatomy.

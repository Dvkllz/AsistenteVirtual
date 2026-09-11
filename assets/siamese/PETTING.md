# Caricias y revisión del paseo

Generación con la herramienta integrada de imágenes de Codex, no con la API del proyecto.
Fecha: 2026-09-11. Referencia: siamés realista aprobado, complexión intermedia.

## Archivos finales

- `petting.png`: pose relajada con ojos cerrados (512 × 512 RGBA).
- `walking.png`, `animation/walking_1.png`, `animation/walking_2.png`, `animation/walking_3.png`: atlas nuevo dividido con un único encuadre y escala comunes.
- `../audio/purr.wav`: ronroneo sintético original, mono PCM 16-bit, 22050 Hz, 2 segundos en bucle; creado por `scripts/create_purr.py`, sin descargar audio.
- Las imágenes de salto, reposo y conversación se conservan sin cambios.

Limpieza local del fondo autorizada previamente: `scripts/prepare_cat_sprite.py` y `scripts/prepare_walk_atlas.py`. No se redimensiona cada paso por separado. Los originales generados se conservan en la carpeta de imágenes de Codex.

## Prompts utilizados

### petting

Use case: precise-object-edit. Asset type: ONE desktop pet sprite.
Reference is the approved photorealistic Siamese cat. Preserve its exact seal-point cream/chocolate coat, realistic adult proportions, modestly rounded body, natural facial anatomy and short fur. Same camera, lighting, entire cat including ears and tail.
Change pose only: the cat is enjoying gentle head strokes, sitting compactly with eyes softly CLOSED, ears relaxed to the sides (not flattened), chin tilted a little upward into an invisible hand, neck leaning subtly forward, body relaxed. Mouth CLOSED, natural contented expression, not a human smile, no human hands or people, no hearts or effects. Slightly tuck front paws together. No cartoon, oversized eyes or anthropomorphism.
One centered full-body cat, square canvas, clean genuine transparent background with alpha. No checkerboard, no ground shadow, text or props.

### walk_sheet

Use case: precise-object-edit. Asset type: ONE production sprite atlas, a 2 by 2 grid containing FOUR frames of a realistic cat walk cycle.
Use reference only for the identity of the exact Siamese cat: cream short fur, dark chocolate seal points, blue eyes, natural adult anatomy, mildly rounded but not fat. Photorealistic, no cartoon.
Every frame MUST have identical camera in PURE SIDE PROFILE facing RIGHT (not 3/4), identical body scale, identical head shape and same head/hip/shoulder locations. Same low horizontal tail position with tip gently upward, not large curled tail. Torso horizontal, head calm, near ear and eye visible in profile. All paws grounded on exactly the same invisible baseline where in contact. No jumping or running.
Four equal square cells in a 2x2 atlas. Center one complete cat inside each cell with generous clear margins. No outlines, dividing lines, labels or text. Transparent background with genuine alpha; do not draw checkerboards. No floor/shadow.
Frame order reading order:
TOP LEFT, contact A: NEAR front leg extends forward, NEAR hind leg extends backward; FAR front leg extends backward and FAR hind leg forward.
TOP RIGHT, passing A: NEAR front paw is grounded vertically under shoulder, NEAR hind leg swings forward bent beneath belly; FAR front paw lifts bent moving forward, FAR hind paw supports under hip.
BOTTOM LEFT, contact B: exact opposite of A, NEAR front leg extends backward, NEAR hind leg extends forward; FAR front leg extends forward, FAR hind leg backward.
BOTTOM RIGHT, passing B: NEAR front leg bends and lifts forward, NEAR hind paw supports under hip; FAR front paw supports under shoulder, FAR hind leg lifts and swings forward.
CRITICAL: FOUR clearly DIFFERENT limb arrangements, anatomically natural four-legged walk. Do not duplicate near-leg poses between contact A and B. Four legs only per cat. Stable head/torso positioning across frames so this loops without resizing or wobbling. Entire tails and paws stay inside each cell.

### Corrección del atlas seleccionado

Use case: precise-object-edit. Edit this exact 2x2 Siamese cat walking sprite atlas. Keep the TOP ROW unchanged and preserve the exact HEAD, NECK, TORSO, TAIL, scale and positions in all FOUR cells. Change ONLY the legs of the BOTTOM TWO cats to create the opposite half of the walk. BOTTOM LEFT: the visible NEAR front leg (attached to visible right shoulder) must angle BACKWARD to the LEFT under the belly with paw on the ground behind the shoulder; FAR front leg angles FORWARD to the RIGHT with paw grounded in front of shoulder. Visible NEAR hind leg must angle FORWARD to the RIGHT under the belly, FAR hind leg extends BACKWARD LEFT. BOTTOM RIGHT: near front leg grounded straight under the shoulder, far front leg bends backward in recovery; near hind leg supports straight under hip, far hind leg swings forward bent. Four anatomically correct legs, clear occlusion so near limbs cover far limbs. Absolutely do NOT repeat top-row limb poses in bottom row. All heads/backs/hips stay locked to original frame coordinates. No human limbs or extra paws. Keep same photorealistic seal-point Siamese short fur. Full cat tails and paws inside equal square cells. Output single four-cell 2x2 atlas with genuine transparent background alpha, no checkerboard, no floor, no shadow or text.

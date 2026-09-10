# Animaciones del siamés

Seis fotogramas nuevos creados con la herramienta integrada de imágenes, usando
el gato aprobado como referencia. Preparados localmente con transparencia real,
sin cambiar el tamaño de visualización (112 px de alto). No se usó la clave API
del proyecto para generar ni probar las animaciones.

## Archivos y reproducción

- Caminar: `../walking.png`, `walking_1.png`, `walking_2.png`, `walking_3.png`.
  Ciclo de cuatro pasos, 120 ms por fotograma, reflejado para ir a la izquierda.
- Saltar: `jumping_0.png` (impulso), `jumping_1.png` (ascenso),
  `jumping_2.png` (recoger patas), `../falling.png` (descenso).
  La física determina la fase; el salto al cursor usa el progreso de su movimiento.
- El reposo y el diálogo mantienen sus imágenes anteriores. No hay temporizador
  de animación permanente: se aprovechan los del movimiento, parándose en reposo.

Todos los fotogramas se cargan, escalan y reflejan una sola vez al iniciar.
`scripts/preview_cat_animation.py` produce una hoja y un GIF de revisión en
`artifacts/`. La limpieza de fondos usa el procedimiento local ya autorizado.

## Interacción con el cursor

La captura está activada por defecto: al alcanzar el cursor quieto, lo lleva
junto a la boca hasta tres segundos, caminando como máximo 120 píxeles. Reutiliza
los fotogramas de caminar. Comprueba la posición, los botones y Escape antes de
cada movimiento; se suelta sin recolocarlo si el usuario vuelve a usar el ratón.
No bloquea ni oculta el cursor. Tiene un interruptor propio:
Llevarse el cursor (3 segundos).

Cuando la captura está desactivada, al alcanzar el cursor quieto,
un zarpazo puede moverlo 24 px horizontalmente y 8 px hacia arriba, limitado al
área útil del monitor. No hace clics, no bloquea el cursor y no encadena empujones
por su propio movimiento. Comprueba otra vez la posición y los botones justo
antes del contacto. Si el usuario lo mueve o mantiene un botón pulsado, cancela.
Se puede desactivar con clic derecho → Empujar cursor al dar zarpazo.
Las pruebas simulan el movimiento, sin mover el cursor real del usuario.

## Prompts finales

### walking_1.png

Use case: precise-object-edit. Asset: ONE animation frame of this exact desktop pet.
Reference: the realistic seal-point Siamese cat provided. Preserve its exact face, blue eyes, cream short coat, brown points, modestly rounded intermediate body weight, real feline anatomy, realistic photographic texture. Do not make it fat, skinny, cartoon, anthropomorphic, or change identity. Keep camera angle fixed: full side view facing RIGHT, head slightly toward viewer. Keep head/torso size and location consistent with reference: same body proportions, tail to the left, entire cat within a square canvas and safe margins.
Background: genuine transparent alpha, no checkerboard or floor, no cast shadow, no text or props. Only change limb positions and pose for the requested animation phase. One cat only, not a sheet.
Pose: Walking passing phase: near foreleg bent and passing directly under the chest, far foreleg supporting forward, near hind leg passing under hip, far hind leg supporting behind. Tail remains curved upward. Torso level, realistic slow feline gait.

### walking_2.png

Use case: precise-object-edit. Asset: ONE animation frame of this exact desktop pet.
Reference: the realistic seal-point Siamese cat provided. Preserve its exact face, blue eyes, cream short coat, brown points, modestly rounded intermediate body weight, real feline anatomy, realistic photographic texture. Do not make it fat, skinny, cartoon, anthropomorphic, or change identity. Keep camera angle fixed: full side view facing RIGHT, head slightly toward viewer. Keep head/torso size and location consistent with reference: same body proportions, tail to the left, entire cat within a square canvas and safe margins.
Background: genuine transparent alpha, no checkerboard or floor, no cast shadow, no text or props. Only change limb positions and pose for the requested animation phase. One cat only, not a sheet.
Pose: Walking opposite-contact phase, OPPOSITE legs to reference: near foreleg reaches BACKWARD supporting weight, far foreleg reaches FORWARD; near hind leg reaches FORWARD, far hind leg extends BACKWARD. Four distinct legs, no extra limbs. Torso level and same tail curve.

### walking_3.png

Use case: precise-object-edit. Asset: ONE animation frame of this exact desktop pet.
Reference: the realistic seal-point Siamese cat provided. Preserve its exact face, blue eyes, cream short coat, brown points, modestly rounded intermediate body weight, real feline anatomy, realistic photographic texture. Do not make it fat, skinny, cartoon, anthropomorphic, or change identity. Keep camera angle fixed: full side view facing RIGHT, head slightly toward viewer. Keep head/torso size and location consistent with reference: same body proportions, tail to the left, entire cat within a square canvas and safe margins.
Background: genuine transparent alpha, no checkerboard or floor, no cast shadow, no text or props. Only change limb positions and pose for the requested animation phase. One cat only, not a sheet.
Pose: Walking second passing phase: near foreleg planted vertically under shoulder, far foreleg bent and advancing, near hind leg vertical supporting hip, far hind leg lifted and passing forward. This must differ clearly from reference and make a natural four-step walk loop. Same tail curve.

### jumping_0.png

Use case: precise-object-edit. Asset: ONE animation frame of this exact desktop pet.
Reference: the realistic seal-point Siamese cat provided. Preserve its exact face, blue eyes, cream short coat, brown points, modestly rounded intermediate body weight, real feline anatomy, realistic photographic texture. Do not make it fat, skinny, cartoon, anthropomorphic, or change identity. Keep camera angle fixed: full side view facing RIGHT, head slightly toward viewer. Keep head/torso size and location consistent with reference: same body proportions, tail to the left, entire cat within a square canvas and safe margins.
Background: genuine transparent alpha, no checkerboard or floor, no cast shadow, no text or props. Only change limb positions and pose for the requested animation phase. One cat only, not a sheet.
Pose: Jump launch: cat crouches low on all four legs with compressed hindquarters, front paws close under shoulders, hind legs deeply bent ready to spring, spine gently rounded, head looking right. Tail balances behind.

### jumping_1.png

Use case: precise-object-edit. Asset: ONE animation frame of this exact desktop pet.
Reference: the realistic seal-point Siamese cat provided. Preserve its exact face, blue eyes, cream short coat, brown points, modestly rounded intermediate body weight, real feline anatomy, realistic photographic texture. Do not make it fat, skinny, cartoon, anthropomorphic, or change identity. Keep camera angle fixed: full side view facing RIGHT, head slightly toward viewer. Keep head/torso size and location consistent with reference: same body proportions, tail to the left, entire cat within a square canvas and safe margins.
Background: genuine transparent alpha, no checkerboard or floor, no cast shadow, no text or props. Only change limb positions and pose for the requested animation phase. One cat only, not a sheet.
Pose: Jump rising: airborne upward leap, hind legs extend backward after takeoff, forepaws bend lightly forward near chest, torso angled slightly upward 15 degrees, tail extends behind. Natural real cat, full body.

### jumping_2.png

Use case: precise-object-edit. Asset: ONE animation frame of this exact desktop pet.
Reference: the realistic seal-point Siamese cat provided. Preserve its exact face, blue eyes, cream short coat, brown points, modestly rounded intermediate body weight, real feline anatomy, realistic photographic texture. Do not make it fat, skinny, cartoon, anthropomorphic, or change identity. Keep camera angle fixed: full side view facing RIGHT, head slightly toward viewer. Keep head/torso size and location consistent with reference: same body proportions, tail to the left, entire cat within a square canvas and safe margins.
Background: genuine transparent alpha, no checkerboard or floor, no cast shadow, no text or props. Only change limb positions and pose for the requested animation phase. One cat only, not a sheet.
Pose: Jump apex: airborne compact tuck, all four paws gently drawn toward the belly, horizontal torso and tail balancing backward, head looking right, preparing to extend paws for descent. Natural cat aerial posture.

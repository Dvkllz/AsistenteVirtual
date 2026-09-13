# Pose de dormir

Sprite final: `assets/siamese/sleeping.png` (512 × 512, RGBA).
Se genera con la herramienta integrada de imágenes, usando `idle.png` como
referencia de identidad. No utiliza la clave API del proyecto.
Se conserva el siamés realista, sin rasgos antropomórficos, en una pose acurrucada
con ojos cerrados. El recorte usa el proceso local ya autorizado:
`scripts/prepare_cat_sprite.py`; no modifica las otras poses.
Se muestra en el marco base de 117 × 112, sin el aumento aplicado al paseo:
el cuerpo acurrucado ya llena su encuadre. Conserva el mismo suelo y una
superficie visible similar a la pose sentada; no crece al dormirse.

## Prompt final

Use case: photorealistic-natural. Asset type: transparent desktop pet sleeping sprite. The reference image is the identity/style reference: create the SAME realistic adult seal-point Siamese cat, moderately rounded build, short cream fur, dark chocolate face, ears, paws and tail. New pose ONLY: sleeping peacefully curled on its side, eyes fully closed, chin resting on front paws, hindquarters curled with tail wrapping the body. Natural feline anatomy, realistic fur and gentle studio lighting, not furry anthropomorphic, not cartoon, not obese. Entire body including ears paws tail within frame, side/three-quarter view, horizontal compact silhouette with head toward viewer's right. Center on a square canvas with 5 percent empty margin. Genuinely transparent RGBA background, no shadow outside cat, no floor, no checkerboard, no text, no Zzz, no accessories, no other objects. Preserve the reference cat's identity and proportions.

## Origen

Original conservado en la carpeta de imágenes de Codex:
`exec-ee86cd71-a2e5-40c2-9a18-a8aa97d1312e.png`.
El proyecto utiliza únicamente la copia preparada dentro de `assets/siamese/`.

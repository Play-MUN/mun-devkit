# Contribuir

[English](CONTRIBUTING.md) · **Español**

MUN™ Devkit está en una fase temprana: compila, comprueba, empaqueta y
simula un juego para una consola todavía en desarrollo, y nada de él se ha
ejecutado en el hardware de esa consola. Las contribuciones son
bienvenidas: correcciones, pruebas, documentación, ejemplos, adaptadores
de motores. Lee primero el [README](README.es.md); dice qué existe y qué
no.

Quien participa sigue el [código de conducta](CODE_OF_CONDUCT.es.md).

## Formas de ayudar

No toda la ayuda es código. Cada una de estas pasa por un issue o por un
pull request contra `dev`, como describe el resto de esta página:

- **Pruébalo en tu ordenador.** Sigue el README desde `./mdk doctor` hasta
  una partida guardada en Linux x86-64, en un Mac con procesador Intel, o
  en una distribución de Linux que no sea Ubuntu. Cuenta lo que pasó con la plantilla de fallo; un informe de que
  funciona vale tanto como uno de que no.
- **Lleva un juego a una tarjeta.** Pasa un juego SDL2 u OpenGL que puedas
  redistribuir por `mdk new`, `build`, `check`, `pack` y `sim`, y convierte
  en una corrección cada paso que tuviste que adivinar.
- **Errores e instrucciones poco claras.** Un paso que no hace lo que dice
  la página es un fallo de la documentación: abre un issue, o un pull
  request que corrija la página, en inglés y, cuando la tenga, en su
  traducción.
- **Traducciones.** Las páginas en español se mantienen contra sus
  originales en inglés ([más abajo](#documentación-y-traducciones)). Un
  idioma nuevo empieza como propuesta en un issue.
- **Un motor.** Un adaptador o una receta para un motor que pueda producir
  un juego para Linux ARM64: proponlo primero en un issue, con lo que el
  motor necesita de una sesión.

Las preguntas van en un issue o en el canal de desarrolladores del
[Discord de MUN](https://discord.gg/UxgExjjhxH). Las decisiones quedan en los issues, para que quien
llegue después pueda encontrarlas.

## Tu primera contribución

El resto de esta página dice con qué debe llegar un cambio en el cliente o
en un contrato. Una primera contribución necesita mucho menos:

1. Elige un issue con la etiqueta
   [good first issue](https://github.com/Play-MUN/mun-devkit/labels/good%20first%20issue),
   o arregla algo pequeño con lo que te hayas topado: una errata, un paso
   que no estaba claro, un mensaje de error que no ayudaba.
2. Haz un fork del repositorio, crea una rama desde `dev`, haz el cambio y
   ejecuta `make check`.
3. Haz el commit con `git commit -s`. El `-s` añade una línea que dice que
   el cambio es tuyo para darlo ([más abajo](#derechos-y-firma)); no hay
   más que eso.
4. Abre un pull request contra `dev` y di qué ejecutaste.

Si el cambio necesita una prueba y no sabes bien cómo escribirla, o toca
una página que tiene traducción y no escribes español, dilo en el pull
request: el mantenedor añade lo que falte o te enseña cómo. Nadie espera
que te sepas esta página de memoria la primera vez.

## Quién decide

MUN Devkit lo fundó y lo mantiene Iván Moreno Mendoza (Play MUN). El
mantenedor revisa los pull requests y decide qué entra en `dev` y, desde
ahí, en `main`. Es una sola persona y responde cuando puede. Un fork puede,
por supuesto, seguir su propio camino
([NAME-AND-LOGO.txt](NAME-AND-LOGO.txt) dice cómo puede llamarse).

## Antes de empezar

- **Correcciones pequeñas y documentación**: abre un pull request
  directamente.
- **Cualquier cosa mayor** (una orden nueva, una dependencia nueva, un
  motor, un cambio que un juego pueda notar): abre primero un issue y
  describe el problema y la propuesta, para discutirla antes de que le
  dediques tiempo.
- **Un cambio en `client/` o en `contracts/` llega a todos los juegos.** Se
  acuerda en un issue antes de escribirlo, y dice con qué se encuentra un
  juego hecho contra el contrato anterior. El formato de la tarjeta, su
  validador y las reglas de guardado son de MUN OS: un cambio en ellos va
  [allí](https://github.com/Play-MUN/mun-os).
- Los problemas de seguridad van en privado al mantenedor, no a un issue
  ([seguridad](SECURITY.es.md)).

## Preparación y comprobaciones

*Qué necesitas*, en el README, enumera los requisitos. Después:

```sh
./mdk doctor        # qué tiene este ordenador y qué le falta
./mdk os fetch      # las herramientas de MUN OS en la revisión fijada
make check          # las pruebas que este ordenador puede ejecutar; nombra las que omitió
```

`make check` necesita Python 3.9 o posterior y Make; un compilador de C
añade las pruebas del cliente. Las pruebas que compilan o ejecutan un
programa de consola necesitan un motor de contenedores y algo más:

```sh
./mdk env build             # el entorno de compilación (necesita la red una vez)
make sample                 # el ejemplo nativo, compilado y empaquetado
engines/godot/fetch.sh      # el motor fijado, para las pruebas del adaptador
make dev-tools              # los analizadores fijados, en .local/venv
make check-full             # todas las pruebas; la que no puede ejecutarse falla
make analyse                # pyflakes y bandit
```

Los pull requests ejecutan `make check` en Linux y macOS y
`make check-full` en Linux ARM64. Di en el pull request qué comprobaciones
ejecutaste y cuáles no pudiste: una prueba omitida no es una prueba
superada.

## Cambios

- Un cambio, un propósito.
- **Una corrección o un comportamiento nuevo llega con una prueba que falla
  antes y pasa después.** Dilo en el pull request.
- **Las pruebas esperan a lo que ocurrió, no al tiempo.** Ningún sleep, y
  ningún plazo que decida un resultado: espera al estado (hay una partida
  en la tarjeta, un proceso ha terminado). `tests/test_no_clock.py` lo
  comprueba.
- **Un aviso de un analizador se corrige, o se revisa en su propia línea**:
  la regla y el motivo, `# nosec B603: no shell; ...`. Nunca para un
  fichero o una regla enteros. `tests/test_static.py` ata cada marca a un
  aviso.
- Trata cada fichero que leen las herramientas como entrada no fiable:
  límites antes de usarlo, y un error con un código, qué está mal y qué
  hacer.
- `mdk` usa solo la biblioteca estándar de Python. Una dependencia nueva se
  propone en un issue.
- El cliente C no crea hilos, no guarda estado global y solo reserva la
  sesión; `client/c/mun.h` enuncia cada contrato. Respétalos, o cámbialos
  allí donde están escritos.
- El código que se compila para una consola va endurecido
  (`mk/hardening.mk`), y `tests/test_hardening.py` lo lee del programa
  compilado.
- Un fichero nuevo nombra su licencia en sus primeras líneas
  ([licencias](docs/licensing.md)); `tests/test_licensing.py` lo comprueba.
- Explica en comentarios las razones que no son obvias; no repitas el
  código.
- Di qué clase de evidencia tiene una afirmación: el simulador, una consola
  virtual o el hardware de una consola.

## Documentación y traducciones

La documentación se escribe en inglés, la referencia técnica. Algunas
páginas tienen además una traducción al español: `NAME.es.md` junto a
`NAME.md`, cada par enlazado en los dos sentidos por una línea English /
Español. `docs/translations.json` enumera cada traducción con el SHA-256
del texto inglés contra el que se revisó por última vez.

Cuando cambies una página que tiene traducción, actualiza la traducción en
el mismo cambio si puedes, o di en el pull request que la necesita.
`make check` falla hasta que la traducción se haya revisado contra el nuevo
texto inglés y su `source_sha256` tenga el valor que imprime la
comprobación; ponlo solo después de leer las dos. Las órdenes, opciones,
rutas, nombres de fichero, campos y códigos de error se quedan como están
en una traducción, y la salida de una herramienta se cita en el idioma en
que la herramienta la imprime. Si la traducción y el original difieren,
vale el inglés.

Los issues y los pull requests son bienvenidos en inglés o en español.

## Ramas, commits y pull requests

1. Una rama de vida corta desde `dev`: `feat/…`, `fix/…`, `docs/…`,
   `chore/…`. Haz un fork del repositorio salvo que tengas permiso de
   escritura.
2. Un pull request contra `dev` (GitHub propone `main`: cambia la base),
   con su plantilla rellena y sus comprobaciones en verde, revisado por el
   mantenedor. Los pull requests a `dev` se fusionan con squash.
3. `main` recibe `dev` mediante un pull request, fusionado con un commit de
   merge, cuando lo que hay en `dev` está listo para que se cuente con
   ello.

- Usa [Conventional Commits](https://www.conventionalcommits.org/) y tu
  propio nombre y correo en Git: tu contribución sigue siendo tuya.
- Firma cada commit (`git commit -s`, más abajo).
- Revisa `git diff --cached` antes de hacer el commit, y no reescribas
  historia que otros ya tienen.

## Derechos y firma

El devkit tiene tres licencias, según dónde acaba cada parte
([licencias](docs/licensing.md)), y una contribución queda bajo la licencia
de la parte a la que va: como establece la sección 5 de la Apache License,
lo que envías intencionadamente para su inclusión queda bajo esos términos,
sin condiciones adicionales, salvo que digas explícitamente otra cosa. Tu
contribución sigue siendo tuya; la licencias, no la transfieres.

La línea `Signed-off-by:` que añade `git commit -s` certifica el
[Developer Certificate of Origin 1.1](https://developercertificate.org/):
que escribiste el cambio o que tienes derecho a enviarlo bajo esa licencia.
Envía solo lo que puedas licenciar así. El código, las tipografías, las
imágenes o los sonidos que vengan de otra parte conservan sus propios
términos: di de dónde vienen y bajo qué licencia, para que
[lo que usa el devkit](docs/third-party.md) pueda enumerarlos. Los nombres
y logotipos de MUN y Play MUN no se licencian.

## Qué queda fuera de Git

Todo lo generado vive en `.local/` y en los directorios `build/`, que Git
ignora: la copia de MUN OS, el motor, las compilaciones, las imágenes de
tarjeta. Este repositorio no lleva ningún juego de terceros ni ningún
motor: nunca hagas commit de datos de un juego que no tengas derecho a
distribuir, de los binarios o el código de un motor, de credenciales ni de
configuración personal de herramientas; esta última guárdala en
`.git/info/exclude` o en tu fichero global de exclusiones, no en
`.gitignore`.

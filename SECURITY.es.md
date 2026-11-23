# Seguridad

[English](SECURITY.md) · **Español**

MUN™ Devkit está en una fase temprana: herramientas, un cliente y ejemplos
para una consola todavía en desarrollo, sin ninguna versión publicada
propia. Lee ficheros que no ha escrito y pone código dentro de los juegos
de otras personas, así que tiene fronteras que deben sostenerse, y los
avisos sobre ellas son bienvenidos.

## Avisar de una vulnerabilidad

Avisa en privado, no en un issue público:

- en GitHub, **Security → Report a vulnerability** en este repositorio, o
- por correo a **hello@playmun.com**, con «security» en el asunto.

Di a qué afecta (el commit, y lo que imprime `./mdk doctor`), cómo
reproducirlo y qué permite hacer. Una sola persona mantiene el devkit:
espera una respuesta en unos días, no en horas, y que después se te
mantenga informado. La corrección entra en `dev`, después en `main`, y se
publica como aviso de seguridad de este repositorio. Dale ese tiempo antes
de contárselo a nadie más, y di si quieres que se te reconozca.

## Qué cubre

Lo que el devkit promete proteger:

- **Los ficheros como entrada no fiable.** Lo que leen `mdk check`,
  `mdk pack` y `mdk sim`: el programa que un proyecto nombra como su
  ejecutable de entrada (`tools/mdk/mdk/elf.py`), `mun-project.toml`, un
  directorio de contenido, una partida guardada, la salida de una
  compilación. Un fichero que haga que una herramienta falle, se quede
  colgada, escriba fuera del proyecto o ejecute algo es un hallazgo.
- **El cliente dentro de un juego** (`client/c`,
  `engines/godot/addons/mun`): la partida guardada y las respuestas de la
  consola que lee, y la memoria que toca. Un juego compila este código
  dentro de sí, así que un fallo aquí es un fallo en todos los juegos.
- **Lo que el devkit descarga y da por bueno**: la revisión fijada de
  MUN OS (`mun-os.lock.json`, `mdk os fetch`), la imagen base y la
  instantánea de paquetes del entorno de compilación
  (`tools/env/Dockerfile`), el motor fijado (`engines/godot/fetch.sh`) y los
  analizadores (`tools/dev-requirements.txt`). Una forma de hacer que
  cualquiera de ellos acepte algo distinto de lo fijado es un hallazgo.
- **La palabra de las comprobaciones.** Un programa que `mdk check` da por
  endurecido, o por apto para su perfil de ejecución, y no lo es.

## Qué no cubre

- **El simulador de sesión no es un sandbox.** `mdk sim` ejecuta el juego
  con los permisos del propio desarrollador, a propósito: reproduce los
  contratos de una sesión, no el confinamiento de la consola.
- **La compilación propia de un proyecto.** `mdk build` ejecuta la orden de
  compilación que el proyecto nombra, dentro del entorno de compilación. Lo
  que esa orden haga allí es cosa del proyecto, como con cualquier árbol de
  código que decides compilar; la seguridad del motor de contenedores y la
  del ordenador anfitrión son suyas.
- **MUN OS**: el formato de la tarjeta y su validador, el servicio de
  tarjetas, el lanzador y el sandbox del juego. Su propia
  [página de seguridad](https://github.com/Play-MUN/mun-os/blob/main/SECURITY.es.md)
  dice cómo avisar de eso.
- **Un juego hecho con el devkit**: sus fallos le corresponden a su autor.

## Versiones con soporte

Solo `main` y `dev`. Todavía no hay ninguna versión publicada; cuando la
haya, solo la última recibirá correcciones.

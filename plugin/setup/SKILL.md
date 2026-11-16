---
name: diavlo-mind-setup
description: "Configura y comprueba DIAVLO MIND en la app de Claude: que el plugin y la skill estén activos, que la ejecución de código esté encendida y que funcione con una prueba real. Úsala cuando alguien pida instalar, configurar o dejar listo DIAVLO MIND, diga que no aparece o no funciona, pregunte cómo usarlo, o acabe de subir el plugin."
---

# Configurar DIAVLO MIND

Haz los pasos en orden. Dile a la persona qué tocar en la pantalla y espera su respuesta antes de seguir. No hace falta ninguna contraseña, clave de API ni dato personal: si alguien te los ofrece, no los guardes ni los uses.

## 1. ¿Está cargado?

Pide que escriba `/` en el cuadro de mensaje. Deben salir `diavlo-mind` y `diavlo-mind-setup`; el menú indica de qué plugin viene cada una.

Si no salen:
- Abre Customize > Plugins (en claude.ai o en la app de escritorio) y busca DIAVLO MIND.
- Si no está, sube el archivo `diavlo-mind-plugin.zip` con Add > Upload plugin.
- Si está pero apagado, enciende el interruptor de Disable plugin.

## 2. ¿Puede ejecutar código?

Sin esto las skills no funcionan. En Ajustes > Capacidades, «Ejecución de código y creación de archivos» (en la versión nueva del menú, «Create and edit files») debe estar activada.

## 3. Prueba real

Pide una tarea de varios pasos, por ejemplo: «Planifica en tres pasos cómo ordenar una carpeta de fotos, con criterios para saber si está terminada y cómo lo comprobarías».

La respuesta debe:
- elegir un modo (FAST, STANDARD, DEEP o AUTONOMOUS) según el tamaño de la tarea;
- dar pasos comprobables;
- terminar con un informe que separe lo verificado de lo que no se pudo verificar.

Si no lo hace, pide: «usa la skill diavlo-mind». Si aun así no aparece, vuelve al paso 1.

## 4. Uso diario

- En tareas de varios pasos, la skill se carga sola.
- Para elegirla a mano: escribe `/`, selecciona diavlo-mind en el menú y luego escribe la tarea.
- En Claude Code con la misma cuenta, el plugin se sincroniza al empezar sesión; en una sesión ya abierta, escribe `/reload-plugins`.

## 5. Actualizar

Abre el plugin, pulsa su menú y elige Remove. Luego sube el zip nuevo y comprueba que la versión que aparece es la nueva.

## Si algo falla

Di qué ves en pantalla (el mensaje exacto, qué menú está abierto) y qué pasos ya hiciste. No inventes ajustes que no ves: si no encuentras un menú, dilo.

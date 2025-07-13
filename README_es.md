# 🔥 MediaCrawler - Rastreador de Plataformas de Redes Sociales 🕷️

<div align="center">

<a href="https://trendshift.io/repositories/8291" target="_blank">
  <img src="https://trendshift.io/api/badge/repositories/8291" alt="NanmiCoder%2FMediaCrawler | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
</a>

[![GitHub Stars](https://img.shields.io/github/stars/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/pulls)
[![License](https://img.shields.io/github/license/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE)
[![中文](https://img.shields.io/badge/🇨🇳_中文-Available-blue)](README.md)
[![English](https://img.shields.io/badge/🇺🇸_English-Available-green)](README_en.md)
[![Español](https://img.shields.io/badge/🇪🇸_Español-Current-green)](README_es.md)

</div>

> **Descargo de responsabilidad:**
> 
> Por favor, utilice este repositorio únicamente con fines de aprendizaje ⚠️⚠️⚠️⚠️, [Casos ilegales de web scraping](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)  <br>
>
>Todo el contenido de este repositorio es únicamente para fines de aprendizaje y referencia, y está prohibido el uso comercial. Ninguna persona u organización puede usar el contenido de este repositorio para propósitos ilegales o infringir los derechos e intereses legítimos de otros. La tecnología de web scraping involucrada en este repositorio es solo para aprendizaje e investigación, y no puede ser utilizada para rastreo a gran escala de otras plataformas u otras actividades ilegales. Este repositorio no asume ninguna responsabilidad legal por cualquier responsabilidad legal que surja del uso del contenido de este repositorio. Al usar el contenido de este repositorio, usted acepta todos los términos y condiciones de este descargo de responsabilidad.
>
> Haga clic para ver un descargo de responsabilidad más detallado. [Haga clic para saltar](#disclaimer)

## 📖 Introducción del Proyecto

Una poderosa **herramienta de recolección de datos de redes sociales multiplataforma** que soporta el rastreo de información pública de plataformas principales incluyendo Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, Zhihu, y más.

### 🔧 Principios Técnicos

- **Tecnología Central**: Basado en el framework de automatización de navegador [Playwright](https://playwright.dev/) para login y mantenimiento del estado de login
- **No Requiere Ingeniería Inversa de JS**: Utiliza el entorno de contexto del navegador con estado de login preservado para obtener parámetros de firma a través de expresiones JS
- **Ventajas**: No necesita hacer ingeniería inversa de algoritmos de encriptación complejos, reduciendo significativamente la barrera técnica

## ✨ Características
| Plataforma | Búsqueda por Palabras Clave | Rastreo de ID de Publicación Específica | Comentarios Secundarios | Página de Inicio de Creador Específico | Caché de Estado de Login | Pool de Proxy IP | Generar Nube de Palabras de Comentarios | Análisis Inteligente de URL | Entrada Interactiva |
| ------ | ---------- | -------------- | -------- | -------------- | ---------- | -------- | -------------- | ------------ | ---------- |
| Xiaohongshu | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |
| Douyin   | ✅          | 🔥**Mejorado**  | ✅        | 🔥**Mejorado**  | ✅          | ✅        | ✅              | 🔥**Nueva Función** | 🔥**Nueva Función** |
| Kuaishou   | ✅          | 🔥**Mejorado**  | ✅        | 🔥**Mejorado**  | ✅          | ✅        | ✅              | 🔥**Nueva Función** | 🔥**Nueva Función** |
| Bilibili   | ✅          | 🔥**Mejorado**  | ✅        | 🔥**Mejorado**  | ✅          | ✅        | ✅              | 🔥**Nueva Función** | 🔥**Nueva Función** |
| Weibo   | ✅          | 🔥**Mejorado**  | ✅        | 🔥**Mejorado**  | ✅          | ✅        | ✅              | 🔥**Nueva Función** | 🔥**Nueva Función** |
| Tieba   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |
| Zhihu   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |

### 🔥 Destacados de Funciones Mejoradas

#### 🎯 Entrada Interactiva Unificada
- **Detección Inteligente de Entrada**: Habilita automáticamente el modo de entrada interactiva cuando los archivos de configuración están vacíos
- **Mensajes Formateados**: Proporciona ejemplos detallados de formato de entrada e instrucciones
- **Soporte de Formato Mixto**: Soporta entrada simultánea de múltiples formatos (URLs, enlaces cortos, IDs)

#### 🔗 Motor de Análisis Inteligente de URL
- **Redirección de Enlaces Cortos**: Analiza inteligentemente enlaces cortos compartidos y automáticamente redirige para obtener URLs reales
- **Compatibilidad Multi-formato**: Soporta URLs completas, enlaces cortos, IDs directos y otros formatos de entrada
- **Mecanismo de Validación**: Validación de ID incorporada para prevenir errores de entrada inválida

#### 📱 Interfaz de Línea de Comandos Unificada
**Nuevo formato de comando unificado**:
```bash
# Uso unificado del parámetro --urls, soporta todas las plataformas
uv run main.py --platform [dy|ks|wb|bili] --lt qrcode --type [search|detail|creator] --urls "URL1" "URL2" "URL3"
```

### 🔥 Funciones Mejoradas de Douyin

| Formato de Entrada | Ejemplo | Método de Análisis |
|---------|------|----------|
| URL Completa de Página de Usuario | `https://www.douyin.com/user/MS4wLjABAAAA...` | Extraer sec_user_id directamente |
| URL Completa de Video | `https://www.douyin.com/video/7525082444551310602` | Extraer video_id directamente |
| Enlace Corto Compartido | `https://v.douyin.com/J7v_LxD7vUQ/` | Análisis de redirección inteligente |
| ID Directo | `MS4wLjABAAAA...` o `7525082444551310602` | Usar directamente |

### 🔥 Funciones Mejoradas de Kuaishou

| Formato de Entrada | Ejemplo | Método de Análisis |
|---------|------|----------|
| URL Completa de Video | `https://www.kuaishou.com/short-video/3xf8enb8dbj6uig` | Extraer video_id directamente |
| URL Completa de Página de Usuario | `https://www.kuaishou.com/profile/3xi4kwp2pg8tp8k` | Extraer user_id directamente |
| Enlace Corto Compartido | `https://v.kuaishou.com/2F50ZXj` | Análisis de redirección inteligente |
| ID Directo | `3xf8enb8dbj6uig` o `3xi4kwp2pg8tp8k` | Usar directamente |

### 🔥 Funciones Mejoradas de Bilibili

| Formato de Entrada | Ejemplo | Método de Análisis |
|---------|------|----------|
| URL Completa de Video | `https://www.bilibili.com/video/BV1Q2MXzgEgW` | Extraer BVID/AID directamente |
| URL Completa de Espacio de Usuario | `https://space.bilibili.com/449342345` | Extraer UID directamente |
| Enlace Corto Compartido | `https://b23.tv/B6gPE4M` | Análisis de redirección inteligente |
| ID Directo | `BV1Q2MXzgEgW` o `449342345` | Usar directamente |

### 🔥 Funciones Mejoradas de Weibo

| Formato de Entrada | Ejemplo | Método de Análisis |
|---------|------|----------|
| Enlace Compartido de Escritorio | `https://weibo.com/7643904561/5182160183232445` | Extraer post_id directamente |
| URL Móvil | `https://m.weibo.cn/detail/5182160183232445` | Extraer post_id directamente |
| URL de Página de Usuario | `https://weibo.com/u/5533390220` | Extraer user_id directamente |
| ID Directo | `5182160183232445` o `5533390220` | Usar directamente |


<details id="pro-version">
<summary>🔗 <strong>🚀 ¡Lanzamiento Mayor de MediaCrawlerPro! ¡Más características, mejor diseño arquitectónico!</strong></summary>

### 🚀 ¡Lanzamiento Mayor de MediaCrawlerPro!

> Enfócate en aprender el diseño arquitectónico de proyectos maduros, no solo tecnología de rastreo. ¡La filosofía de diseño de código de la versión Pro también vale la pena estudiar en profundidad!

[MediaCrawlerPro](https://github.com/MediaCrawlerPro) ventajas principales sobre la versión de código abierto:

#### 🎯 Actualizaciones de Características Principales
- ✅ **Funcionalidad de reanudación de rastreo** (Característica clave)
- ✅ **Soporte de múltiples cuentas + pool de proxy IP** (Característica clave)
- ✅ **Eliminar dependencia de Playwright**, más fácil de usar
- ✅ **Soporte completo de entorno Linux**

#### 🏗️ Optimización de Diseño Arquitectónico
- ✅ **Optimización de refactorización de código**, más legible y mantenible (lógica de firma JS desacoplada)
- ✅ **Calidad de código de nivel empresarial**, adecuado para construir proyectos de rastreo a gran escala
- ✅ **Diseño arquitectónico perfecto**, alta escalabilidad, mayor valor de aprendizaje del código fuente

#### 🎁 Características Adicionales
- ✅ **Aplicación de escritorio descargadora de videos de redes sociales** (adecuada para aprender desarrollo full-stack)
- ✅ **Recomendaciones de feed de página de inicio multiplataforma** (HomeFeed)
- [ ] **Agente AI basado en plataformas de redes sociales está en desarrollo 🚀🚀**

Haga clic para ver: [Página de Inicio del Proyecto MediaCrawlerPro](https://github.com/MediaCrawlerPro) para más información
</details>

## 🚀 Inicio Rápido

> 💡 **¡El código abierto no es fácil, si este proyecto te ayuda, por favor da una ⭐ Estrella para apoyar!**

## 📋 Prerrequisitos

### 🚀 Instalación de uv (Recomendado)

Antes de proceder con los siguientes pasos, por favor asegúrese de que uv esté instalado en su computadora:

- **Guía de Instalación**: [Guía Oficial de Instalación de uv](https://docs.astral.sh/uv/getting-started/installation)
- **Verificar Instalación**: Ingrese el comando `uv --version` en la terminal. Si el número de versión se muestra normalmente, la instalación fue exitosa
- **Razón de Recomendación**: uv es actualmente la herramienta de gestión de paquetes Python más poderosa, con velocidad rápida y resolución de dependencias precisa

### 🟢 Instalación de Node.js

El proyecto depende de Node.js, por favor descargue e instale desde el sitio web oficial:

- **Enlace de Descarga**: https://nodejs.org/en/download/
- **Requisito de Versión**: >= 16.0.0

### 📦 Instalación de Paquetes Python

```shell
# Entrar al directorio del proyecto
cd MediaCrawler

# Usar el comando uv sync para asegurar la consistencia de la versión de python y paquetes de dependencias relacionados
uv sync
```

### 🌐 Instalación de Controlador de Navegador

```shell
# Instalar controlador de navegador
uv run playwright install
```

> **💡 Consejo**: MediaCrawler ahora soporta usar playwright para conectarse a su navegador Chrome local, resolviendo algunos problemas causados por Webdriver.
>
> Actualmente, `xhs` y `dy` están disponibles usando el modo CDP para conectarse a navegadores locales. Si es necesario, verifique los elementos de configuración en `config/base_config.py`.

## 🚀 Ejecutar Programa Rastreador

### Uso Básico

```shell
# El proyecto no habilita el modo de rastreo de comentarios por defecto. Si necesita comentarios, por favor modifique la variable ENABLE_GET_COMMENTS en config/base_config.py
# Otras opciones soportadas también pueden verse en config/base_config.py con comentarios en chino

# Rastreo de búsqueda por palabra clave
uv run main.py --platform xhs --lt qrcode --type search

# Rastreo de ID de publicación especificada
uv run main.py --platform xhs --lt qrcode --type detail

# Rastreo de página de inicio de creador
uv run main.py --platform xhs --lt qrcode --type creator

# Para ejemplos de uso de rastreador de otras plataformas, ejecute el siguiente comando para ver
uv run main.py --help
```

### 🔥 Función de Análisis Inteligente de URL Unificada

**No necesita extraer IDs manualmente, soporta pegar directamente enlaces compartidos, operación unificada para todas las plataformas**:

#### Modo de Entrada Interactiva (Recomendado)
```shell
# Plataforma Douyin - Entra automáticamente a entrada interactiva después de limpiar archivo de configuración
uv run main.py --platform dy --lt qrcode --type creator
uv run main.py --platform dy --lt qrcode --type detail

# Plataforma Kuaishou - Soporta análisis inteligente de enlaces cortos
uv run main.py --platform ks --lt qrcode --type creator
uv run main.py --platform ks --lt qrcode --type detail

# Plataforma Bilibili - Soporta análisis de enlaces cortos b23.tv
uv run main.py --platform bili --lt qrcode --type creator
uv run main.py --platform bili --lt qrcode --type detail

# Plataforma Weibo - Soporta múltiples formatos de URL
uv run main.py --platform wb --lt qrcode --type creator
uv run main.py --platform wb --lt qrcode --type detail
```

#### Entrada Directa por Línea de Comandos
```shell
# Uso unificado del parámetro --urls, soporta todas las plataformas
uv run main.py --platform dy --lt qrcode --type creator --urls "https://v.douyin.com/J7v_LxD7vUQ/"
uv run main.py --platform ks --lt qrcode --type detail --urls "https://v.kuaishou.com/2F50ZXj"
uv run main.py --platform bili --lt qrcode --type detail --urls "https://b23.tv/B6gPE4M"
uv run main.py --platform wb --lt qrcode --type creator --urls "https://weibo.com/u/5533390220"

# Rastreo en lote de múltiples objetivos
uv run main.py --platform dy --lt qrcode --type detail --urls "URL1" "URL2" "URL3"
```

**Ejemplos de Formatos de Entrada Soportados**:
- **Douyin**: `https://v.douyin.com/J7v_LxD7vUQ/`, `https://www.douyin.com/video/7525082444551310602`
- **Kuaishou**: `https://v.kuaishou.com/2F50ZXj`, `https://www.kuaishou.com/short-video/3xf8enb8dbj6uig`
- **Bilibili**: `https://b23.tv/B6gPE4M`, `https://www.bilibili.com/video/BV1Q2MXzgEgW`
- **Weibo**: URLs de escritorio, móvil o IDs directos

<details>
<summary>🔗 <strong>Usando gestión de entorno venv nativo de Python (No recomendado)</strong></summary>

#### Crear y activar entorno virtual de Python

> Si rastrea Douyin y Zhihu, necesita instalar el entorno nodejs con anticipación, versión mayor o igual a: `16`

```shell
# Entrar al directorio raíz del proyecto
cd MediaCrawler

# Crear entorno virtual
# Mi versión de python es: 3.9.6, las librerías en requirements.txt están basadas en esta versión
# Si usa otras versiones de python, las librerías en requirements.txt pueden no ser compatibles, por favor resuelva por su cuenta
python -m venv venv

# macOS & Linux activar entorno virtual
source venv/bin/activate

# Windows activar entorno virtual
venv\Scripts\activate
```

#### Instalar librerías de dependencias

```shell
pip install -r requirements.txt
```

#### Instalar controlador de navegador playwright

```shell
playwright install
```

#### Ejecutar programa rastreador (entorno nativo)

```shell
# El proyecto no habilita el modo de rastreo de comentarios por defecto. Si necesita comentarios, por favor modifique la variable ENABLE_GET_COMMENTS en config/base_config.py
# Otras opciones soportadas también pueden verse en config/base_config.py con comentarios en chino

# Leer palabras clave del archivo de configuración para buscar publicaciones relacionadas y rastrear información de publicaciones y comentarios
python main.py --platform xhs --lt qrcode --type search

# Leer lista de ID de publicaciones específicas del archivo de configuración para obtener información e información de comentarios de publicaciones específicas
python main.py --platform xhs --lt qrcode --type detail

# Abrir la APP correspondiente para escanear código QR para login

# Para ejemplos de uso de rastreador de otras plataformas, ejecute el siguiente comando para ver
python main.py --help
```

</details>


## 💾 Almacenamiento de Datos

Soporta múltiples métodos de almacenamiento de datos:

- **Base de Datos MySQL**: Soporta guardar en base de datos relacional MySQL (necesita crear base de datos con anticipación)
  - Ejecute `python db.py` para inicializar la estructura de tablas de la base de datos (solo ejecutar en la primera ejecución)
- **Archivos CSV**: Soporta guardar en CSV (bajo el directorio `data/`)
- **Archivos JSON**: Soporta guardar en JSON (bajo el directorio `data/`)

---

[🚀 ¡Lanzamiento Mayor de MediaCrawlerPro 🚀! ¡Más características, mejor diseño arquitectónico!](https://github.com/MediaCrawlerPro)

## 🤝 Comunidad y Soporte

### 💬 Grupos de Discusión
- **Grupo de Discusión WeChat**: [Haga clic para unirse](https://nanmicoder.github.io/MediaCrawler/%E5%BE%AE%E4%BF%A1%E4%BA%A4%E6%B5%81%E7%BE%A4.html)

### 📚 Documentación y Tutoriales
- **Documentación en Línea**: [Documentación Completa de MediaCrawler](https://nanmicoder.github.io/MediaCrawler/)
- **Tutorial de Rastreador**: [Tutorial Gratuito CrawlerTutorial](https://github.com/NanmiCoder/CrawlerTutorial)


# Otras preguntas comunes pueden verse en la documentación en línea
>
> La documentación en línea incluye métodos de uso, preguntas comunes, unirse a grupos de discusión del proyecto, etc.
> [Documentación en Línea de MediaCrawler](https://nanmicoder.github.io/MediaCrawler/)
>

# Servicios de Conocimiento del Autor
> Si quiere comenzar rápidamente y aprender el uso de este proyecto, diseño arquitectónico del código fuente, aprender tecnología de programación, o quiere entender el diseño del código fuente de MediaCrawlerPro, puede revisar mi columna de conocimiento pagado.

[Introducción de la Columna de Conocimiento Pagado del Autor](https://nanmicoder.github.io/MediaCrawler/%E7%9F%A5%E8%AF%86%E4%BB%98%E8%B4%B9%E4%BB%8B%E7%BB%8D.html)


---

## ⭐ Gráfico de Tendencia de Estrellas

¡Si este proyecto te ayuda, por favor da una ⭐ Estrella para apoyar y que más personas vean MediaCrawler!

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)

### 💰 Exhibición de Patrocinadores

<a href="https://www.swiftproxy.net/?ref=nanmi">
<img src="docs/static/images/img_5.png">
<br>
**Swiftproxy** - ¡90M+ IPs residenciales puras de alta calidad globales, regístrese para obtener 500MB de tráfico de prueba gratuito, el tráfico dinámico nunca expira!
> Código de descuento exclusivo: **GHB5** ¡Obtenga 10% de descuento instantáneamente!
</a>

<br><br>

<a href="https://sider.ai/ad-land-redirect?source=github&p1=mi&p2=kk">**Sider** - ¡El plugin de ChatGPT más popular en la web, experiencia increíble!</a>

### 🤝 Conviértase en Patrocinador

¡Conviértase en patrocinador y muestre su producto aquí, obteniendo exposición masiva diariamente!

**Información de Contacto**:
- WeChat: `yzglan`
- Email: `relakkes@gmail.com`


## 📚 Referencias

- **Cliente Xiaohongshu**: [Repositorio xhs de ReaJason](https://github.com/ReaJason/xhs)
- **Reenvío de SMS**: [Repositorio de referencia SmsForwarder](https://github.com/pppscn/SmsForwarder)
- **Herramienta de Penetración de Intranet**: [Documentación oficial de ngrok](https://ngrok.com/docs/)


# Descargo de Responsabilidad
<div id="disclaimer">

## 1. Propósito y Naturaleza del Proyecto
Este proyecto (en adelante denominado "este proyecto") fue creado como una herramienta de investigación técnica y aprendizaje, con el objetivo de explorar y aprender tecnologías de recolección de datos de red. Este proyecto se enfoca en la investigación de tecnologías de rastreo de datos para plataformas de redes sociales, destinado a proporcionar a estudiantes e investigadores propósitos de intercambio técnico.

## 2. Declaración de Cumplimiento Legal
El desarrollador del proyecto (en adelante denominado "desarrollador") recuerda solemnemente a los usuarios que cumplan estrictamente con las leyes y regulaciones relevantes de la República Popular China al descargar, instalar y usar este proyecto, incluyendo pero no limitado a la "Ley de Ciberseguridad de la República Popular China", "Ley de Contraespionaje de la República Popular China" y todas las leyes y políticas nacionales aplicables. Los usuarios deberán asumir todas las responsabilidades legales que puedan surgir del uso de este proyecto.

## 3. Restricciones de Propósito de Uso
Este proyecto está estrictamente prohibido de ser utilizado para cualquier propósito ilegal o actividades comerciales que no sean de aprendizaje o investigación. Este proyecto no puede ser utilizado para ninguna forma de intrusión ilegal en sistemas informáticos de otras personas, ni puede ser utilizado para cualquier actividad que infrinja los derechos de propiedad intelectual de otros u otros derechos e intereses legítimos. Los usuarios deben asegurar que su uso de este proyecto sea puramente para aprendizaje personal e investigación técnica, y no puede ser utilizado para ninguna forma de actividades ilegales.

## 4. Descargo de Responsabilidad
El desarrollador ha hecho todos los esfuerzos para asegurar la legitimidad y seguridad de este proyecto, pero no asume responsabilidad por ninguna forma de pérdidas directas o indirectas que puedan surgir del uso de este proyecto por parte de los usuarios. Incluyendo pero no limitado a cualquier pérdida de datos, daño de equipos, litigios legales, etc. causados por el uso de este proyecto.

## 5. Declaración de Propiedad Intelectual
Los derechos de propiedad intelectual de este proyecto pertenecen al desarrollador. Este proyecto está protegido por la ley de derechos de autor y tratados internacionales de derechos de autor, así como otras leyes y tratados de propiedad intelectual. Los usuarios pueden descargar y usar este proyecto bajo la premisa de cumplir con esta declaración y las leyes y regulaciones relevantes.

## 6. Derechos de Interpretación Final
El desarrollador tiene los derechos de interpretación final con respecto a este proyecto. El desarrollador se reserva el derecho de cambiar o actualizar este descargo de responsabilidad en cualquier momento sin previo aviso.
</div>


## 🙏 Agradecimientos

### Soporte de Licencia de Código Abierto de JetBrains

¡Gracias a JetBrains por proporcionar soporte de licencia de código abierto gratuito para este proyecto!

<a href="https://www.jetbrains.com/?from=MediaCrawler">
    <img src="https://www.jetbrains.com/company/brand/img/jetbrains_logo.png" width="100" alt="JetBrains" />
</a>

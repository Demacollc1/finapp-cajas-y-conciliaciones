# Manual de Operación y Documentación Técnica
## Sistema de Control de Caja, Valijas y Custodia (FinancePro)

Este documento detalla el funcionamiento lógico, técnico y operativo de la aplicación de **Control de Caja & Valijas**. La solución está diseñada para operar como una aplicación de una sola página (SPA) responsiva que agiliza el flujo financiero desde el conteo físico en el local hasta la confirmación de depósito en el banco y envío de cheques posfechados a la matriz.

---

## 1. Arquitectura y Dependencias

La aplicación se ha desarrollado bajo un enfoque ágil y portable utilizando tecnologías estándar del ecosistema web que garantizan una carga ultra rápida sin necesidad de compilación en el servidor:

* **HTML5 & CSS3:** Maquetación semántica y estructura robusta.
* **Tailwind CSS (CDN):** Framework de utilidades CSS de alto rendimiento para garantizar un diseño premium y adaptativo (móvil y escritorio).
* **JavaScript Vanilla (ES6):** Manejo de estados de la aplicación, interactividad de vistas y persistencia en memoria local.
* **Librerías Externas Integradas (CDNs Autorizados):**
    * **jsPDF (v2.5.1):** Motor de generación de documentos en PDF en el cliente para la creación inmediata de los manifiestos de valija y papeletas de depósito bancarias.
    * **QRCodeJS (v1.0.0):** Generador dinámico de códigos QR para la autenticación y traspaso de custodia al mensajero sin contacto.

---

## 2. Flujo de Trabajo Operativo (Paso a Paso)

El sistema automatiza un ciclo de control cerrado estructurado en 6 etapas secuenciales:
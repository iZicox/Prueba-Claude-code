# Calculadora web

Calculadora sencilla en HTML, CSS y JavaScript puro. No necesita dependencias ni build.

## Uso

Abre `index.html` en el navegador, o sirve la carpeta con cualquier servidor estático:

```bash
npm start        # http://localhost:8000
```

### Teclado

| Tecla | Acción |
| --- | --- |
| `0`–`9` | Introducir dígitos |
| `+` `-` `*` `/` | Operaciones |
| `Enter` o `=` | Calcular |
| `.` o `,` | Decimal |
| `%` | Porcentaje |
| `Backspace` | Borrar último dígito |
| `Escape` o `Delete` | Limpiar (AC) |

## Estructura

- `calculator.js`: lógica pura (estado, operaciones, formato). No toca el DOM.
- `app.js`: conecta la lógica con los botones y el teclado.
- `index.html` / `styles.css`: interfaz. Modo claro y oscuro según el sistema.
- `calculator.test.js`: pruebas de la lógica.

## Pruebas

```bash
npm test
```

Usa el runner integrado de Node (`node --test`), así que requiere Node 18 o superior.

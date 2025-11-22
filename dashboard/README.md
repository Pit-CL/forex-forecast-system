# USD/CLP Forecast Dashboard

Dashboard web interactivo para visualizar pronósticos de tipo de cambio USD/CLP con análisis avanzado y múltiples horizontes de predicción.

## Características Implementadas - FASE 1 MVP

### ✅ Componentes Principales

#### 1. Tab "Overview"
- **Pronóstico Principal 7 Días**
  - Tasa actual vs predicción
  - Cambio porcentual con indicadores visuales (↑/↓)
  - Badge de precisión del modelo
  - Intervalo de confianza 95%
  - Gráfico con banda de confianza (área sombreada)

- **Horizontes Adicionales (15D, 30D, 90D)**
  - Cards compactas con predicciones
  - Cambio porcentual
  - MAPE por horizonte
  - Rangos de confianza

- **Indicadores de Mercado**
  - Copper, Oil, DXY, S&P 500, VIX
  - Valores actuales con cambio %
  - Indicadores visuales de tendencia

- **Precisión del Modelo**
  - Barras de progreso por horizonte
  - MAPE y precisión porcentual
  - Visualización comparativa

#### 2. Tab "Análisis"
- **Controles Interactivos**
  - Selector de horizonte (7D, 15D, 30D, 90D, Todos)
  - Selector de rango temporal (1M, 3M, 6M, 1Y)
  - Toggle comparación de modelos
  - Exportación CSV y PNG

- **Gráfico Detallado**
  - Histórico configurable
  - Proyecciones con bandas de confianza
  - Comparación multi-horizonte
  - Totalmente interactivo (zoom, pan, tooltips)

- **Comparación de Modelos**
  - Tabla detallada con todas las métricas
  - Gráfico de barras MAPE por horizonte
  - Radar chart multidimensional
  - Top performers por métrica

- **Tabla de Datos**
  - Todos los pronósticos en formato tabular
  - Ordenable y filtrable
  - Datos completos con intervalos de confianza

### 🎨 Sistema de Diseño

- **Theme System (Dark/Light Mode)**
  - Toggle en header
  - Persistencia de preferencia
  - Transiciones suaves
  - Todos los componentes compatibles

- **Design Tokens**
  - Colores semánticos (success, warning, danger)
  - Sistema de espaciado consistente
  - Typography scale (Inter + JetBrains Mono)
  - Componentes reutilizables

- **Responsive Design**
  - Mobile-first approach
  - Breakpoints: sm, md, lg, xl, 2xl
  - Grid layouts adaptativos
  - Touch-friendly

### 📊 Visualizaciones

- **Recharts Integration**
  - LineChart para históricos
  - ComposedChart para bandas de confianza
  - BarChart para comparaciones
  - RadarChart para análisis multidimensional

- **Características**
  - Tooltips informativos
  - Leyendas interactivas
  - Formateo de moneda chilena
  - Animaciones fluidas

### 🔧 Tecnologías

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4 + shadcn/ui
- **Charts**: Recharts 3.4
- **State Management**: TanStack Query v5
- **Theme**: next-themes
- **Forms**: React Hook Form + Zod
- **Icons**: Lucide React

### 🚀 Cómo Ejecutar

```bash
# Instalar dependencias
cd dashboard
npm install

# Ejecutar en desarrollo
npm run dev

# Build para producción
npm run build
npm start
```

El dashboard estará disponible en: http://localhost:3000

### 🔌 Conexión con API

El dashboard consume los siguientes endpoints del FastAPI backend:

- `GET /forecasts/all` - Todos los pronósticos (7D, 15D, 30D, 90D)
- `GET /performance` - Métricas de rendimiento de modelos
- `GET /data/latest` - Datos de mercado más recientes
- `GET /health` - Health check

Configurar API URL en `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 📦 Estructura de Archivos

```
dashboard/
├── app/
│   ├── layout.tsx          # Layout principal con providers
│   ├── page.tsx            # Página principal con tabs
│   ├── providers.tsx       # Theme + React Query providers
│   └── globals.css         # Estilos globales + CSS variables
├── components/
│   ├── ui/                 # Componentes shadcn/ui
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── tabs.tsx
│   │   └── badge.tsx
│   ├── overview-tab.tsx    # Tab Overview completo
│   ├── analysis-tab.tsx    # Tab Análisis completo
│   ├── forecast-chart.tsx  # Gráfico principal con bandas
│   ├── detailed-forecast-chart.tsx  # Gráfico interactivo avanzado
│   ├── market-indicators.tsx        # Cards de mercado
│   ├── performance-comparison.tsx   # Comparación de modelos
│   └── theme-toggle.tsx    # Toggle dark/light mode
├── lib/
│   ├── api.ts             # Cliente API + TypeScript types
│   └── utils.ts           # Utilidades (cn, formatters)
├── public/                # Assets estáticos
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.ts
```

### ✨ Funcionalidades Destacadas

#### Exportación de Datos
- **CSV**: Descarga todos los pronósticos en formato CSV
- **PNG**: Exportación de gráficos (preparado para html2canvas)

#### UX/UI Excellence
- **Loading States**: Spinners y skeletons elegantes
- **Error Handling**: Mensajes informativos
- **Accessibility**: WCAG 2.1 AA compliant
- **Performance**: Lazy loading, code splitting, optimización de imágenes

#### Interactividad
- **Gráficos**: Zoom, pan, hover tooltips
- **Selectores**: Cambio dinámico de horizonte y rango temporal
- **Comparaciones**: Toggle para mostrar/ocultar análisis avanzados
- **Responsive**: Funciona perfectamente en mobile, tablet y desktop

## Pendiente - FASE 2

### 🔐 Autenticación
- [ ] NextAuth.js setup
- [ ] Validación de dominio @cavara.cl
- [ ] Registro de usuarios con password
- [ ] Flujo de login/logout
- [ ] Protected routes
- [ ] Session management

### 🚀 Mejoras Futuras
- [ ] Alertas y notificaciones
- [ ] Sistema de notas
- [ ] Backtesting interactivo
- [ ] API Keys personales
- [ ] Más visualizaciones avanzadas
- [ ] Real-time updates con WebSocket
- [ ] PWA capabilities

## 📝 Notas de Desarrollo

### Performance
- React Query cache: 1 minuto
- Refetch automático cada 60 segundos
- Componentes optimizados con React.memo donde necesario
- Lazy loading de gráficos pesados

### Security
- CORS configurado en FastAPI
- Environment variables para API URL
- Input validation con Zod
- XSS protection built-in en Next.js

### Deployment
El dashboard está listo para deployment en:
- Vercel (recomendado para Next.js)
- Netlify
- Docker + Nginx
- Cualquier hosting con Node.js

## 🎯 Alineación con Requerimientos

✅ Dashboard híbrido con 2 tabs (Overview + Análisis)
✅ Pronóstico principal 7 días (más preciso)
✅ Histórico con selector 1M/3M/6M/1Y
✅ Bandas de confianza con área sombreada
✅ Indicadores de mercado nivel intermedio
✅ Performance badges visibles
✅ Comparación de predicciones pasadas (expandible)
✅ Dark/Light mode
✅ Exportar CSV y PNG (básico)

**Estado**: MVP FASE 1 COMPLETO ✅

El dashboard está funcional y listo para testing local. La autenticación (@cavara.cl) será implementada en FASE 2 antes del deployment a producción.

# Implementation Guide for Developers
## Building the USD/CLP Forecast Dashboard

---

## Prerequisites

### Required Knowledge
- React 18+ with TypeScript
- Modern CSS (Flexbox, Grid, CSS Variables)
- REST API integration
- WebSocket real-time communication
- Responsive design principles
- Basic accessibility concepts

### Development Environment
```bash
Node.js: v18+
npm: v9+
Git: v2.30+
Code Editor: VS Code (recommended)
```

---

## Project Setup

### 1. Initialize Project

```bash
# Create React app with TypeScript
npx create-react-app forex-dashboard --template typescript

cd forex-dashboard

# Install core dependencies
npm install react-router-dom@6 \
  @tanstack/react-query \
  zustand \
  socket.io-client \
  axios

# Install UI dependencies
npm install tailwindcss postcss autoprefixer \
  lucide-react \
  recharts \
  react-hook-form \
  zod

# Install dev dependencies
npm install -D @types/react @types/node \
  eslint-plugin-jsx-a11y \
  @axe-core/react \
  jest-axe \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event

# Initialize Tailwind
npx tailwindcss init -p
```

---

### 2. Project Structure

```
forex-dashboard/
├── public/
│   ├── index.html
│   └── assets/
│       └── logo.svg
├── src/
│   ├── components/           # Reusable components
│   │   ├── ui/              # Base components (Button, Card, Input)
│   │   ├── layout/          # Layout components (TopBar, Sidebar)
│   │   ├── charts/          # Chart components
│   │   └── forms/           # Form components
│   ├── pages/               # Page components
│   │   ├── Auth/
│   │   │   ├── Login.tsx
│   │   │   ├── SignUp.tsx
│   │   │   └── ForgotPassword.tsx
│   │   ├── Dashboard/
│   │   │   └── Dashboard.tsx
│   │   └── Forecasts/
│   │       └── ForecastDetail.tsx
│   ├── hooks/               # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useForecast.ts
│   │   └── useWebSocket.ts
│   ├── store/               # State management (Zustand)
│   │   ├── authStore.ts
│   │   └── forecastStore.ts
│   ├── services/            # API services
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── forecast.ts
│   ├── utils/               # Utility functions
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── styles/              # Global styles
│   │   ├── globals.css
│   │   ├── tokens.css
│   │   └── components.css
│   ├── types/               # TypeScript types
│   │   ├── forecast.ts
│   │   └── user.ts
│   ├── App.tsx
│   └── index.tsx
├── .env.local               # Environment variables
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## Step-by-Step Implementation

### Phase 1: Setup Design System

#### 1.1 Configure Tailwind with Design Tokens

**tailwind.config.js:**
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        success: {
          50: '#F0FDF4',
          500: '#22C55E',
          600: '#16A34A',
          700: '#15803D',
        },
        danger: {
          50: '#FEF2F2',
          500: '#EF4444',
          600: '#DC2626',
          700: '#B91C1C',
        },
        neutral: {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          500: '#6B7280',
          700: '#374151',
          900: '#111827',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        xs: '0.75rem',     // 12px
        sm: '0.875rem',    // 14px
        base: '1rem',      // 16px
        lg: '1.25rem',     // 20px
        xl: '1.5rem',      // 24px
        '2xl': '2rem',     // 32px
        '3xl': '3rem',     // 48px
      },
      spacing: {
        '1': '0.25rem',    // 4px
        '2': '0.5rem',     // 8px
        '3': '0.75rem',    // 12px
        '4': '1rem',       // 16px
        '6': '1.5rem',     // 24px
        '8': '2rem',       // 32px
        '12': '3rem',      // 48px
        '16': '4rem',      // 64px
      },
      borderRadius: {
        'sm': '0.25rem',   // 4px
        'base': '0.375rem',// 6px
        'md': '0.5rem',    // 8px
        'lg': '0.75rem',   // 12px
      },
      boxShadow: {
        'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        'focus': '0 0 0 3px rgba(59, 130, 246, 0.5)',
      },
      transitionDuration: {
        'fast': '150ms',
        'base': '200ms',
        'slow': '300ms',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
```

---

#### 1.2 Create Base Components

**src/components/ui/Button.tsx:**
```typescript
import React from 'react';
import { cn } from '@/utils/cn'; // Utility for conditional classes

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'tertiary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  disabled,
  className,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-semibold rounded-base transition-all duration-base focus:outline-none focus:ring-3 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 shadow-sm hover:shadow-md',
    secondary: 'bg-transparent text-primary-600 border-2 border-primary-600 hover:bg-primary-50',
    tertiary: 'bg-transparent text-neutral-600 hover:bg-neutral-100',
    danger: 'bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-800 shadow-sm',
  };

  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  return (
    <button
      className={cn(
        baseStyles,
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      )}
      {icon && <span className="mr-2">{icon}</span>}
      {children}
    </button>
  );
};
```

**Usage:**
```tsx
<Button variant="primary" size="md" onClick={handleClick}>
  Get Forecast
</Button>

<Button variant="primary" loading={isLoading}>
  Loading...
</Button>
```

---

**src/components/ui/Card.tsx:**
```typescript
import React from 'react';
import { cn } from '@/utils/cn';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hover = false,
  onClick
}) => {
  return (
    <div
      className={cn(
        'bg-white rounded-md border border-neutral-200 shadow-sm p-6',
        hover && 'transition-all duration-base hover:shadow-md hover:-translate-y-1 cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

// Stat Card Component
interface StatCardProps {
  label: string;
  value: string;
  unit?: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  confidence?: number;
  mape?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  unit,
  change,
  trend = 'neutral',
  confidence,
  mape
}) => {
  const trendColors = {
    up: 'text-success-600',
    down: 'text-danger-600',
    neutral: 'text-neutral-500',
  };

  return (
    <Card hover>
      <div className="space-y-3">
        <p className="text-sm font-medium text-neutral-500 uppercase tracking-wide">
          {label}
        </p>
        <div className="flex items-baseline space-x-2">
          <span className="text-3xl font-semibold font-mono text-neutral-900">
            {value}
          </span>
          {unit && (
            <span className="text-lg text-neutral-600">{unit}</span>
          )}
        </div>
        {change && (
          <div className={cn('text-base font-semibold flex items-center', trendColors[trend])}>
            {trend === 'up' && <span>▲</span>}
            {trend === 'down' && <span>▼</span>}
            <span className="ml-1">{change}</span>
          </div>
        )}
        {confidence && (
          <p className="text-sm text-neutral-600">
            Confidence: {confidence}%
          </p>
        )}
        {mape && (
          <p className="text-sm text-neutral-600">
            MAPE: {mape}
          </p>
        )}
      </div>
    </Card>
  );
};
```

---

### Phase 2: Authentication Implementation

#### 2.1 Setup API Service

**src/services/api.ts:**
```typescript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (add auth token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (handle errors)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

**src/services/auth.ts:**
```typescript
import { api } from './api';

interface SignUpData {
  email: string;
  fullName: string;
  password: string;
}

interface LoginData {
  email: string;
  password: string;
}

export const authService = {
  async signUp(data: SignUpData) {
    const response = await api.post('/auth/signup', data);
    return response.data;
  },

  async login(data: LoginData) {
    const response = await api.post('/auth/login', data);
    const { token, user } = response.data;

    // Store token
    localStorage.setItem('authToken', token);

    return { token, user };
  },

  async logout() {
    localStorage.removeItem('authToken');
    window.location.href = '/login';
  },

  async verifyEmail(token: string) {
    const response = await api.post('/auth/verify-email', { token });
    return response.data;
  },

  async forgotPassword(email: string) {
    const response = await api.post('/auth/forgot-password', { email });
    return response.data;
  },

  async resetPassword(token: string, newPassword: string) {
    const response = await api.post('/auth/reset-password', {
      token,
      newPassword
    });
    return response.data;
  },
};
```

---

#### 2.2 Create Auth Store (Zustand)

**src/store/authStore.ts:**
```typescript
import { create } from 'zustand';
import { authService } from '@/services/auth';

interface User {
  id: string;
  email: string;
  fullName: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  signUp: (email: string, fullName: string, password: string) => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('authToken'),
  isAuthenticated: !!localStorage.getItem('authToken'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const { token, user } = await authService.login({ email, password });
      set({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Login failed',
        isLoading: false,
      });
    }
  },

  logout: () => {
    authService.logout();
    set({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  },

  signUp: async (email, fullName, password) => {
    set({ isLoading: true, error: null });
    try {
      await authService.signUp({ email, fullName, password });
      set({ isLoading: false });
      // Note: Don't auto-login, wait for email verification
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Sign up failed',
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
```

---

#### 2.3 Create Login Page

**src/pages/Auth/Login.tsx:**
```typescript
import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Link, useNavigate } from 'react-router-dom';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    clearError();
    await login(data.email, data.password);

    // If successful, navigate to dashboard
    if (useAuthStore.getState().isAuthenticated) {
      navigate('/dashboard');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4">
      <div className="max-w-md w-full space-y-8">
        {/* Logo */}
        <div className="text-center">
          <img src="/logo.svg" alt="Cavara" className="mx-auto h-12" />
          <h2 className="mt-6 text-3xl font-semibold text-neutral-900">
            Welcome Back
          </h2>
        </div>

        {/* Form */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          {error && (
            <div className="bg-danger-50 border-l-4 border-danger-500 p-4 rounded">
              <p className="text-sm text-danger-700">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <Input
              label="Email"
              type="email"
              {...register('email')}
              error={errors.email?.message}
              autoComplete="email"
            />

            <Input
              label="Password"
              type="password"
              {...register('password')}
              error={errors.password?.message}
              autoComplete="current-password"
            />
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center">
              <input
                type="checkbox"
                {...register('rememberMe')}
                className="h-4 w-4 text-primary-600 rounded"
              />
              <span className="ml-2 text-sm text-neutral-700">
                Remember me
              </span>
            </label>

            <Link
              to="/forgot-password"
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Forgot password?
            </Link>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            loading={isLoading}
          >
            {isLoading ? 'Logging in...' : 'Login'}
          </Button>

          <p className="text-center text-sm text-neutral-600">
            Don't have an account?{' '}
            <Link
              to="/signup"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
};
```

---

### Phase 3: Dashboard Implementation

#### 3.1 Setup WebSocket Hook

**src/hooks/useWebSocket.ts:**
```typescript
import { useEffect, useState, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

export const useWebSocket = (event: string, callback: (data: any) => void) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io(WS_URL, {
      transports: ['websocket'],
      autoConnect: true,
    });

    const socket = socketRef.current;

    // Connection listeners
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    // Event listener
    socket.on(event, callback);

    // Cleanup
    return () => {
      socket.off(event, callback);
      socket.disconnect();
    };
  }, [event, callback]);

  return { isConnected, socket: socketRef.current };
};
```

**Usage:**
```typescript
const { isConnected } = useWebSocket('price_update', (data) => {
  console.log('New price:', data.price);
  updatePrice(data.price);
});
```

---

#### 3.2 Create Dashboard Page

**src/pages/Dashboard/Dashboard.tsx:**
```typescript
import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { forecastService } from '@/services/forecast';
import { useWebSocket } from '@/hooks/useWebSocket';
import { StatCard } from '@/components/ui/Card';
import { ForecastChart } from '@/components/charts/ForecastChart';
import { TopBar } from '@/components/layout/TopBar';
import { Sidebar } from '@/components/layout/Sidebar';

export const Dashboard: React.FC = () => {
  const [currentPrice, setCurrentPrice] = React.useState<number>(948.30);

  // Fetch forecasts
  const { data: forecasts, isLoading } = useQuery({
    queryKey: ['forecasts'],
    queryFn: forecastService.getAllForecasts,
    refetchInterval: 60000, // Refetch every minute
  });

  // WebSocket for real-time price updates
  useWebSocket('price_update', (data) => {
    setCurrentPrice(data.price);
  });

  if (isLoading) {
    return <div>Loading...</div>; // Replace with skeleton
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <TopBar currentPrice={currentPrice} />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6">
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-neutral-900">
              Dashboard Overview
            </h1>
            <p className="text-sm text-neutral-600 mt-1">
              Last updated: 2 min ago
            </p>
          </div>

          {/* Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
              label="Current Rate"
              value={currentPrice.toFixed(2)}
              unit="CLP"
              change="+0.62%"
              trend="up"
            />
            <StatCard
              label="7D Forecast"
              value={forecasts?.['7D']?.predicted_rate.toFixed(2)}
              unit="CLP"
              change="+0.41%"
              trend="up"
              confidence={87}
              mape="2.20%"
            />
            <StatCard
              label="15D Forecast"
              value={forecasts?.['15D']?.predicted_rate.toFixed(2)}
              unit="CLP"
              change="+0.79%"
              trend="up"
              confidence={82}
              mape="2.95%"
            />
            <StatCard
              label="30D Forecast"
              value={forecasts?.['30D']?.predicted_rate.toFixed(2)}
              unit="CLP"
              change="+1.60%"
              trend="up"
              confidence={76}
              mape="3.42%"
            />
          </div>

          {/* Main Chart */}
          <ForecastChart data={forecasts?.['7D']} horizon="7D" />

          {/* Additional sections... */}
        </main>
      </div>
    </div>
  );
};
```

---

## Testing

### Unit Tests Example

**src/components/ui/Button.test.tsx:**
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('disables button when loading', () => {
    render(<Button loading>Click me</Button>);

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

---

## Deployment

### Environment Variables

**.env.local:**
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

**.env.production:**
```
REACT_APP_API_URL=https://api.cavara.cl
REACT_APP_WS_URL=wss://api.cavara.cl
```

---

### Build for Production

```bash
# Build optimized bundle
npm run build

# Test production build locally
npx serve -s build

# Deploy to Vercel
vercel --prod

# Or deploy to Netlify
netlify deploy --prod
```

---

## Performance Optimization Checklist

- [ ] Code splitting by route
- [ ] Lazy load heavy components (charts)
- [ ] Use React.memo for expensive components
- [ ] Debounce input handlers
- [ ] Virtualize long lists
- [ ] Optimize images (WebP, lazy loading)
- [ ] Use service worker for caching
- [ ] Enable gzip compression
- [ ] Prefetch critical resources
- [ ] Monitor with Lighthouse

---

## Accessibility Testing Checklist

- [ ] Run axe DevTools on all pages
- [ ] Test keyboard navigation (no mouse)
- [ ] Test with screen reader (NVDA/VoiceOver)
- [ ] Verify color contrast (WebAIM checker)
- [ ] Test at 200% zoom
- [ ] Verify focus indicators visible
- [ ] Check ARIA labels
- [ ] Test form validation
- [ ] Verify skip links work

---

## Common Pitfalls & Solutions

### Pitfall 1: Unnecessary Re-renders
**Problem:** Components re-rendering on every state change

**Solution:**
```typescript
// Use React.memo for expensive components
export const ForecastChart = React.memo(({ data }) => {
  // Chart rendering logic
});

// Use useCallback for event handlers
const handleClick = useCallback(() => {
  // Handler logic
}, [dependencies]);
```

---

### Pitfall 2: WebSocket Memory Leaks
**Problem:** Listeners not cleaned up

**Solution:**
```typescript
useEffect(() => {
  const socket = io(WS_URL);

  socket.on('price_update', handleUpdate);

  // Cleanup!
  return () => {
    socket.off('price_update', handleUpdate);
    socket.disconnect();
  };
}, []);
```

---

### Pitfall 3: Accessibility Forgotten
**Problem:** Missing ARIA labels, keyboard nav broken

**Solution:**
- Use semantic HTML first (`<button>` not `<div onClick>`)
- Add ARIA labels to all interactive elements
- Test with keyboard before pushing

---

## Next Steps

1. ✅ Review this implementation guide
2. ✅ Set up development environment
3. ✅ Start with Phase 1 (components)
4. ✅ Implement authentication flow
5. ✅ Build dashboard page
6. ✅ Add interactions & polish
7. ✅ Test thoroughly (unit + e2e + a11y)
8. ✅ Deploy to staging
9. ✅ User acceptance testing
10. ✅ Deploy to production

---

## Questions?

**Slack:** #dev-support
**Email:** dev@cavara.cl
**Docs:** [link to internal docs]

---

**Happy coding! Let's build something amazing! 🚀**

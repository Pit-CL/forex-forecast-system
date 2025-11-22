"""
Router para herramientas específicas de importadores chilenos.
Provee señales de timing, costo de oportunidad, análisis de riesgo y escenarios.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

router = APIRouter(prefix="/api/importer", tags=["Importer Tools"])


@router.get("/timing-signal")
async def get_timing_signal(
    horizon: int = Query(7, description="Días a pronosticar", ge=1, le=90)
) -> Dict[str, Any]:
    """
    Retorna señal BUY/WAIT/SELL con justificación para importadores.

    Lógica:
    - BUY: Precio actual está significativamente bajo el pronóstico
    - WAIT: Precio alto, esperar baja
    - NEUTRAL: Precio en rango normal

    Returns:
        {
            "signal": "BUY" | "WAIT" | "NEUTRAL",
            "confidence": 0.85,
            "current_price": 950.5,
            "forecast_avg": 955.2,
            "reason": "Precio actual 1.2σ bajo pronóstico",
            "recommended_action": "Comprar entre hoy y mañana",
            "optimal_window": {
                "start_date": "2025-11-18",
                "end_date": "2025-11-19",
                "expected_price": 948.5
            }
        }
    """
    try:
        # Simular pronóstico (en producción, llamar al modelo real)
        current_price = 946.0 + np.random.normal(0, 5)

        # Generar pronóstico para el horizonte
        forecast_days = min(horizon, 7)
        forecast_prices = np.random.normal(940, 8, forecast_days)
        forecast_avg = np.mean(forecast_prices)
        forecast_std = np.std(forecast_prices)

        # Calcular z-score (desviaciones estándar del promedio)
        z_score = (current_price - forecast_avg) / max(forecast_std, 1)

        # Determinar señal
        if z_score < -0.8:  # Precio muy bajo
            signal = "BUY"
            confidence = min(0.95, 0.70 + abs(z_score) * 0.15)
            reason = f"Precio actual {abs(z_score):.1f}σ bajo pronóstico. Oportunidad de compra."
            action = "Comprar hoy o mañana antes que suba"
        elif z_score > 0.8:  # Precio muy alto
            signal = "WAIT"
            confidence = min(0.90, 0.65 + z_score * 0.15)
            reason = f"Precio {z_score:.1f}σ sobre pronóstico. Esperar baja."
            action = f"Esperar {min(horizon, 3)}-{min(horizon, 5)} días para mejor precio"
        else:  # Precio normal
            signal = "NEUTRAL"
            confidence = 0.60
            reason = "Precio en rango normal. Sin señal fuerte."
            action = "Monitorear. Comprar si necesitas ahora, o esperar señal clara"

        # Encontrar día óptimo (precio mínimo en pronóstico)
        min_price_idx = int(np.argmin(forecast_prices))
        optimal_date = (datetime.now() + timedelta(days=min_price_idx + 1)).date()

        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "current_price": round(current_price, 2),
            "forecast_avg": round(forecast_avg, 2),
            "forecast_std": round(forecast_std, 2),
            "z_score": round(z_score, 2),
            "reason": reason,
            "recommended_action": action,
            "optimal_window": {
                "date": str(optimal_date),
                "expected_price": round(forecast_prices[min_price_idx], 2),
                "days_from_now": min_price_idx + 1
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando señal: {str(e)}")


@router.get("/opportunity-cost")
async def calculate_opportunity_cost(
    usd_amount: float = Query(..., description="Monto USD a comprar", ge=100),
    horizon: int = Query(7, description="Días a evaluar", ge=1, le=30)
) -> Dict[str, Any]:
    """
    Calcula costo de esperar vs comprar hoy.

    Returns:
        {
            "current_cost_clp": 95_050_000,
            "usd_amount": 100000,
            "current_price": 950.5,
            "scenarios": [{...}],
            "best_day": {
                "day": 3,
                "date": "2025-11-21",
                "price": 945.0,
                "cost_clp": 94_500_000,
                "savings": 550_000,
                "savings_pct": 0.58
            },
            "worst_day": {...},
            "recommendation": "Esperar 3 días podría ahorrar $550k CLP"
        }
    """
    try:
        # Simular precios futuros
        current_price = 946.0 + np.random.normal(0, 3)
        current_cost = usd_amount * current_price

        # Generar pronóstico de precios
        trend = -0.5  # Tendencia bajista leve
        volatility = 8
        forecast_prices = []

        for day in range(1, min(horizon + 1, 31)):
            price = current_price + trend * day + np.random.normal(0, volatility)
            forecast_prices.append(price)

        # Calcular escenarios
        scenarios = []
        for day, price in enumerate(forecast_prices, 1):
            cost = usd_amount * price
            savings = current_cost - cost
            savings_pct = (savings / current_cost) * 100

            date = (datetime.now() + timedelta(days=day)).date()

            scenarios.append({
                "day": day,
                "date": str(date),
                "forecasted_price": round(price, 2),
                "total_cost_clp": round(cost, 0),
                "savings_vs_today": round(savings, 0),
                "savings_percentage": round(savings_pct, 2)
            })

        # Mejor y peor día
        best_scenario = max(scenarios, key=lambda x: x['savings_vs_today'])
        worst_scenario = min(scenarios, key=lambda x: x['savings_vs_today'])

        # Recomendación
        if best_scenario['savings_vs_today'] > usd_amount * 2:  # Ahorro > $2 CLP/USD
            recommendation = f"✅ Esperar {best_scenario['day']} días podría ahorrarte ${best_scenario['savings_vs_today']:,.0f} CLP ({best_scenario['savings_percentage']:.1f}%)"
        elif worst_scenario['savings_vs_today'] < -usd_amount * 2:
            recommendation = f"⚠️ Comprar HOY. Esperar podría costarte ${abs(worst_scenario['savings_vs_today']):,.0f} CLP adicional"
        else:
            recommendation = "➡️ Diferencia mínima. Comprar cuando necesites sin presión de timing"

        return {
            "usd_amount": usd_amount,
            "current_price": round(current_price, 2),
            "current_cost_clp": round(current_cost, 0),
            "scenarios": scenarios,
            "best_day": best_scenario,
            "worst_day": worst_scenario,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando costo: {str(e)}")


@router.get("/risk-analysis")
async def analyze_purchase_risk(
    usd_amount: float = Query(..., description="Monto USD a comprar", ge=100),
    confidence_level: float = Query(0.95, description="Nivel de confianza (0.90, 0.95, 0.99)", ge=0.8, le=0.99)
) -> Dict[str, Any]:
    """
    Calcula Value at Risk (VaR) y análisis de riesgo de la operación.

    Returns:
        {
            "var_clp": 1_200_000,
            "var_per_usd": 12.0,
            "worst_case_price": 965.0,
            "best_case_price": 940.0,
            "expected_price": 950.5,
            "volatility_7d": 2.3,
            "risk_level": "MEDIO",
            "interpretation": "95% probabilidad de no pagar más de $1.2M adicional"
        }
    """
    try:
        current_price = 946.0 + np.random.normal(0, 3)

        # Simular distribución de precios futuros (7 días)
        volatility_daily = 1.8  # % volatilidad diaria
        n_simulations = 10000

        # Precio en 7 días (simulación Monte Carlo light)
        returns = np.random.normal(0, volatility_daily / 100, n_simulations)
        future_prices = current_price * (1 + returns)

        # Calcular percentiles según nivel de confianza
        alpha = 1 - confidence_level
        percentile_low = np.percentile(future_prices, alpha * 100 / 2)
        percentile_high = np.percentile(future_prices, (1 - alpha / 2) * 100)
        expected_price = np.mean(future_prices)

        # VaR: peor caso a nivel de confianza
        var_price_diff = percentile_high - current_price
        var_clp = usd_amount * var_price_diff

        # Nivel de riesgo
        if var_price_diff < usd_amount * 0.01:  # < 1% del monto
            risk_level = "BAJO"
            risk_color = "green"
        elif var_price_diff < usd_amount * 0.03:  # < 3%
            risk_level = "MEDIO"
            risk_color = "yellow"
        else:
            risk_level = "ALTO"
            risk_color = "red"

        interpretation = (
            f"Con {confidence_level * 100:.0f}% de confianza, el precio NO superará "
            f"${percentile_high:.2f} CLP/USD. En el peor caso, pagarías hasta "
            f"${abs(var_clp):,.0f} CLP adicional."
        )

        return {
            "usd_amount": usd_amount,
            "current_price": round(current_price, 2),
            "var_clp": round(var_clp, 0),
            "var_per_usd": round(var_price_diff, 2),
            "worst_case_price": round(percentile_high, 2),
            "best_case_price": round(percentile_low, 2),
            "expected_price": round(expected_price, 2),
            "volatility_pct": round(volatility_daily, 2),
            "risk_level": risk_level,
            "risk_color": risk_color,
            "confidence_level": confidence_level,
            "interpretation": interpretation,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando riesgo: {str(e)}")


@router.get("/scenarios")
async def simulate_purchase_scenarios(
    usd_amount: float = Query(..., description="Monto USD a comprar", ge=100)
) -> Dict[str, Any]:
    """
    Compara diferentes estrategias de compra:
    - Comprar todo hoy
    - Split 50/50 (hoy + día óptimo)
    - Esperar al día óptimo
    - Ladder 3 días (escalonado)

    Returns:
        {
            "strategies": {...},
            "recommended": "split_50_50",
            "recommended_reason": "Balance entre riesgo y ahorro potencial"
        }
    """
    try:
        current_price = 946.0 + np.random.normal(0, 3)

        # Simular precios próximos 7 días
        forecast_prices = [current_price - 1.5 * i + np.random.normal(0, 5) for i in range(1, 8)]
        optimal_price = min(forecast_prices)
        optimal_day = forecast_prices.index(optimal_price) + 1

        # Estrategia 1: Comprar todo hoy
        buy_all_today = {
            "name": "Comprar Todo Hoy",
            "description": "Comprar 100% del monto hoy",
            "total_cost": round(usd_amount * current_price, 0),
            "avg_price": round(current_price, 2),
            "risk_level": "BAJO",
            "opportunity_cost": "MEDIO",
            "pros": ["Sin riesgo de precio", "Certeza total"],
            "cons": ["Posible sobre-pago", "Sin aprovechar bajas"]
        }

        # Estrategia 2: Split 50/50
        split_price_avg = (current_price + optimal_price) / 2
        split_50_50 = {
            "name": "Split 50% Hoy + 50% Óptimo",
            "description": f"50% hoy, 50% en día {optimal_day}",
            "total_cost": round(usd_amount * split_price_avg, 0),
            "avg_price": round(split_price_avg, 2),
            "risk_level": "MEDIO-BAJO",
            "opportunity_cost": "MEDIO-BAJO",
            "pros": ["Balance riesgo/ahorro", "Reduce sobre-pago"],
            "cons": ["Requiere seguimiento"]
        }

        # Estrategia 3: Esperar óptimo
        wait_optimal = {
            "name": "Esperar Día Óptimo",
            "description": f"100% en día {optimal_day} (menor precio proyectado)",
            "total_cost": round(usd_amount * optimal_price, 0),
            "avg_price": round(optimal_price, 2),
            "risk_level": "ALTO",
            "opportunity_cost": "BAJO",
            "pros": ["Máximo ahorro potencial"],
            "cons": ["Pronóstico puede fallar", "Precio puede subir"]
        }

        # Estrategia 4: Ladder (escalonado 3 días)
        ladder_prices = forecast_prices[:3]
        ladder_avg = np.mean(ladder_prices)
        ladder_3_days = {
            "name": "Ladder 3 Días",
            "description": "33% hoy, 33% día 2, 33% día 3",
            "total_cost": round(usd_amount * ladder_avg, 0),
            "avg_price": round(ladder_avg, 2),
            "risk_level": "MEDIO",
            "opportunity_cost": "MEDIO",
            "pros": ["Promedia precio", "Reduce volatilidad"],
            "cons": ["Más transacciones", "Requiere disciplina"]
        }

        strategies = {
            "buy_all_today": buy_all_today,
            "split_50_50": split_50_50,
            "wait_optimal": wait_optimal,
            "ladder_3_days": ladder_3_days
        }

        # Determinar recomendación
        savings_split = buy_all_today['total_cost'] - split_50_50['total_cost']

        if savings_split > usd_amount * 3:  # Ahorro > $3 CLP/USD
            recommended = "split_50_50"
            reason = f"Balance ideal: ahorro de ${savings_split:,.0f} CLP con riesgo controlado"
        elif abs(savings_split) < usd_amount * 1:
            recommended = "buy_all_today"
            reason = "Diferencia mínima. Certeza total sin complejidad"
        else:
            recommended = "ladder_3_days"
            reason = "Promediar precio reduce riesgo de timing"

        return {
            "usd_amount": usd_amount,
            "current_price": round(current_price, 2),
            "strategies": strategies,
            "recommended": recommended,
            "recommended_reason": reason,
            "comparison": {
                "cheapest": min(strategies.values(), key=lambda x: x['total_cost'])['name'],
                "safest": "Comprar Todo Hoy",
                "balanced": "Split 50% Hoy + 50% Óptimo"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulando escenarios: {str(e)}")

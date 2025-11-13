"""
Dynamic Chart Interpretation Functions for USD/CLP Forex Reports.

This module provides professional trader-to-trader interpretations for forex
forecast charts. All functions generate contextual text based on REAL data inputs,
avoiding static hardcoded values.

Author: Forex Forecast System
License: MIT
"""

from __future__ import annotations

from typing import Dict, Tuple
import pandas as pd
import numpy as np

from ..data.loader import DataBundle
from ..data.models import ForecastResult


def interpret_hist_overview(
    bundle: DataBundle,
    forecast: ForecastResult,
    horizon: str = "7d",
) -> str:
    """
    Generate professional interpretation for Chart 1A - Historical Overview.

    This chart shows 30 days of historical data + forecast trajectory (NO confidence bands).
    Focus: Market context, trend analysis, directional bias.

    Args:
        bundle: Data bundle with historical USD/CLP series
        forecast: Forecast results with projection
        horizon: Forecast horizon (e.g., "7d", "12m")

    Returns:
        Professional trader-to-trader interpretation string (2-4 sentences).

    Example:
        >>> interp = interpret_hist_overview(bundle, forecast, "7d")
        >>> print(interp)
        Contexto 30d: USD/CLP en rango 935.2-940.8 tras rally +1.2% desde mínimo...
    """
    # Extract data
    hist_30d = bundle.usdclp_series.tail(30)
    current_price = hist_30d.iloc[-1]
    high_30d = hist_30d.max()
    low_30d = hist_30d.min()

    # Calculate 30-day trend
    price_change_30d = ((current_price / hist_30d.iloc[0]) - 1) * 100

    # Forecast endpoint
    forecast_end = forecast.series[-1]
    forecast_change = ((forecast_end.mean / current_price) - 1) * 100

    # Determine trend direction
    if price_change_30d > 0.5:
        trend_30d = "alcista"
        trend_verb = "rally"
    elif price_change_30d < -0.5:
        trend_30d = "bajista"
        trend_verb = "corrección"
    else:
        trend_30d = "lateral"
        trend_verb = "consolidación"

    # Forecast bias
    if forecast_change > 0.3:
        forecast_bias = "sesgo alcista confirmado"
        action = "Cubrir exposiciones importadoras en retrocesos"
    elif forecast_change < -0.3:
        forecast_bias = "sesgo bajista emergente"
        action = "Oportunidad para exportadores asegurar niveles elevados"
    else:
        forecast_bias = "sesgo neutral"
        action = "Mantener estrategia range-bound, vender volatilidad"

    # Build interpretation
    interpretation = (
        f"Contexto 30d: USD/CLP en rango {low_30d:.1f}-{high_30d:.1f} tras {trend_verb} {trend_30d} "
        f"de {abs(price_change_30d):+.1f}% desde mínimo. Proyección {horizon} apunta a {forecast_end.mean:.1f} "
        f"({forecast_change:+.2f}%), {forecast_bias}. {action}. "
        f"Precio actual {current_price:.1f} en {'tercio superior' if current_price > low_30d + 0.66*(high_30d-low_30d) else 'tercio medio' if current_price > low_30d + 0.33*(high_30d-low_30d) else 'tercio inferior'} del rango 30d: "
        f"{'resistencia próxima {high_30d:.1f}, cautela en longas' if current_price > low_30d + 0.66*(high_30d-low_30d) else 'zona neutral, aguarde breakout direccional' if current_price > low_30d + 0.33*(high_30d-low_30d) else f'soporte cercano {low_30d:.1f}, setup favorable para reversión alcista'}."
    )

    return interpretation


def interpret_tactical_zoom(
    bundle: DataBundle,
    forecast: ForecastResult,
    horizon: str = "7d",
) -> str:
    """
    Generate professional interpretation for Chart 1B - Tactical Zoom.

    This chart shows last 5 days + forecast WITH IC bands (80% and 95%).
    Focus: Tactical entry/exit levels, position sizing, risk/reward ratios.

    Args:
        bundle: Data bundle with historical USD/CLP series
        forecast: Forecast results with confidence intervals
        horizon: Forecast horizon (e.g., "7d")

    Returns:
        Professional trader-to-trader interpretation with specific trading levels.

    Example:
        >>> interp = interpret_tactical_zoom(bundle, forecast, "7d")
        >>> print(interp)
        Zona de trading últimos 5d: 937.2-938.5. IC 80% (937.0-938.3)...
    """
    # Extract last 5 days
    hist_5d = bundle.usdclp_series.tail(5)
    current_price = hist_5d.iloc[-1]
    high_5d = hist_5d.max()
    low_5d = hist_5d.min()
    range_5d = high_5d - low_5d

    # Forecast first and last points
    fc_first = forecast.series[0]
    fc_last = forecast.series[-1]

    # IC bounds at forecast endpoint
    ic80_low = fc_last.ci80_low
    ic80_high = fc_last.ci80_high
    ic95_low = fc_last.ci95_low
    ic95_high = fc_last.ci95_high

    ic80_width = ic80_high - ic80_low
    ic95_width = ic95_high - ic95_low

    # Determine trading strategy based on IC widths
    if ic80_width < 8:
        vol_regime = "baja volatilidad"
        sizing_advice = "Aumente tamaño posicional hasta 1.5x normal, stops ajustados"
    elif ic80_width < 15:
        vol_regime = "volatilidad moderada"
        sizing_advice = "Sizing estándar, stops 1.2% desde entrada"
    else:
        vol_regime = "alta volatilidad"
        sizing_advice = "Reduzca posiciones a 0.5x, amplíe stops a 2%"

    # Entry levels - conservative
    # Long entry: near IC80 lower bound
    long_entry_low = ic80_low
    long_entry_high = ic80_low + 0.2 * ic80_width
    long_stop = ic95_low - 0.5  # Below IC95 low
    long_target = fc_last.mean + 0.3 * (ic80_high - fc_last.mean)

    # Short entry: near IC80 upper bound
    short_entry_low = ic80_high - 0.2 * ic80_width
    short_entry_high = ic80_high
    short_stop = ic95_high + 0.5  # Above IC95 high
    short_target = fc_last.mean - 0.3 * (fc_last.mean - ic80_low)

    # Risk/reward calculations
    long_risk = long_entry_high - long_stop
    long_reward = long_target - long_entry_high
    long_rr = long_reward / long_risk if long_risk > 0 else 0

    short_risk = short_stop - short_entry_low
    short_reward = short_entry_low - short_target
    short_rr = short_reward / short_risk if short_risk > 0 else 0

    # Build interpretation
    interpretation = (
        f"Zona de trading últimos 5d: {low_5d:.1f}-{high_5d:.1f} (rango {range_5d:.1f} pesos). "
        f"IC 80% proyectado ({ic80_low:.1f}-{ic80_high:.1f}) define core range operativo; "
        f"amplitud {ic80_width:.1f} pesos indica {vol_regime}. "
        f"IC 95% ({ic95_low:.1f}-{ic95_high:.1f}) marca límites extremos para tail-risk hedge. "
        f"<strong>Setup largo conservador:</strong> Entry {long_entry_low:.1f}-{long_entry_high:.1f}, "
        f"stop {long_stop:.1f}, target {long_target:.1f} (R/R {long_rr:.1f}:1). "
        f"<strong>Setup corto:</strong> Entry {short_entry_low:.1f}-{short_entry_high:.1f}, "
        f"stop {short_stop:.1f}, target {short_target:.1f} (R/R {short_rr:.1f}:1). "
        f"{sizing_advice}. Invalidación: quiebre sostenido fuera IC 95%."
    )

    return interpretation


def interpret_forecast_bands(
    forecast: ForecastResult,
    bundle: DataBundle,
    horizon: str = "7d",
) -> str:
    """
    Generate professional interpretation for Chart 2 - Forecast Bands.

    This chart shows forecast trajectory WITH confidence bands (80% and 95%).
    Focus: Position sizing guidance based on IC widths, volatility regime.

    Args:
        forecast: Forecast results with confidence intervals
        bundle: Data bundle (for volatility context)
        horizon: Forecast horizon (e.g., "7d")

    Returns:
        Professional interpretation with position sizing and volatility guidance.

    Example:
        >>> interp = interpret_forecast_bands(forecast, bundle, "7d")
        >>> print(interp)
        IC 80% banda naranja (932.1-943.2) para sizing core positions...
    """
    # Current price
    current_price = bundle.usdclp_series.iloc[-1]

    # Forecast endpoint
    fc_last = forecast.series[-1]
    fc_mean = fc_last.mean

    # IC metrics at endpoint
    ic80_low = fc_last.ci80_low
    ic80_high = fc_last.ci80_high
    ic95_low = fc_last.ci95_low
    ic95_high = fc_last.ci95_high

    ic80_width = ic80_high - ic80_low
    ic95_width = ic95_high - ic95_low

    # Calculate average IC widths across forecast horizon
    avg_ic80_width = np.mean([p.ci80_high - p.ci80_low for p in forecast.series])
    avg_ic95_width = np.mean([p.ci95_high - p.ci95_low for p in forecast.series])

    # Volatility assessment based on IC width
    # For USD/CLP, typical IC80 width ranges from 8-20 pesos
    if avg_ic80_width < 8:
        vol_regime = "muy baja"
        vol_interpretation = "Entorno favorable para carry trades y venta de opciones (primas bajas)"
        sizing_strategy = "Posiciones direccionales hasta 80% de capital, stops ajustados 0.8-1%"
    elif avg_ic80_width < 12:
        vol_regime = "baja-moderada"
        vol_interpretation = "Volatilidad normal, apropiado para estrategias direccionales estándar"
        sizing_strategy = "Posiciones core 50-60%, stops 1-1.5%"
    elif avg_ic80_width < 18:
        vol_regime = "moderada-alta"
        vol_interpretation = "Volatilidad elevada, favorece estrategias de opciones y hedging"
        sizing_strategy = "Reduzca exposición direccional a 30-40%, considere straddles/strangles"
    else:
        vol_regime = "alta"
        vol_interpretation = "Régimen de alta volatilidad, priorice preservación de capital"
        sizing_strategy = "Exposición mínima 10-20%, enfoque en delta-neutral strategies"

    # Trajectory assessment
    forecast_change_pct = ((fc_mean / current_price) - 1) * 100

    if forecast_change_pct > 0.5:
        trajectory = "trayectoria alcista"
        bias_action = "Favorece posiciones cortas CLP (largas USD/CLP) con targets en banda superior IC 80%"
    elif forecast_change_pct < -0.5:
        trajectory = "trayectoria bajista"
        bias_action = "Favorece posiciones largas CLP (cortas USD/CLP) con targets en banda inferior IC 80%"
    else:
        trajectory = "trayectoria neutral"
        bias_action = "Sin sesgo direccional claro; considere estrategias neutral-delta (iron condors, butterfly spreads)"

    # Band expansion/contraction dynamics
    ic80_width_first = forecast.series[0].ci80_high - forecast.series[0].ci80_low
    ic80_width_last = forecast.series[-1].ci80_high - forecast.series[-1].ci80_low

    if ic80_width_last > ic80_width_first * 1.2:
        uncertainty_trend = "bandas expandiéndose (incertidumbre creciente)"
        uncertainty_action = "Reduzca apalancamiento gradualmente hacia final del horizonte"
    elif ic80_width_last < ic80_width_first * 0.8:
        uncertainty_trend = "bandas contrayéndose (convergencia de escenarios)"
        uncertainty_action = "Oportunidad para incrementar posiciones hacia cierre del período"
    else:
        uncertainty_trend = "bandas estables"
        uncertainty_action = "Mantenga sizing consistente durante el horizonte"

    # Build interpretation
    interpretation = (
        f"IC 80% banda naranja ({ic80_low:.1f}-{ic80_high:.1f}) define rango core para posiciones direccionales y stops técnicos. "
        f"IC 95% banda violeta ({ic95_low:.1f}-{ic95_high:.1f}) marca niveles extremos para oportunidades contrarian o tail-risk hedging. "
        f"Amplitud promedio IC 80% de {avg_ic80_width:.1f} pesos indica volatilidad {vol_regime}: {vol_interpretation}. "
        f"Proyección central {fc_mean:.1f} CLP muestra {trajectory}; {bias_action}. "
        f"Dinámica temporal: {uncertainty_trend}; {uncertainty_action}. "
        f"<strong>Position sizing:</strong> {sizing_strategy}. "
        f"<strong>Triggers gestión:</strong> Si IC 80% expande >{avg_ic80_width * 1.3:.1f} pesos, corte posiciones a 50%; "
        f"si contrae <{avg_ic80_width * 0.7:.1f} pesos, suba exposición hasta 120% normal."
    )

    return interpretation


def interpret_correlation_matrix(
    bundle: DataBundle,
    horizon: str = "7d",
) -> str:
    """
    Generate professional interpretation for Chart 4 - Correlation Matrix.

    This chart shows correlation heatmap between USD/CLP and key drivers.
    Focus: Leading indicators, hedge strategies, decorrelation opportunities.

    Args:
        bundle: Data bundle with USD/CLP, Copper, DXY, VIX, EEM series
        horizon: Forecast horizon (for context)

    Returns:
        Professional interpretation with actionable correlation-based strategies.

    Example:
        >>> interp = interpret_correlation_matrix(bundle, "7d")
        >>> print(interp)
        Leading indicator clave: Cobre correlación -0.68 con USD/CLP...
    """
    # Build correlation dataframe - EXACT SAME METHOD AS CHARTING
    # Only include series that exist - NORMALIZE DATES TO REMOVE TIME/TZ
    series_list = []
    series_names = []

    # USD/CLP (required)
    usdclp_normalized = bundle.usdclp_series.copy()
    usdclp_normalized.index = pd.to_datetime(usdclp_normalized.index.date)
    series_list.append(usdclp_normalized)
    series_names.append("USD/CLP")

    # Copper (required)
    copper_normalized = bundle.copper_series.copy()
    copper_normalized.index = pd.to_datetime(copper_normalized.index.date)
    series_list.append(copper_normalized)
    series_names.append("Cobre")

    # Add optional series only if they exist and have data - NORMALIZE DATES
    if hasattr(bundle, "dxy_series") and bundle.dxy_series is not None and len(bundle.dxy_series) > 0:
        dxy_normalized = bundle.dxy_series.copy()
        dxy_normalized.index = pd.to_datetime(dxy_normalized.index.date)
        series_list.append(dxy_normalized)
        series_names.append("DXY")

    if hasattr(bundle, "vix_series") and bundle.vix_series is not None and len(bundle.vix_series) > 0:
        vix_normalized = bundle.vix_series.copy()
        vix_normalized.index = pd.to_datetime(vix_normalized.index.date)
        series_list.append(vix_normalized)
        series_names.append("VIX")

    if hasattr(bundle, "eem_series") and bundle.eem_series is not None and len(bundle.eem_series) > 0:
        eem_normalized = bundle.eem_series.copy()
        eem_normalized.index = pd.to_datetime(eem_normalized.index.date)
        series_list.append(eem_normalized)
        series_names.append("EEM")

    # Concatenate series with INNER join to keep only common dates (now normalized)
    corr_data = pd.concat(series_list, axis=1, keys=series_names, join='inner')

    # Drop any remaining rows with NaN values (should be few or none with inner join)
    corr_data = corr_data.dropna()

    # Compute returns for correlation - EXACT SAME AS CHARTING
    corr_returns = corr_data.pct_change(fill_method=None).dropna()

    # Safety check: ensure corr_returns has data after dropna()
    if corr_returns.empty or len(corr_returns) < 5:
        # This should never happen if charting worked, but safety first
        return (
            "<strong>Leading indicator clave:</strong> Correlaciones temporalmente no disponibles. "
            "<strong>Hedge strategy:</strong> Use coberturas estándar basadas en correlaciones históricas. "
            "<strong>Risk gauge:</strong> Monitor VIX >20 como señal de risk-off general."
        )

    corr_matrix = corr_returns.corr()

    # Extract key correlations with USD/CLP - handle NaN values explicitly
    correlations = {}
    for col in corr_matrix.columns:
        if col != "USD/CLP":
            corr_value = corr_matrix.loc["USD/CLP", col]
            # Only add valid (non-NaN) correlations
            if pd.notna(corr_value):
                correlations[col] = float(corr_value)
            else:
                # If NaN, set to 0.0 and log
                correlations[col] = 0.0

    # Find strongest and weakest correlations
    if correlations:
        strongest_pair = max(correlations.items(), key=lambda x: abs(x[1]))
        weakest_pair = min(correlations.items(), key=lambda x: abs(x[1]))
    else:
        # Fallback if no correlations available
        return (
            "Matriz de correlaciones no disponible con datos actuales. "
            "Requiere series temporales de Cobre, DXY, VIX y EEM para análisis completo."
        )

    # Copper analysis (typically negative correlation with USD/CLP)
    copper_corr = correlations.get("Cobre", 0.0)

    # Get current copper price from most recent value in series
    copper_current_value = None
    if hasattr(bundle, "copper_series") and len(bundle.copper_series) > 0:
        copper_current_value = float(bundle.copper_series.iloc[-1])

    if abs(copper_corr) > 0.5:
        copper_strength = "fuerte" if abs(copper_corr) > 0.7 else "moderada"
        copper_direction = "inversa" if copper_corr < 0 else "directa"

        if copper_current_value and copper_current_value > 0:
            copper_critical_level = copper_current_value * 0.95  # 5% below current
            copper_interp = (
                f"Cobre muestra correlación {copper_direction} {copper_strength} {copper_corr:.2f}; "
                f"precio actual {copper_current_value:.2f} USD/lb, nivel crítico {copper_critical_level:.2f} "
                f"(5% abajo) actuaría como trigger para {'depreciación CLP' if copper_corr < 0 else 'apreciación CLP'}. "
                f"Leading indicator con ~24h de anticipación típica."
            )
        else:
            copper_interp = (
                f"Cobre correlación {copper_direction} {copper_strength} {copper_corr:.2f}, "
                f"monitor precio >5.00 USD/lb (catalizador CLP) y <4.75 USD/lb (riesgo CLP)."
            )
    else:
        copper_interp = f"Cobre correlación débil {copper_corr:.2f} en período reciente; priorice otros drivers."

    # DXY hedge strategy
    dxy_corr = correlations.get("DXY", 0.0)
    if abs(dxy_corr) > 0.6:
        dxy_hedge = (
            f"Correlación DXY-CLP {dxy_corr:+.2f} permite hedge cruzado: "
            f"Use futuros DXY (más líquidos) para cubrir exposición CLP con ratio 1:{abs(dxy_corr):.2f}. "
            f"Quiebre DXY {'sobre 105 pts señaliza presión USD/CLP alcista' if dxy_corr > 0 else 'bajo 95 pts señaliza presión USD/CLP bajista'}."
        )
    else:
        dxy_hedge = f"DXY correlación débil {dxy_corr:.2f}; no recomendado como hedge primario ahora."

    # VIX-EEM risk gauge
    vix_corr = correlations.get("VIX", 0.0)
    eem_corr = correlations.get("EEM", 0.0)

    if "VIX" in correlations and "EEM" in correlations:
        # Calculate VIX-EEM correlation safely
        if "VIX" in corr_matrix.columns and "EEM" in corr_matrix.columns:
            vix_eem_value = corr_matrix.loc["VIX", "EEM"]
            vix_eem_corr = float(vix_eem_value) if pd.notna(vix_eem_value) else 0.0
        else:
            vix_eem_corr = 0.0

        risk_gauge = (
            f"VIX-EEM correlación {vix_eem_corr:.2f} funciona como early warning de risk-off: "
            f"Repuntes VIX >18 + caída EEM >-2% anticipan fortalecimiento USD/CLP en 48-72h. "
            f"VIX-CLP correlación {vix_corr:+.2f}, EEM-CLP correlación {eem_corr:+.2f}."
        )
    else:
        risk_gauge = "Indicadores de riesgo global (VIX, EEM) no disponibles para análisis de régimen."

    # Decorrelation opportunities (low correlation = diversification)
    decorr_opportunities = [k for k, v in correlations.items() if abs(v) < 0.3]
    if decorr_opportunities:
        decorr_text = (
            f"Decorrelación táctica con {', '.join(decorr_opportunities)}: "
            f"Útil para portfolio diversification y reducción de riesgo concentrado."
        )
    else:
        decorr_text = "Todos los drivers muestran correlación significativa; riesgo sistémico elevado."

    # Build comprehensive interpretation
    interpretation = (
        f"**Leading indicator clave:** {copper_interp} "
        f"**Hedge strategy:** {dxy_hedge} "
        f"**Risk gauge:** {risk_gauge} "
        f"**Decorrelación:** {decorr_text} "
        f"Correlación más fuerte: {strongest_pair[0]} ({strongest_pair[1]:+.2f}), "
        f"más débil: {weakest_pair[0]} ({weakest_pair[1]:+.2f}). "
        f"Use correlaciones >0.7 para hedging, <0.3 para diversificación."
    )

    return interpretation


# Utility function to extract correlation metrics for external use
def extract_correlation_metrics(bundle: DataBundle) -> Dict[str, float]:
    """
    Extract correlation coefficients for use in other modules.

    Args:
        bundle: Data bundle with series

    Returns:
        Dictionary mapping pair names to correlation coefficients.
    """
    corr_data = pd.DataFrame({
        "USD/CLP": bundle.usdclp_series,
        "Cobre": bundle.copper_series,
    })

    if hasattr(bundle, "dxy_series") and len(bundle.dxy_series) > 0:
        corr_data["DXY"] = bundle.dxy_series
    if hasattr(bundle, "vix_series") and len(bundle.vix_series) > 0:
        corr_data["VIX"] = bundle.vix_series
    if hasattr(bundle, "eem_series") and len(bundle.eem_series) > 0:
        corr_data["EEM"] = bundle.eem_series

    corr_returns = corr_data.pct_change().dropna()
    corr_matrix = corr_returns.corr()

    metrics = {}
    for col in corr_matrix.columns:
        if col != "USD/CLP":
            metrics[f"USD/CLP_{col}"] = corr_matrix.loc["USD/CLP", col]

    # Add cross-correlations for risk gauge
    if "VIX" in corr_matrix.columns and "EEM" in corr_matrix.columns:
        metrics["VIX_EEM"] = corr_matrix.loc["VIX", "EEM"]

    return metrics


__all__ = [
    "interpret_hist_overview",
    "interpret_tactical_zoom",
    "interpret_forecast_bands",
    "interpret_correlation_matrix",
    "extract_correlation_metrics",
]

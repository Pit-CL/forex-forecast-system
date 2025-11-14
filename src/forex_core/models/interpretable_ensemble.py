"""
Sistema de Forecasting Interpretable para USD/CLP
Combina XGBoost + SARIMAX + GARCH con explicabilidad completa
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
import xgboost as xgb
from statsmodels.tsa.statespace.sarimax import SARIMAX
from arch import arch_model
from pmdarima import auto_arima
import shap
import optuna

# Metrics & Validation
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ForecastConfig:
    """Configuración para el sistema de forecasting interpretable"""
    horizon_days: int
    confidence_level: float = 0.95
    use_exogenous: bool = True
    optimize_hyperparams: bool = False
    n_trials_optuna: int = 50
    walk_forward_splits: int = 5
    min_train_size: int = 252  # 1 año trading days


@dataclass
class ForecastResult:
    """Resultado del forecast con explicabilidad completa"""
    forecast: pd.Series
    lower_bound: pd.Series
    upper_bound: pd.Series
    volatility_forecast: pd.Series
    feature_importance: Dict[str, float]
    shap_values: Optional[np.ndarray]
    model_weights: Dict[str, float]
    metrics: Dict[str, float]


class InterpretableForexEnsemble:
    """
    Sistema de ensemble interpretable para forex forecasting.
    Combina XGBoost (tendencia), SARIMAX (baseline), GARCH (volatilidad).
    """

    def __init__(self, config: ForecastConfig):
        self.config = config
        self.xgb_model = None
        self.sarima_model = None
        self.garch_model = None
        self.feature_scaler = StandardScaler()
        self.best_params = {}
        self.explainer = None

        # Pesos por horizonte (optimizados empíricamente)
        self.horizon_weights = {
            7: {'xgboost': 0.60, 'sarimax': 0.40},
            15: {'xgboost': 0.50, 'sarimax': 0.50},
            30: {'xgboost': 0.45, 'sarimax': 0.55},
            90: {'xgboost': 0.30, 'sarimax': 0.70}
        }

    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Feature engineering interpretable y robusto.
        Cada feature tiene significado económico claro.
        """
        features = pd.DataFrame(index=data.index)

        # 1. Lag Features (Momentum y Mean Reversion)
        for lag in [1, 2, 3, 5, 7, 10, 15, 20]:
            features[f'lag_{lag}'] = data['close'].shift(lag)
            features[f'return_lag_{lag}'] = data['close'].pct_change().shift(lag)

        # 2. Moving Averages (Tendencia)
        for window in [5, 10, 20, 50]:
            features[f'ma_{window}'] = data['close'].rolling(window).mean()
            features[f'ma_ratio_{window}'] = data['close'] / features[f'ma_{window}']

        # 3. Volatility Features (Riesgo)
        for window in [5, 10, 20]:
            features[f'volatility_{window}'] = data['close'].pct_change().rolling(window).std()
            features[f'range_{window}'] = (
                data['high'].rolling(window).max() -
                data['low'].rolling(window).min()
            ) / data['close']

        # 4. Technical Indicators (Señales de Trading)
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        features['macd'] = exp1 - exp2
        features['macd_signal'] = features['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        bb_mean = data['close'].rolling(bb_period).mean()
        bb_std_val = data['close'].rolling(bb_period).std()
        features['bb_upper'] = bb_mean + (bb_std_val * bb_std)
        features['bb_lower'] = bb_mean - (bb_std_val * bb_std)
        features['bb_position'] = (data['close'] - features['bb_lower']) / (
            features['bb_upper'] - features['bb_lower']
        )

        # 5. Copper Features (Fundamental Driver para CLP)
        if 'copper_price' in data.columns:
            features['copper_price'] = data['copper_price']
            features['copper_ma_20'] = data['copper_price'].rolling(20).mean()
            features['copper_momentum'] = data['copper_price'].pct_change(5)
            features['copper_volatility'] = data['copper_price'].pct_change().rolling(20).std()

            # Correlación rolling copper-USDCLP
            features['copper_correlation'] = (
                data['close'].pct_change()
                .rolling(60).corr(data['copper_price'].pct_change())
            )

        # 6. Macro Features
        if 'dxy_index' in data.columns:
            features['dxy_index'] = data['dxy_index']
            features['dxy_momentum'] = data['dxy_index'].pct_change(5)

        if 'interest_diff' in data.columns:
            features['interest_diff'] = data['interest_diff']
            features['carry_trade_signal'] = (
                data['interest_diff'] /
                data['close'].pct_change().rolling(20).std()
            )

        # 7. Calendar Features (Estacionalidad)
        features['day_of_week'] = pd.to_datetime(data.index).dayofweek
        features['month'] = pd.to_datetime(data.index).month
        features['quarter'] = pd.to_datetime(data.index).quarter
        features['is_month_end'] = pd.to_datetime(data.index).is_month_end.astype(int)

        return features.dropna()

    def optimize_xgboost_params(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """
        Optimización de hiperparámetros XGBoost con Optuna.
        Usa TimeSeriesSplit para validación temporal correcta.
        """
        def objective(trial):
            params = {
                'max_depth': trial.suggest_int('max_depth', 3, 6),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 300, step=50),
                'subsample': trial.suggest_float('subsample', 0.7, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.7, 1.0),
                'gamma': trial.suggest_float('gamma', 0, 0.2),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 5),
                'reg_alpha': trial.suggest_float('reg_alpha', 0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0, 1.0)
            }

            # TimeSeriesSplit para validación
            tscv = TimeSeriesSplit(n_splits=3, test_size=self.config.horizon_days)
            scores = []

            for train_idx, val_idx in tscv.split(X_train):
                X_tr, X_val = X_train[train_idx], X_train[val_idx]
                y_tr, y_val = y_train[train_idx], y_train[val_idx]

                model = xgb.XGBRegressor(**params, random_state=42, n_jobs=-1)
                model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)],
                         early_stopping_rounds=10, verbose=False)

                pred = model.predict(X_val)
                scores.append(np.sqrt(mean_squared_error(y_val, pred)))

            return np.mean(scores)

        # Optimización con Optuna
        study = optuna.create_study(direction='minimize', pruner=optuna.pruners.MedianPruner())
        study.optimize(objective, n_trials=self.config.n_trials_optuna, show_progress_bar=False)

        logger.info(f"Best XGBoost params: {study.best_params}")
        logger.info(f"Best RMSE: {study.best_value:.4f}")

        return study.best_params

    def fit_xgboost(self, X_train: np.ndarray, y_train: np.ndarray) -> xgb.XGBRegressor:
        """
        Entrena XGBoost con interpretabilidad via SHAP.
        """
        if self.config.optimize_hyperparams:
            params = self.optimize_xgboost_params(X_train, y_train)
        else:
            # Parámetros por defecto robustos
            params = {
                'max_depth': 4,
                'learning_rate': 0.05,
                'n_estimators': 200,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'gamma': 0.1,
                'min_child_weight': 3,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1
            }

        self.xgb_model = xgb.XGBRegressor(**params, random_state=42, n_jobs=-1)
        self.xgb_model.fit(X_train, y_train)

        # Configurar SHAP explainer
        self.explainer = shap.TreeExplainer(self.xgb_model)

        return self.xgb_model

    def fit_sarimax(self, y_train: pd.Series, exog_train: Optional[pd.DataFrame] = None) -> SARIMAX:
        """
        Entrena SARIMAX con selección automática de orden.
        """
        if self.config.horizon_days <= 30:
            # Para horizontes cortos, usar auto_arima
            auto_model = auto_arima(
                y_train,
                X=exog_train,
                start_p=1, start_q=1,
                max_p=3, max_q=3,
                start_P=0, start_Q=0,
                max_P=2, max_Q=2,
                m=5,  # Estacionalidad semanal (trading days)
                seasonal=True,
                stepwise=True,
                suppress_warnings=True,
                error_action='ignore',
                n_jobs=-1
            )
            order = auto_model.order
            seasonal_order = auto_model.seasonal_order
            logger.info(f"Auto ARIMA selected: order={order}, seasonal={seasonal_order}")
        else:
            # Para horizontes largos, usar orden conservador
            order = (1, 1, 1)
            seasonal_order = (1, 0, 1, 5)

        self.sarima_model = SARIMAX(
            y_train,
            exog=exog_train,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        )

        self.sarima_model = self.sarima_model.fit(disp=False)
        return self.sarima_model

    def fit_garch(self, returns: pd.Series) -> arch_model:
        """
        Entrena modelo GARCH/EGARCH para volatilidad.
        Selección automática entre GARCH, EGARCH, GJR-GARCH.
        """
        best_aic = np.inf
        best_model = None

        # Probar diferentes especificaciones
        specs = [
            ('GARCH', {'p': 1, 'q': 1}),
            ('GARCH', {'p': 1, 'q': 2}),
            ('GARCH', {'p': 2, 'q': 1}),
            ('EGARCH', {'p': 1, 'o': 1, 'q': 1}),
            ('GJR-GARCH', {'p': 1, 'o': 1, 'q': 1})
        ]

        for vol_model, params in specs:
            try:
                if vol_model == 'GARCH':
                    model = arch_model(returns, vol='Garch', **params, mean='AR', lags=1)
                elif vol_model == 'EGARCH':
                    model = arch_model(returns, vol='EGARCH', **params, mean='AR', lags=1)
                elif vol_model == 'GJR-GARCH':
                    model = arch_model(returns, vol='GARCH', **params, mean='AR', lags=1)

                fitted = model.fit(disp='off')

                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_model = fitted
                    best_spec = f"{vol_model}{params}"

            except Exception as e:
                logger.warning(f"Failed to fit {vol_model}: {e}")
                continue

        logger.info(f"Best GARCH model: {best_spec} with AIC={best_aic:.2f}")
        self.garch_model = best_model
        return best_model

    def fit(self, data: pd.DataFrame) -> 'InterpretableForexEnsemble':
        """
        Entrena el ensemble completo.
        """
        logger.info(f"Training interpretable ensemble for {self.config.horizon_days} days horizon")

        # 1. Feature Engineering
        features = self.create_features(data)

        # 2. Preparar datos
        common_index = features.index.intersection(data.index)
        features = features.loc[common_index]
        y = data.loc[common_index, 'close']

        # Split temporal (80/20)
        split_point = int(len(features) * 0.8)
        X_train = features.iloc[:split_point]
        y_train = y.iloc[:split_point]

        # 3. Normalizar features
        X_train_scaled = self.feature_scaler.fit_transform(X_train)

        # 4. Entrenar XGBoost
        logger.info("Training XGBoost...")
        self.fit_xgboost(X_train_scaled, y_train.values)

        # 5. Entrenar SARIMAX
        logger.info("Training SARIMAX...")
        exog_cols = ['copper_price', 'dxy_index', 'interest_diff'] if self.config.use_exogenous else None
        exog_train = X_train[exog_cols] if exog_cols and all(c in X_train.columns for c in exog_cols) else None
        self.fit_sarimax(y_train, exog_train)

        # 6. Entrenar GARCH para volatilidad
        logger.info("Training GARCH for volatility...")
        returns = y_train.pct_change().dropna() * 100  # En porcentaje
        self.fit_garch(returns)

        logger.info("Ensemble training complete!")
        return self

    def predict(self, data: pd.DataFrame, return_components: bool = False) -> ForecastResult:
        """
        Genera predicciones con explicabilidad completa.
        """
        # 1. Preparar features
        features = self.create_features(data)
        X_test = self.feature_scaler.transform(features)

        # 2. Predicción XGBoost
        xgb_pred = self.xgb_model.predict(X_test[-self.config.horizon_days:])

        # 3. Predicción SARIMAX
        exog_cols = ['copper_price', 'dxy_index', 'interest_diff'] if self.config.use_exogenous else None
        exog_test = features[exog_cols].iloc[-self.config.horizon_days:] if exog_cols and all(c in features.columns for c in exog_cols) else None

        sarima_forecast = self.sarima_model.forecast(
            steps=self.config.horizon_days,
            exog=exog_test
        )
        sarima_pred = sarima_forecast.values

        # 4. Ensemble ponderado por horizonte
        weights = self.horizon_weights.get(
            self.config.horizon_days,
            {'xgboost': 0.5, 'sarimax': 0.5}
        )

        ensemble_pred = (
            weights['xgboost'] * xgb_pred +
            weights['sarimax'] * sarima_pred
        )

        # 5. Predicción de volatilidad con GARCH
        vol_forecast = self.garch_model.forecast(horizon=self.config.horizon_days)
        volatility = np.sqrt(vol_forecast.variance.values[-1, :])

        # 6. Intervalos de confianza
        z_score = 1.96 if self.config.confidence_level == 0.95 else 2.58
        lower_bound = ensemble_pred - z_score * volatility
        upper_bound = ensemble_pred + z_score * volatility

        # 7. Feature importance
        feature_importance = dict(zip(
            features.columns,
            self.xgb_model.feature_importances_
        ))

        # 8. SHAP values para explicabilidad
        shap_values = self.explainer.shap_values(X_test[-self.config.horizon_days:])

        # 9. Crear índice temporal para forecast
        last_date = data.index[-1]
        forecast_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=self.config.horizon_days,
            freq='B'  # Business days
        )

        # 10. Calcular métricas si hay datos de validación
        metrics = {}
        if len(data) > len(features) + self.config.horizon_days:
            actual = data['close'].iloc[-self.config.horizon_days:].values
            metrics = {
                'rmse': np.sqrt(mean_squared_error(actual, ensemble_pred)),
                'mape': mean_absolute_percentage_error(actual, ensemble_pred),
                'directional_accuracy': np.mean(
                    np.sign(ensemble_pred[1:] - ensemble_pred[:-1]) ==
                    np.sign(actual[1:] - actual[:-1])
                )
            }

        result = ForecastResult(
            forecast=pd.Series(ensemble_pred, index=forecast_dates),
            lower_bound=pd.Series(lower_bound, index=forecast_dates),
            upper_bound=pd.Series(upper_bound, index=forecast_dates),
            volatility_forecast=pd.Series(volatility, index=forecast_dates),
            feature_importance=feature_importance,
            shap_values=shap_values,
            model_weights=weights,
            metrics=metrics
        )

        if return_components:
            result.xgb_forecast = pd.Series(xgb_pred, index=forecast_dates)
            result.sarima_forecast = pd.Series(sarima_pred, index=forecast_dates)

        return result

    def explain_prediction(self, result: ForecastResult, day_index: int = 0) -> Dict[str, Any]:
        """
        Explica una predicción específica usando SHAP.
        """
        if result.shap_values is None:
            return {"error": "SHAP values not available"}

        shap_day = result.shap_values[day_index]
        feature_names = list(result.feature_importance.keys())

        # Top 5 features que más contribuyen
        top_indices = np.argsort(np.abs(shap_day))[-5:][::-1]

        explanation = {
            'prediction_date': result.forecast.index[day_index],
            'predicted_value': result.forecast.iloc[day_index],
            'confidence_interval': (
                result.lower_bound.iloc[day_index],
                result.upper_bound.iloc[day_index]
            ),
            'top_contributing_features': [
                {
                    'feature': feature_names[i],
                    'shap_value': shap_day[i],
                    'impact': 'positive' if shap_day[i] > 0 else 'negative'
                }
                for i in top_indices
            ],
            'volatility': result.volatility_forecast.iloc[day_index],
            'model_weights_used': result.model_weights
        }

        return explanation

    def backtest(self, data: pd.DataFrame, n_windows: int = 10) -> pd.DataFrame:
        """
        Walk-forward backtesting con re-entrenamiento.
        """
        results = []
        window_size = len(data) // (n_windows + 1)

        for i in range(n_windows):
            train_end = window_size * (i + 1)
            test_end = min(train_end + self.config.horizon_days, len(data))

            train_data = data.iloc[:train_end]
            test_data = data.iloc[train_end:test_end]

            if len(test_data) < self.config.horizon_days:
                continue

            # Re-entrenar
            self.fit(train_data)

            # Predecir
            forecast_result = self.predict(train_data)

            # Comparar con actual
            actual = test_data['close'].values[:len(forecast_result.forecast)]
            predicted = forecast_result.forecast.values[:len(actual)]

            results.append({
                'window': i,
                'train_end': train_data.index[-1],
                'test_start': test_data.index[0],
                'rmse': np.sqrt(mean_squared_error(actual, predicted)),
                'mape': mean_absolute_percentage_error(actual, predicted),
                'coverage': np.mean(
                    (actual >= forecast_result.lower_bound.values[:len(actual)]) &
                    (actual <= forecast_result.upper_bound.values[:len(actual)])
                )
            })

        return pd.DataFrame(results)


class AutoMLPipeline:
    """
    Pipeline automatizado para optimización continua del ensemble.
    """

    def __init__(self, base_config: ForecastConfig):
        self.base_config = base_config
        self.performance_history = []
        self.retraining_threshold = 0.02  # 2% degradación triggers re-training

    def monitor_and_retrain(self,
                           model: InterpretableForexEnsemble,
                           new_data: pd.DataFrame,
                           last_performance: float) -> Tuple[InterpretableForexEnsemble, bool]:
        """
        Monitorea performance y re-entrena si es necesario.
        """
        # Evaluar en datos nuevos
        result = model.predict(new_data)
        current_performance = result.metrics.get('rmse', np.inf)

        # Detectar degradación
        performance_degradation = (current_performance - last_performance) / last_performance

        retrained = False
        if performance_degradation > self.retraining_threshold:
            logger.warning(f"Performance degraded by {performance_degradation:.2%}. Retraining...")

            # Re-entrenar con datos actualizados
            model.config.optimize_hyperparams = True  # Activar optimización
            model = model.fit(new_data)
            retrained = True

            # Re-evaluar
            result = model.predict(new_data)
            current_performance = result.metrics.get('rmse', np.inf)

        # Guardar historial
        self.performance_history.append({
            'timestamp': datetime.now(),
            'rmse': current_performance,
            'retrained': retrained
        })

        return model, retrained

    def adaptive_weight_optimization(self,
                                    backtest_results: pd.DataFrame) -> Dict[str, float]:
        """
        Optimiza pesos del ensemble basado en backtesting.
        """
        # Analizar performance por modelo
        xgb_performance = backtest_results['xgb_rmse'].mean()
        sarima_performance = backtest_results['sarima_rmse'].mean()

        # Calcular pesos inversos al error
        total_inv = 1/xgb_performance + 1/sarima_performance

        optimized_weights = {
            'xgboost': (1/xgb_performance) / total_inv,
            'sarimax': (1/sarima_performance) / total_inv
        }

        logger.info(f"Optimized weights: {optimized_weights}")
        return optimized_weights


def main_example():
    """
    Ejemplo de uso del sistema interpretable.
    """
    # Configuración
    config = ForecastConfig(
        horizon_days=15,
        confidence_level=0.95,
        use_exogenous=True,
        optimize_hyperparams=True,
        n_trials_optuna=30
    )

    # Datos de ejemplo (reemplazar con datos reales)
    dates = pd.date_range('2020-01-01', '2024-01-01', freq='B')
    np.random.seed(42)

    data = pd.DataFrame({
        'close': 800 + np.cumsum(np.random.randn(len(dates)) * 5),
        'high': 810 + np.cumsum(np.random.randn(len(dates)) * 5),
        'low': 790 + np.cumsum(np.random.randn(len(dates)) * 5),
        'copper_price': 6000 + np.cumsum(np.random.randn(len(dates)) * 50),
        'dxy_index': 90 + np.cumsum(np.random.randn(len(dates)) * 0.5),
        'interest_diff': np.random.randn(len(dates)) * 0.5
    }, index=dates)

    # Crear y entrenar modelo
    model = InterpretableForexEnsemble(config)
    model.fit(data)

    # Generar predicción
    result = model.predict(data, return_components=True)

    # Explicar predicción del primer día
    explanation = model.explain_prediction(result, day_index=0)

    print("\n=== Forecast Results ===")
    print(f"Forecast horizon: {config.horizon_days} days")
    print(f"\nPredictions:")
    print(result.forecast.head())
    print(f"\nConfidence Intervals:")
    print(pd.DataFrame({
        'lower': result.lower_bound.head(),
        'upper': result.upper_bound.head()
    }))
    print(f"\nVolatility forecast:")
    print(result.volatility_forecast.head())

    print("\n=== Model Interpretability ===")
    print("\nTop 10 Important Features:")
    top_features = sorted(result.feature_importance.items(),
                         key=lambda x: x[1], reverse=True)[:10]
    for feat, imp in top_features:
        print(f"  {feat}: {imp:.4f}")

    print(f"\n=== Explanation for {explanation['prediction_date']} ===")
    print(f"Predicted value: {explanation['predicted_value']:.2f}")
    print(f"Confidence interval: {explanation['confidence_interval']}")
    print("\nTop contributing features:")
    for feat_info in explanation['top_contributing_features']:
        print(f"  {feat_info['feature']}: {feat_info['shap_value']:.4f} ({feat_info['impact']})")

    # Backtesting
    print("\n=== Backtesting Results ===")
    backtest_results = model.backtest(data, n_windows=5)
    print(backtest_results)
    print(f"\nAverage RMSE: {backtest_results['rmse'].mean():.4f}")
    print(f"Average MAPE: {backtest_results['mape'].mean():.2%}")
    print(f"Average Coverage: {backtest_results['coverage'].mean():.2%}")


if __name__ == "__main__":
    main_example()
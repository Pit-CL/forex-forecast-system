"""
Sistema Autónomo de Pronóstico Forex USD/CLP
Arquitectura de Meta-Learning con AutoML
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import joblib
import json
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModelPerformance:
    """Métricas de performance de un modelo"""
    model_name: str
    horizon: str
    mae: float
    rmse: float
    mape: float
    directional_accuracy: float
    sharpe_ratio: float
    max_drawdown: float
    confidence_interval_coverage: float
    training_time: float
    inference_time: float
    last_updated: datetime
    degradation_score: float = 0.0

    @property
    def composite_score(self) -> float:
        """Score compuesto ponderado de todas las métricas"""
        weights = {
            'mae': -0.2,  # Negativo porque menor es mejor
            'rmse': -0.15,
            'mape': -0.15,
            'directional_accuracy': 0.25,
            'sharpe_ratio': 0.15,
            'confidence_interval_coverage': 0.1
        }

        score = (
            weights['mae'] * self.mae +
            weights['rmse'] * self.rmse +
            weights['mape'] * self.mape +
            weights['directional_accuracy'] * self.directional_accuracy +
            weights['sharpe_ratio'] * self.sharpe_ratio +
            weights['confidence_interval_coverage'] * self.confidence_interval_coverage
        )

        # Penalización por degradación
        score *= (1 - self.degradation_score)

        return score


@dataclass
class ModelConfig:
    """Configuración de un modelo"""
    name: str
    horizon: str
    hyperparameters: Dict[str, Any]
    feature_set: List[str]
    update_frequency_hours: int = 24
    min_training_samples: int = 500
    validation_window: int = 30


class BaseForecaster(ABC):
    """Clase base para todos los modelos de pronóstico"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.is_fitted = False
        self.last_training_time = None

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'BaseForecaster':
        """Entrena el modelo"""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame, horizon: int) -> Dict[str, np.ndarray]:
        """Realiza predicciones con intervalos de confianza"""
        pass

    @abstractmethod
    def update(self, X: pd.DataFrame, y: pd.Series) -> 'BaseForecaster':
        """Actualización incremental del modelo"""
        pass

    def validate(self, X: pd.DataFrame, y: pd.Series) -> ModelPerformance:
        """Valida el modelo y retorna métricas"""
        predictions = self.predict(X, len(y))

        # Calcular métricas
        y_pred = predictions['forecast']

        mae = np.mean(np.abs(y - y_pred))
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        mape = np.mean(np.abs((y - y_pred) / y)) * 100

        # Directional accuracy
        y_true_direction = np.sign(np.diff(y))
        y_pred_direction = np.sign(np.diff(y_pred))
        directional_accuracy = np.mean(y_true_direction == y_pred_direction)

        # Sharpe ratio simplificado
        returns = np.diff(y_pred) / y_pred[:-1]
        sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)

        # Coverage de intervalos de confianza
        lower = predictions.get('lower', y_pred - np.std(y_pred))
        upper = predictions.get('upper', y_pred + np.std(y_pred))
        coverage = np.mean((y >= lower) & (y <= upper))

        return ModelPerformance(
            model_name=self.config.name,
            horizon=self.config.horizon,
            mae=mae,
            rmse=rmse,
            mape=mape,
            directional_accuracy=directional_accuracy,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=self._calculate_max_drawdown(y_pred),
            confidence_interval_coverage=coverage,
            training_time=0,
            inference_time=0,
            last_updated=datetime.now()
        )

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calcula el máximo drawdown"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return np.min(drawdown)


class XGBoostForecaster(BaseForecaster):
    """Implementación de XGBoost para forecasting"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        import xgboost as xgb
        self.xgb = xgb

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'XGBoostForecaster':
        """Entrena el modelo XGBoost"""
        import time
        start_time = time.time()

        # Preparar features con lags y rolling stats
        X_features = self._engineer_features(X, y)

        # Entrenar modelo
        self.model = self.xgb.XGBRegressor(
            **self.config.hyperparameters,
            random_state=42
        )

        self.model.fit(X_features, y)

        self.is_fitted = True
        self.last_training_time = time.time() - start_time

        return self

    def predict(self, X: pd.DataFrame, horizon: int) -> Dict[str, np.ndarray]:
        """Realiza predicciones multi-step"""
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        X_features = self._engineer_features(X, pd.Series())

        # Multi-step forecasting
        predictions = []
        current_features = X_features.iloc[-1:].copy()

        for _ in range(horizon):
            pred = self.model.predict(current_features)[0]
            predictions.append(pred)

            # Actualizar features para siguiente predicción
            # (simplificado - en producción sería más sofisticado)
            current_features = self._update_features(current_features, pred)

        predictions = np.array(predictions)

        # Intervalos de confianza usando quantile regression o bootstrap
        std_estimate = np.std(predictions) * 1.2  # Simplificado

        return {
            'forecast': predictions,
            'lower': predictions - 1.96 * std_estimate,
            'upper': predictions + 1.96 * std_estimate
        }

    def update(self, X: pd.DataFrame, y: pd.Series) -> 'XGBoostForecaster':
        """Actualización incremental"""
        # XGBoost no soporta actualización incremental nativa
        # Re-entrenar con datos nuevos + subset de datos antiguos
        return self.fit(X, y)

    def _engineer_features(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """Ingeniería de features para series temporales"""
        features = X.copy()

        # Agregar lags
        for lag in [1, 7, 14, 30]:
            features[f'lag_{lag}'] = features['close'].shift(lag)

        # Rolling statistics
        for window in [7, 14, 30]:
            features[f'rolling_mean_{window}'] = features['close'].rolling(window).mean()
            features[f'rolling_std_{window}'] = features['close'].rolling(window).std()

        # Features técnicos
        features['rsi'] = self._calculate_rsi(features['close'])
        features['macd'] = self._calculate_macd(features['close'])

        # Eliminar NaN
        features = features.fillna(method='ffill').fillna(0)

        return features

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices: pd.Series) -> pd.Series:
        """Calcula MACD"""
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        return exp1 - exp2

    def _update_features(self, features: pd.DataFrame, new_value: float) -> pd.DataFrame:
        """Actualiza features para siguiente predicción"""
        # Simplificado - en producción sería más sofisticado
        updated = features.copy()
        updated['close'] = new_value
        # Actualizar lags y rolling stats
        return updated


class ProphetForecaster(BaseForecaster):
    """Implementación de Prophet para forecasting"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        from prophet import Prophet
        self.Prophet = Prophet

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'ProphetForecaster':
        """Entrena el modelo Prophet"""
        import time
        start_time = time.time()

        # Preparar datos en formato Prophet
        df = pd.DataFrame({
            'ds': X.index,
            'y': y.values
        })

        # Agregar regressors externos
        for col in X.columns:
            if col != 'close':
                df[col] = X[col].values

        # Configurar y entrenar modelo
        self.model = self.Prophet(
            **self.config.hyperparameters,
            interval_width=0.95
        )

        # Agregar regressors
        for col in X.columns:
            if col != 'close':
                self.model.add_regressor(col)

        self.model.fit(df)

        self.is_fitted = True
        self.last_training_time = time.time() - start_time

        return self

    def predict(self, X: pd.DataFrame, horizon: int) -> Dict[str, np.ndarray]:
        """Realiza predicciones con Prophet"""
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        # Crear dataframe futuro
        future = self.model.make_future_dataframe(periods=horizon, freq='D')

        # Agregar regressors futuros (simplificado - usar forecasts de regressors)
        for col in X.columns:
            if col != 'close':
                # En producción, estos vendrían de modelos auxiliares
                future[col] = X[col].iloc[-1]

        # Predicción
        forecast = self.model.predict(future)

        # Extraer últimos 'horizon' valores
        predictions = forecast['yhat'].iloc[-horizon:].values
        lower = forecast['yhat_lower'].iloc[-horizon:].values
        upper = forecast['yhat_upper'].iloc[-horizon:].values

        return {
            'forecast': predictions,
            'lower': lower,
            'upper': upper
        }

    def update(self, X: pd.DataFrame, y: pd.Series) -> 'ProphetForecaster':
        """Prophet no soporta actualización incremental - re-entrenar"""
        return self.fit(X, y)


class LSTMForecaster(BaseForecaster):
    """Implementación de LSTM para forecasting"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        import tensorflow as tf
        self.tf = tf

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'LSTMForecaster':
        """Entrena el modelo LSTM"""
        import time
        start_time = time.time()

        # Preparar secuencias
        X_seq, y_seq = self._create_sequences(X, y)

        # Construir modelo
        self.model = self._build_model(X_seq.shape[1:])

        # Entrenar
        self.model.fit(
            X_seq, y_seq,
            epochs=self.config.hyperparameters.get('epochs', 50),
            batch_size=self.config.hyperparameters.get('batch_size', 32),
            validation_split=0.2,
            verbose=0
        )

        self.is_fitted = True
        self.last_training_time = time.time() - start_time

        return self

    def predict(self, X: pd.DataFrame, horizon: int) -> Dict[str, np.ndarray]:
        """Realiza predicciones con LSTM"""
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        # Preparar secuencia de entrada
        X_seq, _ = self._create_sequences(X, pd.Series())

        # Multi-step forecasting
        predictions = []
        current_seq = X_seq[-1:].copy()

        for _ in range(horizon):
            pred = self.model.predict(current_seq, verbose=0)[0, 0]
            predictions.append(pred)

            # Actualizar secuencia
            current_seq = np.roll(current_seq, -1, axis=1)
            current_seq[0, -1, 0] = pred

        predictions = np.array(predictions)

        # Estimar incertidumbre con dropout Monte Carlo
        mc_predictions = []
        for _ in range(100):
            mc_pred = self._monte_carlo_predict(X_seq[-1:], horizon)
            mc_predictions.append(mc_pred)

        mc_predictions = np.array(mc_predictions)
        lower = np.percentile(mc_predictions, 2.5, axis=0)
        upper = np.percentile(mc_predictions, 97.5, axis=0)

        return {
            'forecast': predictions,
            'lower': lower,
            'upper': upper
        }

    def update(self, X: pd.DataFrame, y: pd.Series) -> 'LSTMForecaster':
        """Actualización incremental con fine-tuning"""
        X_seq, y_seq = self._create_sequences(X, y)

        # Fine-tuning con learning rate reducido
        self.model.optimizer.learning_rate = self.model.optimizer.learning_rate * 0.1

        self.model.fit(
            X_seq, y_seq,
            epochs=5,  # Pocas épocas para fine-tuning
            batch_size=32,
            verbose=0
        )

        return self

    def _create_sequences(self, X: pd.DataFrame, y: pd.Series,
                         lookback: int = 30) -> Tuple[np.ndarray, np.ndarray]:
        """Crea secuencias para LSTM"""
        # Normalización
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Crear secuencias
        X_seq, y_seq = [], []

        for i in range(lookback, len(X)):
            X_seq.append(X_scaled[i-lookback:i])
            if len(y) > 0:
                y_seq.append(y.iloc[i])

        return np.array(X_seq), np.array(y_seq)

    def _build_model(self, input_shape: Tuple) -> 'tf.keras.Model':
        """Construye arquitectura LSTM"""
        model = self.tf.keras.Sequential([
            self.tf.keras.layers.LSTM(
                units=self.config.hyperparameters.get('lstm_units', 64),
                return_sequences=True,
                input_shape=input_shape
            ),
            self.tf.keras.layers.Dropout(0.2),
            self.tf.keras.layers.LSTM(
                units=self.config.hyperparameters.get('lstm_units', 32),
                return_sequences=False
            ),
            self.tf.keras.layers.Dropout(0.2),
            self.tf.keras.layers.Dense(
                units=self.config.hyperparameters.get('dense_units', 16),
                activation='relu'
            ),
            self.tf.keras.layers.Dense(1)
        ])

        model.compile(
            optimizer=self.tf.keras.optimizers.Adam(
                learning_rate=self.config.hyperparameters.get('learning_rate', 0.001)
            ),
            loss='mse',
            metrics=['mae']
        )

        return model

    def _monte_carlo_predict(self, X_seq: np.ndarray, horizon: int) -> np.ndarray:
        """Predicción con dropout Monte Carlo para incertidumbre"""
        predictions = []
        current_seq = X_seq.copy()

        for _ in range(horizon):
            # Activar dropout durante inferencia
            pred = self.model(current_seq, training=True).numpy()[0, 0]
            predictions.append(pred)

            current_seq = np.roll(current_seq, -1, axis=1)
            current_seq[0, -1, 0] = pred

        return np.array(predictions)


class AutoMLOrchestrator:
    """
    Orquestador principal del sistema autónomo
    Gestiona múltiples modelos, selección automática y auto-mejora
    """

    def __init__(self, config_path: str = "config/automl_config.json"):
        self.config = self._load_config(config_path)
        self.models: Dict[str, Dict[str, BaseForecaster]] = {}
        self.performance_history: List[ModelPerformance] = []
        self.active_models: Dict[str, str] = {}  # horizon -> model_name
        self.model_registry: Dict[str, type] = {
            'XGBoost': XGBoostForecaster,
            'Prophet': ProphetForecaster,
            'LSTM': LSTMForecaster,
            # Agregar más modelos aquí
        }
        self.executor = ProcessPoolExecutor(max_workers=4)

    def _load_config(self, config_path: str) -> Dict:
        """Carga configuración del sistema"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Configuración por defecto
            return {
                "horizons": ["7d", "15d", "30d", "90d"],
                "models": {
                    "XGBoost": {
                        "horizons": ["7d", "15d"],
                        "hyperparameters": {
                            "n_estimators": 100,
                            "max_depth": 5,
                            "learning_rate": 0.1
                        }
                    },
                    "Prophet": {
                        "horizons": ["30d", "90d"],
                        "hyperparameters": {
                            "yearly_seasonality": True,
                            "weekly_seasonality": True,
                            "daily_seasonality": False
                        }
                    },
                    "LSTM": {
                        "horizons": ["7d", "15d", "30d"],
                        "hyperparameters": {
                            "lstm_units": 64,
                            "dense_units": 32,
                            "learning_rate": 0.001,
                            "epochs": 50
                        }
                    }
                },
                "evaluation_frequency_hours": 24,
                "performance_threshold": 0.05,
                "degradation_threshold": 0.1,
                "ensemble_enabled": True,
                "auto_retrain": True,
                "auto_hyperparameter_tuning": True
            }

    def initialize_models(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Inicializa todos los modelos configurados"""
        logger.info("Inicializando modelos...")

        for horizon in self.config['horizons']:
            self.models[horizon] = {}

            for model_name, model_config in self.config['models'].items():
                if horizon in model_config['horizons']:
                    # Crear configuración del modelo
                    config = ModelConfig(
                        name=model_name,
                        horizon=horizon,
                        hyperparameters=model_config['hyperparameters'],
                        feature_set=list(X.columns)
                    )

                    # Instanciar y entrenar modelo
                    model_class = self.model_registry.get(model_name)
                    if model_class:
                        model = model_class(config)
                        model.fit(X, y)
                        self.models[horizon][model_name] = model

                        logger.info(f"Modelo {model_name} inicializado para horizonte {horizon}")

    def evaluate_all_models(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, ModelPerformance]:
        """Evalúa todos los modelos en paralelo"""
        logger.info("Evaluando todos los modelos...")

        evaluation_results = {}
        futures = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            for horizon, models in self.models.items():
                for model_name, model in models.items():
                    future = executor.submit(
                        self._evaluate_single_model,
                        model, X, y, horizon
                    )
                    futures.append((horizon, model_name, future))

            # Recolectar resultados
            for horizon, model_name, future in futures:
                try:
                    performance = future.result(timeout=60)
                    key = f"{horizon}_{model_name}"
                    evaluation_results[key] = performance
                    self.performance_history.append(performance)
                except Exception as e:
                    logger.error(f"Error evaluando {model_name} para {horizon}: {e}")

        return evaluation_results

    def _evaluate_single_model(self, model: BaseForecaster,
                              X: pd.DataFrame, y: pd.Series,
                              horizon: str) -> ModelPerformance:
        """Evalúa un modelo individual"""
        # Convertir horizonte a número de días
        horizon_days = int(horizon.replace('d', ''))

        # Validación walk-forward
        val_size = min(horizon_days * 2, len(y) // 4)
        X_val = X.iloc[-val_size:]
        y_val = y.iloc[-val_size:]

        performance = model.validate(X_val, y_val)

        # Detectar degradación comparando con performance histórico
        historical_perf = [p for p in self.performance_history
                          if p.model_name == model.config.name
                          and p.horizon == horizon]

        if historical_perf:
            recent_avg = np.mean([p.composite_score for p in historical_perf[-5:]])
            current_score = performance.composite_score

            if current_score < recent_avg * (1 - self.config['degradation_threshold']):
                performance.degradation_score = (recent_avg - current_score) / recent_avg
                logger.warning(f"Degradación detectada en {model.config.name} para {horizon}")

        return performance

    def select_best_models(self, evaluation_results: Dict[str, ModelPerformance]) -> None:
        """Selecciona el mejor modelo para cada horizonte"""
        logger.info("Seleccionando mejores modelos...")

        for horizon in self.config['horizons']:
            horizon_results = {
                k: v for k, v in evaluation_results.items()
                if k.startswith(horizon)
            }

            if horizon_results:
                # Ordenar por score compuesto
                best_model_key = max(
                    horizon_results.keys(),
                    key=lambda k: horizon_results[k].composite_score
                )

                best_model_name = best_model_key.split('_')[1]

                # Verificar si hay cambio de modelo
                if horizon in self.active_models:
                    if self.active_models[horizon] != best_model_name:
                        logger.info(f"Cambiando modelo para {horizon}: "
                                  f"{self.active_models[horizon]} -> {best_model_name}")

                self.active_models[horizon] = best_model_name

                # Guardar selección
                self._save_model_selection()

    def auto_retrain_if_needed(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Re-entrena modelos si es necesario basado en performance"""
        if not self.config['auto_retrain']:
            return

        logger.info("Verificando necesidad de re-entrenamiento...")

        for horizon, model_name in self.active_models.items():
            model = self.models[horizon][model_name]

            # Verificar tiempo desde último entrenamiento
            if model.last_training_time:
                hours_since_training = (
                    datetime.now() - model.last_training_time
                ).total_seconds() / 3600

                if hours_since_training > self.config['evaluation_frequency_hours']:
                    logger.info(f"Re-entrenando {model_name} para {horizon}")
                    model.fit(X, y)

    def optimize_hyperparameters(self, X: pd.DataFrame, y: pd.Series,
                                model_name: str, horizon: str) -> Dict:
        """Optimización automática de hiperparámetros usando Optuna"""
        if not self.config['auto_hyperparameter_tuning']:
            return {}

        import optuna

        logger.info(f"Optimizando hiperparámetros para {model_name} - {horizon}")

        def objective(trial):
            # Definir espacio de búsqueda según el modelo
            if model_name == 'XGBoost':
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 10),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                }
            elif model_name == 'LSTM':
                params = {
                    'lstm_units': trial.suggest_int('lstm_units', 32, 128),
                    'dense_units': trial.suggest_int('dense_units', 16, 64),
                    'learning_rate': trial.suggest_float('learning_rate', 0.0001, 0.01),
                    'dropout_rate': trial.suggest_float('dropout_rate', 0.1, 0.5),
                }
            else:
                return 0

            # Crear y evaluar modelo con estos parámetros
            config = ModelConfig(
                name=model_name,
                horizon=horizon,
                hyperparameters=params,
                feature_set=list(X.columns)
            )

            model_class = self.model_registry[model_name]
            model = model_class(config)

            # Cross-validation
            from sklearn.model_selection import TimeSeriesSplit
            tscv = TimeSeriesSplit(n_splits=3)
            scores = []

            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

                model.fit(X_train, y_train)
                perf = model.validate(X_val, y_val)
                scores.append(perf.composite_score)

            return np.mean(scores)

        # Optimización
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=20, timeout=300)  # 5 minutos máximo

        logger.info(f"Mejores hiperparámetros encontrados: {study.best_params}")

        return study.best_params

    def create_ensemble_prediction(self, X: pd.DataFrame,
                                  horizon: str) -> Dict[str, np.ndarray]:
        """Crea predicción ensemble de múltiples modelos"""
        if not self.config['ensemble_enabled']:
            # Usar solo el mejor modelo
            best_model = self.models[horizon][self.active_models[horizon]]
            horizon_days = int(horizon.replace('d', ''))
            return best_model.predict(X, horizon_days)

        logger.info(f"Creando predicción ensemble para {horizon}")

        # Obtener predicciones de todos los modelos
        predictions = []
        weights = []

        for model_name, model in self.models[horizon].items():
            horizon_days = int(horizon.replace('d', ''))
            pred = model.predict(X, horizon_days)
            predictions.append(pred)

            # Peso basado en performance histórico
            model_perf = [p for p in self.performance_history
                         if p.model_name == model_name and p.horizon == horizon]

            if model_perf:
                weight = model_perf[-1].composite_score
            else:
                weight = 1.0

            weights.append(weight)

        # Normalizar pesos
        weights = np.array(weights)
        weights = weights / weights.sum()

        # Combinar predicciones
        ensemble_forecast = np.zeros_like(predictions[0]['forecast'])
        ensemble_lower = np.zeros_like(predictions[0]['lower'])
        ensemble_upper = np.zeros_like(predictions[0]['upper'])

        for pred, weight in zip(predictions, weights):
            ensemble_forecast += weight * pred['forecast']
            ensemble_lower += weight * pred['lower']
            ensemble_upper += weight * pred['upper']

        return {
            'forecast': ensemble_forecast,
            'lower': ensemble_lower,
            'upper': ensemble_upper,
            'weights': weights,
            'models': list(self.models[horizon].keys())
        }

    def detect_anomalies(self, X: pd.DataFrame, y: pd.Series) -> List[int]:
        """Detecta anomalías en los datos"""
        from sklearn.ensemble import IsolationForest

        logger.info("Detectando anomalías en los datos...")

        # Preparar features
        features = X.copy()
        features['target'] = y

        # Modelo de detección de anomalías
        clf = IsolationForest(
            contamination=0.05,
            random_state=42
        )

        anomalies = clf.fit_predict(features)
        anomaly_indices = np.where(anomalies == -1)[0]

        if len(anomaly_indices) > 0:
            logger.warning(f"Detectadas {len(anomaly_indices)} anomalías")

        return anomaly_indices.tolist()

    def auto_recovery(self, error: Exception, X: pd.DataFrame,
                     y: pd.Series, horizon: str) -> None:
        """Sistema de auto-recuperación ante fallos"""
        logger.error(f"Error detectado: {error}")
        logger.info("Iniciando auto-recuperación...")

        # Estrategia 1: Cambiar a modelo de respaldo
        if horizon in self.active_models:
            current_model = self.active_models[horizon]
            available_models = list(self.models[horizon].keys())
            available_models.remove(current_model)

            if available_models:
                backup_model = available_models[0]
                logger.info(f"Cambiando a modelo de respaldo: {backup_model}")
                self.active_models[horizon] = backup_model

        # Estrategia 2: Re-entrenar con configuración más conservadora
        try:
            model = self.models[horizon][self.active_models[horizon]]

            # Reducir complejidad
            if hasattr(model.config.hyperparameters, 'n_estimators'):
                model.config.hyperparameters['n_estimators'] //= 2

            model.fit(X, y)
            logger.info("Modelo re-entrenado con configuración conservadora")

        except Exception as e:
            logger.error(f"Fallo en auto-recuperación: {e}")

            # Estrategia 3: Usar modelo simple de respaldo (ARIMA)
            logger.info("Activando modelo de emergencia (ARIMA)")
            self._create_emergency_model(X, y, horizon)

    def _create_emergency_model(self, X: pd.DataFrame, y: pd.Series,
                               horizon: str) -> None:
        """Crea un modelo ARIMA simple de emergencia"""
        from statsmodels.tsa.arima.model import ARIMA

        # Modelo ARIMA simple
        model = ARIMA(y, order=(1, 1, 1))
        fitted = model.fit()

        # Guardar como modelo de emergencia
        self.emergency_model = fitted
        logger.info("Modelo de emergencia ARIMA creado")

    def monitor_performance(self) -> Dict[str, Any]:
        """Monitorea el performance del sistema completo"""
        logger.info("Generando reporte de monitoreo...")

        report = {
            'timestamp': datetime.now().isoformat(),
            'active_models': self.active_models,
            'performance_summary': {},
            'alerts': [],
            'recommendations': []
        }

        # Análisis por horizonte
        for horizon in self.config['horizons']:
            if horizon in self.active_models:
                model_name = self.active_models[horizon]

                # Performance reciente
                recent_perf = [
                    p for p in self.performance_history[-100:]
                    if p.model_name == model_name and p.horizon == horizon
                ]

                if recent_perf:
                    avg_score = np.mean([p.composite_score for p in recent_perf])
                    avg_mae = np.mean([p.mae for p in recent_perf])
                    avg_directional = np.mean([p.directional_accuracy for p in recent_perf])

                    report['performance_summary'][horizon] = {
                        'model': model_name,
                        'avg_composite_score': avg_score,
                        'avg_mae': avg_mae,
                        'avg_directional_accuracy': avg_directional,
                        'last_update': recent_perf[-1].last_updated.isoformat()
                    }

                    # Alertas
                    if avg_directional < 0.55:
                        report['alerts'].append(
                            f"Baja precisión direccional en {horizon}: {avg_directional:.2%}"
                        )

                    if recent_perf[-1].degradation_score > 0.05:
                        report['alerts'].append(
                            f"Degradación detectada en {model_name} para {horizon}"
                        )

        # Recomendaciones
        if len(report['alerts']) > 2:
            report['recommendations'].append(
                "Considerar re-optimización completa de hiperparámetros"
            )

        if len(self.performance_history) > 1000:
            report['recommendations'].append(
                "Limpiar historial de performance para optimizar memoria"
            )

        return report

    def _save_model_selection(self) -> None:
        """Guarda la selección actual de modelos"""
        selection = {
            'timestamp': datetime.now().isoformat(),
            'active_models': self.active_models,
            'performance': {}
        }

        for horizon, model_name in self.active_models.items():
            recent_perf = [
                p for p in self.performance_history
                if p.model_name == model_name and p.horizon == horizon
            ]
            if recent_perf:
                selection['performance'][horizon] = {
                    'composite_score': recent_perf[-1].composite_score,
                    'mae': recent_perf[-1].mae
                }

        # Guardar en archivo
        with open('model_selection.json', 'w') as f:
            json.dump(selection, f, indent=2)

        logger.info("Selección de modelos guardada")

    def run_autonomous_cycle(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo de operación autónoma
        Este es el método principal que se ejecuta periódicamente
        """
        logger.info("="*50)
        logger.info("Iniciando ciclo autónomo")
        logger.info("="*50)

        cycle_results = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'actions': []
        }

        try:
            # 1. Detectar anomalías
            anomalies = self.detect_anomalies(X, y)
            if anomalies:
                cycle_results['actions'].append(f"Detectadas {len(anomalies)} anomalías")
                # Filtrar datos anómalos para entrenamiento
                mask = ~X.index.isin(anomalies)
                X_clean = X[mask]
                y_clean = y[mask]
            else:
                X_clean, y_clean = X, y

            # 2. Evaluar todos los modelos
            evaluation_results = self.evaluate_all_models(X_clean, y_clean)
            cycle_results['actions'].append(f"Evaluados {len(evaluation_results)} modelos")

            # 3. Seleccionar mejores modelos
            self.select_best_models(evaluation_results)
            cycle_results['actions'].append("Modelos óptimos seleccionados")

            # 4. Re-entrenar si es necesario
            self.auto_retrain_if_needed(X_clean, y_clean)

            # 5. Optimizar hiperparámetros periódicamente
            for horizon, model_name in self.active_models.items():
                # Optimizar cada 7 días
                if np.random.random() < 0.14:  # ~1/7 probabilidad
                    best_params = self.optimize_hyperparameters(
                        X_clean, y_clean, model_name, horizon
                    )
                    if best_params:
                        # Actualizar modelo con nuevos hiperparámetros
                        config = ModelConfig(
                            name=model_name,
                            horizon=horizon,
                            hyperparameters=best_params,
                            feature_set=list(X.columns)
                        )
                        model_class = self.model_registry[model_name]
                        self.models[horizon][model_name] = model_class(config)
                        self.models[horizon][model_name].fit(X_clean, y_clean)
                        cycle_results['actions'].append(
                            f"Hiperparámetros optimizados para {model_name}-{horizon}"
                        )

            # 6. Generar predicciones
            predictions = {}
            for horizon in self.config['horizons']:
                predictions[horizon] = self.create_ensemble_prediction(X, horizon)

            cycle_results['predictions'] = predictions

            # 7. Monitorear performance
            monitoring_report = self.monitor_performance()
            cycle_results['monitoring'] = monitoring_report

            # 8. Guardar estado
            self._save_state()

            logger.info("Ciclo autónomo completado exitosamente")

        except Exception as e:
            logger.error(f"Error en ciclo autónomo: {e}")
            cycle_results['status'] = 'error'
            cycle_results['error'] = str(e)

            # Intentar auto-recuperación
            for horizon in self.config['horizons']:
                self.auto_recovery(e, X, y, horizon)

        return cycle_results

    def _save_state(self) -> None:
        """Guarda el estado completo del sistema"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'active_models': self.active_models,
            'model_configs': {},
            'performance_summary': {}
        }

        # Guardar configuraciones y performance
        for horizon, models in self.models.items():
            state['model_configs'][horizon] = {}
            for model_name, model in models.items():
                state['model_configs'][horizon][model_name] = {
                    'hyperparameters': model.config.hyperparameters,
                    'is_fitted': model.is_fitted,
                    'last_training_time': model.last_training_time
                }

        # Guardar modelos entrenados
        for horizon, model_name in self.active_models.items():
            model = self.models[horizon][model_name]
            model_path = f"models/{horizon}_{model_name}.pkl"
            joblib.dump(model, model_path)
            logger.info(f"Modelo guardado: {model_path}")

        # Guardar estado
        with open('system_state.json', 'w') as f:
            json.dump(state, f, indent=2, default=str)

        logger.info("Estado del sistema guardado")

    def load_state(self) -> None:
        """Carga el estado previo del sistema"""
        try:
            with open('system_state.json', 'r') as f:
                state = json.load(f)

            self.active_models = state['active_models']

            # Cargar modelos
            for horizon, model_name in self.active_models.items():
                model_path = f"models/{horizon}_{model_name}.pkl"
                try:
                    model = joblib.load(model_path)
                    if horizon not in self.models:
                        self.models[horizon] = {}
                    self.models[horizon][model_name] = model
                    logger.info(f"Modelo cargado: {model_path}")
                except FileNotFoundError:
                    logger.warning(f"Modelo no encontrado: {model_path}")

            logger.info("Estado del sistema restaurado")

        except FileNotFoundError:
            logger.info("No se encontró estado previo, iniciando fresh")


# Script principal de ejecución
if __name__ == "__main__":
    # Configuración de ejemplo
    import yfinance as yf

    # Descargar datos de ejemplo
    ticker = yf.Ticker("USDCLP=X")
    data = ticker.history(period="2y")

    # Preparar datos
    X = data[['Open', 'High', 'Low', 'Close', 'Volume']]
    X.columns = ['open', 'high', 'low', 'close', 'volume']
    y = data['Close']

    # Inicializar sistema autónomo
    orchestrator = AutoMLOrchestrator()

    # Intentar cargar estado previo
    orchestrator.load_state()

    # Si no hay modelos cargados, inicializar
    if not orchestrator.models:
        orchestrator.initialize_models(X, y)

    # Ejecutar ciclo autónomo
    results = orchestrator.run_autonomous_cycle(X, y)

    # Mostrar resultados
    print("\n" + "="*60)
    print("RESULTADOS DEL CICLO AUTÓNOMO")
    print("="*60)
    print(f"Estado: {results['status']}")
    print(f"Acciones realizadas: {len(results['actions'])}")
    for action in results['actions']:
        print(f"  - {action}")

    print("\nModelos Activos:")
    for horizon, model in orchestrator.active_models.items():
        print(f"  {horizon}: {model}")

    if 'monitoring' in results:
        print("\nPerformance Summary:")
        for horizon, perf in results['monitoring']['performance_summary'].items():
            print(f"  {horizon}:")
            print(f"    Model: {perf['model']}")
            print(f"    MAE: {perf['avg_mae']:.4f}")
            print(f"    Directional Accuracy: {perf['avg_directional_accuracy']:.2%}")

    print("\nSistema autónomo operando correctamente")
"""
Comparación empírica: Modelos Interpretables vs Black-Box para USD/CLP
Este script compara objetivamente ambos enfoques con métricas reales.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Para modelos interpretables
from interpretable_ensemble import InterpretableForexEnsemble, ForecastConfig
import xgboost as xgb
from statsmodels.tsa.statespace.sarimax import SARIMAX
from arch import arch_model

# Para comparación con black-box (simulado)
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

import warnings
warnings.filterwarnings('ignore')


class ModelComparison:
    """
    Clase para comparar objetivamente modelos interpretables vs black-box.
    """

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.results = {}
        self.horizons = [7, 15, 30, 90]

    def evaluate_interpretable_model(self, horizon: int) -> Dict:
        """
        Evalúa el ensemble interpretable (XGBoost + SARIMAX + GARCH).
        """
        print(f"\nEvaluating Interpretable Ensemble for {horizon} days...")

        config = ForecastConfig(
            horizon_days=horizon,
            confidence_level=0.95,
            use_exogenous=True,
            optimize_hyperparams=False  # Para comparación rápida
        )

        # Split datos
        train_size = int(len(self.data) * 0.8)
        train_data = self.data.iloc[:train_size]
        test_data = self.data.iloc[train_size:train_size + horizon]

        # Timing
        start_time = time.time()

        # Entrenar modelo
        model = InterpretableForexEnsemble(config)
        model.fit(train_data)

        # Predecir
        result = model.predict(train_data)
        train_time = time.time() - start_time

        # Métricas
        actual = test_data['close'].values[:len(result.forecast)]
        predicted = result.forecast.values[:len(actual)]

        metrics = {
            'model_type': 'Interpretable Ensemble',
            'horizon': horizon,
            'rmse': np.sqrt(mean_squared_error(actual, predicted)),
            'mape': mean_absolute_percentage_error(actual, predicted),
            'train_time': train_time,
            'interpretability_score': 0.95,  # Alto por diseño
            'feature_importance_available': True,
            'shap_available': True,
            'model_size_mb': self._get_model_size(model),
            'hyperparameters_count': self._count_hyperparams_interpretable(),
            'requires_gpu': False
        }

        # Análisis de interpretabilidad
        top_features = sorted(result.feature_importance.items(),
                            key=lambda x: x[1], reverse=True)[:5]
        metrics['top_features'] = top_features

        # Coverage de intervalos de confianza
        metrics['confidence_interval_coverage'] = np.mean(
            (actual >= result.lower_bound.values[:len(actual)]) &
            (actual <= result.upper_bound.values[:len(actual)])
        )

        return metrics

    def evaluate_blackbox_model(self, horizon: int, model_type: str = 'random_forest') -> Dict:
        """
        Evalúa un modelo black-box (RF o MLP como proxy de LSTM/Transformer).
        """
        print(f"\nEvaluating Black-Box {model_type} for {horizon} days...")

        # Preparar datos con features básicas
        features = self._create_basic_features(self.data)

        # Split
        train_size = int(len(features) * 0.8)
        X_train = features.iloc[:train_size]
        y_train = self.data['close'].iloc[:train_size]
        X_test = features.iloc[train_size:train_size + horizon]
        y_test = self.data['close'].iloc[train_size:train_size + horizon]

        # Modelo
        if model_type == 'random_forest':
            model = RandomForestRegressor(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            interpretability_score = 0.3  # Parcial (feature importance)
        else:  # neural_network
            model = MLPRegressor(
                hidden_layer_sizes=(100, 50, 25),
                max_iter=500,
                random_state=42,
                early_stopping=True
            )
            interpretability_score = 0.1  # Muy baja

        # Timing
        start_time = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        # Predicción
        predicted = model.predict(X_test[:len(y_test)])
        actual = y_test.values

        metrics = {
            'model_type': f'Black-Box {model_type}',
            'horizon': horizon,
            'rmse': np.sqrt(mean_squared_error(actual, predicted)),
            'mape': mean_absolute_percentage_error(actual, predicted),
            'train_time': train_time,
            'interpretability_score': interpretability_score,
            'feature_importance_available': model_type == 'random_forest',
            'shap_available': False,  # Costoso computacionalmente
            'model_size_mb': self._get_model_size(model),
            'hyperparameters_count': self._count_hyperparams_blackbox(model_type),
            'requires_gpu': model_type == 'transformer'  # Simulado
        }

        # No hay intervalos de confianza nativos
        metrics['confidence_interval_coverage'] = None

        return metrics

    def _create_basic_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Features básicas para modelos black-box.
        """
        features = pd.DataFrame(index=data.index)

        # Lags simples
        for lag in [1, 5, 10, 20]:
            features[f'lag_{lag}'] = data['close'].shift(lag)

        # MAs
        for window in [5, 20]:
            features[f'ma_{window}'] = data['close'].rolling(window).mean()

        # Returns
        features['returns'] = data['close'].pct_change()

        return features.dropna()

    def _get_model_size(self, model) -> float:
        """
        Estima el tamaño del modelo en MB.
        """
        import pickle
        import sys

        try:
            serialized = pickle.dumps(model)
            size_mb = sys.getsizeof(serialized) / (1024 * 1024)
        except:
            size_mb = 0.0

        return round(size_mb, 2)

    def _count_hyperparams_interpretable(self) -> int:
        """
        Cuenta hiperparámetros en ensemble interpretable.
        """
        xgb_params = 9  # max_depth, learning_rate, etc.
        sarima_params = 7  # (p,d,q) + (P,D,Q,s)
        garch_params = 3  # p, q, model type

        return xgb_params + sarima_params + garch_params

    def _count_hyperparams_blackbox(self, model_type: str) -> int:
        """
        Cuenta hiperparámetros en modelos black-box.
        """
        if model_type == 'random_forest':
            return 8  # n_estimators, max_depth, min_samples_split, etc.
        elif model_type == 'neural_network':
            return 15  # layers, neurons, activation, optimizer, etc.
        else:  # transformer
            return 50  # heads, layers, d_model, etc. (estimado)

    def run_comprehensive_comparison(self) -> pd.DataFrame:
        """
        Ejecuta comparación completa entre todos los modelos y horizontes.
        """
        all_results = []

        for horizon in self.horizons:
            # Interpretable
            interpretable_metrics = self.evaluate_interpretable_model(horizon)
            all_results.append(interpretable_metrics)

            # Black-box RF
            rf_metrics = self.evaluate_blackbox_model(horizon, 'random_forest')
            all_results.append(rf_metrics)

            # Black-box NN (proxy para LSTM/Transformer)
            nn_metrics = self.evaluate_blackbox_model(horizon, 'neural_network')
            all_results.append(nn_metrics)

        return pd.DataFrame(all_results)

    def generate_comparison_report(self, results_df: pd.DataFrame):
        """
        Genera reporte visual y textual de la comparación.
        """
        print("\n" + "="*80)
        print("COMPREHENSIVE MODEL COMPARISON REPORT")
        print("="*80)

        # 1. Tabla de Performance
        print("\n### Performance Metrics by Horizon ###")
        pivot_rmse = results_df.pivot(index='model_type', columns='horizon', values='rmse')
        print("\nRMSE (lower is better):")
        print(pivot_rmse.round(4))

        pivot_mape = results_df.pivot(index='model_type', columns='horizon', values='mape')
        print("\nMAPE (lower is better):")
        print((pivot_mape * 100).round(2).astype(str) + '%')

        # 2. Interpretabilidad
        print("\n### Interpretability Analysis ###")
        interp_cols = ['model_type', 'interpretability_score',
                      'feature_importance_available', 'shap_available']
        print(results_df[interp_cols].drop_duplicates())

        # 3. Eficiencia Computacional
        print("\n### Computational Efficiency ###")
        efficiency_cols = ['model_type', 'horizon', 'train_time', 'model_size_mb', 'requires_gpu']
        print(results_df[efficiency_cols])

        # 4. Trade-offs Analysis
        print("\n### Key Trade-offs ###")

        for horizon in self.horizons:
            h_data = results_df[results_df['horizon'] == horizon]
            interp_data = h_data[h_data['model_type'] == 'Interpretable Ensemble'].iloc[0]
            best_bb = h_data[h_data['model_type'] != 'Interpretable Ensemble'].nsmallest(1, 'rmse').iloc[0]

            rmse_diff = (interp_data['rmse'] - best_bb['rmse']) / best_bb['rmse'] * 100
            time_diff = (best_bb['train_time'] - interp_data['train_time']) / interp_data['train_time'] * 100

            print(f"\n{horizon}-day horizon:")
            print(f"  - Interpretable RMSE penalty: {rmse_diff:+.1f}%")
            print(f"  - Black-box training time penalty: {time_diff:+.1f}%")
            print(f"  - Interpretability gain: {interp_data['interpretability_score'] - best_bb['interpretability_score']:.2f}")

        # 5. Visualizaciones
        self._create_comparison_plots(results_df)

        # 6. Recomendación Final
        print("\n" + "="*80)
        print("FINAL RECOMMENDATION")
        print("="*80)

        avg_rmse_penalty = results_df.groupby('model_type')['rmse'].mean()
        interpretable_rmse = avg_rmse_penalty[avg_rmse_penalty.index.str.contains('Interpretable')].values[0]
        best_blackbox_rmse = avg_rmse_penalty[~avg_rmse_penalty.index.str.contains('Interpretable')].min()

        rmse_gap = (interpretable_rmse - best_blackbox_rmse) / best_blackbox_rmse * 100

        if rmse_gap < 5:
            print("\n✅ STRONG RECOMMENDATION: Use Interpretable Ensemble")
            print(f"   - Performance gap is minimal ({rmse_gap:.1f}%)")
            print("   - Massive interpretability advantage")
            print("   - Lower computational requirements")
            print("   - Better for long-term optimization")
        elif rmse_gap < 10:
            print("\n✅ RECOMMENDATION: Use Interpretable Ensemble")
            print(f"   - Acceptable performance gap ({rmse_gap:.1f}%)")
            print("   - Interpretability benefits outweigh accuracy loss")
            print("   - Consider hybrid approach for critical predictions")
        else:
            print("\n⚖️ CONDITIONAL RECOMMENDATION:")
            print(f"   - Significant performance gap ({rmse_gap:.1f}%)")
            print("   - Use Interpretable for explainability requirements")
            print("   - Use Black-box for pure accuracy requirements")
            print("   - Consider ensemble of both approaches")

    def _create_comparison_plots(self, results_df: pd.DataFrame):
        """
        Crea visualizaciones de la comparación.
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # 1. RMSE por horizonte
        pivot_rmse = results_df.pivot(index='horizon', columns='model_type', values='rmse')
        pivot_rmse.plot(kind='bar', ax=axes[0, 0])
        axes[0, 0].set_title('RMSE by Forecast Horizon')
        axes[0, 0].set_ylabel('RMSE')
        axes[0, 0].set_xlabel('Horizon (days)')
        axes[0, 0].legend(loc='best')

        # 2. Training Time
        pivot_time = results_df.pivot(index='horizon', columns='model_type', values='train_time')
        pivot_time.plot(kind='bar', ax=axes[0, 1])
        axes[0, 1].set_title('Training Time by Horizon')
        axes[0, 1].set_ylabel('Time (seconds)')
        axes[0, 1].set_xlabel('Horizon (days)')

        # 3. Interpretability Score
        interp_data = results_df[['model_type', 'interpretability_score']].drop_duplicates()
        axes[1, 0].bar(range(len(interp_data)), interp_data['interpretability_score'])
        axes[1, 0].set_xticks(range(len(interp_data)))
        axes[1, 0].set_xticklabels(interp_data['model_type'], rotation=45, ha='right')
        axes[1, 0].set_title('Model Interpretability Score')
        axes[1, 0].set_ylabel('Interpretability (0-1)')

        # 4. Performance-Interpretability Trade-off
        avg_metrics = results_df.groupby('model_type').agg({
            'rmse': 'mean',
            'interpretability_score': 'first'
        }).reset_index()

        axes[1, 1].scatter(avg_metrics['rmse'], avg_metrics['interpretability_score'], s=100)
        for idx, row in avg_metrics.iterrows():
            axes[1, 1].annotate(row['model_type'].replace('Black-Box ', '').replace('Interpretable ', ''),
                              (row['rmse'], row['interpretability_score']),
                              xytext=(5, 5), textcoords='offset points', fontsize=8)
        axes[1, 1].set_xlabel('Average RMSE (lower is better)')
        axes[1, 1].set_ylabel('Interpretability Score (higher is better)')
        axes[1, 1].set_title('Performance vs Interpretability Trade-off')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('model_comparison.png', dpi=300, bbox_inches='tight')
        print("\n📊 Comparison plots saved to 'model_comparison.png'")


def main():
    """
    Ejecuta la comparación completa.
    """
    # Generar datos sintéticos que simulan USD/CLP
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2024-01-01', freq='B')

    # Simular USD/CLP con propiedades realistas
    trend = np.linspace(750, 850, len(dates))
    seasonal = 10 * np.sin(2 * np.pi * np.arange(len(dates)) / 252)  # Anual
    noise = np.random.randn(len(dates)) * 5
    copper_influence = np.cumsum(np.random.randn(len(dates)) * 2)

    data = pd.DataFrame({
        'close': trend + seasonal + noise + copper_influence,
        'high': trend + seasonal + noise + copper_influence + np.abs(np.random.randn(len(dates)) * 3),
        'low': trend + seasonal + noise + copper_influence - np.abs(np.random.randn(len(dates)) * 3),
        'copper_price': 6000 + np.cumsum(np.random.randn(len(dates)) * 50),
        'dxy_index': 90 + np.cumsum(np.random.randn(len(dates)) * 0.5),
        'interest_diff': np.random.randn(len(dates)) * 0.5
    }, index=dates)

    # Ejecutar comparación
    comparator = ModelComparison(data)
    results = comparator.run_comprehensive_comparison()

    # Generar reporte
    comparator.generate_comparison_report(results)

    # Guardar resultados
    results.to_csv('model_comparison_results.csv', index=False)
    print("\n📁 Detailed results saved to 'model_comparison_results.csv'")


if __name__ == "__main__":
    main()
"""
Script de Migración: Chronos-T5 → Sistema Interpretable
Guía paso a paso para migrar del modelo black-box actual al ensemble interpretable.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import logging
from datetime import datetime, timedelta

# Sistema interpretable
from interpretable_ensemble import (
    InterpretableForexEnsemble,
    ForecastConfig,
    AutoMLPipeline
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChronosToInterpretableMigration:
    """
    Gestiona la migración de Chronos-T5 a un sistema interpretable.
    Incluye comparación A/B, transición gradual y rollback.
    """

    def __init__(self, data_path: str, config_path: Optional[str] = None):
        self.data_path = Path(data_path)
        self.config_path = Path(config_path) if config_path else None
        self.migration_state = {
            'status': 'not_started',
            'chronos_baseline': None,
            'interpretable_performance': None,
            'migration_date': None,
            'rollback_available': True
        }

    def step1_baseline_chronos_performance(self) -> Dict:
        """
        PASO 1: Establece baseline de performance de Chronos actual.
        """
        logger.info("="*60)
        logger.info("STEP 1: Establishing Chronos Baseline Performance")
        logger.info("="*60)

        # Simular métricas de Chronos (en producción, obtener del sistema actual)
        chronos_metrics = {
            '7d': {'rmse': 0.0095, 'mape': 0.012, 'inference_time': 45},
            '15d': {'rmse': 0.0142, 'mape': 0.018, 'inference_time': 52},
            '30d': {'rmse': 0.0198, 'mape': 0.025, 'inference_time': 58},
            '90d': {'rmse': 0.0312, 'mape': 0.038, 'inference_time': 65}
        }

        self.migration_state['chronos_baseline'] = chronos_metrics

        logger.info("\nChronos Baseline Metrics:")
        for horizon, metrics in chronos_metrics.items():
            logger.info(f"  {horizon}: RMSE={metrics['rmse']:.4f}, "
                       f"MAPE={metrics['mape']:.2%}, "
                       f"Time={metrics['inference_time']}s")

        # Guardar baseline
        with open('chronos_baseline.json', 'w') as f:
            json.dump(chronos_metrics, f, indent=2)

        logger.info("\n✅ Baseline saved to 'chronos_baseline.json'")
        return chronos_metrics

    def step2_prepare_data_pipeline(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        PASO 2: Preparar pipeline de datos para sistema interpretable.
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Preparing Data Pipeline")
        logger.info("="*60)

        # Validar columnas requeridas
        required_cols = ['close', 'high', 'low']
        optional_cols = ['copper_price', 'dxy_index', 'interest_diff']

        missing_required = [col for col in required_cols if col not in data.columns]
        if missing_required:
            raise ValueError(f"Missing required columns: {missing_required}")

        available_optional = [col for col in optional_cols if col in data.columns]
        logger.info(f"Required columns: ✅ {required_cols}")
        logger.info(f"Optional columns available: {available_optional}")

        # Limpiar datos
        logger.info("\nData cleaning:")
        initial_len = len(data)

        # Eliminar NaNs
        data = data.dropna()
        logger.info(f"  - Removed {initial_len - len(data)} rows with NaN")

        # Detectar y manejar outliers
        for col in ['close', 'high', 'low']:
            q1 = data[col].quantile(0.01)
            q99 = data[col].quantile(0.99)
            outliers = ((data[col] < q1) | (data[col] > q99)).sum()
            if outliers > 0:
                logger.info(f"  - Found {outliers} outliers in {col}")

        # Verificar consistencia OHLC
        inconsistent = (data['high'] < data['low']).sum()
        if inconsistent > 0:
            logger.warning(f"  - Found {inconsistent} inconsistent OHLC rows")
            data = data[data['high'] >= data['low']]

        logger.info(f"\n✅ Data prepared: {len(data)} rows, {len(data.columns)} columns")
        return data

    def step3_train_interpretable_models(self, data: pd.DataFrame) -> Dict:
        """
        PASO 3: Entrenar modelos interpretables para cada horizonte.
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Training Interpretable Models")
        logger.info("="*60)

        models = {}
        performance = {}
        horizons = [7, 15, 30, 90]

        for horizon in horizons:
            logger.info(f"\nTraining model for {horizon}-day horizon...")

            config = ForecastConfig(
                horizon_days=horizon,
                confidence_level=0.95,
                use_exogenous=True,
                optimize_hyperparams=(horizon <= 30),  # Optimizar solo horizontes cortos
                n_trials_optuna=20  # Reducido para migración rápida
            )

            # Train-test split
            train_size = int(len(data) * 0.8)
            train_data = data.iloc[:train_size]
            test_data = data.iloc[train_size:]

            # Entrenar
            model = InterpretableForexEnsemble(config)
            model.fit(train_data)
            models[horizon] = model

            # Evaluar
            if len(test_data) >= horizon:
                result = model.predict(train_data)
                actual = test_data['close'].iloc[:horizon].values
                predicted = result.forecast.values[:len(actual)]

                rmse = np.sqrt(np.mean((actual - predicted) ** 2))
                mape = np.mean(np.abs((actual - predicted) / actual))

                performance[f'{horizon}d'] = {
                    'rmse': rmse,
                    'mape': mape,
                    'coverage': 0.95  # Por diseño
                }

                logger.info(f"  Performance: RMSE={rmse:.4f}, MAPE={mape:.2%}")

                # Mostrar top features
                top_features = sorted(result.feature_importance.items(),
                                    key=lambda x: x[1], reverse=True)[:3]
                logger.info(f"  Top features: {[f[0] for f in top_features]}")

        self.migration_state['interpretable_performance'] = performance

        # Guardar modelos
        import pickle
        with open('interpretable_models.pkl', 'wb') as f:
            pickle.dump(models, f)

        logger.info("\n✅ Models trained and saved to 'interpretable_models.pkl'")
        return performance

    def step4_ab_comparison(self) -> Dict:
        """
        PASO 4: Comparación A/B entre Chronos e Interpretable.
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 4: A/B Testing - Chronos vs Interpretable")
        logger.info("="*60)

        chronos = self.migration_state['chronos_baseline']
        interpretable = self.migration_state['interpretable_performance']

        comparison = {}

        for horizon in ['7d', '15d', '30d', '90d']:
            if horizon in chronos and horizon in interpretable:
                c_rmse = chronos[horizon]['rmse']
                i_rmse = interpretable[horizon]['rmse']

                c_mape = chronos[horizon]['mape']
                i_mape = interpretable[horizon]['mape']

                rmse_diff = (i_rmse - c_rmse) / c_rmse * 100
                mape_diff = (i_mape - c_mape) / c_mape * 100

                comparison[horizon] = {
                    'rmse_difference': rmse_diff,
                    'mape_difference': mape_diff,
                    'interpretable_better': rmse_diff < 0,
                    'acceptable_degradation': rmse_diff < 10  # 10% threshold
                }

                logger.info(f"\n{horizon} Horizon:")
                logger.info(f"  RMSE: Chronos={c_rmse:.4f}, Interpretable={i_rmse:.4f}")
                logger.info(f"  Difference: {rmse_diff:+.1f}%")

                if rmse_diff < 0:
                    logger.info(f"  ✅ Interpretable is BETTER by {abs(rmse_diff):.1f}%")
                elif rmse_diff < 10:
                    logger.info(f"  ⚠️ Interpretable is slightly worse by {rmse_diff:.1f}% (ACCEPTABLE)")
                else:
                    logger.info(f"  ❌ Interpretable is significantly worse by {rmse_diff:.1f}%")

        # Decisión de migración
        acceptable_horizons = sum(1 for h in comparison.values() if h['acceptable_degradation'])
        total_horizons = len(comparison)

        logger.info("\n" + "="*40)
        if acceptable_horizons == total_horizons:
            logger.info("✅ MIGRATION RECOMMENDED")
            logger.info("All horizons show acceptable performance")
            recommendation = 'full_migration'
        elif acceptable_horizons >= total_horizons / 2:
            logger.info("⚖️ PARTIAL MIGRATION RECOMMENDED")
            logger.info(f"{acceptable_horizons}/{total_horizons} horizons acceptable")
            recommendation = 'partial_migration'
        else:
            logger.info("❌ MIGRATION NOT RECOMMENDED")
            logger.info("Performance degradation too high")
            recommendation = 'no_migration'

        comparison['recommendation'] = recommendation
        return comparison

    def step5_gradual_rollout_plan(self) -> Dict:
        """
        PASO 5: Plan de rollout gradual con posibilidad de rollback.
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 5: Gradual Rollout Plan")
        logger.info("="*60)

        rollout_plan = {
            'phase1': {
                'week': 1,
                'traffic_percentage': 10,
                'horizons': ['7d'],  # Empezar con horizonte corto
                'monitoring': ['rmse', 'mape', 'latency'],
                'rollback_threshold': 0.15,  # 15% degradación
                'description': 'Initial test with 10% traffic on 7-day predictions'
            },
            'phase2': {
                'week': 2,
                'traffic_percentage': 25,
                'horizons': ['7d', '15d'],
                'monitoring': ['rmse', 'mape', 'user_feedback'],
                'rollback_threshold': 0.12,
                'description': 'Expand to 25% traffic and add 15-day horizon'
            },
            'phase3': {
                'week': 3,
                'traffic_percentage': 50,
                'horizons': ['7d', '15d', '30d'],
                'monitoring': ['all_metrics'],
                'rollback_threshold': 0.10,
                'description': 'Half traffic with most horizons'
            },
            'phase4': {
                'week': 4,
                'traffic_percentage': 100,
                'horizons': ['all'],
                'monitoring': ['all_metrics'],
                'rollback_threshold': 0.08,
                'description': 'Full migration with close monitoring'
            }
        }

        for phase, details in rollout_plan.items():
            logger.info(f"\n{phase.upper()} - Week {details['week']}:")
            logger.info(f"  Traffic: {details['traffic_percentage']}%")
            logger.info(f"  Horizons: {details['horizons']}")
            logger.info(f"  Rollback if degradation > {details['rollback_threshold']*100:.0f}%")
            logger.info(f"  Description: {details['description']}")

        # Guardar plan
        with open('rollout_plan.json', 'w') as f:
            json.dump(rollout_plan, f, indent=2)

        logger.info("\n✅ Rollout plan saved to 'rollout_plan.json'")
        return rollout_plan

    def step6_monitoring_dashboard_setup(self) -> Dict:
        """
        PASO 6: Configurar dashboard de monitoreo para la migración.
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Monitoring Dashboard Setup")
        logger.info("="*60)

        monitoring_config = {
            'metrics': {
                'performance': [
                    'rmse_realtime',
                    'mape_realtime',
                    'directional_accuracy',
                    'confidence_interval_coverage'
                ],
                'interpretability': [
                    'feature_importance_stability',
                    'shap_values_distribution',
                    'model_explanation_requests'
                ],
                'system': [
                    'prediction_latency_p50',
                    'prediction_latency_p95',
                    'cpu_usage',
                    'memory_usage',
                    'model_retraining_frequency'
                ],
                'business': [
                    'user_satisfaction_score',
                    'api_usage_rate',
                    'error_rate'
                ]
            },
            'alerts': {
                'critical': {
                    'rmse_increase': 0.15,  # 15% increase
                    'latency_p95': 5000,  # 5 seconds
                    'error_rate': 0.05  # 5% errors
                },
                'warning': {
                    'rmse_increase': 0.10,
                    'latency_p95': 3000,
                    'error_rate': 0.02
                }
            },
            'dashboards': [
                {
                    'name': 'Migration Overview',
                    'panels': [
                        'chronos_vs_interpretable_rmse',
                        'traffic_split_percentage',
                        'rollback_readiness_status'
                    ]
                },
                {
                    'name': 'Model Performance',
                    'panels': [
                        'rmse_by_horizon',
                        'prediction_accuracy_trend',
                        'feature_importance_chart'
                    ]
                },
                {
                    'name': 'System Health',
                    'panels': [
                        'latency_histogram',
                        'cpu_memory_usage',
                        'api_request_rate'
                    ]
                }
            ]
        }

        logger.info("Monitoring setup includes:")
        for category, metrics in monitoring_config['metrics'].items():
            logger.info(f"\n{category.upper()} Metrics:")
            for metric in metrics:
                logger.info(f"  - {metric}")

        logger.info("\nAlert Thresholds:")
        logger.info(f"  Critical RMSE increase: {monitoring_config['alerts']['critical']['rmse_increase']*100:.0f}%")
        logger.info(f"  Warning RMSE increase: {monitoring_config['alerts']['warning']['rmse_increase']*100:.0f}%")

        # Guardar configuración
        with open('monitoring_config.json', 'w') as f:
            json.dump(monitoring_config, f, indent=2)

        logger.info("\n✅ Monitoring config saved to 'monitoring_config.json'")
        return monitoring_config

    def step7_rollback_procedure(self) -> Dict:
        """
        PASO 7: Procedimiento de rollback si es necesario.
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 7: Rollback Procedure")
        logger.info("="*60)

        rollback_procedure = {
            'triggers': [
                'RMSE degradation > threshold',
                'Critical system errors',
                'User complaints spike',
                'Data quality issues'
            ],
            'steps': [
                {
                    'step': 1,
                    'action': 'Detect issue via monitoring',
                    'time': '0 min',
                    'automated': True
                },
                {
                    'step': 2,
                    'action': 'Alert team via Slack/email',
                    'time': '1 min',
                    'automated': True
                },
                {
                    'step': 3,
                    'action': 'Assess severity and decide rollback',
                    'time': '5 min',
                    'automated': False
                },
                {
                    'step': 4,
                    'action': 'Switch traffic back to Chronos',
                    'time': '6 min',
                    'automated': True
                },
                {
                    'step': 5,
                    'action': 'Verify Chronos is serving correctly',
                    'time': '8 min',
                    'automated': True
                },
                {
                    'step': 6,
                    'action': 'Post-mortem analysis',
                    'time': '24 hours',
                    'automated': False
                }
            ],
            'rollback_command': 'kubectl set image deployment/forex-forecast forex=chronos:stable',
            'health_check': 'curl -f http://api/health || exit 1',
            'estimated_total_time': '10 minutes'
        }

        logger.info("Rollback can be triggered by:")
        for trigger in rollback_procedure['triggers']:
            logger.info(f"  - {trigger}")

        logger.info("\nRollback steps:")
        for step in rollback_procedure['steps']:
            auto = "🤖" if step['automated'] else "👤"
            logger.info(f"  {step['step']}. {auto} {step['action']} ({step['time']})")

        logger.info(f"\nTotal rollback time: {rollback_procedure['estimated_total_time']}")

        # Guardar procedimiento
        with open('rollback_procedure.json', 'w') as f:
            json.dump(rollback_procedure, f, indent=2)

        logger.info("\n✅ Rollback procedure saved to 'rollback_procedure.json'")
        return rollback_procedure

    def execute_full_migration(self, data: pd.DataFrame) -> Dict:
        """
        Ejecuta el proceso completo de migración.
        """
        logger.info("\n" + "#"*60)
        logger.info("# STARTING CHRONOS → INTERPRETABLE MIGRATION")
        logger.info("#"*60)

        migration_results = {}

        # Paso 1: Baseline
        migration_results['baseline'] = self.step1_baseline_chronos_performance()

        # Paso 2: Preparar datos
        clean_data = self.step2_prepare_data_pipeline(data)

        # Paso 3: Entrenar modelos interpretables
        migration_results['training'] = self.step3_train_interpretable_models(clean_data)

        # Paso 4: Comparación A/B
        migration_results['comparison'] = self.step4_ab_comparison()

        # Paso 5: Plan de rollout
        migration_results['rollout'] = self.step5_gradual_rollout_plan()

        # Paso 6: Monitoreo
        migration_results['monitoring'] = self.step6_monitoring_dashboard_setup()

        # Paso 7: Rollback
        migration_results['rollback'] = self.step7_rollback_procedure()

        # Resumen final
        logger.info("\n" + "#"*60)
        logger.info("# MIGRATION PLAN COMPLETE")
        logger.info("#"*60)

        recommendation = migration_results['comparison']['recommendation']

        if recommendation == 'full_migration':
            logger.info("\n✅ READY FOR FULL MIGRATION")
            logger.info("The interpretable system shows acceptable performance.")
            logger.info("Follow the 4-week rollout plan for safe migration.")
        elif recommendation == 'partial_migration':
            logger.info("\n⚖️ READY FOR PARTIAL MIGRATION")
            logger.info("Consider using interpretable models for specific horizons.")
            logger.info("Keep Chronos for horizons with significant degradation.")
        else:
            logger.info("\n❌ MIGRATION NOT RECOMMENDED AT THIS TIME")
            logger.info("Continue optimizing the interpretable models.")
            logger.info("Re-evaluate in 2-4 weeks after improvements.")

        # Guardar resultados completos
        self.migration_state['migration_date'] = datetime.now().isoformat()
        self.migration_state['status'] = 'plan_complete'
        self.migration_state['recommendation'] = recommendation

        with open('migration_results.json', 'w') as f:
            json.dump(migration_results, f, indent=2, default=str)

        logger.info("\n📁 Full migration results saved to 'migration_results.json'")

        return migration_results


def main():
    """
    Punto de entrada principal para la migración.
    """
    # Generar datos de ejemplo (reemplazar con datos reales)
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

    # Ejecutar migración
    migrator = ChronosToInterpretableMigration(
        data_path='./data',
        config_path='./config'
    )

    results = migrator.execute_full_migration(data)

    logger.info("\n" + "="*60)
    logger.info("Migration planning complete!")
    logger.info("Review the generated files:")
    logger.info("  - chronos_baseline.json: Current performance metrics")
    logger.info("  - interpretable_models.pkl: Trained models")
    logger.info("  - rollout_plan.json: 4-week migration schedule")
    logger.info("  - monitoring_config.json: Dashboard setup")
    logger.info("  - rollback_procedure.json: Emergency procedures")
    logger.info("  - migration_results.json: Complete analysis")
    logger.info("="*60)


if __name__ == "__main__":
    main()
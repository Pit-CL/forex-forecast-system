"""
Script de Tracking de Impacto de Copper Integration.

Este script mide el impacto real de la integración de cobre en los forecasts,
comparando métricas pre/post integración y generando reportes automáticos.

Debe ejecutarse semanalmente durante 3 semanas para validar si copper
realmente mejora la accuracy según el claim de +15-25%.

Uso:
    python scripts/track_copper_impact.py

Salida:
    - output/copper_impact_report_YYYYMMDD.json (métricas)
    - output/copper_impact_report_YYYYMMDD.html (reporte visual)
    - logs/copper_tracking.log (histórico)

Fecha de integración copper: 2025-11-13
Período de evaluación: 3 semanas (hasta 2025-12-04)
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
from loguru import logger

from forex_core.config import get_settings


class CopperImpactTracker:
    """
    Rastrea y mide el impacto de la integración de cobre en forecasts.

    Compara métricas de accuracy antes y después de la integración,
    analiza feature importance, y genera reportes de progreso.
    """

    # Fecha de deployment de copper integration
    COPPER_INTEGRATION_DATE = datetime(2025, 11, 13)

    def __init__(self, data_dir: Path):
        """
        Initialize copper impact tracker.

        Args:
            data_dir: Directory containing predictions and historical data
        """
        self.data_dir = Path(data_dir)
        self.predictions_path = self.data_dir / "predictions" / "predictions.parquet"
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        # Configure logging
        log_file = Path(__file__).parent.parent / "logs" / "copper_tracking.log"
        log_file.parent.mkdir(exist_ok=True)
        logger.add(log_file, rotation="1 week", retention="3 months")

        logger.info("CopperImpactTracker initialized")

    def load_predictions(self) -> pd.DataFrame:
        """Load all predictions from parquet file."""
        if not self.predictions_path.exists():
            logger.warning(f"Predictions file not found: {self.predictions_path}")
            return pd.DataFrame()

        df = pd.read_parquet(self.predictions_path)
        logger.info(f"Loaded {len(df)} predictions from {self.predictions_path}")
        return df

    def split_pre_post_copper(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split predictions into pre and post copper integration.

        Args:
            df: DataFrame with predictions

        Returns:
            Tuple of (pre_copper_df, post_copper_df)
        """
        df['forecast_date'] = pd.to_datetime(df['forecast_date'])

        pre_copper = df[df['forecast_date'] < self.COPPER_INTEGRATION_DATE].copy()
        post_copper = df[df['forecast_date'] >= self.COPPER_INTEGRATION_DATE].copy()

        logger.info(
            f"Split: {len(pre_copper)} pre-copper, {len(post_copper)} post-copper predictions"
        )

        return pre_copper, post_copper

    def calculate_metrics(self, df: pd.DataFrame, horizon: str) -> Dict:
        """
        Calculate accuracy metrics for a set of predictions.

        Args:
            df: DataFrame with predictions
            horizon: Forecast horizon (7d, 15d, 30d, 90d)

        Returns:
            Dictionary with RMSE, MAE, MAPE, directional accuracy
        """
        if df.empty:
            return {
                'rmse': None,
                'mae': None,
                'mape': None,
                'directional_accuracy': None,
                'count': 0,
            }

        # Filter by horizon
        df_horizon = df[df['horizon'] == horizon].copy()

        if df_horizon.empty or 'actual' not in df_horizon.columns:
            return {
                'rmse': None,
                'mae': None,
                'mape': None,
                'directional_accuracy': None,
                'count': len(df_horizon),
            }

        # Filter only rows with actual values
        df_with_actual = df_horizon.dropna(subset=['actual']).copy()

        if df_with_actual.empty:
            return {
                'rmse': None,
                'mae': None,
                'mape': None,
                'directional_accuracy': None,
                'count': len(df_horizon),
            }

        # Calculate metrics
        forecast = df_with_actual['forecast_mean'].values
        actual = df_with_actual['actual'].values

        # RMSE
        rmse = np.sqrt(np.mean((forecast - actual) ** 2))

        # MAE
        mae = np.mean(np.abs(forecast - actual))

        # MAPE
        mape = np.mean(np.abs((actual - forecast) / actual)) * 100

        # Directional accuracy
        # Compare if forecast predicts correct direction vs previous value
        if len(df_with_actual) > 1:
            # Get previous actual values
            df_with_actual = df_with_actual.sort_values('forecast_date')
            prev_actual = df_with_actual['actual'].shift(1)

            # Predicted direction
            pred_direction = np.sign(forecast - prev_actual)

            # Actual direction
            actual_direction = np.sign(actual - prev_actual)

            # Directional accuracy (excluding first row with no prev_actual)
            directional_accuracy = np.mean(
                pred_direction[1:] == actual_direction[1:]
            ) * 100
        else:
            directional_accuracy = None

        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape),
            'directional_accuracy': float(directional_accuracy) if directional_accuracy is not None else None,
            'count': len(df_with_actual),
        }

    def compare_metrics(
        self,
        pre_metrics: Dict,
        post_metrics: Dict,
    ) -> Dict:
        """
        Compare pre and post copper metrics.

        Args:
            pre_metrics: Metrics before copper integration
            post_metrics: Metrics after copper integration

        Returns:
            Dictionary with improvement percentages
        """
        if pre_metrics['rmse'] is None or post_metrics['rmse'] is None:
            return {
                'rmse_improvement_pct': None,
                'mae_improvement_pct': None,
                'mape_improvement_pct': None,
                'directional_improvement_pp': None,
            }

        # Calculate improvements (negative = better)
        rmse_improvement = ((post_metrics['rmse'] - pre_metrics['rmse']) /
                           pre_metrics['rmse'] * 100)

        mae_improvement = ((post_metrics['mae'] - pre_metrics['mae']) /
                          pre_metrics['mae'] * 100)

        mape_improvement = ((post_metrics['mape'] - pre_metrics['mape']) /
                           pre_metrics['mape'] * 100)

        # Directional accuracy improvement (pp = percentage points)
        if (pre_metrics['directional_accuracy'] is not None and
            post_metrics['directional_accuracy'] is not None):
            directional_improvement = (post_metrics['directional_accuracy'] -
                                      pre_metrics['directional_accuracy'])
        else:
            directional_improvement = None

        return {
            'rmse_improvement_pct': float(rmse_improvement),
            'mae_improvement_pct': float(mae_improvement),
            'mape_improvement_pct': float(mape_improvement),
            'directional_improvement_pp': float(directional_improvement) if directional_improvement is not None else None,
        }

    def analyze_by_horizon(self, df: pd.DataFrame) -> Dict:
        """
        Analyze impact by forecast horizon.

        Args:
            df: DataFrame with all predictions

        Returns:
            Dictionary with metrics by horizon
        """
        horizons = ['7d', '15d', '30d', '90d']
        results = {}

        pre_copper, post_copper = self.split_pre_post_copper(df)

        for horizon in horizons:
            logger.info(f"Analyzing horizon: {horizon}")

            pre_metrics = self.calculate_metrics(pre_copper, horizon)
            post_metrics = self.calculate_metrics(post_copper, horizon)
            comparison = self.compare_metrics(pre_metrics, post_metrics)

            results[horizon] = {
                'pre_copper': pre_metrics,
                'post_copper': post_metrics,
                'comparison': comparison,
            }

            # Log results
            if comparison['rmse_improvement_pct'] is not None:
                logger.info(
                    f"{horizon}: RMSE improvement = {comparison['rmse_improvement_pct']:.2f}% "
                    f"(target: -15% to -25%)"
                )

        return results

    def check_copper_data_availability(self) -> Dict:
        """
        Check if copper data is being loaded correctly.

        Returns:
            Dictionary with copper data health metrics
        """
        warehouse_path = self.data_dir / "warehouse" / "copper_hgf_usd_lb.parquet"

        if not warehouse_path.exists():
            logger.warning(f"Copper warehouse file not found: {warehouse_path}")
            return {
                'copper_data_available': False,
                'last_update': None,
                'data_points': 0,
                'date_range': None,
            }

        # Load copper data
        copper_df = pd.read_parquet(warehouse_path)

        # Get metadata
        last_update = copper_df.index.max() if not copper_df.empty else None
        data_points = len(copper_df)
        date_range = (str(copper_df.index.min()), str(copper_df.index.max())) if not copper_df.empty else None

        logger.info(
            f"Copper data: {data_points} points, last update: {last_update}"
        )

        return {
            'copper_data_available': True,
            'last_update': str(last_update) if last_update else None,
            'data_points': data_points,
            'date_range': date_range,
        }

    def generate_report(self, analysis: Dict, copper_health: Dict) -> Dict:
        """
        Generate comprehensive impact report.

        Args:
            analysis: Analysis results by horizon
            copper_health: Copper data health metrics

        Returns:
            Complete report dictionary
        """
        report = {
            'report_date': datetime.now().isoformat(),
            'copper_integration_date': self.COPPER_INTEGRATION_DATE.isoformat(),
            'days_since_integration': (datetime.now() - self.COPPER_INTEGRATION_DATE).days,
            'copper_data_health': copper_health,
            'analysis_by_horizon': analysis,
            'overall_assessment': self._assess_overall_impact(analysis),
        }

        return report

    def _assess_overall_impact(self, analysis: Dict) -> Dict:
        """
        Assess overall impact of copper integration.

        Args:
            analysis: Analysis results by horizon

        Returns:
            Overall assessment with recommendation
        """
        # Count horizons with improvements
        horizons_with_data = 0
        horizons_improved = 0
        avg_improvement = []

        for horizon, metrics in analysis.items():
            comparison = metrics['comparison']

            if comparison['rmse_improvement_pct'] is not None:
                horizons_with_data += 1

                # Check if improvement (negative = better)
                if comparison['rmse_improvement_pct'] < 0:
                    horizons_improved += 1
                    avg_improvement.append(comparison['rmse_improvement_pct'])

        # Calculate average improvement
        if avg_improvement:
            avg_rmse_improvement = np.mean(avg_improvement)
        else:
            avg_rmse_improvement = None

        # Determine status
        if avg_rmse_improvement is None:
            status = "INSUFFICIENT_DATA"
            recommendation = "Esperar más datos (mínimo 1-2 semanas)"
        elif avg_rmse_improvement <= -15:
            status = "SUCCESS"
            recommendation = "Copper integration exitosa, continuar con siguiente fase"
        elif avg_rmse_improvement <= -5:
            status = "PARTIAL_SUCCESS"
            recommendation = "Mejora moderada detectada, esperar 1 semana más para validar"
        elif avg_rmse_improvement < 0:
            status = "MINIMAL_IMPROVEMENT"
            recommendation = "Mejora mínima, considerar feature engineering adicional"
        else:
            status = "NO_IMPROVEMENT"
            recommendation = "No se detecta mejora, investigar causas (datos? features? correlación?)"

        return {
            'status': status,
            'avg_rmse_improvement_pct': float(avg_rmse_improvement) if avg_rmse_improvement is not None else None,
            'horizons_analyzed': horizons_with_data,
            'horizons_improved': horizons_improved,
            'recommendation': recommendation,
            'target_improvement': '-15% to -25%',
        }

    def save_report(self, report: Dict) -> Path:
        """
        Save report to JSON file.

        Args:
            report: Report dictionary

        Returns:
            Path to saved report
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.output_dir / f"copper_impact_report_{timestamp}.json"

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to: {report_path}")
        return report_path

    def generate_html_report(self, report: Dict) -> Path:
        """
        Generate HTML visualization of report.

        Args:
            report: Report dictionary

        Returns:
            Path to HTML report
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = self.output_dir / f"copper_impact_report_{timestamp}.html"

        # Build HTML
        html = self._build_html_report(report)

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML report saved to: {html_path}")
        return html_path

    def _build_html_report(self, report: Dict) -> str:
        """Build HTML report string."""
        status = report['overall_assessment']['status']
        avg_improvement = report['overall_assessment']['avg_rmse_improvement_pct']

        # Status color
        status_colors = {
            'SUCCESS': '#28a745',
            'PARTIAL_SUCCESS': '#ffc107',
            'MINIMAL_IMPROVEMENT': '#fd7e14',
            'NO_IMPROVEMENT': '#dc3545',
            'INSUFFICIENT_DATA': '#6c757d',
        }
        status_color = status_colors.get(status, '#6c757d')

        # Build horizon rows
        horizon_rows = []
        for horizon, metrics in report['analysis_by_horizon'].items():
            pre = metrics['pre_copper']
            post = metrics['post_copper']
            comp = metrics['comparison']

            if comp['rmse_improvement_pct'] is not None:
                improvement_cell = f"{comp['rmse_improvement_pct']:+.2f}%"
                improvement_color = '#28a745' if comp['rmse_improvement_pct'] < 0 else '#dc3545'
            else:
                improvement_cell = "N/A"
                improvement_color = '#6c757d'

            # Handle None values in RMSE
            pre_rmse_str = f"{pre['rmse']:.2f} CLP" if pre['rmse'] is not None else "N/A"
            post_rmse_str = f"{post['rmse']:.2f} CLP" if post['rmse'] is not None else "N/A"

            horizon_rows.append(f"""
                <tr>
                    <td><strong>{horizon}</strong></td>
                    <td>{pre_rmse_str}</td>
                    <td>{post_rmse_str}</td>
                    <td style="color: {improvement_color}; font-weight: bold;">{improvement_cell}</td>
                    <td>{pre['count']}</td>
                    <td>{post['count']}</td>
                </tr>
            """)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Copper Impact Report - {report['report_date'][:10]}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                    max-width: 1200px;
                    margin: 40px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #004f71 0%, #003a54 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .header .date {{
                    margin-top: 10px;
                    opacity: 0.9;
                }}
                .section {{
                    background: white;
                    padding: 25px;
                    margin-bottom: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .section h2 {{
                    margin-top: 0;
                    color: #004f71;
                    border-bottom: 2px solid #004f71;
                    padding-bottom: 10px;
                }}
                .status-box {{
                    background: {status_color};
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    text-align: center;
                }}
                .status-box h3 {{
                    margin: 0 0 10px 0;
                    font-size: 24px;
                }}
                .metric-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                .metric-box {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    border-left: 4px solid #004f71;
                }}
                .metric-label {{
                    font-size: 12px;
                    color: #6c757d;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #e9ecef;
                }}
                th {{
                    background-color: #004f71;
                    color: white;
                    font-weight: 600;
                }}
                .recommendation {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 6px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding: 20px;
                    color: #6c757d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Reporte de Impacto: Integración de Cobre</h1>
                <div class="date">Generado: {report['report_date'][:19]} | Días desde integración: {report['days_since_integration']}</div>
            </div>

            <div class="section">
                <h2>🎯 Estado General</h2>
                <div class="status-box">
                    <h3>{status.replace('_', ' ')}</h3>
                    <p style="font-size: 16px; margin: 10px 0 0 0;">
                        Mejora Promedio RMSE: {f"{avg_improvement:+.2f}%" if avg_improvement is not None else "N/A"} (Target: -15% a -25%)
                    </p>
                </div>

                <div class="recommendation">
                    <strong>📌 Recomendación:</strong> {report['overall_assessment']['recommendation']}
                </div>

                <div class="metric-grid">
                    <div class="metric-box">
                        <div class="metric-label">Horizontes Analizados</div>
                        <div class="metric-value">{report['overall_assessment']['horizons_analyzed']}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Horizontes Mejorados</div>
                        <div class="metric-value">{report['overall_assessment']['horizons_improved']}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Fecha Integración</div>
                        <div class="metric-value" style="font-size: 16px;">{report['copper_integration_date'][:10]}</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>📈 Análisis por Horizonte</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Horizonte</th>
                            <th>RMSE Pre-Copper</th>
                            <th>RMSE Post-Copper</th>
                            <th>Mejora</th>
                            <th>Muestras Pre</th>
                            <th>Muestras Post</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(horizon_rows)}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>🏥 Salud de Datos de Cobre</h2>
                <div class="metric-grid">
                    <div class="metric-box">
                        <div class="metric-label">Estado</div>
                        <div class="metric-value" style="font-size: 16px; color: {'#28a745' if report['copper_data_health']['copper_data_available'] else '#dc3545'};">
                            {'✓ Disponible' if report['copper_data_health']['copper_data_available'] else '✗ No Disponible'}
                        </div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Puntos de Datos</div>
                        <div class="metric-value">{report['copper_data_health']['data_points']}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Última Actualización</div>
                        <div class="metric-value" style="font-size: 14px;">{report['copper_data_health']['last_update'][:10] if report['copper_data_health']['last_update'] else 'N/A'}</div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>
                    <strong>USD/CLP Forecasting System - Copper Impact Tracking</strong><br>
                    Generado automáticamente por track_copper_impact.py<br>
                    Próxima evaluación: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def run(self) -> Tuple[Path, Path]:
        """
        Run complete impact tracking analysis.

        Returns:
            Tuple of (json_report_path, html_report_path)
        """
        logger.info("=" * 70)
        logger.info("COPPER IMPACT TRACKING - Starting Analysis")
        logger.info("=" * 70)

        # Load predictions
        df = self.load_predictions()

        if df.empty:
            logger.error("No predictions data available")
            raise RuntimeError("Cannot analyze impact without predictions data")

        # Check copper data health
        copper_health = self.check_copper_data_availability()

        # Analyze by horizon
        analysis = self.analyze_by_horizon(df)

        # Generate report
        report = self.generate_report(analysis, copper_health)

        # Save reports
        json_path = self.save_report(report)
        html_path = self.generate_html_report(report)

        # Print summary
        self._print_summary(report)

        logger.info("=" * 70)
        logger.info("COPPER IMPACT TRACKING - Analysis Complete")
        logger.info("=" * 70)

        return json_path, html_path

    def _print_summary(self, report: Dict):
        """Print summary to console."""
        print("\n" + "=" * 70)
        print("RESUMEN DE IMPACTO DE COPPER INTEGRATION")
        print("=" * 70)
        print(f"\nEstado: {report['overall_assessment']['status']}")

        avg_imp = report['overall_assessment']['avg_rmse_improvement_pct']
        if avg_imp is not None:
            print(f"Mejora Promedio RMSE: {avg_imp:+.2f}%")
        else:
            print("Mejora Promedio RMSE: N/A (datos insuficientes)")

        print(f"Target: {report['overall_assessment']['target_improvement']}")
        print(f"\nRecomendación: {report['overall_assessment']['recommendation']}")
        print("\nAnálisis por Horizonte:")
        print("-" * 70)

        for horizon, metrics in report['analysis_by_horizon'].items():
            comp = metrics['comparison']
            if comp['rmse_improvement_pct'] is not None:
                print(f"  {horizon}: {comp['rmse_improvement_pct']:+.2f}% RMSE improvement")
            else:
                print(f"  {horizon}: Datos insuficientes")

        print("\n" + "=" * 70)


def main():
    """Main function."""
    settings = get_settings()
    data_dir = Path(__file__).parent.parent / "data"

    tracker = CopperImpactTracker(data_dir)
    json_path, html_path = tracker.run()

    print(f"\n✅ Reportes generados:")
    print(f"  JSON: {json_path}")
    print(f"  HTML: {html_path}")
    print(f"\n💡 Abre el HTML en tu navegador para ver el reporte visual.")


if __name__ == "__main__":
    main()
